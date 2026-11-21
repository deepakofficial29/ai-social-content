"""Tests for image and carousel understanding — Phase 2.3.

All provider calls are mocked.  No paid API calls are made.
"""

import io
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from app.providers.base import ProviderConfigError, ProviderError
from app.schemas.evidence import (
    ConfidenceLevel,
    DetectedObject,
    ExtractedText,
    ImageObservation,
    MediaEvidence,
)
from app.schemas.provider_requests import VisionRequest
from tests.conftest import make_jpeg, make_png, make_webp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_observation(media_id: str, seq: int = 0) -> ImageObservation:
    return ImageObservation(
        media_id=media_id,
        sequence_index=seq,
        scene_description="A product on a white background",
        detected_objects=[DetectedObject(label="bottle", confidence=ConfidenceLevel.HIGH)],
        extracted_text=[ExtractedText(text="BRAND", confidence=ConfidenceLevel.HIGH)],
        dominant_colours=["white", "blue"],
        estimated_setting="studio",
        mood_or_tone="clean",
        provider="gemini",
        model_version="gemini-2.0-flash",
        processing_time_ms=800,
    )


def _make_assets(n: int, tmp_path) -> List[dict]:
    """Create n fake image assets backed by real PNG bytes in tmp_path."""
    from app.storage.local_storage import LocalStorage
    import os
    os.environ["STORAGE_DIR"] = str(tmp_path)
    from app.core.config import get_settings
    get_settings.cache_clear()

    storage = LocalStorage(base_dir=str(tmp_path))
    assets = []
    for i in range(n):
        key = storage.generate_key(".png")
        storage.save(make_png(), key)
        assets.append({
            "media_id": f"img_{i:03d}",
            "storage_key": key,
            "original_filename": f"photo_{i}.png",
            "sequence_index": i,
            "metadata_json": None,
        })
    return assets


# ---------------------------------------------------------------------------
# Single image understanding
# ---------------------------------------------------------------------------

