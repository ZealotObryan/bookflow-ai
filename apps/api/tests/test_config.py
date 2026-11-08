import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.core.config import Settings


def test_production_settings_require_secure_infrastructure() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        database_url="postgresql+psycopg://user:pass@db.example.com/bookflow?sslmode=verify-full",
        redis_url="rediss://default:secret@redis.example.com:6379/0",
        jwt_secret_key="j" * 64,
        otp_pepper="p" * 64,
        otp_encryption_key=Fernet.generate_key().decode(),
        frontend_base_url="https://bookflow.example.com",
        smtp_host="smtp.example.com",
        smtp_username="bookflow",
        smtp_password="smtp-secret",
        smtp_from_email="no-reply@example.com",
    )
    assert settings.environment == "production"


def test_production_rejects_sample_secrets() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            database_url="postgresql+psycopg://user:pass@db.example.com/bookflow?sslmode=verify-full",
            redis_url="rediss://default:secret@redis.example.com:6379/0",
            jwt_secret_key="replace-with-a-long-random-secret",
            otp_pepper="p" * 64,
            otp_encryption_key=Fernet.generate_key().decode(),
            frontend_base_url="https://bookflow.example.com",
            smtp_host="smtp.example.com",
            smtp_username="bookflow",
            smtp_password="smtp-secret",
            smtp_from_email="no-reply@example.com",
        )


def test_production_rejects_insecure_redis() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            database_url="postgresql+psycopg://user:pass@db.example.com/bookflow?sslmode=verify-full",
            redis_url="redis://localhost:6379/0",
            jwt_secret_key="j" * 64,
            otp_pepper="p" * 64,
            otp_encryption_key=Fernet.generate_key().decode(),
            frontend_base_url="https://bookflow.example.com",
            smtp_host="smtp.example.com",
            smtp_username="bookflow",
            smtp_password="smtp-secret",
            smtp_from_email="no-reply@example.com",
        )
