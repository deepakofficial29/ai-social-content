"""Image understanding service — Phase 2.3.

Orchestrates vision provider calls for single images and carousels.
Reads image bytes from local storage, builds provider requests, and
returns structured ImageObservation results.
"""

import json
from pathlib import Path
from typing import List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.base import ProviderConfigError, ProviderError
from app.providers.registry import get_vision_provider
from app.schemas.evidence import (
    ConfidenceLevel,
    ExtractedText,
    ImageObservation,
    MediaEvidence,
)
from app.schemas.provider_requests import ImageInput, VisionRequest
from app.storage.local_storage import LocalStorage

logger = get_logger(__name__)

_MIME_MAP = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


def _get_storage() -> LocalStorage:
    return LocalStorage()


def _ext_from_filename(filename: str) -> str:
    return Path(filename).suffix.lstrip(".").lower()


def _mime_from_filename(filename: str) -> str:
    ext = _ext_from_filename(filename)
    return _MIME_MAP.get(ext, "image/jpeg")


def analyse_images(
    assets: List[dict],
    collection_id: str,
    collection_type: str,
) -> MediaEvidence:
    """Analyse one or more image assets and return a MediaEvidence.

    Args:
        assets: list of dicts with keys: media_id, storage_key,
                original_filename, sequence_index, metadata_json
        collection_id: the collection these assets belong to
        collection_type: single | carousel | multi

    Returns:
        MediaEvidence with image_observations populated.
        On provider failure, returns partial evidence with errors recorded.
    """
    settings = get_settings()
    storage = _get_storage()
    provider_name = settings.VISION_PROVIDER
    errors: List[str] = []

    # Load image bytes from storage
    image_inputs: List[ImageInput] = []
    for asset in sorted(assets, key=lambda a: a.get("sequence_index", 0)):
        try:
            data = storage.load(asset["storage_key"])
        except Exception as exc:
            errors.append(f"Failed to load image {asset['media_id']}: {exc}")
            continue

        image_inputs.append(
            ImageInput(
                data=data,
                filename=asset["original_filename"],
                media_id=asset["media_id"],
                sequence_index=asset.get("sequence_index", 0),
                mime_type=_mime_from_filename(asset["original_filename"]),
            )
        )

    if not image_inputs:
        return MediaEvidence(
            collection_id=collection_id,
            collection_type=collection_type,
            processing_status="failed",
            processing_errors=errors or ["No image data could be loaded"],
        )

    request = VisionRequest(
        images=image_inputs,
        collection_id=collection_id,
    )

    try:
        provider = get_vision_provider(provider_name)
        observations = provider.analyse(request)
    except ProviderConfigError as exc:
        logger.warning("Vision provider not configured: %s", exc)
        return MediaEvidence(
            collection_id=collection_id,
            collection_type=collection_type,
            processing_status="failed",
            processing_errors=[str(exc)],
        )
    except ProviderError as exc:
        logger.error("Vision provider error: %s", exc)
        return MediaEvidence(
            collection_id=collection_id,
            collection_type=collection_type,
            processing_status="failed",
            processing_errors=[str(exc)],
        )

    # Aggregate all extracted text
    all_text: List[ExtractedText] = []
    for obs in observations:
        all_text.extend(obs.extracted_text)

    providers_used = list({obs.provider for obs in observations if obs.provider})

    return MediaEvidence(
        collection_id=collection_id,
        collection_type=collection_type,
        image_observations=observations,
        all_extracted_text=all_text,
        processing_status="complete",
        processing_errors=errors,
        has_visual_evidence=bool(observations),
        overall_confidence=_aggregate_confidence(observations),
        providers_used=providers_used,
    )


def _aggregate_confidence(observations: List[ImageObservation]) -> ConfidenceLevel:
    if not observations:
        return ConfidenceLevel.LOW
    levels = [o.confidence for o in observations]
    if all(l == ConfidenceLevel.HIGH for l in levels):
        return ConfidenceLevel.HIGH
    if any(l == ConfidenceLevel.LOW for l in levels):
        return ConfidenceLevel.LOW
    return ConfidenceLevel.MEDIUM
