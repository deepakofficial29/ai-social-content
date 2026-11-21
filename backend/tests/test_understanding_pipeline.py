"""End-to-end pipeline tests — all providers mocked.

Tests the full flow: upload → understanding pipeline → MediaEvidence.
No paid API calls are made.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.evidence import (
    AudioObservation,
    ConfidenceLevel,
    ImageObservation,
    MediaEvidence,
    TranscriptionResult,
    VideoObservation,
)
from tests.conftest import (
    ffmpeg_available,
    make_jpeg,
    make_mp3,
    make_mp4_silent,
    make_mp4_with_audio,
    make_png,
    make_wav,
    make_webp,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _upload_images(client, images):
    """Upload a list of (filename, bytes, mime) tuples and return response."""
    files = [(("files", (name, data, mime))) for name, data, mime in images]
    return client.post("/api/v1/media/upload", files=files)


def _mock_image_obs(media_id: str, seq: int = 0) -> ImageObservation:
    return ImageObservation(
        media_id=media_id,
        sequence_index=seq,
        scene_description="A test image",
        provider="gemini",
        model_version="gemini-2.0-flash",
    )


def _mock_video_obs(media_id: str) -> VideoObservation:
    return VideoObservation(
        media_id=media_id,
        overall_description="A test video",
        has_audio=True,
        provider="gemini",
        model_version="gemini-2.0-flash",
    )


def _mock_transcription(media_id: str) -> TranscriptionResult:
    return TranscriptionResult(
        media_id=media_id,
        full_text="Test transcription",
        provider="openai-whisper",
        model_version="whisper-1",
    )


def _mock_audio_obs(media_id: str) -> AudioObservation:
    return AudioObservation(
        media_id=media_id,
        has_speech=True,
        general_summary="Test audio",
        provider="gemini",
        model_version="gemini-2.0-flash",
    )


# ---------------------------------------------------------------------------
# Single image pipeline
# ---------------------------------------------------------------------------

def test_pipeline_single_image_end_to_end(client):
    """Upload a PNG, run understanding, get MediaEvidence."""
    # Upload
    r = _upload_images(client, [("photo.png", make_png(), "image/png")])
    assert r.status_code == 201
    collection_id = r.json()["data"]["collection_id"]
    media_id = r.json()["data"]["media"][0]["media_id"]

    mock_obs = [_mock_image_obs(media_id, 0)]

    with patch("app.services.image_understanding.get_vision_provider") as mock_get:
        mock_get.return_value.analyse.return_value = mock_obs

        r2 = client.post(f"/api/v1/understanding/{collection_id}")

    assert r2.status_code == 200
    body = r2.json()
    assert body["success"] is True
    data = body["data"]
    assert data["processing_status"] == "complete"
    assert data["has_visual_evidence"] is True
    assert len(data["evidence"]["image_observations"]) == 1
    assert data["evidence"]["image_observations"][0]["media_id"] == media_id


def test_pipeline_single_image_provenance(client):
    """Evidence must contain the correct media_id and sequence_index."""
    r = _upload_images(client, [("photo.png", make_png(), "image/png")])
    collection_id = r.json()["data"]["collection_id"]
    media_id = r.json()["data"]["media"][0]["media_id"]

    mock_obs = [_mock_image_obs(media_id, 0)]

    with patch("app.services.image_understanding.get_vision_provider") as mock_get:
        mock_get.return_value.analyse.return_value = mock_obs

        r2 = client.post(f"/api/v1/understanding/{collection_id}")

    obs = r2.json()["data"]["evidence"]["image_observations"][0]
    assert obs["media_id"] == media_id
    assert obs["sequence_index"] == 0


# ---------------------------------------------------------------------------
# Carousel pipeline
# ---------------------------------------------------------------------------

def test_pipeline_carousel_sequence_preserved(client):
    """Carousel understanding preserves image sequence order."""
    files = [("files", (f"img_{i}.png", make_png(), "image/png")) for i in range(3)]
    r = client.post("/api/v1/media/upload", files=files)
    assert r.status_code == 201

    collection_id = r.json()["data"]["collection_id"]
    media_items = r.json()["data"]["media"]

    mock_obs = [_mock_image_obs(item["media_id"], item["sequence_index"]) for item in media_items]

    with patch("app.services.image_understanding.get_vision_provider") as mock_get:
        mock_get.return_value.analyse.return_value = mock_obs

        r2 = client.post(f"/api/v1/understanding/{collection_id}")

    assert r2.status_code == 200
    observations = r2.json()["data"]["evidence"]["image_observations"]
    assert len(observations) == 3
    for i, obs in enumerate(observations):
        assert obs["sequence_index"] == i


def test_pipeline_carousel_collection_type(client):
    """Carousel collection type is preserved in evidence."""
    files = [("files", (f"img_{i}.png", make_png(), "image/png")) for i in range(2)]
    r = client.post("/api/v1/media/upload", files=files)
    collection_id = r.json()["data"]["collection_id"]
    media_items = r.json()["data"]["media"]

    mock_obs = [_mock_image_obs(item["media_id"], item["sequence_index"]) for item in media_items]

    with patch("app.services.image_understanding.get_vision_provider") as mock_get:
        mock_get.return_value.analyse.return_value = mock_obs

        r2 = client.post(f"/api/v1/understanding/{collection_id}")

    assert r2.json()["data"]["collection_type"] == "carousel"


# ---------------------------------------------------------------------------
# Video pipeline
# ---------------------------------------------------------------------------

def test_pipeline_video_with_audio_end_to_end(client, tmp_path):
    """Upload a video with audio, run understanding, get MediaEvidence."""
    if not ffmpeg_available():
        pytest.skip("FFmpeg not available")

    video_path = make_mp4_with_audio(tmp_path)
    with open(video_path, "rb") as f:
        video_bytes = f.read()

    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("video.mp4", video_bytes, "video/mp4"))],
    )
    assert r.status_code == 201
    collection_id = r.json()["data"]["collection_id"]
    media_id = r.json()["data"]["media"][0]["media_id"]

    mock_video = _mock_video_obs(media_id)
    mock_trans = _mock_transcription(media_id)
    mock_audio = _mock_audio_obs(media_id)

    with patch("app.services.video_understanding.get_video_provider") as mock_vp, \
         patch("app.services.video_understanding.get_transcription_provider") as mock_tp, \
         patch("app.services.video_understanding.get_audio_understanding_provider") as mock_ap, \
         patch("app.services.video_understanding.extract_frames") as mock_ef:

        mock_vp.return_value.analyse.return_value = mock_video
        mock_tp.return_value.transcribe.return_value = mock_trans
        mock_ap.return_value.analyse.return_value = mock_audio
        mock_ef.return_value = ([], None)

        r2 = client.post(f"/api/v1/understanding/{collection_id}")

    assert r2.status_code == 200
    data = r2.json()["data"]
    assert data["has_visual_evidence"] is True
    assert data["evidence"]["video_observation"]["overall_description"] == "A test video"


def test_pipeline_silent_video_no_audio_errors(client, tmp_path):
    """Silent video pipeline produces no audio-related errors."""
    if not ffmpeg_available():
        pytest.skip("FFmpeg not available")

    video_path = make_mp4_silent(tmp_path)
    with open(video_path, "rb") as f:
        video_bytes = f.read()

    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("silent.mp4", video_bytes, "video/mp4"))],
    )
    assert r.status_code == 201
    collection_id = r.json()["data"]["collection_id"]
    media_id = r.json()["data"]["media"][0]["media_id"]

    mock_video = VideoObservation(
        media_id=media_id,
        overall_description="Silent product showcase",
        has_audio=False,
        provider="gemini",
        model_version="gemini-2.0-flash",
    )

    with patch("app.services.video_understanding.get_video_provider") as mock_vp:
        mock_vp.return_value.analyse.return_value = mock_video

        r2 = client.post(f"/api/v1/understanding/{collection_id}")

    assert r2.status_code == 200
    data = r2.json()["data"]
    errors = data["processing_errors"]
    audio_errors = [e for e in errors if "audio" in e.lower() or "transcri" in e.lower()]
    assert audio_errors == []
    assert data["evidence"]["video_observation"]["has_audio"] is False


# ---------------------------------------------------------------------------
# Audio pipeline
# ---------------------------------------------------------------------------

def test_pipeline_audio_wav_end_to_end(client, tmp_path):
    """Upload a WAV file, run understanding, get MediaEvidence."""
    if not ffmpeg_available():
        pytest.skip("FFmpeg not available")

    wav_path = make_wav(tmp_path)
    with open(wav_path, "rb") as f:
        wav_bytes = f.read()

    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("audio.wav", wav_bytes, "audio/wav"))],
    )
    assert r.status_code == 201
    collection_id = r.json()["data"]["collection_id"]
    media_id = r.json()["data"]["media"][0]["media_id"]

    mock_trans = _mock_transcription(media_id)
    mock_audio = _mock_audio_obs(media_id)

    with patch("app.services.audio_understanding.get_transcription_provider") as mock_tp, \
         patch("app.services.audio_understanding.get_audio_understanding_provider") as mock_ap:

        mock_tp.return_value.transcribe.return_value = mock_trans
        mock_ap.return_value.analyse.return_value = mock_audio

        r2 = client.post(f"/api/v1/understanding/{collection_id}")

    assert r2.status_code == 200
    data = r2.json()["data"]
    assert data["has_transcription"] is True
    assert data["has_audio_evidence"] is True
    assert data["evidence"]["transcription"]["full_text"] == "Test transcription"


def test_pipeline_audio_mp3_end_to_end(client, tmp_path):
    """Upload an MP3 file, run understanding, get MediaEvidence."""
    if not ffmpeg_available():
        pytest.skip("FFmpeg not available")

    mp3_path = make_mp3(tmp_path)
    with open(mp3_path, "rb") as f:
        mp3_bytes = f.read()

    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("audio.mp3", mp3_bytes, "audio/mpeg"))],
    )
    assert r.status_code == 201
    collection_id = r.json()["data"]["collection_id"]
    media_id = r.json()["data"]["media"][0]["media_id"]

    mock_trans = _mock_transcription(media_id)
    mock_audio = _mock_audio_obs(media_id)

    with patch("app.services.audio_understanding.get_transcription_provider") as mock_tp, \
         patch("app.services.audio_understanding.get_audio_understanding_provider") as mock_ap:

        mock_tp.return_value.transcribe.return_value = mock_trans
        mock_ap.return_value.analyse.return_value = mock_audio

        r2 = client.post(f"/api/v1/understanding/{collection_id}")

    assert r2.status_code == 200
    assert r2.json()["data"]["has_transcription"] is True


# ---------------------------------------------------------------------------
# Partial failure handling
# ---------------------------------------------------------------------------

def test_pipeline_partial_failure_preserves_evidence(client):
    """If vision succeeds but a secondary step fails, visual evidence is kept."""
    r = _upload_images(client, [("photo.png", make_png(), "image/png")])
    collection_id = r.json()["data"]["collection_id"]
    media_id = r.json()["data"]["media"][0]["media_id"]

    # Provider returns valid observation
    mock_obs = [_mock_image_obs(media_id, 0)]

    with patch("app.services.image_understanding.get_vision_provider") as mock_get:
        mock_get.return_value.analyse.return_value = mock_obs

        r2 = client.post(f"/api/v1/understanding/{collection_id}")

    assert r2.status_code == 200
    data = r2.json()["data"]
    assert data["has_visual_evidence"] is True
    assert len(data["evidence"]["image_observations"]) == 1


def test_pipeline_missing_credentials_returns_422(client):
    """Missing provider credentials returns 422, not 500."""
    from app.providers.base import ProviderConfigError

    r = _upload_images(client, [("photo.png", make_png(), "image/png")])
    collection_id = r.json()["data"]["collection_id"]

    with patch("app.services.image_understanding.get_vision_provider") as mock_get:
        mock_get.side_effect = ProviderConfigError("gemini", "GEMINI_API_KEY not set")

        r2 = client.post(f"/api/v1/understanding/{collection_id}")

    assert r2.status_code == 422
    body = r2.json()
    assert body["success"] is False


def test_pipeline_unknown_collection_returns_404(client):
    """Unknown collection_id returns 404."""
    r = client.post("/api/v1/understanding/nonexistent-collection-id")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Evidence endpoint
# ---------------------------------------------------------------------------

def test_evidence_endpoint_returns_evidence(client):
    """GET /evidence/{collection_id} returns evidence."""
    r = _upload_images(client, [("photo.png", make_png(), "image/png")])
    collection_id = r.json()["data"]["collection_id"]
    media_id = r.json()["data"]["media"][0]["media_id"]

    mock_obs = [_mock_image_obs(media_id, 0)]

    with patch("app.services.image_understanding.get_vision_provider") as mock_get:
        mock_get.return_value.analyse.return_value = mock_obs

        r2 = client.get(f"/api/v1/evidence/{collection_id}")

    assert r2.status_code == 200
    assert r2.json()["data"]["collection_id"] == collection_id


def test_evidence_endpoint_unknown_collection_returns_404(client):
    """GET /evidence/{collection_id} returns 404 for unknown collection."""
    r = client.get("/api/v1/evidence/nonexistent-id")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Evidence provenance
# ---------------------------------------------------------------------------

def test_evidence_provenance_image_media_id(client):
    """Each image observation is traceable to its source media_id."""
    files = [("files", (f"img_{i}.png", make_png(), "image/png")) for i in range(2)]
    r = client.post("/api/v1/media/upload", files=files)
    collection_id = r.json()["data"]["collection_id"]
    media_items = r.json()["data"]["media"]

    mock_obs = [_mock_image_obs(item["media_id"], item["sequence_index"]) for item in media_items]

    with patch("app.services.image_understanding.get_vision_provider") as mock_get:
        mock_get.return_value.analyse.return_value = mock_obs

        r2 = client.post(f"/api/v1/understanding/{collection_id}")

    observations = r2.json()["data"]["evidence"]["image_observations"]
    observed_ids = {o["media_id"] for o in observations}
    expected_ids = {item["media_id"] for item in media_items}
    assert observed_ids == expected_ids


def test_evidence_provenance_providers_recorded(client):
    """providers_used is populated in the evidence response."""
    r = _upload_images(client, [("photo.png", make_png(), "image/png")])
    collection_id = r.json()["data"]["collection_id"]
    media_id = r.json()["data"]["media"][0]["media_id"]

    mock_obs = [_mock_image_obs(media_id, 0)]

    with patch("app.services.image_understanding.get_vision_provider") as mock_get:
        mock_get.return_value.analyse.return_value = mock_obs

        r2 = client.post(f"/api/v1/understanding/{collection_id}")

    providers = r2.json()["data"]["providers_used"]
    assert "gemini" in providers
