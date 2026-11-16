"""Tests for media upload, retrieval, and deletion."""

import io

import pytest

from tests.conftest import make_jpeg, make_png, make_webp


# ---------------------------------------------------------------------------
# Single image upload
# ---------------------------------------------------------------------------

def test_upload_single_png(client):
    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("photo.png", make_png(), "image/png"))],
    )
    assert r.status_code == 201
    body = r.json()
    assert body["success"] is True
    media = body["data"]["media"]
    assert len(media) == 1
    assert media[0]["media_type"] == "image"
    assert media[0]["metadata"]["width"] == 10
    assert media[0]["metadata"]["format"] == "PNG"
    assert media[0]["sequence_index"] == 0


def test_upload_single_jpeg(client):
    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("photo.jpg", make_jpeg(), "image/jpeg"))],
    )
    assert r.status_code == 201
    assert r.json()["data"]["media"][0]["media_type"] == "image"


def test_upload_single_webp(client):
    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("photo.webp", make_webp(), "image/webp"))],
    )
    assert r.status_code == 201


# ---------------------------------------------------------------------------
# Multiple images / carousel ordering
# ---------------------------------------------------------------------------

def test_upload_multiple_images_preserves_order(client):
    files = [
        ("files", (f"img_{i}.png", make_png(), "image/png"))
        for i in range(3)
    ]
    r = client.post("/api/v1/media/upload", files=files)
    assert r.status_code == 201
    media = r.json()["data"]["media"]
    assert len(media) == 3
    for expected_idx, item in enumerate(media):
        assert item["sequence_index"] == expected_idx


def test_carousel_collection_id_shared(client):
    files = [("files", (f"img_{i}.png", make_png(), "image/png")) for i in range(2)]
    r = client.post("/api/v1/media/upload", files=files)
    assert r.status_code == 201
    data = r.json()["data"]
    collection_id = data["collection_id"]
    assert collection_id
    for item in data["media"]:
        # Each item belongs to the same collection
        detail_r = client.get(f"/api/v1/media/{item['media_id']}")
        assert detail_r.json()["data"]["collection_id"] == collection_id


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def test_get_media_returns_metadata(client):
    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("photo.png", make_png(), "image/png"))],
    )
    media_id = r.json()["data"]["media"][0]["media_id"]
    r2 = client.get(f"/api/v1/media/{media_id}")
    assert r2.status_code == 200
    data = r2.json()["data"]
    assert data["media_id"] == media_id
    assert data["media_type"] == "image"
    assert "width" in data["metadata"]


def test_get_missing_media_returns_404(client):
    r = client.get("/api/v1/media/nonexistent-id")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "MEDIA_NOT_FOUND"


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------

def test_delete_media(client):
    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("photo.png", make_png(), "image/png"))],
    )
    media_id = r.json()["data"]["media"][0]["media_id"]
    del_r = client.delete(f"/api/v1/media/{media_id}")
    assert del_r.status_code == 200
    # Confirm gone
    assert client.get(f"/api/v1/media/{media_id}").status_code == 404


def test_delete_missing_media_returns_404(client):
    r = client.delete("/api/v1/media/nonexistent-id")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Database persistence
# ---------------------------------------------------------------------------

def test_media_persisted_in_db(client):
    r = client.post(
        "/api/v1/media/upload",
        files=[("files", ("photo.png", make_png(), "image/png"))],
    )
    media_id = r.json()["data"]["media"][0]["media_id"]
    # Retrieve via API (which reads from DB)
    r2 = client.get(f"/api/v1/media/{media_id}")
    assert r2.status_code == 200
    assert r2.json()["data"]["media_id"] == media_id
