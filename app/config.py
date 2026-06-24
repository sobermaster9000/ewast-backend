# import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "EWAST API"
    DESCRIPTION: str = "An API service for EWAST"
    VERSION: str = "1.0.0"

    DATABASE_URL: str = "postgresql://postgres:postgres123@localhost:5432/ewast_db"
    DATABASE_KEY: str

    OPENROUTER_MODEL: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
    OPENROUTER_API_ENDPOINT: str = "https://openrouter.ai/api/v1/chat/completions"
    OPENROUTER_API_KEY: str = "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"
    HASHING_ITERATIONS: int = 694200
    JWT_SIGNATURE: str = "6308733e506b23bcb530d80642be4498798e5c99cec972b78816f27c38a0fb777018bd06c951e19dbb3b2ec1e1056408248da9d51b15d4a4a3af0d4dc3fe4d80"
    TOKEN_EXPIRY_HOURS: int = 24
    OSRM_BASE_URL: str = "https://router.project-osrm.org"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()