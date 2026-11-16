"""Media service – orchestrates validation, metadata extraction, storage, and DB persistence."""

import json
from typing import List, Tuple

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import MediaNotFoundError, StorageError
from app.core.logging import get_logger
from app.core.security import sanitize_filename
from app.database import repository as repo
from app.database.models import MediaAsset, MediaCollection
from app.schemas.media import MediaDetailResponse, MediaItemResponse, UploadResponseData
from app.services.metadata_service import (
    extract_audio_metadata,
    extract_image_metadata,
    extract_video_metadata,
)
from app.services.validation_service import (
    read_and_validate_upload,
    validate_image_bytes,
)
from app.storage.local_storage import LocalStorage
from app.utils.file_utils import guess_mime_type

logger = get_logger(__name__)


def _get_storage() -> LocalStorage:
    """Return a LocalStorage instance rooted at the current STORAGE_DIR setting.

    Called per-request so that test overrides of STORAGE_DIR take effect.
    """
    return LocalStorage()


async def ingest_uploads(
    files: List[UploadFile],
    db: Session,
) -> UploadResponseData:
    """Validate, store, and persist one or more uploaded files.

    Preserves sequence order for multi-image / carousel uploads.
    Rolls back storage on any failure.
    """
    settings = get_settings()
    saved_keys: List[str] = []
    storage = _get_storage()

    # Determine collection type
    if len(files) == 1:
        # Will be refined after we know the media type
        collection_type_placeholder = "single"
    else:
        collection_type_placeholder = "carousel"

    collection = repo.create_collection(db, collection_type_placeholder)

    media_items: List[MediaItemResponse] = []

    try:
        for index, file in enumerate(files):
            data, ext, media_type = await read_and_validate_upload(file, settings)

            # Deep content validation
            if media_type == "image":
                validate_image_bytes(data)
                metadata = extract_image_metadata(data)
            elif media_type == "video":
                metadata = extract_video_metadata(data, ext)
            else:
                metadata = extract_audio_metadata(data, ext)

            # Update collection type on first (and possibly only) file
            if index == 0:
                collection.collection_type = _collection_type(media_type, len(files))

            # Safe storage key
            storage_key = storage.generate_key(f".{ext}")
            storage.save(data, storage_key)
            saved_keys.append(storage_key)

            safe_name = sanitize_filename(file.filename or f"upload.{ext}")
            mime = file.content_type or guess_mime_type(file.filename or "")

            asset = repo.create_asset(
                db,
                original_filename=safe_name,
                stored_filename=storage_key,
                media_type=media_type,
                mime_type=mime,
                file_size=len(data),
                storage_key=storage_key,
                metadata_json=json.dumps(metadata),
                collection_id=collection.id,
                sequence_index=index,
            )

            # Create an initial processing job
            repo.create_job(db, asset_id=asset.id, collection_id=collection.id)

            media_items.append(
                MediaItemResponse(
                    media_id=asset.id,
                    filename=safe_name,
                    media_type=media_type,
                    file_size=len(data),
                    metadata=metadata,
                    processing_status="uploaded",
                    sequence_index=index,
                )
            )

        db.commit()

    except Exception:
        db.rollback()
        # Clean up any files already written
        for key in saved_keys:
            try:
                storage.delete(key)
            except Exception:
                pass
        raise

    return UploadResponseData(collection_id=collection.id, media=media_items)


def get_media_detail(media_id: str, db: Session) -> MediaDetailResponse:
    asset = repo.get_asset(db, media_id)
    if not asset:
        raise MediaNotFoundError(f"Media '{media_id}' not found.")
    return _asset_to_detail(asset)


def delete_media(media_id: str, db: Session) -> None:
    asset = repo.get_asset(db, media_id)
    if not asset:
        raise MediaNotFoundError(f"Media '{media_id}' not found.")

    storage = _get_storage()
    try:
        storage.delete(asset.storage_key)
    except StorageError as exc:
        logger.warning("Could not delete storage file for %s: %s", media_id, exc)

    repo.delete_asset(db, asset)
    db.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collection_type(media_type: str, count: int) -> str:
    if media_type == "video":
        return "video"
    if media_type == "audio":
        return "audio"
    return "carousel" if count > 1 else "single"


def _asset_to_detail(asset: MediaAsset) -> MediaDetailResponse:
    metadata = json.loads(asset.metadata_json) if asset.metadata_json else None
    return MediaDetailResponse(
        media_id=asset.id,
        filename=asset.original_filename,
        media_type=asset.media_type,
        mime_type=asset.mime_type,
        file_size=asset.file_size,
        metadata=metadata,
        collection_id=asset.collection_id,
        sequence_index=asset.sequence_index,
        processing_status="uploaded",
        created_at=asset.created_at.isoformat(),
    )
