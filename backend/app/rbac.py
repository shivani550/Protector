from typing import Callable, Optional
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.db import get_db
from backend.app.models import User, CaseAssignment
from backend.app.auth import get_current_user
from backend.app.audit import log_audit


def require_role(allowed_roles: list[str]) -> Callable:
    async def role_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        if current_user.role not in allowed_roles:
            client_ip = request.client.host if request.client else None
            await log_audit(
                db=db,
                action="role_access_denied",
                actor_user_id=current_user.id,
                actor_role=current_user.role,
                ip=client_ip,
                result="denied"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action"
            )
        return current_user
    return role_checker


require_admin = require_role(["admin"])
require_staff = require_role(["admin", "case_worker"])


async def check_patient_access(
    patient_id: str,
    user: User,
    db: AsyncSession,
    request: Optional[Request] = None
) -> bool:
    """Core logic to check whether user has access to patient_id."""
    if user.role == "admin":
        return True

    if user.role == "case_worker":
        stmt = select(CaseAssignment).where(
            CaseAssignment.user_id == user.id,
            CaseAssignment.patient_id == patient_id
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none() is not None

    if user.role == "patient":
        return user.patient_id == patient_id

    return False


def get_patient_access_dependency():
    """Returns a dependency function that enforces patient access given patient_id path param."""
    async def dependency(
        patient_id: str,
        request: Request,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        has_access = await check_patient_access(patient_id, current_user, db, request)
        if not has_access:
            client_ip = request.client.host if request.client else None
            await log_audit(
                db=db,
                action="patient_access_denied",
                actor_user_id=current_user.id,
                actor_role=current_user.role,
                patient_id=patient_id,
                ip=client_ip,
                result="denied"
            )
            # Use 404 for patients to prevent enumeration/existence leaks; 403 for workers
            if current_user.role == "patient":
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
            else:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access to patient denied")

        return current_user

    return dependency


require_patient_access = get_patient_access_dependency()
