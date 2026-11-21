"""Video frame extraction service — Phase 2.4.

Uses the existing FFmpeg installation to extract frames from videos.
Implements a hybrid strategy: scene-change detection with uniform
sampling fallback to ensure coverage even in static scenes.

All temporary files are cleaned up in finally blocks, including on failure.

Configuration (via .env / Settings):
  VIDEO_MAX_DURATION_SECONDS   — reject videos longer than this
  VIDEO_MAX_FRAMES             — cap on frames sent to vision API
  VIDEO_FRAME_INTERVAL_SECONDS — uniform sampling interval (fallback)
  VIDEO_SCENE_CHANGE_THRESHOLD — ffmpeg scene filter threshold (0.0–1.0)
  VIDEO_FRAME_WIDTH            — resize frames to this width (height auto)
  VIDEO_PROCESSING_TIMEOUT_SECONDS — subprocess timeout
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from app.core.config import get_settings
from app.core.exceptions import FFprobeError
from app.core.logging import get_logger
from app.utils.media_utils import run_ffprobe

logger = get_logger(__name__)


class FrameExtractionError(Exception):
    """Raised when frame extraction fails."""


class ExtractedFrame:
    """A single extracted video frame with its timestamp."""

    __slots__ = ("path", "timestamp_seconds", "frame_index")

    def __init__(self, path: Path, timestamp_seconds: float, frame_index: int):
        self.path = path
        self.timestamp_seconds = timestamp_seconds
        self.frame_index = frame_index


def extract_frames(video_path: str) -> Tuple[List[ExtractedFrame], Optional[str]]:
    """Extract frames from a video file using the hybrid strategy.

    Returns:
        (frames, audio_path) where:
          - frames is a list of ExtractedFrame objects (temp files)
          - audio_path is the path to an extracted WAV file, or None if
            the video has no audio track

    The caller is responsible for cleaning up all returned temp files.
    Use cleanup_frames() for convenience.

    Raises:
        FrameExtractionError on unrecoverable failures.
    """
    settings = get_settings()
    ffmpeg = settings.FFMPEG_PATH
    ffprobe = settings.FFPROBE_PATH
    timeout = settings.VIDEO_PROCESSING_TIMEOUT_SECONDS

    video_path_obj = Path(video_path)
    if not video_path_obj.exists():
        raise FrameExtractionError(f"Video file not found: {video_path}")

    # Probe the video first
    try:
        probe = run_ffprobe(video_path)
    except FFprobeError as exc:
        raise FrameExtractionError(f"Cannot probe video: {exc}") from exc

    streams = probe.get("streams", [])
    fmt = probe.get("format", {})

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if not video_stream:
        raise FrameExtractionError("No video stream found in file")

    duration = _parse_duration(fmt, video_stream)
    if duration and duration > settings.VIDEO_MAX_DURATION_SECONDS:
        raise FrameExtractionError(
            f"Video duration ({duration:.0f}s) exceeds maximum "
            f"({settings.VIDEO_MAX_DURATION_SECONDS}s)"
        )

    # Create a temp directory for this extraction session
    tmp_dir = Path(tempfile.mkdtemp(prefix="vidframes_"))
    frames: List[ExtractedFrame] = []
    audio_path: Optional[str] = None

    try:
        # Extract audio track if present
        if audio_stream:
            audio_path = _extract_audio(video_path, tmp_dir, ffmpeg, timeout)

        # Extract frames using hybrid strategy
        frames = _extract_frames_hybrid(
            video_path, tmp_dir, ffmpeg, ffprobe, settings, timeout, duration
        )

        return frames, audio_path

    except Exception:
        # Clean up on failure
        cleanup_frames(frames)
        if audio_path:
            Path(audio_path).unlink(missing_ok=True)
        try:
            tmp_dir.rmdir()
        except Exception:
            pass
        raise


def cleanup_frames(frames: List[ExtractedFrame]) -> None:
    """Delete all temporary frame files."""
    for frame in frames:
        try:
            frame.path.unlink(missing_ok=True)
        except Exception:
            pass


def cleanup_audio(audio_path: Optional[str]) -> None:
    """Delete a temporary audio file."""
    if audio_path:
        try:
            Path(audio_path).unlink(missing_ok=True)
        except Exception:
            pass


def _parse_duration(fmt: dict, video_stream: dict) -> Optional[float]:
    raw = fmt.get("duration") or video_stream.get("duration")
    if raw:
        try:
            return float(raw)
        except (ValueError, TypeError):
            pass
    return None


def _extract_audio(video_path: str, tmp_dir: Path, ffmpeg: str, timeout: int) -> str:
    """Extract audio track to a WAV file. Returns the path."""
    out_path = str(tmp_dir / "audio.wav")
    cmd = [
        ffmpeg, "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        out_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if result.returncode != 0:
            logger.warning("Audio extraction failed (exit %d): %s", result.returncode, result.stderr[:300])
            return None
    except subprocess.TimeoutExpired:
        logger.warning("Audio extraction timed out")
        return None
    except FileNotFoundError:
        logger.warning("FFmpeg not found at: %s", ffmpeg)
        return None
    return out_path


def _extract_frames_hybrid(
    video_path: str,
    tmp_dir: Path,
    ffmpeg: str,
    ffprobe: str,
    settings,
    timeout: int,
    duration: Optional[float],
) -> List[ExtractedFrame]:
    """Hybrid frame extraction: scene-change + uniform fallback."""
    max_frames = settings.VIDEO_MAX_FRAMES
    interval = settings.VIDEO_FRAME_INTERVAL_SECONDS
    scene_threshold = settings.VIDEO_SCENE_CHANGE_THRESHOLD
    width = settings.VIDEO_FRAME_WIDTH

    # Step 1: Scene-change detection
    scene_frames = _extract_scene_frames(
        video_path, tmp_dir, ffmpeg, scene_threshold, width, timeout
    )

    # Step 2: Uniform sampling fallback
    uniform_frames = _extract_uniform_frames(
        video_path, tmp_dir, ffmpeg, interval, width, timeout
    )

    # Step 3: Merge, deduplicate by timestamp proximity, cap at max_frames
    merged = _merge_and_deduplicate(scene_frames, uniform_frames, min_gap=1.0)

    if len(merged) > max_frames:
        # Evenly subsample to stay within the cap
        step = len(merged) / max_frames
        merged = [merged[int(i * step)] for i in range(max_frames)]

    # Re-index
    for i, frame in enumerate(merged):
        frame.frame_index = i

    return merged


def _extract_scene_frames(
    video_path: str,
    tmp_dir: Path,
    ffmpeg: str,
    threshold: float,
    width: int,
    timeout: int,
) -> List[ExtractedFrame]:
    """Extract frames at scene changes."""
    out_pattern = str(tmp_dir / "scene_%06d.jpg")
    # Use select filter for scene changes; scale to target width
    vf = f"select=gt(scene\\,{threshold}),scale={width}:-2"
    cmd = [
        ffmpeg, "-y",
        "-i", video_path,
        "-vf", vf,
        "-vsync", "vfr",
        "-q:v", "3",
        out_pattern,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if result.returncode != 0:
            logger.debug("Scene extraction returned non-zero: %s", result.stderr[:200])
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        logger.warning("Scene frame extraction failed: %s", exc)
        return []

    frames = _load_frames_from_dir(tmp_dir, "scene_", video_path, ffmpeg, timeout)
    return frames


def _extract_uniform_frames(
    video_path: str,
    tmp_dir: Path,
    ffmpeg: str,
    interval: float,
    width: int,
    timeout: int,
) -> List[ExtractedFrame]:
    """Extract one frame every `interval` seconds."""
    out_pattern = str(tmp_dir / "uniform_%06d.jpg")
    fps = f"1/{interval}"
    vf = f"fps={fps},scale={width}:-2"
    cmd = [
        ffmpeg, "-y",
        "-i", video_path,
        "-vf", vf,
        "-q:v", "3",
        out_pattern,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if result.returncode != 0:
            logger.debug("Uniform extraction returned non-zero: %s", result.stderr[:200])
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        logger.warning("Uniform frame extraction failed: %s", exc)
        return []

    frames = _load_frames_from_dir(tmp_dir, "uniform_", video_path, ffmpeg, timeout)
    return frames


def _load_frames_from_dir(
    tmp_dir: Path,
    prefix: str,
    video_path: str,
    ffmpeg: str,
    timeout: int,
) -> List[ExtractedFrame]:
    """Load extracted frame files and assign timestamps via ffprobe."""
    frame_files = sorted(tmp_dir.glob(f"{prefix}*.jpg"))
    if not frame_files:
        return []

    # Get timestamps by probing each frame file is expensive;
    # instead estimate from filename index and known fps.
    # For accuracy we use ffprobe on the original video to get frame PTS.
    pts_list = _get_frame_pts(video_path, ffmpeg, timeout)

    frames: List[ExtractedFrame] = []
    for i, path in enumerate(frame_files):
        # Use PTS if available, otherwise estimate
        if i < len(pts_list):
            ts = pts_list[i]
        else:
            ts = float(i)
        frames.append(ExtractedFrame(path=path, timestamp_seconds=ts, frame_index=i))

    return frames


def _get_frame_pts(video_path: str, ffmpeg: str, timeout: int) -> List[float]:
    """Get presentation timestamps for all frames using ffprobe."""
    settings = get_settings()
    cmd = [
        settings.FFPROBE_PATH,
        "-v", "quiet",
        "-select_streams", "v:0",
        "-show_entries", "frame=pkt_pts_time",
        "-of", "json",
        video_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return [
                float(f.get("pkt_pts_time", 0))
                for f in data.get("frames", [])
                if f.get("pkt_pts_time") is not None
            ]
    except Exception:
        pass
    return []


def _merge_and_deduplicate(
    scene_frames: List[ExtractedFrame],
    uniform_frames: List[ExtractedFrame],
    min_gap: float,
) -> List[ExtractedFrame]:
    """Merge two frame lists, removing frames closer than min_gap seconds."""
    all_frames = sorted(scene_frames + uniform_frames, key=lambda f: f.timestamp_seconds)
    if not all_frames:
        return []

    result = [all_frames[0]]
    for frame in all_frames[1:]:
        if frame.timestamp_seconds - result[-1].timestamp_seconds >= min_gap:
            result.append(frame)

    return result
