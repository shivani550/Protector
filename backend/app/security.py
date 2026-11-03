import time
import hmac
import hashlib
import base64
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from cryptography.fernet import Fernet
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import jwt, JWTError
from backend.app.config import settings

# Fernet Cipher initialized with DATA_KEY
fernet = Fernet(settings.DATA_KEY.encode() if isinstance(settings.DATA_KEY, str) else settings.DATA_KEY)
ph = PasswordHasher()


# --- Encryption at rest (Fernet AES-128 CBC + HMAC) ---
def encrypt_bytes(data: bytes) -> bytes:
    return fernet.encrypt(data)


def decrypt_bytes(cipher_data: bytes) -> bytes:
    return fernet.decrypt(cipher_data)


def encrypt_text(plain: Optional[str]) -> Optional[str]:
    if plain is None:
        return None
    return fernet.encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_text(cipher_text: Optional[str]) -> Optional[str]:
    if cipher_text is None:
        return None
    return fernet.decrypt(cipher_text.encode("utf-8")).decode("utf-8")


# --- Password Hashing (Argon2id) ---
def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


# --- JWT Tokens ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


# --- HMAC Signed Expiring URLs for Files ---
def create_signed_file_token(doc_id: str, user_id: str, ttl_seconds: int = 300) -> str:
    """Creates a URL-safe signed expiring token bound to doc_id and user_id."""
    exp = int(time.time()) + ttl_seconds
    raw_message = f"{doc_id}:{user_id}:{exp}".encode("utf-8")
    sig = hmac.new(settings.JWT_SECRET.encode("utf-8"), raw_message, hashlib.sha256).hexdigest()
    payload = f"{doc_id}|{user_id}|{exp}|{sig}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")


def verify_signed_file_token(token_b64: str, expected_doc_id: str, expected_user_id: Optional[str] = None) -> bool:
    try:
        raw = base64.urlsafe_b64decode(token_b64.encode("utf-8")).decode("utf-8")
        parts = raw.split("|")
        if len(parts) != 4:
            return False
        doc_id, user_id, exp_str, sig = parts
        exp = int(exp_str)
        if time.time() > exp:
            return False
        if doc_id != expected_doc_id:
            return False
        if expected_user_id and user_id != expected_user_id and user_id != "magic_link":
            return False
        
        raw_message = f"{doc_id}:{user_id}:{exp}".encode("utf-8")
        expected_sig = hmac.new(settings.JWT_SECRET.encode("utf-8"), raw_message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected_sig)
    except Exception:
        return False


# --- Magic Links for Patient Uploads ---
def create_magic_upload_token(patient_id: str, query_letter_id: Optional[str] = None, ttl_hours: int = 72) -> str:
    exp = int(time.time()) + (ttl_hours * 3600)
    raw = f"{patient_id}:{query_letter_id or ''}:{exp}".encode("utf-8")
    sig = hmac.new(settings.JWT_SECRET.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    payload = f"{patient_id}|{query_letter_id or ''}|{exp}|{sig}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")


def verify_magic_upload_token(token_b64: str) -> Optional[Dict[str, Any]]:
    try:
        raw = base64.urlsafe_b64decode(token_b64.encode("utf-8")).decode("utf-8")
        parts = raw.split("|")
        if len(parts) != 4:
            return None
        patient_id, query_letter_id, exp_str, sig = parts
        exp = int(exp_str)
        if time.time() > exp:
            return None
        raw_message = f"{patient_id}:{query_letter_id}:{exp}".encode("utf-8")
        expected_sig = hmac.new(settings.JWT_SECRET.encode("utf-8"), raw_message, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        return {
            "patient_id": patient_id,
            "query_letter_id": query_letter_id if query_letter_id else None,
            "exp": exp
        }
    except Exception:
        return None


# --- Masking Utilities ---
def mask_aadhaar(aadhaar: Optional[str]) -> Optional[str]:
    if not aadhaar:
        return None
    clean = "".join(filter(str.isdigit, aadhaar))
    if len(clean) >= 4:
        last4 = clean[-4:]
        return f"XXXX-XXXX-{last4}"
    return "XXXX-XXXX-XXXX"


def mask_policy_number(policy: Optional[str]) -> str:
    if not policy:
        return "********"
    if len(policy) <= 4:
        return "****" + policy
    return "****" + policy[-4:]


def mask_claim_ref(claim_ref: Optional[str]) -> str:
    if not claim_ref:
        return "****"
    if len(claim_ref) <= 4:
        return "****" + claim_ref
    return "****" + claim_ref[-4:]


def mask_phone(phone: Optional[str]) -> str:
    if not phone:
        return "******"
    if len(phone) <= 4:
        return phone
    return phone[:3] + "******" + phone[-2:]


def mask_email(email: Optional[str]) -> str:
    if not email or "@" not in email:
        return "***@***.***"
    user, domain = email.split("@", 1)
    if len(user) <= 2:
        masked_user = user[0] + "*"
    else:
        masked_user = user[:2] + "***" + user[-1]
    return f"{masked_user}@{domain}"
