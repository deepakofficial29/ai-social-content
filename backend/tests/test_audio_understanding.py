"""Tests for audio transcription and understanding — Phase 2.5.

All provider calls are mocked.  No paid API calls are made.
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.providers.base import ProviderConfigError, ProviderError
from app.schemas.evidence import (
    AudioObservation,
    ConfidenceLevel,
    MediaEvidence,
    TranscriptionResult,
    TranscriptionSegment,
)
from tests.conftest import make_mp3, make_wav, requires_ffprobe


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_audio_asset(storage_key: str, filename: str = "audio.wav") -> dict:
    return {
        "media_id": "aud_001",
        "storage_key": storage_key,
        "original_filename": filename,
        "sequence_index": 0,
        "metadata_json": json.dumps({"duration_seconds": 1.0, "codec": "pcm_s16le"}),
    }


def _mock_transcription(media_id: str = "aud_001") -> TranscriptionResult:
    return TranscriptionResult(
        media_id=media_id,
        full_text="Hello this is a test recording",
        segments=[
            TranscriptionSegment(
                text="Hello this is a test recording",
                start_seconds=0.0,
                end_seconds=2.5,
                confidence=ConfidenceLevel.HIGH,
                language="en",
            )
        ],
        detected_language="en",
        detected_languages=["en"],
        provider="openai-whisper",
        model_version="whisper-1",
    )


def _mock_audio_observation(media_id: str = "aud_001") -> AudioObservation:
    return AudioObservation(
        media_id=media_id,
        has_speech=True,
        has_music=False,
        ambient_sounds=[],
        background_noise_level="low",
        general_summary="Clear speech recording",
        provider="gemini",
        model_version="gemini-2.0-flash",
    )


# ---------------------------------------------------------------------------
# Audio understanding service — mocked providers
# ---------------------------------------------------------------------------

def test_audio_understanding_success_wav(tmp_path):
    """analyse_audio returns complete MediaEvidence for a WAV file."""
    from app.services.audio_understanding import analyse_audio

    if not (hasattr(pytest, "_ffmpeg_available") or True):
        pass  # always run — uses mocked providers

    # Create a real WAV file in storage
    try:
        wav_path = make_wav(tmp_path)
    except Exception:
        pytest.skip("FFmpeg not available for WAV generation")

    storage_key = wav_path.name
    os.environ["STORAGE_DIR"] = str(tmp_path)
    from app.core.config import get_settings
    get_settings.cache_clear()

    asset = _make_audio_asset(storage_key, "audio.wav")
    mock_trans = _mock_transcription()
    mock_obs = _mock_audio_observation()

    with patch("app.services.audio_understanding.get_transcription_provider") as mock_tp, \
         patch("app.services.audio_understanding.get_audio_understanding_provider") as mock_ap:

        mock_tp.return_value.transcribe.return_value = mock_trans
        mock_ap.return_value.analyse.return_value = mock_obs

        evidence = analyse_audio(asset, "col001")

    assert evidence.processing_status == "complete"
    assert evidence.transcription is not None
    assert evidence.transcription.full_text == "Hello this is a test recording"
    assert evidence.audio_observation is not None
    assert evidence.has_transcription is True
    assert evidence.has_audio_evidence is True


def test_audio_understanding_success_mp3(tmp_path):
    """analyse_audio returns complete MediaEvidence for an MP3 file."""
    from app.services.audio_understanding import analyse_audio

    try:
        mp3_path = make_mp3(tmp_path)
    except Exception:
        pytest.skip("FFmpeg not available for MP3 generation")

    storage_key = mp3_path.name
    os.environ["STORAGE_DIR"] = str(tmp_path)
    from app.core.config import get_settings
    get_settings.cache_clear()

    asset = _make_audio_asset(storage_key, "audio.mp3")
    mock_trans = _mock_transcription()
    mock_obs = _mock_audio_observation()

    with patch("app.services.audio_understanding.get_transcription_provider") as mock_tp, \
         patch("app.services.audio_understanding.get_audio_understanding_provider") as mock_ap:

        mock_tp.return_value.transcribe.return_value = mock_trans
        mock_ap.return_value.analyse.return_value = mock_obs

        evidence = analyse_audio(asset, "col001")

    assert evidence.processing_status == "complete"


def test_audio_understanding_missing_file(tmp_path):
    """Missing audio file returns failed evidence."""
    from app.services.audio_understanding import analyse_audio

    os.environ["STORAGE_DIR"] = str(tmp_path)
    from app.core.config import get_settings
    get_settings.cache_clear()

    asset = _make_audio_asset("nonexistent.wav")
    evidence = analyse_audio(asset, "col001")

    assert evidence.processing_status == "failed"
    assert len(evidence.processing_errors) > 0


def test_transcription_config_error_recorded(tmp_path):
    """Missing transcription credentials recorded as error, not exception."""
    from app.services.audio_understanding import analyse_audio

    try:
        wav_path = make_wav(tmp_path)
    except Exception:
        pytest.skip("FFmpeg not available")

    storage_key = wav_path.name
    os.environ["STORAGE_DIR"] = str(tmp_path)
    from app.core.config import get_settings
    get_settings.cache_clear()

    asset = _make_audio_asset(storage_key)

    with patch("app.services.audio_understanding.get_transcription_provider") as mock_tp, \
         patch("app.services.audio_understanding.get_audio_understanding_provider") as mock_ap:

        mock_tp.side_effect = ProviderConfigError("openai-whisper", "OPENAI_API_KEY not set")
        mock_ap.return_value.analyse.return_value = _mock_audio_observation()

        evidence = analyse_audio(asset, "col001")

    assert any("OPENAI_API_KEY" in e for e in evidence.processing_errors)
    # Audio understanding should still succeed
    assert evidence.audio_observation is not None
    assert evidence.processing_status == "partial"


def test_transcription_provider_error_recorded(tmp_path):
    """Transcription runtime error recorded, audio understanding preserved."""
    from app.services.audio_understanding import analyse_audio

    try:
        wav_path = make_wav(tmp_path)
    except Exception:
        pytest.skip("FFmpeg not available")

    storage_key = wav_path.name
    os.environ["STORAGE_DIR"] = str(tmp_path)
    from app.core.config import get_settings
    get_settings.cache_clear()

    asset = _make_audio_asset(storage_key)

    with patch("app.services.audio_understanding.get_transcription_provider") as mock_tp, \
         patch("app.services.audio_understanding.get_audio_understanding_provider") as mock_ap:

        mock_tp.return_value.transcribe.side_effect = ProviderError("openai-whisper", "rate limit")
        mock_ap.return_value.analyse.return_value = _mock_audio_observation()

        evidence = analyse_audio(asset, "col001")

    assert evidence.transcription is None
    assert evidence.audio_observation is not None
    assert evidence.processing_status == "partial"


def test_audio_understanding_provider_error_recorded(tmp_path):
    """Audio understanding error recorded, transcription preserved."""
    from app.services.audio_understanding import analyse_audio

    try:
        wav_path = make_wav(tmp_path)
    except Exception:
        pytest.skip("FFmpeg not available")

    storage_key = wav_path.name
    os.environ["STORAGE_DIR"] = str(tmp_path)
    from app.core.config import get_settings
    get_settings.cache_clear()

    asset = _make_audio_asset(storage_key)

    with patch("app.services.audio_understanding.get_transcription_provider") as mock_tp, \
         patch("app.services.audio_understanding.get_audio_understanding_provider") as mock_ap:

        mock_tp.return_value.transcribe.return_value = _mock_transcription()
        mock_ap.return_value.analyse.side_effect = ProviderError("gemini", "timeout")

        evidence = analyse_audio(asset, "col001")

    assert evidence.transcription is not None
    assert evidence.audio_observation is None
    assert evidence.processing_status == "partial"


def test_both_providers_fail_returns_failed(tmp_path):
    """If both providers fail, status is 'failed'."""
    from app.services.audio_understanding import analyse_audio

    try:
        wav_path = make_wav(tmp_path)
    except Exception:
        pytest.skip("FFmpeg not available")

    storage_key = wav_path.name
    os.environ["STORAGE_DIR"] = str(tmp_path)
    from app.core.config import get_settings
    get_settings.cache_clear()

    asset = _make_audio_asset(storage_key)

    with patch("app.services.audio_understanding.get_transcription_provider") as mock_tp, \
         patch("app.services.audio_understanding.get_audio_understanding_provider") as mock_ap:

        mock_tp.return_value.transcribe.side_effect = ProviderError("openai-whisper", "error")
        mock_ap.return_value.analyse.side_effect = ProviderError("gemini", "error")

        evidence = analyse_audio(asset, "col001")

    assert evidence.processing_status == "failed"
    assert evidence.transcription is None
    assert evidence.audio_observation is None


# ---------------------------------------------------------------------------
# Transcription schema tests
# ---------------------------------------------------------------------------

def test_transcription_result_empty_speech():
    """Empty transcript is valid — audio may contain no speech."""
    result = TranscriptionResult(
        media_id="aud001",
        full_text="",
        segments=[],
        detected_language="en",
        provider="openai-whisper",
        model_version="whisper-1",
    )
    assert result.full_text == ""
    assert result.segments == []


def test_transcription_segment_timestamps_ordered():
    """Segment timestamps must be in chronological order."""
    segments = [
        TranscriptionSegment(text="First", start_seconds=0.0, end_seconds=1.0),
        TranscriptionSegment(text="Second", start_seconds=1.0, end_seconds=2.5),
        TranscriptionSegment(text="Third", start_seconds=2.5, end_seconds=4.0),
    ]
    for i in range(len(segments) - 1):
        assert segments[i].end_seconds <= segments[i + 1].start_seconds


def test_audio_observation_silence():
    """Silence is a valid audio observation."""
    obs = AudioObservation(
        media_id="aud001",
        has_speech=False,
        has_music=False,
        ambient_sounds=[],
        sound_events=[],
        background_noise_level="none",
        general_summary="The recording is silent",
        provider="gemini",
        model_version="gemini-2.0-flash",
    )
    assert obs.has_speech is False
    assert obs.has_music is False
    assert obs.general_summary == "The recording is silent"


def test_audio_observation_music_only():
    """Music-only audio is handled correctly."""
    obs = AudioObservation(
        media_id="aud002",
        has_speech=False,
        has_music=True,
        music_genre="classical",
        emotional_tone="calm",
        background_noise_level="low",
        general_summary="Classical music, no speech",
        provider="gemini",
        model_version="gemini-2.0-flash",
    )
    assert obs.has_music is True
    assert obs.music_genre == "classical"


def test_audio_observation_noisy():
    """Noisy audio is handled correctly."""
    obs = AudioObservation(
        media_id="aud003",
        has_speech=True,
        has_music=False,
        ambient_sounds=["crowd noise", "traffic"],
        background_noise_level="high",
        general_summary="Speech with heavy background noise",
        provider="gemini",
        model_version="gemini-2.0-flash",
    )
    assert obs.background_noise_level == "high"
    assert "crowd noise" in obs.ambient_sounds
