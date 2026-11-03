from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.db import get_db
from backend.app.models import OutboundMessage, User
from backend.app.schemas import OutboundMessageOut
from backend.app.auth import get_current_user
from backend.app.rbac import require_patient_access, require_staff
from backend.app.delivery.base import OutboundPayload
from backend.app.delivery.factory import get_whatsapp_provider, get_email_provider
from backend.app.audit import log_audit

router = APIRouter(prefix="", tags=["messages"])


@router.get("/patients/{patient_id}/messages", response_model=List[OutboundMessageOut])
async def list_patient_messages(
    patient_id: str,
    request: Request,
    current_user: User = Depends(require_patient_access),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(OutboundMessage)
        .where(OutboundMessage.patient_id == patient_id)
        .order_by(OutboundMessage.created_at.desc())
    )
    res = await db.execute(stmt)
    messages = res.scalars().all()

    client_ip = request.client.host if request.client else None
    await log_audit(
        db=db,
        action="view_patient_messages",
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        patient_id=patient_id,
        ip=client_ip,
        result="allowed"
    )

    return messages


@router.post("/messages/{message_id}/resend")
async def resend_message(
    message_id: str,
    request: Request,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(OutboundMessage).where(OutboundMessage.id == message_id)
    res = await db.execute(stmt)
    msg = res.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    if msg.status in ("delivered", "read"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message already delivered. Resend disabled."
        )

    provider = get_whatsapp_provider() if msg.channel == "whatsapp" else get_email_provider()
    payload = OutboundPayload(
        channel=msg.channel,
        recipient=msg.recipient_masked,  # In live, provider uses patient profile contact
        body=msg.body_rendered
    )

    send_res = await provider.send(payload)
    if send_res.accepted:
        msg.status = "sent"
        msg.provider_message_id = send_res.provider_message_id
    else:
        msg.status = "failed"
        msg.status_detail = send_res.error_message

    await db.commit()
    return {"message": "Resend attempt completed", "status": msg.status}
