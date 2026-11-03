import os
import hashlib
import aiofiles
from pathlib import Path
from typing import Tuple, Optional
from fastapi import HTTPException, UploadFile, status
from backend.app.config import settings
from backend.app.security import encrypt_bytes, decrypt_bytes, create_signed_file_token, verify_signed_file_token

ALLOWED_MIMES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB


def get_storage_path(patient_id: str, sha256_hash: str) -> Path:
    storage_root = Path(settings.STORAGE_DIR).resolve()
    patient_dir = storage_root / patient_id
    patient_dir.mkdir(parents=True, exist_ok=True)
    return patient_dir / f"{sha256_hash}.enc"


def sanitize_filename(filename: str) -> str:
    # Strip directory components to avoid path traversal
    base = os.path.basename(filename)
    # Remove any special dangerous chars
    cleaned = "".join(c for c in base if c.isalnum() or c in "._- ")
    return cleaned if cleaned else "document.pdf"


async def save_encrypted_file(patient_id: str, file_bytes: bytes, filename: str) -> Tuple[str, str, int, str]:
    """
    Validates, calculates SHA-256, encrypts and writes file ciphertext to disk.
    Returns: (storage_path_str, sha256_hash, file_size, mime_type)
    """
    size = len(file_bytes)
    if size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of 15MB"
        )

    # Calculate SHA256 of plain bytes
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # Determine MIME
    mime = "application/octet-stream"
    lower_fn = filename.lower()
    if lower_fn.endswith(".pdf") or file_bytes.startswith(b"%PDF-"):
        mime = "application/pdf"
    elif lower_fn.endswith((".jpg", ".jpeg")) or file_bytes.startswith(b"\xff\xd8"):
        mime = "image/jpeg"
    elif lower_fn.endswith(".png") or file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif lower_fn.endswith(".docx") or file_bytes.startswith(b"PK\x03\x04"):
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif lower_fn.endswith(".txt"):
        mime = "text/plain"

    if mime not in ALLOWED_MIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{mime}'. Allowed formats: PDF, JPG, PNG, DOCX, TXT."
        )

    target_path = get_storage_path(patient_id, sha256_hash)
    
    # Encrypt bytes before saving
    encrypted_blob = encrypt_bytes(file_bytes)

    async with aiofiles.open(target_path, "wb") as f:
        await f.write(encrypted_blob)

    return str(target_path), sha256_hash, size, mime


async def read_decrypted_file(storage_path_str: str) -> bytes:
    path = Path(storage_path_str)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored document file not found")

    async with aiofiles.open(path, "rb") as f:
        ciphertext = await f.read()

    return decrypt_bytes(ciphertext)


def generate_document_download_url(doc_id: str, user_id: str, ttl_seconds: int = 300) -> str:
    token = create_signed_file_token(doc_id, user_id, ttl_seconds=ttl_seconds)
    return f"{settings.PUBLIC_BASE_URL}/api/files/{doc_id}?token={token}"
