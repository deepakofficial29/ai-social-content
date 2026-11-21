"""Phase 3 — Evidence normalization layer.

Converts Phase 2 provider outputs (MediaEvidence) into normalized
EvidenceItems with full provenance.

Rules:
  - Preserve original provider text in raw_provider_value.
  - Never turn descriptive text into precise structured facts unless
    the underlying result supports that transformation.
  - Preserve uncertainty — do not discard low-confidence items.
  - Observations and interpretations are kept in separate EvidenceItems.
  - Timestamps are preserved exactly.
"""

from typing import List, Optional

from app.core.logging import get_logger
from app.schemas.evidence import (
    AudioObservation,
    ExtractedText,
    FrameObservation,
    ImageObservation,
    TranscriptionResult,
    VideoObservation,
)
from app.schemas.unified_evidence import (
    EvidenceCategory,
    EvidenceItem,
    EvidenceSource,
    ObservationType,
    SourceModality,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _source(
    media_id: str,
    collection_id: str,
    media_type: str,
    modality: SourceModality,
    provider: str = "",
    model_id: str = "",
    image_index: Optional[int] = None,
    video_start: Optional[float] = None,
    video_end: Optional[float] = None,
    frame_index: Optional[int] = None,
    audio_start: Optional[float] = None,
    audio_end: Optional[float] = None,
) -> EvidenceSource:
    return EvidenceSource(
        media_id=media_id,
        collection_id=collection_id,
        media_type=media_type,
        modality=modality,
        image_index=image_index,
        video_start_seconds=video_start,
        video_end_seconds=video_end,
        frame_index=frame_index,
        audio_start_seconds=audio_start,
        audio_end_seconds=audio_end,
        provider=provider,
        model_id=model_id,
    )


def _item(
    category: EvidenceCategory,
    obs_type: ObservationType,
    value: str,
    source: EvidenceSource,
    confidence: Optional[str] = None,
    uncertainty_note: Optional[str] = None,
    raw: Optional[str] = None,
) -> Optional[EvidenceItem]:
    """Return an EvidenceItem, or None if value is empty."""
    v = (value or "").strip()
    if not v:
        return None
    return EvidenceItem(
        category=category,
        observation_type=obs_type,
        value=v,
        source=source,
        confidence=confidence,
        uncertainty_note=uncertainty_note,
        raw_provider_value=raw or v,
    )


# ---------------------------------------------------------------------------
# Image normalizer
# ---------------------------------------------------------------------------


def normalize_image_evidence(
    obs: ImageObservation,
    collection_id: str,
    image_index: Optional[int] = None,
) -> List[EvidenceItem]:
    """Convert one ImageObservation into a list of EvidenceItems."""
    items: List[EvidenceItem] = []
    idx = image_index if image_index is not None else obs.sequence_index

    def src() -> EvidenceSource:
        return _source(
            media_id=obs.media_id,
            collection_id=collection_id,
            media_type="image",
            modality=SourceModality.IMAGE,
            provider=obs.provider,
            model_id=obs.model_version,
            image_index=idx,
        )

    # Detected objects — direct observations
    for obj in obs.detected_objects:
        it = _item(
            EvidenceCategory.OBJECT,
            ObservationType.DIRECT_OBSERVATION,
            obj.label,
            src(),
            confidence=obj.confidence.value if obj.confidence else None,
            raw=obj.label,
        )
        if it:
            items.append(it)

    # OCR text — direct observations
    for txt in obs.extracted_text:
        it = _item(
            EvidenceCategory.TEXT_OCR,
            ObservationType.DIRECT_OBSERVATION,
            txt.text,
            src(),
            confidence=txt.confidence.value if txt.confidence else None,
            raw=txt.text,
        )
        if it:
            items.append(it)

    # Estimated setting — direct observation
    if obs.estimated_setting:
        it = _item(
            EvidenceCategory.ENVIRONMENT,
            ObservationType.DIRECT_OBSERVATION,
            obs.estimated_setting,
            src(),
            confidence=obs.confidence.value if obs.confidence else None,
        )
        if it:
            items.append(it)

    # Scene description — interpretation
    if obs.scene_description:
        it = _item(
            EvidenceCategory.SCENE,
            ObservationType.INTERPRETATION,
            obs.scene_description,
            src(),
            confidence=obs.confidence.value if obs.confidence else None,
            raw=obs.scene_description,
        )
        if it:
            items.append(it)

    # Activities — interpretation
    for act in obs.activities:
        it = _item(
            EvidenceCategory.ACTIVITY,
            ObservationType.INTERPRETATION,
            act,
            src(),
            confidence=obs.confidence.value if obs.confidence else None,
        )
        if it:
            items.append(it)

    # Mood / tone — interpretation with explicit uncertainty
    if obs.mood_or_tone:
        it = _item(
            EvidenceCategory.CONTEXT,
            ObservationType.INTERPRETATION,
            obs.mood_or_tone,
            src(),
            confidence=obs.confidence.value if obs.confidence else None,
            uncertainty_note="Mood and tone are model interpretations, not verified facts.",
        )
        if it:
            items.append(it)

    # Notable details — interpretation
    for detail in obs.notable_details:
        it = _item(
            EvidenceCategory.VISUAL_ATTRIBUTE,
            ObservationType.INTERPRETATION,
            detail,
            src(),
            confidence=obs.confidence.value if obs.confidence else None,
        )
        if it:
            items.append(it)

    return items


# ---------------------------------------------------------------------------
# Carousel normalizer
# ---------------------------------------------------------------------------


def normalize_carousel_evidence(
    observations: List[ImageObservation],
    collection_id: str,
) -> List[EvidenceItem]:
    """Normalize all images in a carousel, preserving sequence order."""
    items: List[EvidenceItem] = []
    for obs in sorted(observations, key=lambda o: o.sequence_index):
        items.extend(
            normalize_image_evidence(obs, collection_id, image_index=obs.sequence_index)
        )
    return items


# ---------------------------------------------------------------------------
# Video normalizer
# ---------------------------------------------------------------------------


def normalize_video_evidence(
    obs: VideoObservation,
    collection_id: str,
) -> List[EvidenceItem]:
    """Convert a VideoObservation into EvidenceItems."""
    items: List[EvidenceItem] = []

    def overall_src() -> EvidenceSource:
        return _source(
            media_id=obs.media_id,
            collection_id=collection_id,
            media_type="video",
            modality=SourceModality.VIDEO_OVERALL,
            provider=obs.provider,
            model_id=obs.model_version,
        )

    # Overall description — interpretation
    if obs.overall_description:
        it = _item(
            EvidenceCategory.SCENE,
            ObservationType.INTERPRETATION,
            obs.overall_description,
            overall_src(),
            raw=obs.overall_description,
        )
        if it:
            items.append(it)

    # Key events — ordered, interpretation
    for event in obs.key_events:
        it = _item(
            EvidenceCategory.EVENT,
            ObservationType.INTERPRETATION,
            event,
            overall_src(),
        )
        if it:
            items.append(it)

    # Detected activities — interpretation
    for act in obs.detected_activities:
        it = _item(
            EvidenceCategory.ACTIVITY,
            ObservationType.INTERPRETATION,
            act,
            overall_src(),
        )
        if it:
            items.append(it)

    # Audio description from video provider — interpretation
    if obs.audio_description:
        audio_src = _source(
            media_id=obs.media_id,
            collection_id=collection_id,
            media_type="video",
            modality=SourceModality.AUDIO_UNDERSTANDING,
            provider=obs.provider,
            model_id=obs.model_version,
        )
        it = _item(
            EvidenceCategory.CONTEXT,
            ObservationType.INTERPRETATION,
            obs.audio_description,
            audio_src,
            uncertainty_note="Audio description from video provider — not a dedicated transcription.",
        )
        if it:
            items.append(it)

    # Frame-level observations
    for frame_obs in obs.frame_observations:
        items.extend(
            _normalize_frame(frame_obs, obs.media_id, collection_id, obs.provider, obs.model_version)
        )

    return items


def _normalize_frame(
    frame: FrameObservation,
    media_id: str,
    collection_id: str,
    provider: str,
    model_id: str,
) -> List[EvidenceItem]:
    """Normalize a single video frame observation."""
    items: List[EvidenceItem] = []
    obs = frame.observation

    def src() -> EvidenceSource:
        return _source(
            media_id=media_id,
            collection_id=collection_id,
            media_type="video",
            modality=SourceModality.VIDEO_FRAME,
            provider=provider,
            model_id=model_id,
            video_start=frame.timestamp_seconds,
            video_end=frame.timestamp_seconds,
            frame_index=frame.frame_index,
        )

    for obj in obs.detected_objects:
        it = _item(
            EvidenceCategory.OBJECT,
            ObservationType.DIRECT_OBSERVATION,
            obj.label,
            src(),
            confidence=obj.confidence.value if obj.confidence else None,
        )
        if it:
            items.append(it)

    for txt in obs.extracted_text:
        it = _item(
            EvidenceCategory.TEXT_OCR,
            ObservationType.DIRECT_OBSERVATION,
            txt.text,
            src(),
            confidence=txt.confidence.value if txt.confidence else None,
        )
        if it:
            items.append(it)

    if obs.scene_description:
        it = _item(
            EvidenceCategory.SCENE,
            ObservationType.INTERPRETATION,
            obs.scene_description,
            src(),
        )
        if it:
            items.append(it)

    return items


# ---------------------------------------------------------------------------
# Transcription normalizer
# ---------------------------------------------------------------------------


def normalize_transcription_evidence(
    result: TranscriptionResult,
    collection_id: str,
) -> List[EvidenceItem]:
    """Convert a TranscriptionResult into EvidenceItems."""
    items: List[EvidenceItem] = []

    if not result.full_text.strip():
        src = _source(
            media_id=result.media_id,
            collection_id=collection_id,
            media_type="audio",
            modality=SourceModality.AUDIO_TRANSCRIPTION,
            provider=result.provider,
            model_id=result.model_version,
        )
        it = _item(
            EvidenceCategory.SPEECH,
            ObservationType.DIRECT_OBSERVATION,
            "No speech detected",
            src,
            uncertainty_note=(
                "Absence of transcript does not confirm silence — "
                "audio may contain non-speech content."
            ),
        )
        if it:
            items.append(it)
        return items

    # Segment-level items (with timestamps)
    for seg in result.segments:
        src = _source(
            media_id=result.media_id,
            collection_id=collection_id,
            media_type="audio",
            modality=SourceModality.AUDIO_TRANSCRIPTION,
            provider=result.provider,
            model_id=result.model_version,
            audio_start=seg.start_seconds,
            audio_end=seg.end_seconds,
        )
        uncertainty = None
        if result.is_code_mixed:
            uncertainty = (
                "Code-mixed speech detected — transcription accuracy may be reduced."
            )
        it = _item(
            EvidenceCategory.SPEECH,
            ObservationType.DIRECT_OBSERVATION,
            seg.text,
            src,
            confidence=seg.confidence.value if seg.confidence else None,
            uncertainty_note=uncertainty,
            raw=seg.text,
        )
        if it:
            items.append(it)

    # If no segments but full_text exists, one item without timestamps
    if not result.segments and result.full_text.strip():
        src = _source(
            media_id=result.media_id,
            collection_id=collection_id,
            media_type="audio",
            modality=SourceModality.AUDIO_TRANSCRIPTION,
            provider=result.provider,
            model_id=result.model_version,
        )
        it = _item(
            EvidenceCategory.SPEECH,
            ObservationType.DIRECT_OBSERVATION,
            result.full_text,
            src,
            uncertainty_note="No segment timestamps available from this provider.",
            raw=result.full_text,
        )
        if it:
            items.append(it)

    return items


# ---------------------------------------------------------------------------
# Audio understanding normalizer
# ---------------------------------------------------------------------------


def normalize_audio_understanding_evidence(
    obs: AudioObservation,
    collection_id: str,
    media_type: str = "audio",
) -> List[EvidenceItem]:
    """Convert an AudioObservation into EvidenceItems."""
    items: List[EvidenceItem] = []

    def src() -> EvidenceSource:
        return _source(
            media_id=obs.media_id,
            collection_id=collection_id,
            media_type=media_type,
            modality=SourceModality.AUDIO_UNDERSTANDING,
            provider=obs.provider,
            model_id=obs.model_version,
        )

    if obs.has_music is True:
        genre_note = f" (genre: {obs.music_genre})" if obs.music_genre else ""
        it = _item(
            EvidenceCategory.MUSIC,
            ObservationType.DIRECT_OBSERVATION,
            f"Music present{genre_note}",
            src(),
        )
        if it:
            items.append(it)

    for sound in obs.ambient_sounds:
        it = _item(
            EvidenceCategory.ENVIRONMENTAL_SOUND,
            ObservationType.DIRECT_OBSERVATION,
            sound,
            src(),
        )
        if it:
            items.append(it)

    for event in obs.sound_events:
        it = _item(
            EvidenceCategory.EVENT,
            ObservationType.DIRECT_OBSERVATION,
            event,
            src(),
        )
        if it:
            items.append(it)

    if obs.emotional_tone:
        it = _item(
            EvidenceCategory.CONTEXT,
            ObservationType.INTERPRETATION,
            obs.emotional_tone,
            src(),
            uncertainty_note="Emotional tone is a model interpretation, not a verified fact.",
        )
        if it:
            items.append(it)

    if obs.general_summary:
        it = _item(
            EvidenceCategory.CONTEXT,
            ObservationType.INTERPRETATION,
            obs.general_summary,
            src(),
        )
        if it:
            items.append(it)

    return items


# ---------------------------------------------------------------------------
# OCR normalizer (aggregated)
# ---------------------------------------------------------------------------


def normalize_ocr_evidence(
    extracted_texts: List[ExtractedText],
    media_id: str,
    collection_id: str,
    provider: str = "",
    model_id: str = "",
    image_index: Optional[int] = None,
) -> List[EvidenceItem]:
    """Normalize aggregated OCR results into EvidenceItems."""
    items: List[EvidenceItem] = []
    for txt in extracted_texts:
        src = _source(
            media_id=media_id,
            collection_id=collection_id,
            media_type="image",
            modality=SourceModality.OCR,
            provider=provider,
            model_id=model_id,
            image_index=image_index,
        )
        it = _item(
            EvidenceCategory.TEXT_OCR,
            ObservationType.DIRECT_OBSERVATION,
            txt.text,
            src,
            confidence=txt.confidence.value if txt.confidence else None,
            raw=txt.text,
        )
        if it:
            items.append(it)
    return items
