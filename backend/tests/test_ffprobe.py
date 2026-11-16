"""Tests for real FFprobe-based video and audio metadata extraction.

All tests in this file are skipped automatically when FFprobe is not installed.
They use FFmpeg to generate minimal synthetic media files as reproducible fixtures.
No external services or AI APIs are required.
"""

import pytest

from tests.conftest import (
    make_mp3,
    make_mp4_silent,
    make_mp4_with_audio,
    make_wav,
    requires_ffprobe,
)


# ---------------------------------------------------------------------------
# Direct metadata service tests (no HTTP layer)
# ---------------------------------------------------------------------------

@requires_ffprobe
def test_video_with_audio_metadata(tmp_path):
    from app.services.metadata_service import extract_video_metadata

    path = make_mp4_with_audio(tmp_path)
    data = path.read_bytes()
    meta = extract_video_metadata(data, "mp4")

    assert meta["has_audio"] is True
    assert meta["audio_codec"] is not None
    assert meta["width"] == 64
    assert meta["height"] == 64
    assert meta["video_codec"] is not None
    assert meta["duration_seconds"] is not None
    assert meta["duration_seconds"] > 0
    assert meta["frame_rate"] is not None
    assert meta["frame_rate"] > 0
    assert meta["file_size"] == len(data)


@requires_ffprobe
def test_silent_video_has_no_audio(tmp_path):
    from app.services.metadata_service import extract_video_metadata

    path = make_mp4_silent(tmp_path)
    data = path.read_bytes()
    meta = extract_video_metadata(data, "mp4")

    assert meta["has_audio"] is False
    assert "audio_codec" not in meta
    assert meta["width"] == 64
    assert meta["height"] == 64
    assert meta["video_codec"] is not None
    assert meta["duration_seconds"] is not None


@requires_ffprobe
def test_wav_audio_metadata(tmp_path):
    from app.services.metadata_service import extract_audio_metadata

    path = make_wav(tmp_path)
    data = path.read_bytes()
    meta = extract_audio_metadata(data, "wav")

    assert meta["codec"] is not None
    assert meta["sample_rate"] is not None
    assert meta["sample_rate"] > 0
    assert meta["channels"] is not None
    assert meta["channels"] > 0
    assert meta["duration_seconds"] is not None
    assert meta["duration_seconds"] > 0
    assert meta["file_size"] == len(data)


@requires_ffprobe
def test_mp3_audio_metadata(tmp_path):
    from app.services.metadata_service import extract_audio_metadata

    path = make_mp3(tmp_path)
    data = path.read_bytes()
    meta = extract_audio_metadata(data, "mp3")

    assert meta["codec"] == "mp3"
    assert meta["sample_rate"] is not None
    assert meta["channels"] is not None
    assert meta["duration_seconds"] is not None
    assert meta["file_size"] == len(data)


@requires_ffprobe
def test_invalid_video_raises_ffprobe_error(tmp_path):
    """Garbage bytes with .mp4 extension must raise FFprobeError."""
    from app.core.exceptions import FFprobeError
    from app.services.metadata_service import extract_video_metadata

    with pytest.raises(FFprobeError):
        extract_video_metadata(b"this is not a video file at all", "mp4")


@requires_ffprobe
def test_corrupted_audio_raises_ffprobe_error(tmp_path):
    """Garbage bytes with .wav extension must raise FFprobeError."""
    from app.core.exceptions import FFprobeError
    from app.services.metadata_service import extract_audio_metadata

    with pytest.raises(FFprobeError):
        extract_audio_metadata(b"\x00\x01\x02\x03garbage", "wav")


# ---------------------------------------------------------------------------
# Full upload pipeline tests via HTTP (requires FFprobe)
# ---------------------------------------------------------------------------

