import binascii
from functools import lru_cache
from urllib.parse import parse_qs, urlsplit

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
    resend_api_key: str | None = None
    resend_from_email: str = "onboarding@resend.dev"
    resend_test_recipient: str | None = None
    resend_test_mode: bool = True
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
    cloudflare_turnstile_site_key: str | None = None
    cloudflare_turnstile_secret_key: str | None = None

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
            redis_url = urlsplit(self.redis_url)
            redis_authenticated = bool(redis_url.password)
            redis_uses_tls = redis_url.scheme == "rediss" and redis_authenticated
            redis_uses_private_railway_network = (
                redis_url.scheme == "redis"
                and bool(redis_url.hostname)
                and redis_url.hostname.endswith(".railway.internal")
                and redis_authenticated
            )
            if not (redis_uses_tls or redis_uses_private_railway_network):
                raise ValueError(
                    "Production REDIS_URL must use authenticated TLS (rediss://) "
                    "or authenticated Railway private networking"
                )

            database_url = urlsplit(self.database_url)
            database_ssl_modes = parse_qs(database_url.query).get("sslmode", [])
            database_authenticated = bool(database_url.username and database_url.password)
            database_uses_verified_tls = "verify-full" in database_ssl_modes
            database_uses_private_railway_network = (
                bool(database_url.hostname)
                and database_url.hostname.endswith(".railway.internal")
                and "require" in database_ssl_modes
            )
            if not database_authenticated or not (
                database_uses_verified_tls or database_uses_private_railway_network
            ):
                raise ValueError(
                    "Production DATABASE_URL must use authenticated PostgreSQL TLS "
                    "(sslmode=verify-full) or authenticated Railway private networking "
                    "with sslmode=require"
                )
            if not self.frontend_base_url.startswith("https://"):
                raise ValueError("Production FRONTEND_BASE_URL must use HTTPS")
            if not all([self.resend_api_key, self.resend_from_email]):
                raise ValueError("Production requires configured Resend API credentials")
            if self.resend_test_mode and not self.resend_test_recipient:
                raise ValueError("RESEND_TEST_RECIPIENT is required while RESEND_TEST_MODE is enabled")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
