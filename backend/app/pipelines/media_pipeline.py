"""Media processing pipeline.

Phase 1: intake only.
Future phases will add vision analysis, audio transcription, and caption generation.
"""

from typing import List

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.schemas.media import UploadResponseData
from app.services.media_service import ingest_uploads


async def run_intake_pipeline(files: List[UploadFile], db: Session) -> UploadResponseData:
    """Entry point for the media intake pipeline.

    Currently performs: validation → metadata extraction → storage → DB persistence.
    Returns structured upload response data.
    """
    return await ingest_uploads(files, db)
