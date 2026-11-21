"""Multimodal evidence schemas — Phase 2.

All AI-populated fields are Optional so the system functions correctly
when a provider is unavailable or returns partial results.

Observed facts (detected objects, extracted text, timestamps) are kept
separate from model interpretations (scene descriptions, mood, inferences).
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BoundingBox(BaseModel):
    """Normalised coordinates (0.0–1.0) relative to image dimensions."""

    x: float
    y: float
    width: float
    height: float


class DetectedObject(BaseModel):
    label: str
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    bounding_box: Optional[BoundingBox] = None


class ExtractedText(BaseModel):
    """A piece of text observed in an image or video frame (OCR)."""

    text: str
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    bounding_box: Optional[BoundingBox] = None
    language: Optional[str] = None  # ISO 639-1


# ---------------------------------------------------------------------------
# Image observation
# ---------------------------------------------------------------------------


class ImageObservation(BaseModel):
    """Structured observations from a single image.

    Fields under 'Directly observed' come from model output that describes
    concrete visual content.  Fields under 'Model interpretation' are
    explicitly labelled as inferences.
    """

    media_id: str
    sequence_index: int = 0

    # Directly observed
    detected_objects: List[DetectedObject] = []
    extracted_text: List[ExtractedText] = []
    dominant_colours: List[str] = []
    estimated_setting: Optional[str] = None  # indoor / outdoor / studio

    # Model interpretation (clearly labelled)
    scene_description: Optional[str] = None
    activities: List[str] = []
    mood_or_tone: Optional[str] = None
    notable_details: List[str] = []
    spatial_relationships: List[str] = []

    # Provenance
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    provider: str = ""
    model_version: str = ""
    processing_time_ms: Optional[int] = None
    warnings: List[str] = []


# ---------------------------------------------------------------------------
# Video observation
# ---------------------------------------------------------------------------


class FrameObservation(BaseModel):
    """Observation for a single extracted video frame."""

    timestamp_seconds: float
    frame_index: int
    observation: ImageObservation


class VideoObservation(BaseModel):
    """Structured observations from a video."""

    media_id: str

    # Frame-level evidence (ordered by timestamp)
    frame_observations: List[FrameObservation] = []

    # Overall video understanding
    overall_description: Optional[str] = None
    key_events: List[str] = []
    detected_activities: List[str] = []
    scene_transitions: List[str] = []

    # Audio references (what was heard, not transcribed)
    has_audio: bool = False
    audio_description: Optional[str] = None

    # Provenance
    frames_analysed: int = 0
    total_duration_seconds: Optional[float] = None
    provider: str = ""
    model_version: str = ""
    processing_time_ms: Optional[int] = None
    warnings: List[str] = []


# ---------------------------------------------------------------------------
# Audio / transcription
# ---------------------------------------------------------------------------


class TranscriptionSegment(BaseModel):
    """A single segment of transcribed speech with timestamps."""

    text: str
    start_seconds: float
    end_seconds: float
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    language: Optional[str] = None  # ISO 639-1; useful for code-mixed speech
    speaker_label: Optional[str] = None


class TranscriptionResult(BaseModel):
    """Full transcription of an audio stream."""

    media_id: str
    full_text: str
    segments: List[TranscriptionSegment] = []
    detected_language: Optional[str] = None
    detected_languages: List[str] = []
    is_code_mixed: bool = False
    provider: str = ""
    model_version: str = ""
    processing_time_ms: Optional[int] = None
    warnings: List[str] = []


class AudioObservation(BaseModel):
    """Non-speech audio understanding.

    The absence of a transcript does not mean the absence of meaningful audio.
    Music, environmental sounds, and noise are captured here.
    """

    media_id: str
    has_speech: Optional[bool] = None
    has_music: Optional[bool] = None
    music_genre: Optional[str] = None
    ambient_sounds: List[str] = []
    sound_events: List[str] = []
    emotional_tone: Optional[str] = None
    background_noise_level: Optional[str] = None  # low / medium / high
    general_summary: Optional[str] = None
    provider: str = ""
    model_version: str = ""
    processing_time_ms: Optional[int] = None
    warnings: List[str] = []


# ---------------------------------------------------------------------------
# Unified evidence structure
# ---------------------------------------------------------------------------


class MediaEvidence(BaseModel):
    """Complete evidence collected from one upload.

    This is the output of the understanding pipeline and the input to the
    caption generator (Phase 3).  The generator must only use information
    present in this structure.

    processing_status values:
      pending   — understanding not yet started
      partial   — some providers succeeded, some failed
      complete  — all providers returned results
      failed    — all providers failed
    """

    # Identity
    collection_id: str
    collection_type: str  # single | carousel | video | audio

    # Image evidence (ordered by sequence_index for carousels)
    image_observations: List[ImageObservation] = []

    # Video evidence
    video_observation: Optional[VideoObservation] = None

    # Audio evidence
    transcription: Optional[TranscriptionResult] = None
    audio_observation: Optional[AudioObservation] = None

    # Aggregated OCR across all images / frames
    all_extracted_text: List[ExtractedText] = []

    # Processing metadata
    processing_status: str = "pending"
    processed_at: Optional[datetime] = None
    processing_errors: List[str] = []

    # Evidence quality indicators
    has_visual_evidence: bool = False
    has_audio_evidence: bool = False
    has_transcription: bool = False
    overall_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM

    # Provider / model info for audit trail
    providers_used: List[str] = []
