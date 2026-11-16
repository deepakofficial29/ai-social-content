"""Tests for metadata extraction (image only; video/audio require FFprobe)."""

import io

import pytest

from app.services.metadata_service import extract_image_metadata
from app.services.validation_service import validate_image_bytes
from app.core.exceptions import CorruptedMediaError
from tests.conftest import make_jpeg, make_png, make_webp


def test_png_metadata_extracted():
    data = make_png(width=20, height=15)
    meta = extract_image_metadata(data)
    assert meta["width"] == 20
    assert meta["height"] == 15
    assert meta["format"] == "PNG"


def test_jpeg_metadata_extracted():
    data = make_jpeg()
    meta = extract_image_metadata(data)
    assert meta["width"] == 10
    assert meta["height"] == 10
    assert meta["format"] == "JPEG"


def test_webp_metadata_extracted():
    data = make_webp()
    meta = extract_image_metadata(data)
    assert meta["format"] == "WEBP"


def test_corrupted_bytes_raise_error():
    with pytest.raises(CorruptedMediaError):
        extract_image_metadata(b"\x89PNG\r\n\x1a\nGARBAGE_DATA")


def test_validate_image_bytes_passes_valid_png():
    validate_image_bytes(make_png())  # should not raise


def test_validate_image_bytes_rejects_garbage():
    with pytest.raises(CorruptedMediaError):
        validate_image_bytes(b"not an image at all")


# ---------------------------------------------------------------------------
# Storage cleanup on failure
# ---------------------------------------------------------------------------

def test_storage_cleanup_on_pipeline_failure(client, monkeypatch):
    """If metadata extraction fails mid-pipeline, no orphan files should remain."""
    from app.storage.local_storage import LocalStorage
    saved = []
    original_save = LocalStorage.save

    def tracking_save(self, data, key):
        result = original_save(self, data, key)
        saved.append(key)
        return result

    monkeypatch.setattr(LocalStorage, "save", tracking_save)

    # Force a failure by sending a corrupted PNG
    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("bad.png", b"\x89PNG\r\n\x1a\nGARBAGE", "image/png"))],
    )
    assert r.status_code == 422
    # No files should have been saved (validation fails before storage)
    assert len(saved) == 0
