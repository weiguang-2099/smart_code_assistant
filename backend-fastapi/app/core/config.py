from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database Configuration
    DATABASE_URL: str = "mysql+aiomysql://appuser:apppassword@localhost:3307/smart_code_assistant"
    DB_HOST: str = "localhost"
    DB_PORT: int = 3307
    DB_USER: str = "appuser"
    DB_PASSWORD: str = "apppassword"
    DB_NAME: str = "smart_code_assistant"

    # FastAPI Configuration
    FASTAPI_ENV: str = "development"
    FASTAPI_PORT: int = 8000
    FASTAPI_HOST: str = "0.0.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"]

    # ZhipuAI Configuration
    ZHIPUAI_API_KEY: str = ""

    # Datalab (Marker) API Configuration
    DATALAB_API_KEY: str = ""
    DATALAB_API_URL: str = "https://www.datalab.to/api/v1/marker"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
