from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from backend.app.db import get_db
from backend.app.models import OutboundMessage

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/twilio")
async def twilio_status_callback(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    form_data = await request.form()
    message_sid = form_data.get("MessageSid")
    msg_status = form_data.get("MessageStatus")  # queued | sent | delivered | undelivered | failed
    err_code = form_data.get("ErrorCode")

    if not message_sid:
        return {"status": "ignored"}

    stmt = select(OutboundMessage).where(OutboundMessage.provider_message_id == message_sid)
    res = await db.execute(stmt)
    msg = res.scalar_one_or_none()

    if msg:
        now = datetime.now(timezone.utc)
        if msg_status == "delivered":
            msg.status = "delivered"
            msg.delivered_at = now
        elif msg_status == "sent":
            msg.status = "sent"
            msg.sent_at = now
        elif msg_status in ("failed", "undelivered"):
            msg.status = "failed"
            msg.failed_at = now
            msg.status_detail = f"Twilio Error {err_code or 'undelivered'}"

        await db.commit()

    return {"status": "ok"}


@router.get("/meta")
async def meta_verify(request: Request):
    query_params = request.query_params
    challenge = query_params.get("hub.challenge")
    return challenge or "ok"


@router.post("/meta")
async def meta_webhook(request: Request):
    return {"status": "ok"}
