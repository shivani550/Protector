from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db import get_db
from backend.app.models import User
from backend.app.auth import authenticate_user, get_current_user
from backend.app.security import create_access_token
from backend.app.schemas import LoginRequest, TokenResponse, UserOut
from backend.app.audit import log_audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    user = await authenticate_user(db, payload.email, payload.password)
    client_ip = request.client.host if request.client else None

    if not user:
        await log_audit(
            db=db,
            action="login_failed",
            actor_user_id=None,
            actor_role=None,
            ip=client_ip,
            result="denied"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Issue JWT
    token_data = {"sub": user.id, "email": user.email, "role": user.role}
    if user.patient_id:
        token_data["patient_id"] = user.patient_id

    access_token = create_access_token(token_data)

    # Set httpOnly cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=8 * 3600,
        samesite="lax",
        secure=False  # Set True in production HTTPS
    )

    await log_audit(
        db=db,
        action="login_success",
        actor_user_id=user.id,
        actor_role=user.role,
        patient_id=user.patient_id,
        ip=client_ip,
        result="allowed"
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        patient_id=user.patient_id
    )


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
