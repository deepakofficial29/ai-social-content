"""Validation service – verifies file type, size, and content integrity."""

import io
from typing import Tuple

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import (
    CorruptedMediaError,
    EmptyFileError,
    FileTooLargeError,
    UnsupportedMediaTypeError,
)
from app.core.logging import get_logger
from app.utils.file_utils import get_extension, get_media_type_from_extension

logger = get_logger(__name__)

# MIME type prefix → expected media type
_MIME_MEDIA_MAP = {
    "image/": "image",
    "video/": "video",
    "audio/": "audio",
}

# Known safe MIME types per extension (non-exhaustive guard)
_EXT_MIME_WHITELIST: dict[str, set[str]] = {
    "jpg":  {"image/jpeg"},
    "jpeg": {"image/jpeg"},
    "png":  {"image/png"},
    "webp": {"image/webp"},
    "mp4":  {"video/mp4"},
    "mov":  {"video/quicktime"},
    "avi":  {"video/x-msvideo", "video/avi"},
    "mkv":  {"video/x-matroska"},
    "webm": {"video/webm"},
    "wav":  {"audio/wav", "audio/x-wav"},
    "mp3":  {"audio/mpeg", "audio/mp3"},
    "m4a":  {"audio/mp4", "audio/x-m4a", "audio/m4a"},
    "aac":  {"audio/aac"},
}


async def read_and_validate_upload(
    file: UploadFile,
    settings=None,
) -> Tuple[bytes, str, str]:
    """Read *file* fully, validate it, and return (data, extension, media_type).

    Raises a typed AppError on any validation failure.
    Does NOT perform deep content inspection (that is done by the metadata service).
    """
    if settings is None:
        settings = get_settings()

    # --- Extension check ---
    ext = get_extension(file.filename or "")
    if not ext:
        raise UnsupportedMediaTypeError("File has no extension.")

    allowed = settings.all_allowed_extensions
    if ext not in allowed:
        raise UnsupportedMediaTypeError(
            f"Extension '.{ext}' is not allowed.",
            {"allowed": sorted(allowed)},
        )

    media_type = get_media_type_from_extension(ext)
    if media_type is None:
        raise UnsupportedMediaTypeError(f"Cannot determine media type for '.{ext}'.")

    # --- Read with size guard ---
    max_bytes = settings.max_upload_size_bytes
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise FileTooLargeError(
            f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit.",
            {"max_mb": settings.MAX_UPLOAD_SIZE_MB},
        )
    if len(data) == 0:
        raise EmptyFileError("Uploaded file is empty.")

    # --- MIME type cross-check (client-provided, not trusted alone) ---
    client_mime = (file.content_type or "").lower().split(";")[0].strip()
    if client_mime and ext in _EXT_MIME_WHITELIST:
        allowed_mimes = _EXT_MIME_WHITELIST[ext]
        if client_mime not in allowed_mimes:
            logger.warning(
                "MIME mismatch for .%s: client sent '%s', expected one of %s",
                ext, client_mime, allowed_mimes,
            )
            raise UnsupportedMediaTypeError(
                f"MIME type '{client_mime}' does not match extension '.{ext}'.",
                {"expected": sorted(allowed_mimes), "received": client_mime},
            )

    return data, ext, media_type


def validate_image_bytes(data: bytes, extension: str | None = None) -> str:
    """Use Pillow to verify actual format, integrity, and configured limits."""
    try:
        from PIL import Image, UnidentifiedImageError
        with Image.open(io.BytesIO(data)) as img:
            img.verify()  # detects truncated / corrupted files
            img_format = (img.format or "").upper()
            with Image.open(io.BytesIO(data)) as decoded:
                width, height = decoded.size
                pixels = width * height
                settings = get_settings()
                if width > settings.MAX_IMAGE_DIMENSION or height > settings.MAX_IMAGE_DIMENSION:
                    raise CorruptedMediaError(
                        f"Image dimensions exceed the configured {settings.MAX_IMAGE_DIMENSION}px limit.",
                        {"width": width, "height": height},
                    )
                if pixels > settings.MAX_IMAGE_PIXELS:
                    raise CorruptedMediaError(
                        f"Image exceeds the configured {settings.MAX_IMAGE_PIXELS} pixel limit.",
                        {"pixels": pixels},
                    )
            format_by_extension = {
                "jpg": "JPEG",
                "jpeg": "JPEG",
                "png": "PNG",
                "webp": "WEBP",
            }
            if extension:
                expected = format_by_extension.get(extension.lower())
                if expected and img_format != expected:
                    raise CorruptedMediaError(
                        f"Image signature does not match .{extension}.",
                        {"detected": img_format, "expected": expected},
                    )
            return img_format
    except Exception as exc:
        if isinstance(exc, CorruptedMediaError):
            raise
        raise CorruptedMediaError(f"Image validation failed: {exc}") from exc
