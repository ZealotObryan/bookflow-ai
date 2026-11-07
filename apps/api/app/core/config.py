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
    otp_delivery_provider: str = "unconfigured"

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def require_production_secrets(self) -> "Settings":
        if self.environment.lower() == "production":
            if self.jwt_secret_key.startswith("development-only") or len(self.jwt_secret_key) < 32:
                raise ValueError("Production requires a strong JWT_SECRET_KEY of at least 32 characters")
            if self.otp_pepper.startswith("development-only") or len(self.otp_pepper) < 32:
                raise ValueError("Production requires a separate strong OTP_PEPPER of at least 32 characters")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