@requires_ffprobe
def test_upload_mp4_with_audio_via_api(client, tmp_path):
    path = make_mp4_with_audio(tmp_path)
    data = path.read_bytes()

    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("clip.mp4", data, "video/mp4"))],
    )
    assert r.status_code == 201
    body = r.json()
    assert body["success"] is True
    item = body["data"]["media"][0]
    assert item["media_type"] == "video"
    meta = item["metadata"]
    assert meta["has_audio"] is True
    assert meta["width"] == 64
    assert meta["height"] == 64
    assert meta["video_codec"] is not None
    assert meta["audio_codec"] is not None
    assert meta["duration_seconds"] > 0


@requires_ffprobe
def test_upload_silent_mp4_via_api(client, tmp_path):
    path = make_mp4_silent(tmp_path)
    data = path.read_bytes()

    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("silent.mp4", data, "video/mp4"))],
    )
    assert r.status_code == 201
    item = r.json()["data"]["media"][0]
    assert item["media_type"] == "video"
    assert item["metadata"]["has_audio"] is False


@requires_ffprobe
def test_upload_wav_via_api(client, tmp_path):
    path = make_wav(tmp_path)
    data = path.read_bytes()

    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("tone.wav", data, "audio/wav"))],
    )
    assert r.status_code == 201
    item = r.json()["data"]["media"][0]
    assert item["media_type"] == "audio"
    meta = item["metadata"]
    assert meta["codec"] is not None
    assert meta["sample_rate"] > 0
    assert meta["channels"] > 0
    assert meta["duration_seconds"] > 0


@requires_ffprobe
def test_upload_mp3_via_api(client, tmp_path):
    path = make_mp3(tmp_path)
    data = path.read_bytes()

    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("tone.mp3", data, "audio/mpeg"))],
    )
    assert r.status_code == 201
    item = r.json()["data"]["media"][0]
    assert item["media_type"] == "audio"
    assert item["metadata"]["codec"] == "mp3"


@requires_ffprobe
def test_invalid_video_upload_returns_500(client):
    """Garbage bytes with .mp4 extension must be rejected with FFprobeError → 500."""
    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("fake.mp4", b"not a video", "video/mp4"))],
    )
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "FFPROBE_ERROR"


@requires_ffprobe
def test_invalid_audio_upload_returns_500(client):
    """Garbage bytes with .wav extension must be rejected with FFprobeError → 500."""
    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("fake.wav", b"\x00\x01garbage", "audio/wav"))],
    )
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "FFPROBE_ERROR"


@requires_ffprobe
def test_video_metadata_persisted_in_db(client, tmp_path):
    """Video metadata must survive the full pipeline and be retrievable via GET."""
    path = make_mp4_with_audio(tmp_path)
    data = path.read_bytes()

    upload_r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("clip.mp4", data, "video/mp4"))],
    )
    assert upload_r.status_code == 201
    media_id = upload_r.json()["data"]["media"][0]["media_id"]

    get_r = client.get(f"/api/v1/media/{media_id}")
    assert get_r.status_code == 200
    stored_meta = get_r.json()["data"]["metadata"]
    assert stored_meta["has_audio"] is True
    assert stored_meta["width"] == 64


@requires_ffprobe
def test_silent_video_metadata_persisted_in_db(client, tmp_path):
    path = make_mp4_silent(tmp_path)
    data = path.read_bytes()

    upload_r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("silent.mp4", data, "video/mp4"))],
    )
    media_id = upload_r.json()["data"]["media"][0]["media_id"]
    get_r = client.get(f"/api/v1/media/{media_id}")
    assert get_r.json()["data"]["metadata"]["has_audio"] is False


@requires_ffprobe
def test_storage_cleanup_on_invalid_video(client):
    """No storage file should be written when FFprobe rejects the content."""
    import os
    from app.core.config import get_settings

    storage_dir = get_settings().STORAGE_DIR
    files_before = set(os.listdir(storage_dir))

    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("fake.mp4", b"not a video", "video/mp4"))],
    )
    assert r.status_code == 500

    files_after = set(os.listdir(storage_dir))
    assert files_before == files_after, (
        f"Orphaned files after failed upload: {files_after - files_before}"
    )
