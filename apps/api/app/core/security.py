import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from cryptography.fernet import Fernet
from pwdlib import PasswordHash

from app.core.config import get_settings

_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def create_access_token(user_id: uuid.UUID, session_id: uuid.UUID) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(phone: str, code: str) -> str:
    pepper = get_settings().otp_pepper.encode("utf-8")
    return hmac.new(pepper, f"{phone}:{code}".encode("utf-8"), hashlib.sha256).hexdigest()


def encrypt_otp(code: str) -> str:
    key = get_settings().otp_encryption_key.encode("ascii")
    return Fernet(key).encrypt(code.encode("ascii")).decode("ascii")


def decrypt_otp(ciphertext: str) -> str:
    key = get_settings().otp_encryption_key.encode("ascii")
    return Fernet(key).decrypt(ciphertext.encode("ascii")).decode("ascii")
