"""File utility helpers."""

import mimetypes
from pathlib import Path


# Mapping from extension to canonical media type
_EXT_TO_MEDIA_TYPE: dict[str, str] = {
    "jpg": "image", "jpeg": "image", "png": "image", "webp": "image",
    "gif": "image", "bmp": "image", "tiff": "image",
    "mp4": "video", "mov": "video", "avi": "video",
    "mkv": "video", "webm": "video", "flv": "video",
    "wav": "audio", "mp3": "audio", "m4a": "audio",
    "aac": "audio", "ogg": "audio", "flac": "audio",
}


def get_extension(filename: str) -> str:
    """Return lowercase extension without leading dot."""
    return Path(filename).suffix.lstrip(".").lower()


def get_media_type_from_extension(extension: str) -> str | None:
    """Return 'image', 'video', or 'audio' for a known extension."""
    return _EXT_TO_MEDIA_TYPE.get(extension.lower())


def guess_mime_type(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"
