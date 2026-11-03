from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.app.db import get_db
from backend.app.models import Patient, User, CaseAssignment, Document, QueryLetter, OutboundMessage
from backend.app.schemas import PatientOut, PatientDetailOut, PatientCreate
from backend.app.auth import get_current_user
from backend.app.rbac import require_patient_access, require_staff
from backend.app.security import encrypt_text, decrypt_text, mask_policy_number, mask_aadhaar
from backend.app.audit import log_audit

router = APIRouter(prefix="/patients", tags=["patients"])


def format_patient_out(patient: Patient, docs_count: int = 0, queries_count: int = 0, latest_status: Optional[str] = None) -> PatientOut:
    return PatientOut(
        id=patient.id,
        patient_code=patient.patient_code,
        full_name=patient.full_name,
        dob=patient.dob,
        gender=patient.gender,
        phone_e164=patient.phone_e164,
        email=patient.email,
        preferred_language=patient.preferred_language,
        insurer_name=patient.insurer_name,
        policy_number_masked=f"****{patient.policy_number_last4}",
        aadhaar_masked=f"XXXX-XXXX-{patient.aadhaar_last4}" if patient.aadhaar_last4 else None,
        consent_whatsapp=patient.consent_whatsapp,
        consent_email=patient.consent_email,
        documents_count=docs_count,
        open_queries_count=queries_count,
        latest_query_status=latest_status,
        created_at=patient.created_at
    )


@router.get("", response_model=List[PatientOut])
async def list_patients(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List patients scoped to current user's role and case assignments."""
    if current_user.role == "admin":
        stmt = select(Patient).order_by(Patient.patient_code)
    elif current_user.role == "case_worker":
        stmt = (
            select(Patient)
            .join(CaseAssignment, CaseAssignment.patient_id == Patient.id)
            .where(CaseAssignment.user_id == current_user.id)
            .order_by(Patient.patient_code)
        )
    elif current_user.role == "patient":
        if not current_user.patient_id:
            return []
        stmt = select(Patient).where(Patient.id == current_user.patient_id)
    else:
        return []

    result = await db.execute(stmt)
    patients = result.scalars().all()

    # Log audit
    client_ip = request.client.host if request.client else None
    await log_audit(
        db=db,
        action="view_patient_list",
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        ip=client_ip,
        result="allowed"
    )

    out: List[PatientOut] = []
    for p in patients:
        # Count documents
        doc_count_res = await db.execute(select(func.count(Document.id)).where(Document.patient_id == p.id))
        doc_count = doc_count_res.scalar() or 0

        # Query letters
        ql_res = await db.execute(
            select(QueryLetter)
            .where(QueryLetter.patient_id == p.id)
            .order_by(QueryLetter.received_at.desc())
        )
        ql_letters = ql_res.scalars().all()
        open_count = sum(1 for q in ql_letters if q.status not in ("completed", "failed"))
        latest_status = ql_letters[0].status if ql_letters else None

        out.append(format_patient_out(p, docs_count=doc_count, queries_count=open_count, latest_status=latest_status))

    return out


@router.get("/{patient_id}", response_model=PatientDetailOut)
async def get_patient(
    patient_id: str,
    reveal: bool = Query(False, description="Reveal unmasked PII (admin only)"),
    request: Request = None,
    current_user: User = Depends(require_patient_access),
    db: AsyncSession = Depends(get_db)
):
    """Get single patient details. Enforces scoped access."""
    stmt = select(Patient).where(Patient.id == patient_id)
    result = await db.execute(stmt)
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    client_ip = request.client.host if request and request.client else None

    # Handle unmasked reveal
    policy_full = None
    aadhaar_full = None
    if reveal:
        if current_user.role != "admin":
            await log_audit(
                db=db,
                action="reveal_pii_denied",
                actor_user_id=current_user.id,
                actor_role=current_user.role,
                patient_id=patient_id,
                ip=client_ip,
                result="denied"
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can reveal unmasked PII")

        policy_full = decrypt_text(patient.policy_number_enc)
        aadhaar_full = decrypt_text(patient.aadhaar_enc) if patient.aadhaar_enc else None

        await log_audit(
            db=db,
            action="reveal_pii",
            actor_user_id=current_user.id,
            actor_role=current_user.role,
            patient_id=patient_id,
            ip=client_ip,
            result="allowed"
        )
    else:
        await log_audit(
            db=db,
            action="view_patient",
            actor_user_id=current_user.id,
            actor_role=current_user.role,
            patient_id=patient_id,
            ip=client_ip,
            result="allowed"
        )

    # Document count
    doc_count_res = await db.execute(select(func.count(Document.id)).where(Document.patient_id == patient.id))
    doc_count = doc_count_res.scalar() or 0

    base_out = format_patient_out(patient, docs_count=doc_count)
    return PatientDetailOut(
        **base_out.model_dump(),
        policy_number_full=policy_full,
        aadhaar_full=aadhaar_full
    )
