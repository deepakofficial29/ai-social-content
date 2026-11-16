"""Central application configuration via Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "multimodal-caption-generator"
    APP_ENV: str = "development"
    DEBUG: bool = True
    APP_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = 100

    # Allowed media types (extensions without dot)
    ALLOWED_IMAGE_TYPES: List[str] = ["jpg", "jpeg", "png", "webp"]
    ALLOWED_VIDEO_TYPES: List[str] = ["mp4", "mov", "avi", "mkv", "webm"]
    ALLOWED_AUDIO_TYPES: List[str] = ["wav", "mp3", "m4a", "aac"]

    # Storage
    STORAGE_DIR: str = "storage"

    # Database
    DATABASE_URL: str = "sqlite:///./caption_generator.db"

    # FFmpeg
    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("APP_ENV")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"APP_ENV must be one of {allowed}")
        return v

    @model_validator(mode="after")
    def ensure_storage_dir(self) -> "Settings":
        Path(self.STORAGE_DIR).mkdir(parents=True, exist_ok=True)
        return self

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def all_allowed_extensions(self) -> set[str]:
        return set(
            self.ALLOWED_IMAGE_TYPES
            + self.ALLOWED_VIDEO_TYPES
            + self.ALLOWED_AUDIO_TYPES
        )

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
