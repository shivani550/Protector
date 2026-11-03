import pytest
import httpx
from pathlib import Path
from backend.app.main import app
from backend.app.storage import save_encrypted_file, read_decrypted_file, generate_document_download_url
from backend.app.security import verify_signed_file_token, create_signed_file_token


@pytest.mark.asyncio
async def test_encrypted_storage_roundtrip():
    patient_id = "test-patient-storage"
    raw_content = b"%PDF-1.4 Simulated Medical Document Content for Testing Fernet Storage"
    filename = "discharge_summary.pdf"

    storage_path, sha256_hash, size, mime = await save_encrypted_file(
        patient_id=patient_id,
        file_bytes=raw_content,
        filename=filename
    )

    # 1. Verify file exists on disk
    p = Path(storage_path)
    assert p.exists()

    # 2. Verify on-disk file is ciphertext, NOT the plain content
    disk_bytes = p.read_bytes()
    assert disk_bytes != raw_content
    assert b"Simulated Medical Document" not in disk_bytes

    # 3. Decrypt and verify exact match
    restored = await read_decrypted_file(storage_path)
    assert restored == raw_content
    assert mime == "application/pdf"
    assert size == len(raw_content)


@pytest.mark.asyncio
async def test_signed_url_tamper_protection():
    doc_id = "doc-12345"
    user_id = "user-777"
    url = generate_document_download_url(doc_id, user_id, ttl_seconds=60)
    assert f"/api/files/{doc_id}?token=" in url

    # Extract token
    token = url.split("token=")[1]
    assert verify_signed_file_token(token, expected_doc_id=doc_id, expected_user_id=user_id) is True

    # Tampered doc_id in verification
    assert verify_signed_file_token(token, expected_doc_id="different-doc", expected_user_id=user_id) is False

    # Tampered token string
    tampered_token = token[:-4] + "AAAA"
    assert verify_signed_file_token(tampered_token, expected_doc_id=doc_id) is False


@pytest.mark.asyncio
async def test_disallowed_file_type():
    with pytest.raises(Exception):
        await save_encrypted_file(
            patient_id="test-p",
            file_bytes=b"MZ\x90\x00executable bytes",
            filename="malicious.exe"
        )
