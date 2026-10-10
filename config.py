from pydantic import BaseModel, Field
from pathlib import Path
from functools import lru_cache
from typing import List
import os

class Settings(BaseModel):
    """Application runtime configuration and environment variables."""
    app_name: str = Field(default_factory=lambda: os.getenv("APP_NAME", "Patient Management System API"))
    app_version: str = Field(default_factory=lambda: os.getenv("APP_VERSION", "1.0.0"))
    app_description: str = Field(
        default_factory=lambda: os.getenv(
            "APP_DESCRIPTION",
            "A high-performance RESTful API built with FastAPI and Pydantic for managing patient records, calculating real-time BMI metrics, and evaluating health statuses."
        )
    )
    environment: str = Field(default_factory=lambda: os.getenv("APP_ENV", "production"))
    debug: bool = Field(default_factory=lambda: os.getenv("APP_DEBUG", "false").lower() in ("true", "1", "yes"))
    data_file_path: Path = Field(
        default_factory=lambda: Path(os.getenv("DATA_FILE_PATH", str(Path(__file__).resolve().parent / "patient.json")))
    )
    cors_origins: List[str] = Field(
        default_factory=lambda: [x.strip() for x in os.getenv("CORS_ORIGINS", "*").split(",") if x.strip()]
    )
    admin_api_key: str = Field(default_factory=lambda: os.getenv("ADMIN_API_KEY", "admin-secret-key-123"))
    api_key_header_name: str = "X-API-Key"
    contact_name: str = "Ekta Singh"
    contact_email: str = "ektasingh19.12.2004@gmail.com"

@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
