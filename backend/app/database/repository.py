"""Data-access layer – thin repository wrappers around SQLAlchemy sessions."""

import uuid
import json
from typing import List, Optional

from sqlalchemy.orm import Session

from app.database.models import (
    EvidenceConflict as EvidenceConflictRow,
    EvidenceItem as EvidenceItemRow,
    EvidencePackage,
    EvidenceProvenance,
    EvidenceQuality,
    EvidenceRelationship,
    EvidenceSummary,
    GenerationConfigRecord,
    GenerationRequestRecord,
    CaptionVariantRecord,
    GroundingResultRecord,
    CaptionQualityResultRecord,
    MediaAsset,
    MediaCollection,
    ProcessingJob,
)
from app.schemas.unified_evidence import UnifiedMediaEvidence
from app.schemas.generation import (
    CaptionVariant,
    GenerationConfig,
    GenerationRequest,
    GroundingResult,
    QualityResult,
)


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# MediaCollection
# ---------------------------------------------------------------------------

def create_collection(db: Session, collection_type: str) -> MediaCollection:
    obj = MediaCollection(id=_new_id(), collection_type=collection_type)
    db.add(obj)
    db.flush()
    return obj


def get_collection(db: Session, collection_id: str) -> Optional[MediaCollection]:
    return db.get(MediaCollection, collection_id)


def list_collections(db: Session) -> List[MediaCollection]:
    return db.query(MediaCollection).order_by(MediaCollection.created_at.desc()).all()


# ---------------------------------------------------------------------------
# MediaAsset
# ---------------------------------------------------------------------------

def create_asset(db: Session, **kwargs) -> MediaAsset:
    obj = MediaAsset(id=_new_id(), **kwargs)
    db.add(obj)
    db.flush()
    return obj


def get_asset(db: Session, asset_id: str) -> Optional[MediaAsset]:
    return db.get(MediaAsset, asset_id)


def delete_asset(db: Session, asset: MediaAsset) -> None:
    db.delete(asset)
    db.flush()


# ---------------------------------------------------------------------------
# ProcessingJob
# ---------------------------------------------------------------------------

def create_job(
    db: Session,
    asset_id: Optional[str] = None,
    collection_id: Optional[str] = None,
) -> ProcessingJob:
    obj = ProcessingJob(id=_new_id(), asset_id=asset_id, collection_id=collection_id)
    db.add(obj)
    db.flush()
    return obj


def get_job(db: Session, job_id: str) -> Optional[ProcessingJob]:
    return db.get(ProcessingJob, job_id)


def update_job_status(
    db: Session,
    job: ProcessingJob,
    status: str,
    error_message: Optional[str] = None,
) -> ProcessingJob:
    job.status = status
    if error_message is not None:
        job.error_message = error_message
    db.flush()
    return job


# ---------------------------------------------------------------------------
# Evidence packages
# ---------------------------------------------------------------------------

def get_evidence_package(db: Session, collection_id: str) -> Optional[EvidencePackage]:
    return db.query(EvidencePackage).filter(EvidencePackage.collection_id == collection_id).first()


def save_evidence_package(db: Session, package: UnifiedMediaEvidence, processing_job_id: Optional[str] = None) -> EvidencePackage:
    existing = get_evidence_package(db, package.collection_id)
    if existing:
        existing.package_version += 1
        existing.schema_version = package.schema_version
        existing.processing_status = package.processing_status
        existing.processing_job_id = processing_job_id
        package.package_id = existing.id
        existing.package_json = package.model_dump_json()
        row = existing

        db.query(EvidenceProvenance).filter(
            EvidenceProvenance.evidence_item_id.in_(
                db.query(EvidenceItemRow.id).filter(EvidenceItemRow.package_id == existing.id)
            )
        ).delete(synchronize_session=False)
        db.query(EvidenceItemRow).filter(EvidenceItemRow.package_id == existing.id).delete(synchronize_session=False)
        db.query(EvidenceRelationship).filter(EvidenceRelationship.package_id == existing.id).delete(synchronize_session=False)
        db.query(EvidenceConflictRow).filter(EvidenceConflictRow.package_id == existing.id).delete(synchronize_session=False)
        db.query(EvidenceQuality).filter(EvidenceQuality.package_id == existing.id).delete(synchronize_session=False)
        db.query(EvidenceSummary).filter(EvidenceSummary.package_id == existing.id).delete(synchronize_session=False)
    else:
        row = EvidencePackage(
            id=package.package_id,
            collection_id=package.collection_id,
            processing_job_id=processing_job_id,
            schema_version=package.schema_version,
            package_version=1,
            processing_status=package.processing_status,
            package_json=package.model_dump_json(),
        )
        db.add(row)

    db.flush()

    for evidence_item in package.evidence_items:
        item_row = EvidenceItemRow(
            id=evidence_item.evidence_id,
            package_id=row.id,
            category=evidence_item.category.value,
            observation_type=evidence_item.observation_type.value,
            source_media_id=evidence_item.source.media_id,
            modality=evidence_item.source.modality.value,
            evidence_json=evidence_item.model_dump_json(),
        )
        db.add(item_row)
        db.add(EvidenceProvenance(
            evidence_item_id=evidence_item.evidence_id,
            source_json=evidence_item.source.model_dump_json(),
        ))

    for relationship in package.cross_modal_relationships:
        db.add(EvidenceRelationship(
            id=relationship.relationship_id,
            package_id=row.id,
            relationship_type=relationship.relationship_type.value,
            relationship_json=relationship.model_dump_json(),
        ))

    for conflict in package.conflicts:
        db.add(EvidenceConflictRow(
            id=conflict.conflict_id,
            package_id=row.id,
            resolution_status=conflict.resolution_status,
            conflict_json=conflict.model_dump_json(),
        ))

    if package.quality:
        db.add(EvidenceQuality(
            package_id=row.id,
            overall_status=package.quality.overall_status.value,
            quality_json=package.quality.model_dump_json(),
        ))
    if package.content_summary:
        db.add(EvidenceSummary(
            package_id=row.id,
            summary_json=package.content_summary.model_dump_json(),
        ))

    db.flush()
    return row


