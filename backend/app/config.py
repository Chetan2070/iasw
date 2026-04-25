"""
IASW Backend Configuration

Loads settings from environment variables with validation.
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ===================
    # Application
    # ===================
    APP_NAME: str = "IASW"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    # ===================
    # Database
    # ===================
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/iasw",
        description="Async database URL for SQLAlchemy"
    )
    DATABASE_SYNC_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/iasw",
        description="Sync database URL for Alembic migrations"
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # ===================
    # Redis
    # ===================
    REDIS_URL: str = "redis://localhost:6379/0"

    # ===================
    # LLM (Anthropic Claude)
    # ===================
    ANTHROPIC_API_KEY: str = Field(
        default="",
        description="Anthropic API key for Claude"
    )
    ANTHROPIC_BASE_URL: str = Field(
        default="",
        description="Anthropic API base URL (for proxy)"
    )
    LLM_MODEL: str = "anthropic--claude-4.5-opus"
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.0

    # ===================
    # OCR
    # ===================
    TESSERACT_CMD: str = "/usr/bin/tesseract"
    OCR_CONFIDENCE_THRESHOLD: float = 0.6
    GOOGLE_VISION_ENABLED: bool = False
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # ===================
    # Storage
    # ===================
    STORAGE_TYPE: str = "local"  # "local" or "s3"
    STORAGE_PATH: str = "./storage"
    S3_BUCKET: str = ""
    S3_REGION: str = ""

    # ===================
    # Processing Thresholds
    # ===================
    FORGERY_PASS_THRESHOLD: float = 0.85
    FORGERY_FAIL_THRESHOLD: float = 0.60
    NAME_MATCH_HIGH_THRESHOLD: float = 0.95
    NAME_MATCH_LOW_THRESHOLD: float = 0.85

    # Confidence Score Weights
    WEIGHT_NAME_MATCH: float = 0.40
    WEIGHT_DOC_AUTHENTICITY: float = 0.30
    WEIGHT_OCR_CONFIDENCE: float = 0.15
    WEIGHT_EXTRACTION_CONFIDENCE: float = 0.15

    # Risk Tier Thresholds
    RISK_LOW_THRESHOLD: float = 0.90
    RISK_MEDIUM_THRESHOLD: float = 0.70

    # ===================
    # Security
    # ===================
    SECRET_KEY: str = "change-me-in-production"
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # ===================
    # Celery
    # ===================
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    CELERY_TASK_TIME_LIMIT: int = 300  # 5 minutes
    CELERY_TASK_SOFT_TIME_LIMIT: int = 270  # 4.5 minutes

    # ===================
    # LangSmith (Observability)
    # ===================
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "iasw"

    # ===================
    # File Validation
    # ===================
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: List[str] = ["application/pdf", "image/jpeg", "image/png", "image/tiff"]
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Export singleton instance
settings = get_settings()
