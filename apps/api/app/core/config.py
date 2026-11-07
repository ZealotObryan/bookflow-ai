from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BookFlow AI API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://bookflow:change-this-local-password@localhost:5432/bookflow"
    jwt_secret_key: str = "development-only-change-this-secret-before-deploying"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    otp_pepper: str = "development-only-change-this-otp-pepper"
    otp_encryption_key: str = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
    tumasend_api_key: str | None = None
    tumasend_base_url: str = "https://gateway.tumasend.com"
    tumasend_sms_sender_id: str | None = None
    tumasend_webhook_secret: str | None = None

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def require_production_secrets(self) -> "Settings":
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
