from fastapi import APIRouter, Depends, HTTPException, Query, Response, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.db import get_db
from backend.app.models import Document
from backend.app.security import verify_signed_file_token
from backend.app.storage import read_decrypted_file
from backend.app.audit import log_audit

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{doc_id}")
async def download_file(
    doc_id: str,
    token: str = Query(..., description="HMAC signed expiring token"),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    if not verify_signed_file_token(token, expected_doc_id=doc_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired download token"
        )

    stmt = select(Document).where(Document.id == doc_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    decrypted_bytes = await read_decrypted_file(doc.storage_path)

    # Log audit
    client_ip = request.client.host if request and request.client else None
    await log_audit(
        db=db,
        action="download_document",
        patient_id=doc.patient_id,
        object_type="document",
        object_id=doc.id,
        ip=client_ip,
        result="allowed"
    )

    headers = {
        "Content-Disposition": f'inline; filename="{doc.filename}"',
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-cache, no-store, must-revalidate",
    }

    return Response(content=decrypted_bytes, media_type=doc.mime, headers=headers)
