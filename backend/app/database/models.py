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
