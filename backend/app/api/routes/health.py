"""Health and readiness endpoints."""

import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_settings
from app.core.config import Settings
from app.schemas.common import APIResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=APIResponse)
def health(settings: Settings = Depends(get_settings)):
    return APIResponse.ok(
        message="Service is healthy",
        data={
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
        },
    )


@router.get("/ready", response_model=APIResponse)
def readiness(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    checks: dict = {}

    # Database
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    # Storage
    storage_path = Path(settings.STORAGE_DIR)
    checks["storage"] = (
        "ok" if storage_path.exists() and storage_path.is_dir() else "error: directory missing"
    )

    # FFprobe – required for video and audio inspection
    try:
        result = subprocess.run(
            [settings.FFPROBE_PATH, "-version"],
            capture_output=True,
            timeout=5,
        )
        checks["ffprobe"] = "ok" if result.returncode == 0 else f"error: exit {result.returncode}"
    except FileNotFoundError:
        checks["ffprobe"] = (
            "unavailable: ffprobe not found – video/audio uploads will fail. "
            "Install FFmpeg and set FFPROBE_PATH in .env"
        )
    except Exception as exc:
        checks["ffprobe"] = f"error: {exc}"

    provider_checks = {
        "gemini": bool(settings.GEMINI_API_KEY),
        "openai-whisper": bool(settings.OPENAI_API_KEY),
    }
    selected_providers = [
        settings.VISION_PROVIDER,
        settings.VIDEO_PROVIDER,
        settings.AUDIO_TRANSCRIPTION_PROVIDER,
        settings.AUDIO_UNDERSTANDING_PROVIDER,
        settings.TEXT_GENERATION_PROVIDER,
    ]
    for provider in selected_providers:
        if provider in provider_checks:
            checks[f"provider:{provider}"] = "configured" if provider_checks[provider] else "missing_api_key"

    all_ok = checks["database"] == "ok" and checks["storage"] == "ok" and checks["ffprobe"] == "ok"

    if not all_ok:
        response = APIResponse.fail("Service not ready", "SERVICE_UNAVAILABLE", checks)
        return JSONResponse(status_code=503, content=response.model_dump())
    return APIResponse.ok("Ready", data={"checks": checks})
