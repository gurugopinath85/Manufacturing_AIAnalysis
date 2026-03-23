"""
Configuration settings for the Manufacturing AI Analysis application.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # LLM Settings
    default_llm_provider: str = "openai"  # "openai" or "anthropic"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4000
    
    # Application Settings
    app_title: str = "Manufacturing AI Analysis"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # File Upload Settings
    max_file_size_mb: int = 100
    allowed_file_types: list = [".csv", ".xlsx", ".xls"]
    upload_directory: str = "app/data/uploads"
    
    # Database Settings (future use)
    database_url: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings


def validate_api_keys():
    """Validate that at least one API key is configured."""
    if not settings.openai_api_key and not settings.anthropic_api_key:
        raise ValueError(
            "At least one LLM API key must be configured. "
            "Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable."
        )


def get_upload_path() -> str:
    """Get the absolute path to the upload directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, settings.upload_directory)