def load_evidence_package(db: Session, collection_id: str) -> Optional[UnifiedMediaEvidence]:
    row = get_evidence_package(db, collection_id)
    if not row:
        return None
    return UnifiedMediaEvidence.model_validate_json(row.package_json)


# ---------------------------------------------------------------------------
# Phase 4 generation records
# ---------------------------------------------------------------------------

def save_generation_config(db: Session, collection_id: str, config: GenerationConfig) -> GenerationConfigRecord:
    row = db.query(GenerationConfigRecord).filter(
        GenerationConfigRecord.collection_id == collection_id
    ).first()
    if row:
        row.config_json = config.model_dump_json()
    else:
        row = GenerationConfigRecord(
            collection_id=collection_id,
            config_json=config.model_dump_json(),
        )
        db.add(row)
    db.flush()
    return row


def get_generation_config(db: Session, collection_id: str) -> Optional[GenerationConfig]:
    row = db.query(GenerationConfigRecord).filter(
        GenerationConfigRecord.collection_id == collection_id
    ).first()
    return GenerationConfig.model_validate_json(row.config_json) if row else None


def save_generation_request(db: Session, request: GenerationRequest) -> GenerationRequestRecord:
    row = GenerationRequestRecord(
        id=request.request_id,
        collection_id=request.collection_id,
        evidence_package_id=request.evidence_package_id,
        evidence_package_version=request.evidence_package_version,
        status=request.status,
        request_json=request.model_dump_json(),
    )
    db.add(row)
    db.flush()

    for variant in request.variants:
        db.add(CaptionVariantRecord(
            id=variant.variant_id,
            request_id=request.request_id,
            approach=variant.approach,
            variant_json=variant.model_dump_json(),
            evidence_ids_json=json.dumps(variant.evidence_ids),
        ))
    db.flush()

    for variant in request.variants:
        grounding = request.grounding.get(variant.variant_id)
        if grounding:
            db.add(GroundingResultRecord(
                id=grounding.grounding_id,
                request_id=request.request_id,
                variant_id=variant.variant_id,
                status=grounding.status,
                is_verified=1 if grounding.is_verified else 0,
                grounding_json=grounding.model_dump_json(),
            ))
        quality = request.quality.get(variant.variant_id)
        if quality:
            db.add(CaptionQualityResultRecord(
                id=quality.quality_id,
                request_id=request.request_id,
                variant_id=variant.variant_id,
                grounding_separate_status=quality.grounding_separate_status,
                quality_json=quality.model_dump_json(),
            ))
    db.flush()
    return row


def get_generation_request(db: Session, generation_id: str) -> Optional[GenerationRequest]:
    row = db.get(GenerationRequestRecord, generation_id)
    if not row:
        return None
    return GenerationRequest.model_validate_json(row.request_json)


def list_generation_requests(db: Session, collection_id: str) -> List[GenerationRequest]:
    rows = db.query(GenerationRequestRecord).filter(
        GenerationRequestRecord.collection_id == collection_id
    ).order_by(GenerationRequestRecord.created_at.desc()).all()
    return [GenerationRequest.model_validate_json(row.request_json) for row in rows]


def list_all_generation_requests(db: Session) -> List[GenerationRequest]:
    rows = db.query(GenerationRequestRecord).order_by(
        GenerationRequestRecord.created_at.desc()
    ).all()
    return [GenerationRequest.model_validate_json(row.request_json) for row in rows]
