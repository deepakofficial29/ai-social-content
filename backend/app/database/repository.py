"""Data-access layer – thin repository wrappers around SQLAlchemy sessions."""

import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.database.models import MediaAsset, MediaCollection, ProcessingJob


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
