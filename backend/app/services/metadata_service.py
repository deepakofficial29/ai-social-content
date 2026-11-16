"""Metadata extraction service.

Extracts technical metadata from images, videos, and audio files.
Does NOT perform any AI-based analysis.
"""

import io
import tempfile
from pathlib import Path
from typing import Any, Dict

from app.core.exceptions import CorruptedMediaError, FFprobeError
from app.core.logging import get_logger
from app.utils.media_utils import run_ffprobe

logger = get_logger(__name__)


def extract_image_metadata(data: bytes) -> Dict[str, Any]:
    """Return width, height, format, and mode for image bytes."""
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as img:
            img.load()  # force full decode to catch truncated files
            return {
                "width": img.width,
                "height": img.height,
                "format": img.format or "UNKNOWN",
                "mode": img.mode,
            }
    except Exception as exc:
        raise CorruptedMediaError(f"Cannot read image metadata: {exc}") from exc


def extract_video_metadata(data: bytes, extension: str) -> Dict[str, Any]:
    """Write *data* to a temp file, run ffprobe, and return structured metadata."""
    with tempfile.NamedTemporaryFile(suffix=f".{extension}", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        probe = run_ffprobe(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    streams = probe.get("streams", [])
    fmt = probe.get("format", {})

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    metadata: Dict[str, Any] = {"file_size": len(data)}

    if video_stream:
        metadata["width"] = video_stream.get("width")
        metadata["height"] = video_stream.get("height")
        metadata["video_codec"] = video_stream.get("codec_name")
        # Parse frame rate fraction e.g. "30000/1001"
        r_frame_rate = video_stream.get("r_frame_rate", "")
        if "/" in r_frame_rate:
            num, den = r_frame_rate.split("/")
            try:
                metadata["frame_rate"] = round(int(num) / int(den), 3) if int(den) else None
            except (ValueError, ZeroDivisionError):
                metadata["frame_rate"] = None

    duration = fmt.get("duration") or (video_stream or {}).get("duration")
    if duration:
        try:
            metadata["duration_seconds"] = round(float(duration), 3)
        except ValueError:
            pass

    metadata["has_audio"] = audio_stream is not None
    if audio_stream:
        metadata["audio_codec"] = audio_stream.get("codec_name")

    return metadata


def extract_audio_metadata(data: bytes, extension: str) -> Dict[str, Any]:
    """Write *data* to a temp file, run ffprobe, and return structured metadata."""
    with tempfile.NamedTemporaryFile(suffix=f".{extension}", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        probe = run_ffprobe(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    streams = probe.get("streams", [])
    fmt = probe.get("format", {})
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    metadata: Dict[str, Any] = {"file_size": len(data)}

    if audio_stream:
        metadata["codec"] = audio_stream.get("codec_name")
        try:
            metadata["sample_rate"] = int(audio_stream.get("sample_rate", 0)) or None
        except (ValueError, TypeError):
            metadata["sample_rate"] = None
        try:
            metadata["channels"] = int(audio_stream.get("channels", 0)) or None
        except (ValueError, TypeError):
            metadata["channels"] = None

    duration = fmt.get("duration") or (audio_stream or {}).get("duration")
    if duration:
        try:
            metadata["duration_seconds"] = round(float(duration), 3)
        except ValueError:
            pass

    return metadata
