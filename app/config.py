from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str
    PROJECT_NAME: str
    DESCRIPTION: str
    VERSION: str

    DATABASE_URL: str
    DATABASE_KEY: str

    OPENROUTER_MODEL: str
    OPENROUTER_API_ENDPOINT: str
    OPENROUTER_API_KEY: str
    HASHING_ITERATIONS: int
    JWT_SIGNATURE: str
    TOKEN_EXPIRY_HOURS: int
    OSRM_BASE_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()