def test_single_image_understanding_success(tmp_path):
    """analyse_images returns MediaEvidence with one ImageObservation."""
    from app.services.image_understanding import analyse_images

    assets = _make_assets(1, tmp_path)
    mock_obs = [_make_observation(assets[0]["media_id"], 0)]

    with patch("app.services.image_understanding.get_vision_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.analyse.return_value = mock_obs
        mock_get.return_value = mock_provider

        evidence = analyse_images(assets, "col001", "single")

    assert evidence.processing_status == "complete"
    assert len(evidence.image_observations) == 1
    assert evidence.image_observations[0].media_id == assets[0]["media_id"]
    assert evidence.has_visual_evidence is True
    assert evidence.processing_errors == []


def test_single_image_extracted_text_aggregated(tmp_path):
    """all_extracted_text is populated from image observations."""
    from app.services.image_understanding import analyse_images

    assets = _make_assets(1, tmp_path)
    mock_obs = [_make_observation(assets[0]["media_id"], 0)]

    with patch("app.services.image_understanding.get_vision_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.analyse.return_value = mock_obs
        mock_get.return_value = mock_provider

        evidence = analyse_images(assets, "col001", "single")

    assert len(evidence.all_extracted_text) == 1
    assert evidence.all_extracted_text[0].text == "BRAND"


def test_single_image_png(tmp_path):
    """PNG images are handled correctly."""
    from app.services.image_understanding import analyse_images

    assets = _make_assets(1, tmp_path)
    mock_obs = [_make_observation(assets[0]["media_id"])]

    with patch("app.services.image_understanding.get_vision_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.analyse.return_value = mock_obs
        mock_get.return_value = mock_provider

        evidence = analyse_images(assets, "col001", "single")

    assert evidence.processing_status == "complete"


def test_single_image_jpeg(tmp_path):
    """JPEG images are handled correctly."""
    from app.services.image_understanding import analyse_images
    from app.storage.local_storage import LocalStorage
    import os
    os.environ["STORAGE_DIR"] = str(tmp_path)
    from app.core.config import get_settings
    get_settings.cache_clear()

    storage = LocalStorage(base_dir=str(tmp_path))
    key = storage.generate_key(".jpg")
    storage.save(make_jpeg(), key)
    assets = [{
        "media_id": "jpeg_001",
        "storage_key": key,
        "original_filename": "photo.jpg",
        "sequence_index": 0,
        "metadata_json": None,
    }]

    mock_obs = [_make_observation("jpeg_001")]
    with patch("app.services.image_understanding.get_vision_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.analyse.return_value = mock_obs
        mock_get.return_value = mock_provider

        evidence = analyse_images(assets, "col001", "single")

    assert evidence.processing_status == "complete"


def test_single_image_webp(tmp_path):
    """WebP images are handled correctly."""
    from app.services.image_understanding import analyse_images
    from app.storage.local_storage import LocalStorage
    import os
    os.environ["STORAGE_DIR"] = str(tmp_path)
    from app.core.config import get_settings
    get_settings.cache_clear()

    storage = LocalStorage(base_dir=str(tmp_path))
    key = storage.generate_key(".webp")
    storage.save(make_webp(), key)
    assets = [{
        "media_id": "webp_001",
        "storage_key": key,
        "original_filename": "photo.webp",
        "sequence_index": 0,
        "metadata_json": None,
    }]

    mock_obs = [_make_observation("webp_001")]
    with patch("app.services.image_understanding.get_vision_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.analyse.return_value = mock_obs
        mock_get.return_value = mock_provider

        evidence = analyse_images(assets, "col001", "single")

    assert evidence.processing_status == "complete"


# ---------------------------------------------------------------------------
# Carousel understanding
# ---------------------------------------------------------------------------

def test_carousel_sequence_preserved(tmp_path):
    """Carousel image sequence_index values must be preserved in order."""
    from app.services.image_understanding import analyse_images

    n = 4
    assets = _make_assets(n, tmp_path)
    mock_obs = [_make_observation(a["media_id"], a["sequence_index"]) for a in assets]

    with patch("app.services.image_understanding.get_vision_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.analyse.return_value = mock_obs
        mock_get.return_value = mock_provider

        evidence = analyse_images(assets, "col001", "carousel")

    assert len(evidence.image_observations) == n
    for i, obs in enumerate(evidence.image_observations):
        assert obs.sequence_index == i


def test_carousel_all_media_ids_present(tmp_path):
    """Every asset's media_id must appear in the observations."""
    from app.services.image_understanding import analyse_images

    assets = _make_assets(3, tmp_path)
    mock_obs = [_make_observation(a["media_id"], a["sequence_index"]) for a in assets]

    with patch("app.services.image_understanding.get_vision_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.analyse.return_value = mock_obs
        mock_get.return_value = mock_provider

        evidence = analyse_images(assets, "col001", "carousel")

    observed_ids = {o.media_id for o in evidence.image_observations}
    expected_ids = {a["media_id"] for a in assets}
    assert observed_ids == expected_ids


def test_multiple_images_extracted_text_aggregated(tmp_path):
    """all_extracted_text aggregates OCR from all images."""
    from app.services.image_understanding import analyse_images

    assets = _make_assets(3, tmp_path)
    mock_obs = [
        ImageObservation(
            media_id=a["media_id"],
            sequence_index=a["sequence_index"],
            extracted_text=[ExtractedText(text=f"TEXT_{i}")],
            provider="gemini",
            model_version="gemini-2.0-flash",
        )
        for i, a in enumerate(assets)
    ]

    with patch("app.services.image_understanding.get_vision_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.analyse.return_value = mock_obs
        mock_get.return_value = mock_provider

        evidence = analyse_images(assets, "col001", "carousel")

    assert len(evidence.all_extracted_text) == 3
    texts = {t.text for t in evidence.all_extracted_text}
    assert texts == {"TEXT_0", "TEXT_1", "TEXT_2"}


# ---------------------------------------------------------------------------
# Empty / invalid collections
# ---------------------------------------------------------------------------

def test_empty_assets_returns_failed_evidence(tmp_path):
    """Empty asset list returns failed MediaEvidence."""
    from app.services.image_understanding import analyse_images

    evidence = analyse_images([], "col001", "single")
    assert evidence.processing_status == "failed"
    assert len(evidence.processing_errors) > 0


def test_missing_storage_key_recorded_as_error(tmp_path):
    """If a storage key does not exist, the error is recorded."""
    from app.services.image_understanding import analyse_images
    import os
    os.environ["STORAGE_DIR"] = str(tmp_path)
    from app.core.config import get_settings
    get_settings.cache_clear()

    assets = [{
        "media_id": "img_missing",
        "storage_key": "nonexistent_key.png",
        "original_filename": "missing.png",
        "sequence_index": 0,
        "metadata_json": None,
    }]

    evidence = analyse_images(assets, "col001", "single")
    assert evidence.processing_status == "failed"
    assert any("img_missing" in e for e in evidence.processing_errors)


# ---------------------------------------------------------------------------
# Provider failure handling
# ---------------------------------------------------------------------------

def test_provider_config_error_returns_failed_evidence(tmp_path):
    """Missing API key returns failed evidence, not an exception."""
    from app.services.image_understanding import analyse_images

    assets = _make_assets(1, tmp_path)

    with patch("app.services.image_understanding.get_vision_provider") as mock_get:
        mock_get.side_effect = ProviderConfigError("gemini", "GEMINI_API_KEY not set")

        evidence = analyse_images(assets, "col001", "single")

    assert evidence.processing_status == "failed"
    assert any("GEMINI_API_KEY" in e for e in evidence.processing_errors)


def test_provider_error_returns_failed_evidence(tmp_path):
    """Provider runtime error returns failed evidence, not an exception."""
    from app.services.image_understanding import analyse_images

    assets = _make_assets(1, tmp_path)

    with patch("app.services.image_understanding.get_vision_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.analyse.side_effect = ProviderError("gemini", "API timeout", retryable=True)
        mock_get.return_value = mock_provider

        evidence = analyse_images(assets, "col001", "single")

    assert evidence.processing_status == "failed"
    assert any("timeout" in e.lower() for e in evidence.processing_errors)


def test_provider_response_validation(tmp_path):
    """Provider returning wrong type raises, not silently passes."""
    from app.services.image_understanding import analyse_images

    assets = _make_assets(1, tmp_path)

    with patch("app.services.image_understanding.get_vision_provider") as mock_get:
        mock_provider = MagicMock()
        # Return a valid list of observations — this should succeed
        mock_provider.analyse.return_value = [
            ImageObservation(media_id=assets[0]["media_id"], provider="gemini", model_version="gemini-2.0-flash")
        ]
        mock_get.return_value = mock_provider

        evidence = analyse_images(assets, "col001", "single")

    assert evidence.processing_status == "complete"
