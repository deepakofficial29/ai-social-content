"""Phase 3 evidence pipeline."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.database import repository as repo
from app.evidence.fusion import (
    detect_contradictions,
    detect_cross_modal_relationships,
    detect_duplicate_relationships,
)
from app.evidence.normalizers import (
    normalize_audio_understanding_evidence,
    normalize_carousel_evidence,
    normalize_image_evidence,
    normalize_ocr_evidence,
    normalize_transcription_evidence,
    normalize_video_evidence,
)
from app.evidence.quality import assess_quality, build_grounded_summary
from app.schemas.evidence import MediaEvidence
from app.schemas.unified_evidence import UnifiedMediaEvidence
from app.pipelines.understanding_pipeline import run_understanding_pipeline


def build_unified_evidence(
    source: MediaEvidence,
) -> UnifiedMediaEvidence:
    """Normalize and fuse an existing Phase 2 MediaEvidence result."""
    items = []

    if source.image_observations:
        if source.collection_type == "carousel":
            items.extend(normalize_carousel_evidence(source.image_observations, source.collection_id))
        else:
            for index, observation in enumerate(source.image_observations):
                items.extend(normalize_image_evidence(
                    observation,
                    source.collection_id,
                    image_index=observation.sequence_index if observation.sequence_index != 0 else index,
                ))

    if source.all_extracted_text:
        media_id = source.image_observations[0].media_id if source.image_observations else "unknown"
        items.extend(normalize_ocr_evidence(
            source.all_extracted_text,
            media_id,
            source.collection_id,
        ))

    if source.video_observation:
        items.extend(normalize_video_evidence(source.video_observation, source.collection_id))
    if source.transcription:
        items.extend(normalize_transcription_evidence(source.transcription, source.collection_id))
    if source.audio_observation:
        media_type = "video" if source.collection_type == "video" else "audio"
        items.extend(normalize_audio_understanding_evidence(
            source.audio_observation,
            source.collection_id,
            media_type=media_type,
        ))

    relationships = detect_duplicate_relationships(items)
    relationships.extend(detect_cross_modal_relationships(items))
    conflicts = detect_contradictions(items)
    quality = assess_quality(
        source,
        items,
        conflicts,
        duplicate_relationship_count=sum(
            1 for relationship in relationships
            if relationship.relationship_type.value == "duplicate"
        ),
    )
    summary = build_grounded_summary(items, conflicts)

    asset_ids = []
    for item in items:
        if item.source.media_id not in asset_ids:
            asset_ids.append(item.source.media_id)

    package_status = "complete"
    if source.processing_status == "failed":
        package_status = "failed"
    elif source.processing_status == "partial" or source.processing_errors:
        package_status = "partial"

    package = UnifiedMediaEvidence(
        collection_id=source.collection_id,
        collection_type=source.collection_type,
        asset_ids=asset_ids,
        evidence_items=items,
        image_evidence_ids=[i.evidence_id for i in items if i.source.modality.value in {"image", "ocr"}],
        carousel_sequence=[i.evidence_id for i in items if i.source.image_index is not None],
        video_evidence_ids=[i.evidence_id for i in items if i.source.modality.value.startswith("video")],
        audio_evidence_ids=[i.evidence_id for i in items if i.source.modality.value.startswith("audio")],
        transcription_evidence_ids=[i.evidence_id for i in items if i.source.modality.value == "audio_transcription"],
        ocr_evidence_ids=[i.evidence_id for i in items if i.source.modality.value == "ocr"],
        cross_modal_relationships=relationships,
        conflicts=conflicts,
        quality=quality,
        content_summary=summary,
        processing_status=package_status,
        processed_at=datetime.now(timezone.utc),
        warnings=source.processing_errors,
        providers_used=source.providers_used,
        source_media_evidence=source.model_dump(mode="json"),
    )
    return package


def run_evidence_pipeline(
    collection_id: str,
    db: Session,
    rebuild: bool = False,
) -> Optional[UnifiedMediaEvidence]:
    """Return a stored package, or build and persist it once."""
    if not rebuild:
        package = repo.load_evidence_package(db, collection_id)
        if package:
            return package

    stored = repo.get_collection(db, collection_id)
    if not stored:
        return None

    source = run_understanding_pipeline(collection_id, db)
    package = build_unified_evidence(source)
    latest_job = sorted(stored.jobs, key=lambda job: job.created_at, reverse=True)[0] if stored.jobs else None
    repo.save_evidence_package(db, package, processing_job_id=latest_job.id if latest_job else None)
    db.commit()
    return package
