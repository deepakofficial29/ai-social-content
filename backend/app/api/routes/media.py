"""Media upload, retrieval, and deletion endpoints."""

from typing import List

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.exceptions import MediaNotFoundError
from app.database import repository as repo
from app.pipelines.media_pipeline import run_intake_pipeline
from app.schemas.common import APIResponse
from app.schemas.media import (
    CollectionSummaryResponse,
    MediaDetailResponse,
    MediaItemResponse,
    UploadResponseData,
)
from app.services.media_service import delete_media, get_media_detail

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/collections", response_model=APIResponse[List[CollectionSummaryResponse]])
def list_collections(db: Session = Depends(get_db)):
    summaries = []
    for collection in repo.list_collections(db):
        media_items = []
        for asset in collection.assets:
            detail = get_media_detail(asset.id, db)
            media_items.append(MediaItemResponse(
                media_id=detail.media_id,
                filename=detail.filename,
                media_type=detail.media_type,
                file_size=detail.file_size,
                metadata=detail.metadata,
                processing_status=detail.processing_status,
                sequence_index=detail.sequence_index,
            ))
        summaries.append(CollectionSummaryResponse(
            collection_id=collection.id,
            collection_type=collection.collection_type,
            created_at=collection.created_at.isoformat(),
            media=media_items,
        ))
    return APIResponse.ok("Media collections retrieved", data=summaries)


@router.post("/upload", response_model=APIResponse[UploadResponseData], status_code=201)
async def upload_media(
    files: List[UploadFile] = File(..., description="One or more media files"),
    db: Session = Depends(get_db),
):
    """Accept one or more media files (images, video, or audio).

    - For multiple images the original list order is preserved as the carousel sequence.
    - Only one video or one audio file may be uploaded per request.
    """
    if not files:
        return APIResponse.fail("No files provided.", "NO_FILES_PROVIDED")

    result = await run_intake_pipeline(files, db)
    return APIResponse.ok("Media uploaded successfully", data=result)


@router.get("/{media_id}", response_model=APIResponse[MediaDetailResponse])
def get_media(media_id: str, db: Session = Depends(get_db)):
    """Return stored metadata for a single media asset."""
    detail = get_media_detail(media_id, db)
    return APIResponse.ok("Media retrieved", data=detail)


@router.delete("/{media_id}", response_model=APIResponse)
def remove_media(media_id: str, db: Session = Depends(get_db)):
    """Delete a media asset and its stored file."""
    delete_media(media_id, db)
    return APIResponse.ok("Media deleted successfully")
