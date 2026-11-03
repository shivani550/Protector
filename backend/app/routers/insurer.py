import hashlib
from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.config import settings
from backend.app.db import get_db
from backend.app.models import Patient, Document, QueryLetter
from backend.app.storage import save_encrypted_file
from backend.app.pipeline.jobs import enqueue_job

router = APIRouter(prefix="/insurer", tags=["insurer"])


@router.post("/query-letters")
async def ingest_insurer_query_letter(
    patient_code: str = Form(...),
    file: UploadFile = File(...),
    claim_ref: str = Form("CLAIM-DEF"),
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db)
):
    if x_api_key != settings.INSURER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Insurer API Key"
        )

    # Find patient
    p_res = await db.execute(select(Patient).where(Patient.patient_code == patient_code.strip()))
    patient = p_res.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient {patient_code} not found")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty query letter file")

    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # Save encrypted file
    storage_path, sha, size, mime = await save_encrypted_file(
        patient_id=patient.id,
        file_bytes=file_bytes,
        filename=file.filename or "insurer_letter.pdf"
    )

    # Create Document as query_letter
    doc = Document(
        patient_id=patient.id,
        filename=file.filename or "insurer_letter.pdf",
        mime=mime,
        size=size,
        sha256=sha,
        storage_path=storage_path,
        uploaded_by="insurer_api",
        source="insurer",
        doc_kind="query_letter",
        classification_status="done",
        doc_type="insurer_query_letter",
        doc_type_confidence=1.0,
        claim_ref=claim_ref
    )
    db.add(doc)
    await db.flush()

    # Create QueryLetter
    ql = QueryLetter(
        patient_id=patient.id,
        document_id=doc.id,
        claim_ref=claim_ref,
        insurer_name=patient.insurer_name,
        status="received"
    )
    db.add(ql)
    await db.flush()

    # In same transaction: enqueue process_letter with priority 0
    await enqueue_job(
        db=db,
        job_type="process_letter",
        payload={"query_letter_id": ql.id},
        dedupe_key=f"letter:{doc.id}",
        priority=0
    )

    await db.commit()

    return {
        "status": "received",
        "query_letter_id": ql.id,
        "patient_code": patient.patient_code,
        "document_id": doc.id,
        "message": "Query letter ingested and pipeline triggered automatically"
    }
