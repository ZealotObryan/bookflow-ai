from functools import lru_cache

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
