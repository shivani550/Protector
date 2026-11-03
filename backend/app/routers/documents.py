import hashlib
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.db import get_db
from backend.app.models import Document, Patient, QueryLetter, User
from backend.app.schemas import DocumentOut, DocumentUploadResponse, SignedUrlResponse
from backend.app.auth import get_current_user
from backend.app.rbac import require_patient_access
from backend.app.storage import save_encrypted_file, generate_document_download_url
from backend.app.audit import log_audit
from backend.app.pipeline.jobs import enqueue_job

router = APIRouter(prefix="", tags=["documents"])


@router.get("/patients/{patient_id}/documents", response_model=List[DocumentOut])
async def list_patient_documents(
    patient_id: str,
    request: Request,
    current_user: User = Depends(require_patient_access),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Document)
        .where(Document.patient_id == patient_id)
        .order_by(Document.created_at.desc())
    )
    res = await db.execute(stmt)
    docs = res.scalars().all()

    client_ip = request.client.host if request.client else None
    await log_audit(
        db=db,
        action="view_patient_documents",
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        patient_id=patient_id,
        ip=client_ip,
        result="allowed"
    )

    return docs


@router.post("/patients/{patient_id}/documents", response_model=DocumentUploadResponse)
async def upload_document(
    patient_id: str,
    request: Request,
    file: UploadFile = File(...),
    doc_kind: str = Form("general"),  # general | query_letter
    claim_ref: Optional[str] = Form(None),
    current_user: User = Depends(require_patient_access),
    db: AsyncSession = Depends(get_db)
):
    # Verify patient exists
    p_res = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = p_res.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # Idempotency check: Document sha256 + patient
    existing_doc_res = await db.execute(
        select(Document).where(Document.patient_id == patient_id, Document.sha256 == sha256_hash)
    )
    existing_doc = existing_doc_res.scalar_one_or_none()
    if existing_doc:
        # Re-uploading an identical file returns existing Document without re-triggering
        return DocumentUploadResponse(
            document=existing_doc,
            duplicate=True,
            message="Identical document already exists in locker"
        )

    # Save encrypted file to disk
    storage_path, sha, size, mime = await save_encrypted_file(
        patient_id=patient_id,
        file_bytes=file_bytes,
        filename=file.filename or "upload.pdf"
    )

    source = "staff" if current_user.role in ("admin", "case_worker") else "patient"
    new_doc = Document(
        patient_id=patient_id,
        filename=file.filename or "document.pdf",
        mime=mime,
        size=size,
        sha256=sha,
        storage_path=storage_path,
        uploaded_by=current_user.id,
        source=source,
        doc_kind=doc_kind,
        classification_status="pending",
        claim_ref=claim_ref,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(new_doc)
    await db.flush()

    # Audit log upload
    client_ip = request.client.host if request.client else None
    await log_audit(
        db=db,
        action="upload_document",
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        patient_id=patient_id,
        object_type="document",
        object_id=new_doc.id,
        ip=client_ip,
        result="allowed"
    )

    # Enqueue classify_document job in same transaction
    prio = 0 if doc_kind == "query_letter" else 5
    await enqueue_job(
        db=db,
        job_type="classify_document",
        payload={"document_id": new_doc.id},
        dedupe_key=f"classify:{sha}",
        priority=prio
    )

    await db.commit()
    await db.refresh(new_doc)

    return DocumentUploadResponse(
        document=new_doc,
        duplicate=False,
        message="Document uploaded and enqueued for classification"
    )


@router.get("/documents/{doc_id}/signed-url", response_model=SignedUrlResponse)
async def get_document_signed_url(
    doc_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Document).where(Document.id == doc_id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Patient role can only get signed URL for their own documents
    if current_user.role == "patient" and current_user.patient_id != doc.patient_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    url = generate_document_download_url(doc_id=doc.id, user_id=current_user.id, ttl_seconds=300)
    
    client_ip = request.client.host if request.client else None
    await log_audit(
        db=db,
        action="issue_signed_url",
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        patient_id=doc.patient_id,
        object_type="document",
        object_id=doc.id,
        ip=client_ip,
        result="allowed"
    )

    return SignedUrlResponse(url=url, expires_at=doc.created_at)
