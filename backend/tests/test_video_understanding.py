"""Tests for video frame extraction and understanding — Phase 2.4.

Real FFmpeg tests are gated behind requires_ffprobe.
All provider calls are mocked.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.providers.base import ProviderConfigError, ProviderError
from app.schemas.evidence import (
    AudioObservation,
    ConfidenceLevel,
    MediaEvidence,
    TranscriptionResult,
    VideoObservation,
)
from tests.conftest import (
    ffmpeg_available,
    make_mp4_silent,
    make_mp4_with_audio,
    requires_ffprobe,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_video_asset(storage_key: str, has_audio: bool, duration: float = 1.0) -> dict:
    return {
        "media_id": "vid_001",
        "storage_key": storage_key,
        "original_filename": "test.mp4",
        "sequence_index": 0,
        "metadata_json": json.dumps({
            "has_audio": has_audio,
            "duration_seconds": duration,
            "width": 64,
            "height": 64,
        }),
    }


def _mock_video_observation(media_id: str = "vid_001") -> VideoObservation:
    return VideoObservation(
        media_id=media_id,
        overall_description="A short test video",
        key_events=["product shown at 0s"],
        has_audio=True,
        audio_description="Background music",
        frames_analysed=2,
        total_duration_seconds=1.0,
        provider="gemini",
        model_version="gemini-2.0-flash",
    )


def _mock_transcription(media_id: str = "vid_001") -> TranscriptionResult:
    return TranscriptionResult(
        media_id=media_id,
        full_text="Hello from the video",
        provider="openai-whisper",
        model_version="whisper-1",
    )


# ---------------------------------------------------------------------------
# Frame extraction — unit tests (no FFmpeg required)
# ---------------------------------------------------------------------------

def test_extract_frames_missing_file():
    """FrameExtractionError raised for non-existent file."""
    from app.services.video_processor import FrameExtractionError, extract_frames

    with pytest.raises(FrameExtractionError, match="not found"):
        extract_frames("/nonexistent/path/video.mp4")


def test_cleanup_frames_handles_missing_files():
    """cleanup_frames does not raise if files are already gone."""
    from app.services.video_processor import ExtractedFrame, cleanup_frames

    frames = [
        ExtractedFrame(path=Path("/nonexistent/frame.jpg"), timestamp_seconds=0.0, frame_index=0)
    ]
    cleanup_frames(frames)  # must not raise


def test_cleanup_audio_handles_none():
    """cleanup_audio handles None gracefully."""
    from app.services.video_processor import cleanup_audio

    cleanup_audio(None)  # must not raise


def test_cleanup_audio_handles_missing_file():
    """cleanup_audio handles missing file gracefully."""
    from app.services.video_processor import cleanup_audio

    cleanup_audio("/nonexistent/audio.wav")  # must not raise


# ---------------------------------------------------------------------------
# Frame extraction — real FFmpeg tests
# ---------------------------------------------------------------------------

@requires_ffprobe
def test_extract_frames_from_silent_video(tmp_path):
    """Frame extraction works on a silent video; audio_path is None."""
    from app.services.video_processor import cleanup_frames, extract_frames

    video_path = make_mp4_silent(tmp_path)
    frames, audio_path = extract_frames(str(video_path))

    try:
        assert isinstance(frames, list)
        assert audio_path is None  # silent video has no audio
    finally:
        cleanup_frames(frames)


@requires_ffprobe
def test_extract_frames_from_video_with_audio(tmp_path):
    """Frame extraction works on a video with audio; audio_path is set."""
    from app.services.video_processor import cleanup_audio, cleanup_frames, extract_frames

    video_path = make_mp4_with_audio(tmp_path)
    frames, audio_path = extract_frames(str(video_path))

    try:
        assert isinstance(frames, list)
        assert audio_path is not None
        assert Path(audio_path).exists()
    finally:
        cleanup_frames(frames)
        cleanup_audio(audio_path)


@requires_ffprobe
def test_extracted_frames_have_timestamps(tmp_path):
    """Each extracted frame has a non-negative timestamp."""
    from app.services.video_processor import cleanup_frames, extract_frames

    video_path = make_mp4_silent(tmp_path)
    frames, audio_path = extract_frames(str(video_path))

    try:
        for frame in frames:
            assert frame.timestamp_seconds >= 0.0
            assert frame.frame_index >= 0
    finally:
        cleanup_frames(frames)


@requires_ffprobe
def test_extracted_frames_are_valid_jpegs(tmp_path):
    """Extracted frame files exist and are readable as images."""
    from PIL import Image
    from app.services.video_processor import cleanup_frames, extract_frames

    video_path = make_mp4_silent(tmp_path)
    frames, _ = extract_frames(str(video_path))

    try:
        for frame in frames:
            assert frame.path.exists()
            with Image.open(frame.path) as img:
                assert img.width > 0
    finally:
        cleanup_frames(frames)


@requires_ffprobe
def test_temp_files_cleaned_up_after_extraction(tmp_path):
    """All temp frame files are deleted after cleanup_frames."""
    from app.services.video_processor import cleanup_frames, extract_frames

    video_path = make_mp4_silent(tmp_path)
    frames, audio_path = extract_frames(str(video_path))
    frame_paths = [f.path for f in frames]

    cleanup_frames(frames)

    for path in frame_paths:
        assert not path.exists(), f"Temp frame not cleaned up: {path}"


@requires_ffprobe
def test_temp_audio_cleaned_up(tmp_path):
    """Extracted audio temp file is deleted after cleanup_audio."""
    from app.services.video_processor import cleanup_audio, cleanup_frames, extract_frames

    video_path = make_mp4_with_audio(tmp_path)
    frames, audio_path = extract_frames(str(video_path))
    cleanup_frames(frames)
    cleanup_audio(audio_path)

    if audio_path:
        assert not Path(audio_path).exists()


# ---------------------------------------------------------------------------
# Video understanding service — mocked provider
# ---------------------------------------------------------------------------

def test_video_understanding_success(tmp_path):
    """analyse_video returns complete MediaEvidence when provider succeeds."""
    from app.services.video_understanding import analyse_video

    # Create a real video file in tmp_path storage
    if not ffmpeg_available():
        pytest.skip("FFmpeg not available")

    video_path = make_mp4_with_audio(tmp_path)
    storage_key = video_path.name

    # Copy to a storage-like location
    import shutil
    os.environ["STORAGE_DIR"] = str(tmp_path)
    from app.core.config import get_settings
    get_settings.cache_clear()

    asset = _make_video_asset(storage_key, has_audio=True)

    mock_video_obs = _mock_video_observation()
    mock_trans = _mock_transcription()

    with patch("app.services.video_understanding.get_video_provider") as mock_vp, \
         patch("app.services.video_understanding.get_transcription_provider") as mock_tp, \
         patch("app.services.video_understanding.get_audio_understanding_provider") as mock_ap, \
         patch("app.services.video_understanding.extract_frames") as mock_ef:

        mock_vp.return_value.analyse.return_value = mock_video_obs
        mock_tp.return_value.transcribe.return_value = mock_trans
        mock_ap.return_value.analyse.return_value = AudioObservation(
            media_id="vid_001",
            has_speech=True,
            general_summary="Test audio",
            provider="gemini",
            model_version="gemini-2.0-flash",
        )
        mock_ef.return_value = ([], str(tmp_path / "audio.wav"))

        # Create a fake audio file so the path exists
        (tmp_path / "audio.wav").write_bytes(b"RIFF")

        evidence = analyse_video(asset, "col001")

    assert evidence.processing_status in ("complete", "partial")
    assert evidence.video_observation is not None
    assert evidence.video_observation.overall_description == "A short test video"


def test_video_understanding_silent_video_skips_audio(tmp_path):
    """Silent video skips audio processing cleanly — not an error."""
    from app.services.video_understanding import analyse_video

    if not ffmpeg_available():
        pytest.skip("FFmpeg not available")

    video_path = make_mp4_silent(tmp_path)
    storage_key = video_path.name

    os.environ["STORAGE_DIR"] = str(tmp_path)
    from app.core.config import get_settings
    get_settings.cache_clear()

    asset = _make_video_asset(storage_key, has_audio=False)
    mock_video_obs = VideoObservation(
        media_id="vid_001",
        overall_description="Silent product showcase",
        has_audio=False,
        provider="gemini",
        model_version="gemini-2.0-flash",
    )

    with patch("app.services.video_understanding.get_video_provider") as mock_vp:
        mock_vp.return_value.analyse.return_value = mock_video_obs

        evidence = analyse_video(asset, "col001")

    assert evidence.transcription is None
    assert evidence.audio_observation is None
    # Silent video should not produce audio-related errors
    audio_errors = [e for e in evidence.processing_errors if "audio" in e.lower() or "transcri" in e.lower()]
    assert audio_errors == []


def test_video_understanding_missing_file(tmp_path):
    """Missing video file returns failed evidence."""
    from app.services.video_understanding import analyse_video

    os.environ["STORAGE_DIR"] = str(tmp_path)
    from app.core.config import get_settings
    get_settings.cache_clear()

    asset = _make_video_asset("nonexistent.mp4", has_audio=False)
    evidence = analyse_video(asset, "col001")

    assert evidence.processing_status == "failed"
    assert len(evidence.processing_errors) > 0


def test_video_provider_config_error_recorded(tmp_path):
    """Missing video provider credentials recorded as error, not exception."""
    from app.services.video_understanding import analyse_video

    if not ffmpeg_available():
        pytest.skip("FFmpeg not available")

    video_path = make_mp4_silent(tmp_path)
    storage_key = video_path.name

    os.environ["STORAGE_DIR"] = str(tmp_path)
    from app.core.config import get_settings
    get_settings.cache_clear()

    asset = _make_video_asset(storage_key, has_audio=False)

    with patch("app.services.video_understanding.get_video_provider") as mock_vp:
        mock_vp.side_effect = ProviderConfigError("gemini", "GEMINI_API_KEY not set")

        evidence = analyse_video(asset, "col001")

    assert evidence.processing_status == "failed"
    assert any("GEMINI_API_KEY" in e for e in evidence.processing_errors)


def test_video_provider_error_recorded(tmp_path):
    """Provider runtime error recorded as error, not exception."""
    from app.services.video_understanding import analyse_video

    if not ffmpeg_available():
        pytest.skip("FFmpeg not available")

    video_path = make_mp4_silent(tmp_path)
    storage_key = video_path.name

    os.environ["STORAGE_DIR"] = str(tmp_path)
    from app.core.config import get_settings
    get_settings.cache_clear()

    asset = _make_video_asset(storage_key, has_audio=False)

    with patch("app.services.video_understanding.get_video_provider") as mock_vp:
        mock_vp.return_value.analyse.side_effect = ProviderError("gemini", "API timeout", retryable=True)

        evidence = analyse_video(asset, "col001")

    assert evidence.processing_status == "failed"
    assert any("timeout" in e.lower() for e in evidence.processing_errors)


def test_video_partial_failure_preserves_visual_evidence(tmp_path):
    """If video analysis succeeds but transcription fails, visual evidence is kept."""
    from app.services.video_understanding import analyse_video

    if not ffmpeg_available():
        pytest.skip("FFmpeg not available")

    video_path = make_mp4_with_audio(tmp_path)
    storage_key = video_path.name

    os.environ["STORAGE_DIR"] = str(tmp_path)
    from app.core.config import get_settings
    get_settings.cache_clear()

    asset = _make_video_asset(storage_key, has_audio=True)
    mock_video_obs = _mock_video_observation()

    with patch("app.services.video_understanding.get_video_provider") as mock_vp, \
         patch("app.services.video_understanding.get_transcription_provider") as mock_tp, \
         patch("app.services.video_understanding.get_audio_understanding_provider") as mock_ap, \
         patch("app.services.video_understanding.extract_frames") as mock_ef:

        mock_vp.return_value.analyse.return_value = mock_video_obs
        mock_tp.return_value.transcribe.side_effect = ProviderError("openai-whisper", "rate limit")
        mock_ap.return_value.analyse.side_effect = ProviderError("gemini", "timeout")
        mock_ef.return_value = ([], str(tmp_path / "audio.wav"))
        (tmp_path / "audio.wav").write_bytes(b"RIFF")

        evidence = analyse_video(asset, "col001")

    # Visual evidence must be preserved despite audio failures
    assert evidence.video_observation is not None
    assert evidence.video_observation.overall_description == "A short test video"
    assert evidence.processing_status == "partial"
    assert evidence.transcription is None
    assert len(evidence.processing_errors) > 0


def test_timestamp_preservation_in_video_observation():
    """Frame timestamps must be preserved in VideoObservation."""
    from app.schemas.evidence import FrameObservation, ImageObservation

    obs = VideoObservation(
        media_id="vid001",
        frame_observations=[
            FrameObservation(
                timestamp_seconds=0.0,
                frame_index=0,
                observation=ImageObservation(media_id="vid001"),
            ),
            FrameObservation(
                timestamp_seconds=5.0,
                frame_index=1,
                observation=ImageObservation(media_id="vid001"),
            ),
            FrameObservation(
                timestamp_seconds=10.0,
                frame_index=2,
                observation=ImageObservation(media_id="vid001"),
            ),
        ],
        provider="gemini",
        model_version="gemini-2.0-flash",
    )
    timestamps = [f.timestamp_seconds for f in obs.frame_observations]
    assert timestamps == [0.0, 5.0, 10.0]
