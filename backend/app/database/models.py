"""SQLAlchemy ORM models."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class MediaCollection(Base):
    __tablename__ = "media_collections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    collection_type: Mapped[str] = mapped_column(String(32))  # single|multi|carousel|video|audio
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    assets: Mapped[list["MediaAsset"]] = relationship(
        "MediaAsset", back_populates="collection", order_by="MediaAsset.sequence_index"
    )
    jobs: Mapped[list["ProcessingJob"]] = relationship("ProcessingJob", back_populates="collection")


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    original_filename: Mapped[str] = mapped_column(String(512))
    stored_filename: Mapped[str] = mapped_column(String(512), unique=True)
    media_type: Mapped[str] = mapped_column(String(16))   # image|video|audio
    mime_type: Mapped[str] = mapped_column(String(128))
    file_size: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    collection_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("media_collections.id"), nullable=True
    )
    sequence_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    collection: Mapped[Optional[MediaCollection]] = relationship(
        "MediaCollection", back_populates="assets"
    )
    jobs: Mapped[list["ProcessingJob"]] = relationship("ProcessingJob", back_populates="asset")

    __table_args__ = (
        Index("ix_media_assets_collection_id", "collection_id"),
        Index("ix_media_assets_media_type", "media_type"),
    )


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    asset_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("media_assets.id"), nullable=True
    )
    collection_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("media_collections.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued|processing|completed|failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    asset: Mapped[Optional[MediaAsset]] = relationship("MediaAsset", back_populates="jobs")
    collection: Mapped[Optional[MediaCollection]] = relationship("MediaCollection", back_populates="jobs")

    __table_args__ = (
        Index("ix_processing_jobs_status", "status"),
    )


class EvidencePackage(Base):
    __tablename__ = "evidence_packages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    collection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("media_collections.id"), unique=True, nullable=False
    )
    processing_job_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("processing_jobs.id"), nullable=True
    )
    schema_version: Mapped[str] = mapped_column(String(16), default="1")
    package_version: Mapped[int] = mapped_column(Integer, default=1)
    processing_status: Mapped[str] = mapped_column(String(16), default="pending")
    package_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    items: Mapped[list["EvidenceItem"]] = relationship(
        "EvidenceItem", back_populates="package", cascade="all, delete-orphan"
    )
    relationships: Mapped[list["EvidenceRelationship"]] = relationship(
        "EvidenceRelationship", back_populates="package", cascade="all, delete-orphan"
    )
    conflicts: Mapped[list["EvidenceConflict"]] = relationship(
        "EvidenceConflict", back_populates="package", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_evidence_packages_collection_id", "collection_id", unique=True),
    )


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    package_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_packages.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(32))
    observation_type: Mapped[str] = mapped_column(String(32))
    source_media_id: Mapped[str] = mapped_column(String(36))
    modality: Mapped[str] = mapped_column(String(32))
    evidence_json: Mapped[str] = mapped_column(Text)

    package: Mapped[EvidencePackage] = relationship("EvidencePackage", back_populates="items")
    provenance: Mapped[Optional["EvidenceProvenance"]] = relationship(
        "EvidenceProvenance", back_populates="item", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_evidence_items_package_id", "package_id"),
        Index("ix_evidence_items_source_media_id", "source_media_id"),
    )


class EvidenceProvenance(Base):
    __tablename__ = "evidence_provenance"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    evidence_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_items.id"), unique=True, nullable=False
    )
    source_json: Mapped[str] = mapped_column(Text)

    item: Mapped[EvidenceItem] = relationship("EvidenceItem", back_populates="provenance")


class EvidenceRelationship(Base):
    __tablename__ = "evidence_relationships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    package_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_packages.id"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String(32))
    relationship_json: Mapped[str] = mapped_column(Text)

    package: Mapped[EvidencePackage] = relationship("EvidencePackage", back_populates="relationships")


class EvidenceConflict(Base):
    __tablename__ = "evidence_conflicts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    package_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_packages.id"), nullable=False
    )
    resolution_status: Mapped[str] = mapped_column(String(32), default="unresolved")
    conflict_json: Mapped[str] = mapped_column(Text)

    package: Mapped[EvidencePackage] = relationship("EvidencePackage", back_populates="conflicts")


class EvidenceQuality(Base):
    __tablename__ = "evidence_quality"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    package_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_packages.id"), unique=True, nullable=False
    )
    overall_status: Mapped[str] = mapped_column(String(32))
    quality_json: Mapped[str] = mapped_column(Text)


class EvidenceSummary(Base):
    __tablename__ = "evidence_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    package_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_packages.id"), unique=True, nullable=False
    )
    summary_json: Mapped[str] = mapped_column(Text)


class GenerationConfigRecord(Base):
    __tablename__ = "generation_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    collection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("media_collections.id"), nullable=False
    )
    config_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    __table_args__ = (
        Index("ix_generation_configs_collection_id", "collection_id"),
    )


class GenerationRequestRecord(Base):
    __tablename__ = "generation_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    collection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("media_collections.id"), nullable=False
    )
    evidence_package_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_packages.id"), nullable=False
    )
    evidence_package_version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="complete")
    request_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        Index("ix_generation_requests_collection_id", "collection_id"),
        Index("ix_generation_requests_package_id", "evidence_package_id"),
    )


class CaptionVariantRecord(Base):
    __tablename__ = "caption_variants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("generation_requests.id"), nullable=False
    )
    approach: Mapped[str] = mapped_column(String(64))
    variant_json: Mapped[str] = mapped_column(Text)
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        Index("ix_caption_variants_request_id", "request_id"),
    )


class GroundingResultRecord(Base):
    __tablename__ = "grounding_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("generation_requests.id"), nullable=False
    )
    variant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("caption_variants.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32))
    is_verified: Mapped[int] = mapped_column(Integer, default=0)
    grounding_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CaptionQualityResultRecord(Base):
    __tablename__ = "caption_quality_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("generation_requests.id"), nullable=False
    )
    variant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("caption_variants.id"), nullable=False
    )
    grounding_separate_status: Mapped[str] = mapped_column(String(32))
    quality_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
