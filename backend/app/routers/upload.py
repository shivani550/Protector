from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.db import get_db
from backend.app.models import Patient, Document, QueryLetter, QueryPoint, PointDecision
from backend.app.security import verify_magic_upload_token
from backend.app.storage import save_encrypted_file
from backend.app.ingest.classify import get_taxonomy
from backend.app.pipeline.jobs import enqueue_job

router = APIRouter(prefix="/upload", tags=["upload"])


@router.get("/{token}")
async def get_magic_upload_info(token: str, db: AsyncSession = Depends(get_db)):
    payload = verify_magic_upload_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired magic upload link."
        )

    patient_id = payload["patient_id"]
    p_res = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = p_res.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    tax = get_taxonomy()
    tax_labels = {dt["key"]: dt["label"] for dt in tax.get("doc_types", [])}

    # Find requested items
    ql_id = payload.get("query_letter_id")
    requested_items = []
    if ql_id:
        dec_res = await db.execute(
            select(PointDecision)
            .join(QueryPoint, QueryPoint.id == PointDecision.query_point_id)
            .where(QueryPoint.query_letter_id == ql_id, PointDecision.decision == "needs_new_document")
        )
        decisions = dec_res.scalars().all()
        for d in decisions:
            for nt in (d.needed_doc_types or []):
                requested_items.append({
                    "doc_type": nt,
                    "label": tax_labels.get(nt, nt.replace("_", " ").title()),
                    "reason": d.reason_patient
                })

    return {
        "patient_first_name": patient.full_name.split()[0],
        "insurer_name": patient.insurer_name,
        "requested_documents": requested_items
    }


@router.post("/{token}")
async def submit_magic_upload(
    token: str,
    file: UploadFile = File(...),
    doc_type: str = Form("other"),
    db: AsyncSession = Depends(get_db)
):
    payload = verify_magic_upload_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired token")

    patient_id = payload["patient_id"]
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    storage_path, sha, size, mime = await save_encrypted_file(
        patient_id=patient_id,
        file_bytes=file_bytes,
        filename=file.filename or "upload.pdf"
    )

    doc = Document(
        patient_id=patient_id,
        filename=file.filename or "uploaded_doc.pdf",
        mime=mime,
        size=size,
        sha256=sha,
        storage_path=storage_path,
        uploaded_by="patient_magic_link",
        source="patient",
        doc_kind="general",
        doc_type=doc_type if doc_type != "other" else None,
        classification_status="pending",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(doc)
    await db.flush()

    # Enqueue classification job
    await enqueue_job(
        db=db,
        job_type="classify_document",
        payload={"document_id": doc.id},
        dedupe_key=f"classify:{sha}",
        priority=3
    )

    ql_id = payload.get("query_letter_id")
    if ql_id:
        # Re-evaluate query letter with newly supplied document to auto-resolve pending points
        await enqueue_job(
            db=db,
            job_type="process_letter",
            payload={"query_letter_id": ql_id},
            dedupe_key=f"reprocess:{ql_id}:{sha}",
            priority=2
        )

    await db.commit()
    return {"status": "success", "message": "Document uploaded successfully! Our team is processing it."}
