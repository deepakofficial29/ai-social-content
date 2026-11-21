# Multimodal Architecture — Provider Interfaces and Evidence Structure

**Phase:** 2.1 — Research and Architecture Planning  
**Status:** Design only. No code implemented.

---

## 1. Design Principles

1. **Provider independence** — the application never calls a specific AI SDK directly from business logic. All AI calls go through a provider interface. Swapping providers requires only a new implementation class, not changes to the pipeline.

2. **Evidence before generation** — the system collects structured observations from media before any caption is generated. The caption generator receives evidence, not raw media.

3. **Observed facts vs. inferences** — the evidence structure distinguishes between directly observed facts (pixel content, waveform data) and model interpretations (scene description, mood). This separation helps the caption validator detect hallucinations.

4. **Null safety** — all AI-populated fields are optional. The system must function correctly when a provider is unavailable or returns partial results.

5. **Temporal integrity** — video evidence preserves the order of events. Frame observations are always associated with their source timestamp.

---

## 2. Provider Interfaces

These are proposed Python abstract base classes. They are not yet implemented.

### 2.1 VisionProvider

Responsible for understanding still images.

```python
from abc import ABC, abstractmethod
from typing import List
from app.schemas.ai_providers import ImageObservation, VisionRequest

class VisionProvider(ABC):
    """Analyse one or more images and return structured observations."""

    @abstractmethod
    def analyse(self, request: VisionRequest) -> List[ImageObservation]:
        """
        Accept one or more images (as bytes or file paths) and a prompt context.
        Return one ImageObservation per image.
        Raise ProviderError on failure.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the provider is reachable and configured."""
        ...
```

### 2.2 VideoUnderstandingProvider

Responsible for understanding video content, either natively or via frame extraction.

```python
from abc import ABC, abstractmethod
from app.schemas.ai_providers import VideoObservation, VideoRequest

class VideoUnderstandingProvider(ABC):
    """Analyse a video and return structured temporal observations."""

    @abstractmethod
    def analyse(self, request: VideoRequest) -> VideoObservation:
        """
        Accept a video (as bytes or file path) and return a VideoObservation
        containing frame-level and overall observations with timestamps.
        Raise ProviderError on failure.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...
```

### 2.3 AudioTranscriptionProvider

Responsible for converting speech to text.

```python
from abc import ABC, abstractmethod
from app.schemas.ai_providers import TranscriptionResult, TranscriptionRequest

class AudioTranscriptionProvider(ABC):
    """Transcribe speech from an audio stream."""

    @abstractmethod
    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        """
        Accept audio bytes and return a structured transcription with
        language detection and optional word-level timestamps.
        Raise ProviderError on failure.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...
```

### 2.4 AudioUnderstandingProvider

Responsible for understanding non-speech audio content.

```python
from abc import ABC, abstractmethod
from app.schemas.ai_providers import AudioObservation, AudioUnderstandingRequest

class AudioUnderstandingProvider(ABC):
    """Describe non-speech audio content: music, ambient sounds, tone."""

    @abstractmethod
    def analyse(self, request: AudioUnderstandingRequest) -> AudioObservation:
        """
        Accept audio bytes and return observations about non-speech content.
        Raise ProviderError on failure.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...
```

---

## 3. Proposed Pydantic Schemas

These schemas are designed for Phase 2 implementation. They extend the existing `MediaContext` schema in `app/schemas/media.py`.

### 3.1 Provider Request Schemas

