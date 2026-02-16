"""Configuration management for CrackATS."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Configuration
    groq_api_key: str = Field(
        default="",
        description="Groq API key for AI generation",
    )
    groq_model: Literal[
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
    ] = Field(
        default="llama-3.3-70b-versatile",
        description="Default Groq model to use",
    )
    groq_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for AI generation",
    )
    groq_max_tokens: int = Field(
        default=4000,
        ge=100,
        le=8000,
        description="Maximum tokens for AI generation",
    )

    # Database
    db_path: Path = Field(
        default=Path("applications.db"),
        description="Path to SQLite database file",
    )

    # Templates
    templates_dir: Path = Field(
        default=Path("templates"),
        description="Directory containing template files",
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level",
    )

    # Security
    max_file_size_mb: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum file size for uploads in MB",
    )
    allowed_file_extensions: list[str] = Field(
        default=[".tex", ".txt", ".json", ".html"],
        description="Allowed file extensions",
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings instance
    """
    return Settings()
