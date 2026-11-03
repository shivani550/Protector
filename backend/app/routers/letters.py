from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.db import get_db
from backend.app.models import QueryLetter, QueryPoint, PointDecision, User
from backend.app.schemas import QueryLetterOut, QueryLetterDetailOut, QueryPointOut, PointDecisionOut
from backend.app.auth import get_current_user
from backend.app.rbac import require_patient_access, require_staff
from backend.app.pipeline.jobs import enqueue_job
from backend.app.audit import log_audit

router = APIRouter(prefix="", tags=["letters"])


@router.get("/patients/{patient_id}/letters", response_model=List[QueryLetterDetailOut])
async def list_patient_letters(
    patient_id: str,
    request: Request,
    current_user: User = Depends(require_patient_access),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(QueryLetter)
        .where(QueryLetter.patient_id == patient_id)
        .order_by(QueryLetter.received_at.desc())
    )
    res = await db.execute(stmt)
    letters = res.scalars().all()

    out = []
    for l in letters:
        pts_res = await db.execute(
            select(QueryPoint)
            .options(selectinload(QueryPoint.decision))
            .where(QueryPoint.query_letter_id == l.id)
            .order_by(QueryPoint.ordinal.asc())
        )
        pts = pts_res.scalars().all()
        covered_count = 0
        needed_count = 0
        points_out = []

        for p in pts:
            dec_out = None
            if p.decision:
                if p.decision.decision == "covered":
                    covered_count += 1
                elif p.decision.decision == "needs_new_document":
                    needed_count += 1

                reason_int = p.decision.reason_internal if current_user.role != "patient" else None
                dec_out = PointDecisionOut(
                    id=p.decision.id,
                    query_point_id=p.decision.query_point_id,
                    decision=p.decision.decision,
                    covering_document_ids=p.decision.covering_document_ids or [],
                    needed_doc_types=p.decision.needed_doc_types or [],
                    reason_patient=p.decision.reason_patient,
                    reason_internal=reason_int,
                    confidence=p.decision.confidence,
                    guardrail_flags=p.decision.guardrail_flags or [],
                    created_at=p.decision.created_at
                )

            points_out.append(QueryPointOut(
                id=p.id,
                query_letter_id=p.query_letter_id,
                ordinal=p.ordinal,
                verbatim_text=p.verbatim_text,
                normalized_ask=p.normalized_ask,
                point_type=p.point_type,
                requested_doc_types=p.requested_doc_types or [],
                period_constraint=p.period_constraint,
                confidence=p.confidence,
                decision=dec_out
            ))

        out_item = QueryLetterDetailOut(
            id=l.id,
            patient_id=l.patient_id,
            document_id=l.document_id,
            claim_ref=l.claim_ref,
            insurer_name=l.insurer_name,
            received_at=l.received_at,
            status=l.status,
            status_detail=l.status_detail,
            started_at=l.started_at,
            completed_at=l.completed_at,
            total_ms=l.total_ms,
            run_no=l.run_no,
            points_count=len(pts),
            covered_points_count=covered_count,
            needed_points_count=needed_count,
            points=points_out,
            pipeline_trace=l.pipeline_trace
        )
        out.append(out_item)

    return out


@router.get("/letters/{letter_id}", response_model=QueryLetterDetailOut)
async def get_letter_detail(
    letter_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(QueryLetter)
        .where(QueryLetter.id == letter_id)
    )
    res = await db.execute(stmt)
    l = res.scalar_one_or_none()
    if not l:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query letter not found")

    # Patient role scoping check
    if current_user.role == "patient" and current_user.patient_id != l.patient_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query letter not found")

    pts_res = await db.execute(
        select(QueryPoint)
        .options(selectinload(QueryPoint.decision))
        .where(QueryPoint.query_letter_id == l.id)
        .order_by(QueryPoint.ordinal.asc())
    )
    pts = pts_res.scalars().all()

    points_out = []
    covered_count = 0
    needed_count = 0

    for p in pts:
        dec_out = None
        if p.decision:
            if p.decision.decision == "covered":
                covered_count += 1
            elif p.decision.decision == "needs_new_document":
                needed_count += 1

            # Patients cannot see reason_internal
            reason_int = p.decision.reason_internal if current_user.role != "patient" else None
            dec_out = PointDecisionOut(
                id=p.decision.id,
                query_point_id=p.decision.query_point_id,
                decision=p.decision.decision,
                covering_document_ids=p.decision.covering_document_ids or [],
                needed_doc_types=p.decision.needed_doc_types or [],
                reason_patient=p.decision.reason_patient,
                reason_internal=reason_int,
                confidence=p.decision.confidence,
                guardrail_flags=p.decision.guardrail_flags or [],
                created_at=p.decision.created_at
            )

        points_out.append(QueryPointOut(
            id=p.id,
            query_letter_id=p.query_letter_id,
            ordinal=p.ordinal,
            verbatim_text=p.verbatim_text,
            normalized_ask=p.normalized_ask,
            point_type=p.point_type,
            requested_doc_types=p.requested_doc_types or [],
            period_constraint=p.period_constraint,
            confidence=p.confidence,
            decision=dec_out
        ))

    client_ip = request.client.host if request.client else None
    await log_audit(
        db=db,
        action="view_letter_detail",
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        patient_id=l.patient_id,
        object_type="query_letter",
        object_id=l.id,
        ip=client_ip,
        result="allowed"
    )

    trace_data = l.pipeline_trace if current_user.role != "patient" else None

    return QueryLetterDetailOut(
        id=l.id,
        patient_id=l.patient_id,
        document_id=l.document_id,
        claim_ref=l.claim_ref,
        insurer_name=l.insurer_name,
        received_at=l.received_at,
        status=l.status,
        status_detail=l.status_detail,
        started_at=l.started_at,
        completed_at=l.completed_at,
        total_ms=l.total_ms,
        run_no=l.run_no,
        points_count=len(pts),
        covered_points_count=covered_count,
        needed_points_count=needed_count,
        points=points_out,
        pipeline_trace=trace_data
    )


@router.post("/letters/{letter_id}/reprocess")
async def reprocess_letter(
    letter_id: str,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(QueryLetter).where(QueryLetter.id == letter_id)
    res = await db.execute(stmt)
    ql = res.scalar_one_or_none()
    if not ql:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query letter not found")

    ql.run_no += 1
    ql.status = "received"
    ql.status_detail = "Reprocessing requested by staff"

    # Enqueue process_letter with priority 0
    await enqueue_job(
        db=db,
        job_type="process_letter",
        payload={"query_letter_id": ql.id},
        dedupe_key=f"reprocess:{ql.id}:{ql.run_no}",
        priority=0
    )
    await db.commit()

    return {"message": "Query letter enqueued for reprocessing", "run_no": ql.run_no}
