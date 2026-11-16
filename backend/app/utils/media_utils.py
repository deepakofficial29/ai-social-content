"""Media utility helpers – FFprobe wrapper."""

import json
import subprocess
from typing import Any, Dict

from app.core.config import get_settings
from app.core.exceptions import FFprobeError
from app.core.logging import get_logger

logger = get_logger(__name__)


def run_ffprobe(file_path: str) -> Dict[str, Any]:
    """Run ffprobe on *file_path* and return the parsed JSON output."""
    settings = get_settings()
    cmd = [
        settings.FFPROBE_PATH,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        file_path,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        raise FFprobeError(
            "ffprobe not found. Ensure FFmpeg is installed and FFPROBE_PATH is configured."
        )
    except subprocess.TimeoutExpired:
        raise FFprobeError("ffprobe timed out.")

    if result.returncode != 0:
        raise FFprobeError(
            f"ffprobe failed (exit {result.returncode}): {result.stderr[:500]}"
        )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise FFprobeError(f"ffprobe returned invalid JSON: {exc}") from exc
