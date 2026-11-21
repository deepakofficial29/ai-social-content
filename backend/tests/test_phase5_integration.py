"""Phase 5 frontend contract and missing-list API tests."""

from tests.conftest import make_png


def test_media_collections_endpoint(client):
    upload = client.post(
        "/api/v1/media/upload",
        files=[("files", ("photo.png", make_png(), "image/png"))],
    )
    assert upload.status_code == 201
    collection_id = upload.json()["data"]["collection_id"]

    response = client.get("/api/v1/media/collections")
    assert response.status_code == 200
    collections = response.json()["data"]
    assert any(item["collection_id"] == collection_id for item in collections)


def test_generation_history_endpoint(client):
    response = client.get("/api/v1/generation")
    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)


def test_health_endpoint_for_frontend_status(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["success"] is True
