import binascii
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BookFlow AI API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://bookflow:change-this-local-password@localhost:5432/bookflow"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: str = "development-only-change-this-secret-before-deploying"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "bookflow-ai"
    jwt_audience: str = "bookflow-ai-api"
    access_token_minutes: int = 10
    refresh_token_days: int = 30
    session_idle_timeout_minutes: int = 720
    otp_pepper: str = "development-only-change-this-otp-pepper"
    otp_encryption_key: str = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
    email_verification_hours: int = 24
    password_reset_minutes: int = 15
    frontend_base_url: str = "http://localhost:3000"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_ssl: bool = False
    tumasend_whatsapp_api_key: str | None = None
    tumasend_sms_api_key: str | None = None
    tumasend_base_url: str = "https://gateway.tumasend.com"
    tumasend_sms_sender_id: str | None = None
    tumasend_webhook_secret: str | None = None
    meta_whatsapp_access_token: str | None = None
    meta_whatsapp_phone_number_id: str | None = None
    meta_whatsapp_app_id: str | None = None
    meta_whatsapp_app_secret: str | None = None
    meta_whatsapp_verify_token: str | None = None
    meta_whatsapp_graph_api_version: str = "v22.0"
    meta_whatsapp_embedded_signup_config_id: str | None = None
    meta_whatsapp_solution_id: str | None = None
    meta_whatsapp_token_encryption_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.jwt_algorithm not in {"HS256", "HS384", "HS512"}:
            raise ValueError("JWT_ALGORITHM must be one of HS256, HS384, or HS512")
        if not 5 <= self.access_token_minutes <= 15:
            raise ValueError("ACCESS_TOKEN_MINUTES must be between 5 and 15")
        if not 1 <= self.refresh_token_days <= 30:
            raise ValueError("REFRESH_TOKEN_DAYS must be between 1 and 30")
        if self.session_idle_timeout_minutes < 5:
            raise ValueError("SESSION_IDLE_TIMEOUT_MINUTES must be at least 5")
        try:
            Fernet(self.otp_encryption_key.encode("ascii"))
        except (ValueError, TypeError, InvalidToken, binascii.Error):
            raise ValueError("OTP_ENCRYPTION_KEY must be a valid Fernet key") from None
        if self.meta_whatsapp_token_encryption_key:
            try:
                Fernet(self.meta_whatsapp_token_encryption_key.encode("ascii"))
            except (ValueError, TypeError, InvalidToken, binascii.Error):
                raise ValueError("META_WHATSAPP_TOKEN_ENCRYPTION_KEY must be a valid Fernet key") from None

        if self.environment.lower() == "production":
            secrets = {
                "JWT_SECRET_KEY": self.jwt_secret_key,
                "OTP_PEPPER": self.otp_pepper,
                "OTP_ENCRYPTION_KEY": self.otp_encryption_key,
            }
            placeholders = ("development-only", "replace-with", "change-this", "example")
            for name, value in secrets.items():
                is_sample_fernet = (
                    name == "OTP_ENCRYPTION_KEY"
                    and value == "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
                )
                if len(value) < 32 or value.lower().startswith(placeholders) or is_sample_fernet:
                    raise ValueError(f"Production requires a unique high-entropy {name}")
            if not self.redis_url.startswith("rediss://") or "@" not in self.redis_url:
                raise ValueError("Production REDIS_URL must use TLS and authenticated Redis credentials")
            if "sslmode=verify-full" not in self.database_url:
                raise ValueError("Production DATABASE_URL must use PostgreSQL TLS with server certificate verification (sslmode=verify-full)")
            if not self.frontend_base_url.startswith("https://"):
                raise ValueError("Production FRONTEND_BASE_URL must use HTTPS")
            if not all([self.smtp_host, self.smtp_username, self.smtp_password, self.smtp_from_email]):
                raise ValueError("Production requires configured transactional SMTP credentials")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
