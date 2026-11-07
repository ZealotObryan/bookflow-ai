from functools import lru_cache

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
    tumasend_whatsapp_api_key: str | None = None
    tumasend_sms_api_key: str | None = None
    tumasend_base_url: str = "https://gateway.tumasend.com"
    tumasend_sms_sender_id: str | None = None
    tumasend_webhook_secret: str | None = None

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.jwt_algorithm not in {"HS256", "HS384", "HS512"}:
            raise ValueError("JWT_ALGORITHM must be one of HS256, HS384, or HS512")
        if self.access_token_minutes < 5 or self.access_token_minutes > 15:
            raise ValueError("ACCESS_TOKEN_MINUTES must be between 5 and 15")
        if self.refresh_token_days < 1 or self.refresh_token_days > 30:
            raise ValueError("REFRESH_TOKEN_DAYS must be between 1 and 30")
        if self.session_idle_timeout_minutes < 5:
            raise ValueError("SESSION_IDLE_TIMEOUT_MINUTES must be at least 5")
        if self.environment.lower() == "production":
            secrets = {
                "JWT_SECRET_KEY": self.jwt_secret_key,
                "OTP_PEPPER": self.otp_pepper,
                "OTP_ENCRYPTION_KEY": self.otp_encryption_key,
            }
            for name, value in secrets.items():
                if value.startswith("development-only") or len(value) < 32:
                    raise ValueError(f"Production requires a strong {name} of at least 32 characters")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
