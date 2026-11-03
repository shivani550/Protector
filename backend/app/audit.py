from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models import AuditLog


async def log_audit(
    db: AsyncSession,
    action: str,
    actor_user_id: Optional[str] = None,
    actor_role: Optional[str] = None,
    patient_id: Optional[str] = None,
    object_type: Optional[str] = None,
    object_id: Optional[str] = None,
    ip: Optional[str] = None,
    result: str = "allowed"
) -> AuditLog:
    """Creates an append-only audit log entry."""
    entry = AuditLog(
        action=action,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        patient_id=patient_id,
        object_type=object_type,
        object_id=object_id,
        ip=ip,
        result=result
    )
    db.add(entry)
    await db.commit()
    return entry
