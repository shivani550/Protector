import asyncio
import json
from typing import AsyncGenerator
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from backend.app.db import AsyncSessionLocal
from backend.app.models import QueryLetter, OutboundMessage

router = APIRouter(prefix="", tags=["events"])


async def event_generator(request: Request) -> AsyncGenerator[str, None]:
    """
    Server-Sent Events (SSE) generator streaming active letter status
    and message delivery updates to the portal in real time.
    """
    last_state = {}
    while True:
        if await request.is_disconnected():
            break

        try:
            async with AsyncSessionLocal() as session:
                # Poll active query letters
                ql_res = await session.execute(
                    select(QueryLetter).order_by(QueryLetter.updated_at.desc()).limit(10)
                )
                letters = ql_res.scalars().all()

                # Poll latest messages
                msg_res = await session.execute(
                    select(OutboundMessage).order_by(OutboundMessage.updated_at.desc()).limit(10)
                )
                messages = msg_res.scalars().all()

                state_snapshot = {
                    "letters": {l.id: l.status for l in letters},
                    "messages": {m.id: m.status for m in messages}
                }

                # Only push event if state changed or heartbeat every 5s
                if state_snapshot != last_state:
                    last_state = state_snapshot
                    payload = {
                        "type": "state_update",
                        "letters": [
                            {
                                "id": l.id,
                                "patient_id": l.patient_id,
                                "status": l.status,
                                "status_detail": l.status_detail,
                                "total_ms": l.total_ms
                            }
                            for l in letters
                        ],
                        "messages": [
                            {
                                "id": m.id,
                                "patient_id": m.patient_id,
                                "channel": m.channel,
                                "status": m.status
                            }
                            for m in messages
                        ]
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                else:
                    # Heartbeat comment to keep connection alive
                    yield ": heartbeat\n\n"

        except Exception:
            yield ": keepalive-error\n\n"

        await asyncio.sleep(1.5)


@router.get("/events")
async def sse_events(request: Request):
    return StreamingResponse(
        event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
