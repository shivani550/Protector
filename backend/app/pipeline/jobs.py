import asyncio
import time
import uuid
import traceback
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from backend.app.db import AsyncSessionLocal
from backend.app.models import Job, Document, QueryLetter, Patient
from backend.app.ingest.extract import extract_document_text
from backend.app.ingest.classify import classify_document_text
from backend.app.storage import read_decrypted_file
from backend.app.pipeline.process_letter import run_process_letter_pipeline

WORKER_ID = f"worker_{uuid.uuid4().hex[:8]}"
BACKOFF_SCHEDULE = [2, 8, 30, 120, 600]  # Exponential backoff in seconds


async def enqueue_job(
    db: AsyncSession,
    job_type: str,
    payload: Dict[str, Any],
    dedupe_key: str,
    priority: int = 5,
    run_after: Optional[datetime] = None
) -> Job:
    """Idempotently enqueues a background job using unique dedupe_key."""
    stmt = select(Job).where(Job.dedupe_key == dedupe_key)
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()
    if existing:
        return existing

    job = Job(
        type=job_type,
        payload=payload,
        dedupe_key=dedupe_key,
        priority=priority,
        status="pending",
        run_after=run_after or datetime.now(timezone.utc),
        attempts=0,
        max_attempts=5 if job_type == "send_message" else 3
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def handle_classify_document_job(payload: Dict[str, Any]):
    doc_id = payload["document_id"]
    async with AsyncSessionLocal() as session:
        doc_res = await session.execute(select(Document).where(Document.id == doc_id))
        doc = doc_res.scalar_one_or_none()
        if not doc:
            return

        p_res = await session.execute(select(Patient).where(Patient.id == doc.patient_id))
        patient = p_res.scalar_one_or_none()
        patient_name = patient.full_name if patient else ""

        # Extract text if missing
        if not doc.extracted_text_enc:
            file_bytes = await read_decrypted_file(doc.storage_path)
            text, method, legibility = extract_document_text(file_bytes, doc.mime, doc.filename)
            doc.extracted_text_enc = text
            doc.redacted_text = text
            doc.extraction_method = method
            doc.legibility_score = legibility

        # Classify
        doc_type, confidence, meta = await classify_document_text(
            text=doc.redacted_text or "",
            patient_full_name=patient_name,
            filename=doc.filename
        )
        doc.doc_type = doc_type
        doc.doc_type_confidence = confidence
        doc.meta = meta
        doc.classification_status = "done"

        # T2 — letter trigger:
        # A document becomes a query letter if doc_kind=query_letter OR doc_type=insurer_query_letter (conf >= 0.6)
        if doc.doc_kind == "query_letter" or (doc_type == "insurer_query_letter" and confidence >= 0.60):
            doc.doc_kind = "query_letter"

            # Check if QueryLetter already exists
            ql_check = await session.execute(select(QueryLetter).where(QueryLetter.document_id == doc.id))
            ql = ql_check.scalar_one_or_none()
            if not ql:
                ql = QueryLetter(
                    patient_id=doc.patient_id,
                    document_id=doc.id,
                    claim_ref=doc.claim_ref or meta.get("claim_no_masked") or "CLAIM",
                    insurer_name=patient.insurer_name if patient else "Insurer",
                    status="received"
                )
                session.add(ql)
                await session.flush()

            # Enqueue process_letter with priority 0
            await enqueue_job(
                db=session,
                job_type="process_letter",
                payload={"query_letter_id": ql.id},
                dedupe_key=f"letter:{doc.id}",
                priority=0
            )

        await session.commit()


async def handle_process_letter_job(payload: Dict[str, Any]):
    query_letter_id = payload["query_letter_id"]
    await run_process_letter_pipeline(query_letter_id)


async def execute_job(job: Job):
    if job.type == "classify_document":
        await handle_classify_document_job(job.payload)
    elif job.type == "process_letter":
        await handle_process_letter_job(job.payload)


async def run_worker_loop():
    """Background worker daemon loop consuming Job table."""
    while True:
        try:
            now = datetime.now(timezone.utc)
            async with AsyncSessionLocal() as session:
                # 1. Reclaim stale locked jobs (> 5 minutes)
                stale_cutoff = now - timedelta(minutes=5)
                await session.execute(
                    update(Job)
                    .where(Job.status == "running", Job.locked_at < stale_cutoff)
                    .values(status="pending", locked_by=None, locked_at=None)
                )

                # 2. Pick next pending job
                stmt = (
                    select(Job)
                    .where(Job.status == "pending", Job.run_after <= now)
                    .order_by(Job.priority.asc(), Job.created_at.asc())
                    .limit(1)
                )
                res = await session.execute(stmt)
                job = res.scalar_one_or_none()

                if not job:
                    await session.commit()
                    await asyncio.sleep(0.5)
                    continue

                # Lock job
                job.status = "running"
                job.locked_by = WORKER_ID
                job.locked_at = now
                job.attempts += 1
                await session.commit()
                job_id = job.id

            # Execute job outside transaction
            err_msg = None
            try:
                await execute_job(job)
            except Exception as e:
                err_msg = f"{str(e)}\n{traceback.format_exc()}"

            # Update job status
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(Job).where(Job.id == job_id))
                locked_job = res.scalar_one_or_none()
                if locked_job:
                    if err_msg is None:
                        locked_job.status = "done"
                        locked_job.last_error = None
                    else:
                        locked_job.last_error = err_msg[:2000]
                        if locked_job.attempts >= locked_job.max_attempts:
                            locked_job.status = "dead"
                        else:
                            locked_job.status = "pending"
                            backoff_idx = min(locked_job.attempts - 1, len(BACKOFF_SCHEDULE) - 1)
                            backoff_secs = BACKOFF_SCHEDULE[backoff_idx]
                            locked_job.run_after = datetime.now(timezone.utc) + timedelta(seconds=backoff_secs)
                    
                    locked_job.locked_by = None
                    locked_job.locked_at = None
                    await session.commit()

        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(1.0)