```python
from pydantic import BaseModel
from typing import List, Optional

class ImageInput(BaseModel):
    """A single image for analysis."""
    data: bytes                          # raw image bytes
    filename: str                        # original filename (for logging)
    media_id: str                        # links back to MediaAsset.id
    sequence_index: int = 0             # position in carousel (0-based)
    mime_type: str = "image/jpeg"

class VisionRequest(BaseModel):
    images: List[ImageInput]             # 1 for single image, N for carousel
    collection_id: Optional[str] = None  # set for carousel uploads
    prompt_context: Optional[str] = None # optional user-provided context

class VideoRequest(BaseModel):
    data: bytes                          # raw video bytes
    filename: str
    media_id: str
    extension: str                       # mp4, mov, etc.
    has_audio: bool                      # from FFprobe metadata
    duration_seconds: Optional[float] = None

class TranscriptionRequest(BaseModel):
    data: bytes                          # raw audio bytes (WAV preferred)
    filename: str
    media_id: str
    language_hint: Optional[str] = None  # ISO 639-1 code, e.g. "hi", "en"

class AudioUnderstandingRequest(BaseModel):
    data: bytes
    filename: str
    media_id: str
```

### 3.2 Provider Response Schemas

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class ConfidenceLevel(str, Enum):
    HIGH = "high"       # model is confident
    MEDIUM = "medium"   # model has some uncertainty
    LOW = "low"         # model is guessing; treat with caution

class BoundingBox(BaseModel):
    """Normalised coordinates (0.0–1.0) relative to image dimensions."""
    x: float
    y: float
    width: float
    height: float

class DetectedObject(BaseModel):
    label: str
    confidence: ConfidenceLevel
    bounding_box: Optional[BoundingBox] = None

class ExtractedText(BaseModel):
    text: str
    confidence: ConfidenceLevel
    bounding_box: Optional[BoundingBox] = None
    language: Optional[str] = None      # ISO 639-1

class ImageObservation(BaseModel):
    """Structured observations from a single image."""
    media_id: str
    sequence_index: int = 0

    # Directly observed
    detected_objects: List[DetectedObject] = []
    extracted_text: List[ExtractedText] = []
    dominant_colours: List[str] = []    # hex codes or colour names
    estimated_setting: Optional[str] = None  # indoor/outdoor/studio

    # Model interpretation (clearly labelled as such)
    scene_description: Optional[str] = None
    mood_or_tone: Optional[str] = None
    notable_details: List[str] = []

    # Metadata
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    provider: str                        # e.g. "gemini-1.5-flash"
    model_version: str
    processing_time_ms: Optional[int] = None

class FrameObservation(BaseModel):
    """Observation for a single video frame."""
    timestamp_seconds: float
    frame_index: int
    observation: ImageObservation

class VideoObservation(BaseModel):
    """Structured observations from a video."""
    media_id: str

    # Frame-level evidence
    frame_observations: List[FrameObservation] = []

    # Overall video understanding
    overall_description: Optional[str] = None
    key_events: List[str] = []          # ordered list of notable events
    has_audio: bool = False
    audio_description: Optional[str] = None  # non-speech audio description

    # Metadata
    frames_analysed: int = 0
    total_duration_seconds: Optional[float] = None
    provider: str
    model_version: str
    processing_time_ms: Optional[int] = None

class TranscriptionSegment(BaseModel):
    """A single segment of transcribed speech."""
    text: str
    start_seconds: float
    end_seconds: float
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    language: Optional[str] = None      # ISO 639-1; useful for code-mixed speech

class TranscriptionResult(BaseModel):
    """Full transcription of an audio stream."""
    media_id: str
    full_text: str
    segments: List[TranscriptionSegment] = []
    detected_language: Optional[str] = None   # primary language
    detected_languages: List[str] = []         # all detected languages (code-mixing)
    is_code_mixed: bool = False
    provider: str
    model_version: str
    processing_time_ms: Optional[int] = None

class AudioObservation(BaseModel):
    """Non-speech audio understanding."""
    media_id: str
    has_music: Optional[bool] = None
    music_genre: Optional[str] = None
    ambient_sounds: List[str] = []
    emotional_tone: Optional[str] = None
    background_noise_level: Optional[str] = None  # low/medium/high
    provider: str
    model_version: str
    processing_time_ms: Optional[int] = None
