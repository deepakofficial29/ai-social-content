"""Media upload, retrieval, and deletion endpoints."""

from typing import List

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.exceptions import MediaNotFoundError
from app.pipelines.media_pipeline import run_intake_pipeline
from app.schemas.common import APIResponse
from app.schemas.media import MediaDetailResponse, UploadResponseData
from app.services.media_service import delete_media, get_media_detail

router = APIRouter(prefix="/media", tags=["media"])


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
