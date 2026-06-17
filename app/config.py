# import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str
    PROJECT_NAME: str
    DESCRIPTION: str
    VERSION: str

    DATABASE_URL: str
    DATABASE_KEY: str

    AI_API_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()