```

---

## 4. Multimodal Evidence Structure

The `MediaEvidence` structure is the central data object that flows from the understanding pipeline to the caption generator. It combines all observations from all media in a single upload.

```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MediaEvidence(BaseModel):
    """
    Complete evidence collected from one upload (single image, carousel,
    video, or audio file).

    This structure is passed to the caption generator.
    The generator must only use information present in this structure.
    It must not invent details not supported by the evidence.
    """

    # Identity
    collection_id: str
    collection_type: str                 # single|carousel|video|audio

    # Image evidence (one entry per image in a carousel, ordered by sequence_index)
    image_observations: List[ImageObservation] = []

    # Video evidence
    video_observation: Optional[VideoObservation] = None

    # Audio evidence
    transcription: Optional[TranscriptionResult] = None
    audio_observation: Optional[AudioObservation] = None

    # Aggregated OCR across all images/frames
    all_extracted_text: List[ExtractedText] = []

    # Processing metadata
    processing_status: str               # pending|partial|complete|failed
    processed_at: Optional[datetime] = None
    processing_errors: List[str] = []   # non-fatal errors during processing

    # Evidence quality indicators
    has_visual_evidence: bool = False
    has_audio_evidence: bool = False
    has_transcription: bool = False
    overall_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
```

### 4.1 Evidence Integrity Rules

These rules must be enforced by the caption generator (Phase 3):

1. A caption claim about a visible object must have a corresponding `DetectedObject` or `scene_description` in `image_observations` or `frame_observations`.
2. A caption claim about spoken content must have a corresponding `TranscriptionSegment`.
3. A caption claim about audio mood must have a corresponding `AudioObservation.emotional_tone`.
4. If `processing_errors` is non-empty, the caption generator must acknowledge uncertainty.
5. `LOW` confidence observations must not be stated as facts in captions.

---

## 5. Pipeline Architecture

```
Upload API
    │
    ▼
Media Intake Pipeline (existing — Phase 1)
    │  validates, stores, extracts technical metadata
    ▼
Media Understanding Pipeline (Phase 2 — not yet implemented)
    │
    ├── VisionProvider.analyse()        ← images / video frames
    ├── VideoUnderstandingProvider.analyse()  ← video files
    ├── AudioTranscriptionProvider.transcribe()  ← audio track
    └── AudioUnderstandingProvider.analyse()  ← non-speech audio
    │
    ▼
MediaEvidence (assembled from all provider outputs)
    │
    ▼
Caption Generation Pipeline (Phase 3 — not yet implemented)
    │  receives MediaEvidence + user intent
    ▼
Caption Validation Pipeline (Phase 3)
    │  checks claims against MediaEvidence
    ▼
Caption Response
```

---

## 6. Provider Registry Pattern

To avoid hardcoding provider selection, a registry pattern is proposed:

```python
from typing import Dict, Type
from app.providers.base import VisionProvider

_vision_registry: Dict[str, Type[VisionProvider]] = {}

def register_vision_provider(name: str, cls: Type[VisionProvider]) -> None:
    _vision_registry[name] = cls

def get_vision_provider(name: str) -> VisionProvider:
    if name not in _vision_registry:
        raise ValueError(f"Unknown vision provider: {name}. Available: {list(_vision_registry)}")
    return _vision_registry[name]()
```

Provider selection is controlled by a new configuration variable:

```
VISION_PROVIDER=gemini-flash
TRANSCRIPTION_PROVIDER=openai-whisper
VIDEO_PROVIDER=gemini-flash
```

This allows switching providers via `.env` without code changes.

---

## 7. Error Handling Strategy

Provider errors must not crash the pipeline. The system should:

1. Catch all provider exceptions and convert them to `ProviderError`
2. Record the error in `MediaEvidence.processing_errors`
3. Set `processing_status = "partial"` if some providers succeeded
4. Set `processing_status = "failed"` only if all providers failed
5. Allow caption generation to proceed with partial evidence, with appropriate uncertainty markers

```python
class ProviderError(Exception):
    """Raised when an AI provider call fails."""
    def __init__(self, provider: str, message: str, retryable: bool = False):
        self.provider = provider
        self.message = message
        self.retryable = retryable
        super().__init__(f"[{provider}] {message}")
```
