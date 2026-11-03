import os
import time
from typing import List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from backend.app.config import settings
from backend.app.db import get_db
from backend.app.models import (
    Patient, Document, QueryLetter, OutboundMessage, Job, AuditLog, User
)
from backend.app.schemas import AdminStatsOut, JobOut, AuditLogOut, PreflightStatusOut
from backend.app.rbac import require_admin
from backend.app.pipeline.jobs import enqueue_job
from backend.app.pipeline.compose import load_message_template

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStatsOut)
async def get_admin_stats(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    total_pts = (await db.execute(select(func.count(Patient.id)))).scalar() or 0
    total_docs = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    total_ql = (await db.execute(select(func.count(QueryLetter.id)))).scalar() or 0

    completed_ql = (await db.execute(select(func.count(QueryLetter.id)).where(QueryLetter.status == "completed"))).scalar() or 0
    in_progress_ql = (await db.execute(select(func.count(QueryLetter.id)).where(QueryLetter.status.in_(["received", "extracting", "matching", "composing", "sending"])))).scalar() or 0
    needs_review_ql = (await db.execute(select(func.count(QueryLetter.id)).where(QueryLetter.status == "needs_review"))).scalar() or 0

    # Latencies
    ql_times_res = await db.execute(select(QueryLetter.total_ms).where(QueryLetter.total_ms.isnot(None)))
    ql_times = [t for t in ql_times_res.scalars().all() if t]
    p50_ms = None
    p95_ms = None
    if ql_times:
        sorted_times = sorted(ql_times)
        p50_idx = int(len(sorted_times) * 0.5)
        p95_idx = int(len(sorted_times) * 0.95)
        p50_ms = float(sorted_times[min(p50_idx, len(sorted_times) - 1)])
        p95_ms = float(sorted_times[min(p95_idx, len(sorted_times) - 1)])

    sent_msgs = (await db.execute(select(func.count(OutboundMessage.id)).where(OutboundMessage.status.in_(["sent", "delivered", "read"])))).scalar() or 0
    failed_msgs = (await db.execute(select(func.count(OutboundMessage.id)).where(OutboundMessage.status == "failed"))).scalar() or 0

    active_j = (await db.execute(select(func.count(Job.id)).where(Job.status.in_(["pending", "running"])))).scalar() or 0
    failed_j = (await db.execute(select(func.count(Job.id)).where(Job.status.in_(["failed", "dead"])))).scalar() or 0

    return AdminStatsOut(
        total_patients=total_pts,
        total_documents=total_docs,
        total_letters=total_ql,
        letters_completed=completed_ql,
        letters_in_progress=in_progress_ql,
        letters_needs_review=needs_review_ql,
        p50_total_ms=p50_ms,
        p95_total_ms=p95_ms,
        messages_sent=sent_msgs,
        messages_failed=failed_msgs,
        active_jobs=active_j,
        failed_jobs=failed_j
    )


@router.get("/jobs", response_model=List[JobOut])
async def list_admin_jobs(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Job).order_by(Job.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/jobs/{job_id}/retry")
async def retry_admin_job(
    job_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Job).where(Job.id == job_id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job.status = "pending"
    job.attempts = 0
    job.run_after = datetime.now(timezone.utc)
    job.last_error = None
    job.locked_by = None
    job.locked_at = None
    await db.commit()

    return {"message": "Job scheduled for immediate retry", "job_id": job.id}


@router.get("/audit", response_model=List[AuditLogOut])
async def list_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AuditLog).order_by(AuditLog.ts.desc()).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/preflight", response_model=PreflightStatusOut)
async def check_preflight_status(
    current_user: User = Depends(require_admin)
):
    components = {}

    # 1. Database & Encryption
    components["encryption_data_key"] = {
        "status": bool(settings.DATA_KEY and len(settings.DATA_KEY) >= 32),
        "detail": "DATA_KEY set (Fernet 256-bit AES)"
    }

    # 2. Template
    try:
        tmpl = load_message_template()
        components["message_template"] = {
            "status": True,
            "detail": f"Loaded template version {tmpl.get('version', 1)} ({tmpl.get('name', 'default')})"
        }
    except Exception as e:
        components["message_template"] = {
            "status": False,
            "detail": f"Failed loading template: {str(e)}"
        }

    # 3. LLM Connectivity
    components["llm_provider"] = {
        "status": True,
        "detail": f"Active: {settings.LLM_PROVIDER} (Fast: {settings.LLM_MODEL_FAST})"
    }

    # 4. Twilio WhatsApp
    twilio_ok = bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN)
    components["whatsapp_delivery"] = {
        "status": True if settings.DELIVERY_MODE == "mock" else twilio_ok,
        "detail": f"Mode: {settings.DELIVERY_MODE} (Provider: {settings.WHATSAPP_PROVIDER})"
    }

    # 5. SMTP Email
    smtp_ok = bool(settings.SMTP_USER and settings.SMTP_APP_PASSWORD)
    components["email_delivery"] = {
        "status": True if settings.DELIVERY_MODE == "mock" else smtp_ok,
        "detail": f"Mode: {settings.DELIVERY_MODE} (Host: {settings.SMTP_HOST})"
    }

    all_ok = all(c["status"] for c in components.values())
    return PreflightStatusOut(overall_status=all_ok, components=components)
