"""Tests for health and readiness endpoints."""

from tests.conftest import ffprobe_available


def _extract_checks(body: dict) -> dict:
    """Pull the checks dict from either a success or failure readiness response."""
    if body.get("success"):
        return body["data"]["checks"]
    return body["error"]["details"]


def test_health_returns_200(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["status"] == "healthy"
    assert body["data"]["service"] == "multimodal-caption-generator"
    assert "version" in body["data"]


def test_readiness_includes_all_checks(client):
    """Readiness must always report database, storage, and ffprobe checks."""
    r = client.get("/api/v1/ready")
    checks = _extract_checks(r.json())
    assert "database" in checks
    assert "storage" in checks
    assert "ffprobe" in checks


def test_readiness_database_and_storage_ok(client):
    """Database and storage checks must pass regardless of FFprobe status."""
    r = client.get("/api/v1/ready")
    checks = _extract_checks(r.json())
    assert checks["database"] == "ok"
    assert checks["storage"] == "ok"


def test_readiness_ffprobe_status_reported(client):
    """FFprobe check is 'ok' when installed, descriptive string when not."""
    r = client.get("/api/v1/ready")
    checks = _extract_checks(r.json())
    ffprobe_status = checks["ffprobe"]
    if ffprobe_available():
        assert ffprobe_status == "ok"
        assert r.status_code == 200
    else:
        assert "unavailable" in ffprobe_status or "error" in ffprobe_status
        assert r.status_code == 503
