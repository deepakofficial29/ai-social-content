"""Understanding pipeline — Phase 2.

Routes media to the appropriate understanding services based on media type
and collection type.  Returns a unified MediaEvidence structure.

Flow:
  Media Upload
      ↓
  Media Inspection (Phase 1 — already done)
      ↓
  Determine Media Type
      ↓
  Modality Processing
      ├── image/single   → VisionProvider
      ├── image/carousel → VisionProvider (ordered multi-image)
      ├── video          → VideoUnderstandingProvider + AudioProcessing
      └── audio          → TranscriptionProvider + AudioUnderstandingProvider
      ↓
  Combine Results → MediaEvidence
      ↓
  Return MediaEvidence
"""

import json
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.database import repository as repo
from app.database.models import MediaAsset, MediaCollection
from app.schemas.evidence import MediaEvidence
from app.services.audio_understanding import analyse_audio
from app.services.image_understanding import analyse_images
from app.services.video_understanding import analyse_video

logger = get_logger(__name__)


def run_understanding_pipeline(
    collection_id: str,
    db: Session,
) -> MediaEvidence:
    """Run the full understanding pipeline for a collection.

    Loads the collection and its assets from the database, routes to the
    appropriate understanding service, and returns a MediaEvidence.

    This is synchronous in Phase 2.  For long videos or large carousels,
    processing may take 10–120 seconds.  A background job queue should be
    introduced in Phase 3 when processing time regularly exceeds 30 seconds.
    """
    collection = repo.get_collection(db, collection_id)
    if not collection:
        return MediaEvidence(
            collection_id=collection_id,
            collection_type="unknown",
            processing_status="failed",
            processing_errors=[f"Collection '{collection_id}' not found"],
        )

    assets = sorted(collection.assets, key=lambda a: a.sequence_index)
    if not assets:
        return MediaEvidence(
            collection_id=collection_id,
            collection_type=collection.collection_type,
            processing_status="failed",
            processing_errors=["Collection has no assets"],
        )

    collection_type = collection.collection_type
    media_type = assets[0].media_type  # all assets in a collection share media type

    logger.info(
        "Starting understanding pipeline: collection=%s type=%s assets=%d",
        collection_id, collection_type, len(assets),
    )

    evidence = _route_to_service(assets, collection_id, collection_type, media_type)

    # Stamp processed_at
    evidence.processed_at = datetime.now(timezone.utc)
    for job in collection.jobs:
        if job.collection_id == collection_id:
            if evidence.processing_status == "failed":
                repo.update_job_status(db, job, "failed", "; ".join(evidence.processing_errors))
            else:
                repo.update_job_status(
                    db,
                    job,
                    "completed",
                    "; ".join(evidence.processing_errors) if evidence.processing_errors else None,
                )
    db.commit()

    logger.info(
        "Understanding pipeline complete: collection=%s status=%s errors=%d",
        collection_id, evidence.processing_status, len(evidence.processing_errors),
    )

    return evidence


def _route_to_service(
    assets: List[MediaAsset],
    collection_id: str,
    collection_type: str,
    media_type: str,
) -> MediaEvidence:
    """Route assets to the correct understanding service."""

    if media_type == "image":
        asset_dicts = [_asset_to_dict(a) for a in assets]
        return analyse_images(asset_dicts, collection_id, collection_type)

    if media_type == "video":
        if len(assets) != 1:
            return MediaEvidence(
                collection_id=collection_id,
                collection_type=collection_type,
                processing_status="failed",
                processing_errors=["Video collection must contain exactly one asset"],
            )
        return analyse_video(_asset_to_dict(assets[0]), collection_id)

    if media_type == "audio":
        if len(assets) != 1:
            return MediaEvidence(
                collection_id=collection_id,
                collection_type=collection_type,
                processing_status="failed",
                processing_errors=["Audio collection must contain exactly one asset"],
            )
        return analyse_audio(_asset_to_dict(assets[0]), collection_id)

    return MediaEvidence(
        collection_id=collection_id,
        collection_type=collection_type,
        processing_status="failed",
        processing_errors=[f"Unknown media type: {media_type}"],
    )


def _asset_to_dict(asset: MediaAsset) -> dict:
    return {
        "media_id": asset.id,
        "storage_key": asset.storage_key,
        "original_filename": asset.original_filename,
        "sequence_index": asset.sequence_index,
        "metadata_json": asset.metadata_json,
        "media_type": asset.media_type,
    }
