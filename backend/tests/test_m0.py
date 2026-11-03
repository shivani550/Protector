import pytest
import httpx
from backend.app.main import app
from backend.app.config import settings
from backend.app.security import (
    encrypt_text, decrypt_text,
    hash_password, verify_password,
    create_access_token, decode_access_token,
    create_signed_file_token, verify_signed_file_token
)


@pytest.mark.asyncio
async def test_health_check():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "protector-api"


def test_encryption_and_decryption():
    secret_text = "POL-123456789-CONFIDENTIAL"
    cipher = encrypt_text(secret_text)
    assert cipher != secret_text
    decrypted = decrypt_text(cipher)
    assert decrypted == secret_text


def test_password_hashing():
    pwd = "SecurePassword123!"
    pw_hash = hash_password(pwd)
    assert pw_hash != pwd
    assert verify_password(pwd, pw_hash) is True
    assert verify_password("WrongPassword", pw_hash) is False


def test_jwt_token():
    payload = {"sub": "user_123", "role": "admin"}
    token = create_access_token(payload)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user_123"
    assert decoded["role"] == "admin"


def test_signed_file_url():
    doc_id = "doc_abc"
    user_id = "user_xyz"
    token = create_signed_file_token(doc_id, user_id, ttl_seconds=60)
    assert verify_signed_file_token(token, doc_id, user_id) is True
    assert verify_signed_file_token(token, "other_doc", user_id) is False
    assert verify_signed_file_token(token, doc_id, "other_user") is False
