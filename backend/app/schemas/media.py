"""Pydantic schemas for media assets and upload responses."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Metadata sub-schemas (populated by inspection services)
# ---------------------------------------------------------------------------

class ImageMetadata(BaseModel):
    width: int
    height: int
    format: str
    mode: Optional[str] = None


class VideoMetadata(BaseModel):
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None
    frame_rate: Optional[float] = None
    video_codec: Optional[str] = None
    has_audio: bool = False
    audio_codec: Optional[str] = None
    file_size: int


class AudioMetadata(BaseModel):
    duration_seconds: Optional[float] = None
    codec: Optional[str] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    file_size: int


# ---------------------------------------------------------------------------
# MediaContext – designed for future AI pipeline population
# ---------------------------------------------------------------------------

class MediaContext(BaseModel):
    media_id: str
    media_type: Literal["image", "video", "audio"]
    original_filename: str
    media_metadata: Optional[Dict[str, Any]] = None

    # AI-populated fields – always null in Phase 1
    visual_observations: Optional[str] = None
    audio_observations: Optional[str] = None
    transcription: Optional[str] = None
    detected_language: Optional[str] = None
    extracted_text: Optional[str] = None
    evidence_references: List[str] = []

    processing_status: str = "uploaded"


# ---------------------------------------------------------------------------
# API response shapes
# ---------------------------------------------------------------------------

class MediaItemResponse(BaseModel):
    media_id: str
    filename: str
    media_type: str
    file_size: int
    metadata: Optional[Dict[str, Any]] = None
    processing_status: str
    sequence_index: int = 0


class UploadResponseData(BaseModel):
    collection_id: str
    media: List[MediaItemResponse]


class MediaDetailResponse(BaseModel):
    media_id: str
    filename: str
    media_type: str
    mime_type: str
    file_size: int
    metadata: Optional[Dict[str, Any]] = None
    collection_id: Optional[str] = None
    sequence_index: int
    processing_status: str
    created_at: str


class CollectionSummaryResponse(BaseModel):
    collection_id: str
    collection_type: str
    created_at: str
    media: List[MediaItemResponse]
