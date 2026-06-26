import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str
    PROJECT_NAME: str
    DESCRIPTION: str
    VERSION: str

    DATABASE_URL: str

    OPENROUTER_MODEL: str
    OPENROUTER_API_ENDPOINT: str
    OPENROUTER_API_KEY: str

    AWS_BEARER_TOKEN_BEDROCK: str

    HASHING_ITERATIONS: int
    JWT_SIGNATURE: str
    TOKEN_EXPIRY_HOURS: int

    OSRM_BASE_URL: str

    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str | None = None
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    SMTP_TIMEOUT_SECONDS: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

os.environ["AWS_BEARER_TOKEN_BEDROCK"] = settings.AWS_BEARER_TOKEN_BEDROCK