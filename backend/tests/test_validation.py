"""Tests for file validation rules."""

import io

from tests.conftest import make_png


# ---------------------------------------------------------------------------
# Extension / type rejection
# ---------------------------------------------------------------------------

def test_unsupported_extension_rejected(client):
    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("document.pdf", b"%PDF-1.4", "application/pdf"))],
    )
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_no_extension_rejected(client):
    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("noextension", make_png(), "image/png"))],
    )
    assert r.status_code == 415


def test_mime_type_mismatch_rejected(client):
    """Send a PNG file but claim it is a JPEG."""
    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("photo.jpg", make_png(), "image/png"))],
    )
    # Extension is jpg but MIME is image/png → mismatch
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


# ---------------------------------------------------------------------------
# Corrupted / empty files
# ---------------------------------------------------------------------------

def test_corrupted_image_rejected(client):
    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("bad.png", b"\x89PNG\r\n\x1a\nGARBAGE", "image/png"))],
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "CORRUPTED_MEDIA"


def test_empty_file_rejected(client):
    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("empty.png", b"", "image/png"))],
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "EMPTY_FILE"


# ---------------------------------------------------------------------------
# File size limit
# ---------------------------------------------------------------------------

def test_file_too_large_rejected(client, monkeypatch):
    """Override max_upload_size_bytes on the live cached settings object."""
    import app.services.validation_service as val_svc

    real_settings = val_svc.get_settings()
    # Patch the property on the instance via __class__ trick – simplest approach
    # is to monkeypatch the function that returns settings inside the module.
    monkeypatch.setattr(real_settings.__class__, "max_upload_size_bytes", property(lambda self: 0))

    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("photo.png", make_png(), "image/png"))],
    )
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_image_signature_mismatch_rejected(client):
    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("photo.webp", make_png(), "image/webp"))],
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "CORRUPTED_MEDIA"


def test_request_id_header_is_returned(client):
    r = client.get("/api/v1/health", headers={"X-Request-ID": "phase6-test"})
    assert r.status_code == 200
    assert r.headers["x-request-id"] == "phase6-test"
