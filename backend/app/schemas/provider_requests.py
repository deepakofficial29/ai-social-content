"""Provider request schemas — inputs to AI provider calls."""

from typing import List, Optional

from pydantic import BaseModel


class ImageInput(BaseModel):
    """A single image for analysis."""

    data: bytes
    filename: str
    media_id: str
    sequence_index: int = 0
    mime_type: str = "image/jpeg"


class VisionRequest(BaseModel):
    """Request to a VisionProvider."""

    images: List[ImageInput]
    collection_id: Optional[str] = None
    prompt_context: Optional[str] = None


class VideoRequest(BaseModel):
    """Request to a VideoUnderstandingProvider."""

    file_path: str          # absolute path to the stored video file
    filename: str
    media_id: str
    extension: str
    has_audio: bool
    duration_seconds: Optional[float] = None


class TranscriptionRequest(BaseModel):
    """Request to an AudioTranscriptionProvider."""

    file_path: str          # absolute path to audio file (WAV preferred)
    filename: str
    media_id: str
    language_hint: Optional[str] = None  # ISO 639-1


class AudioUnderstandingRequest(BaseModel):
    """Request to an AudioUnderstandingProvider."""

    file_path: str
    filename: str
    media_id: str
