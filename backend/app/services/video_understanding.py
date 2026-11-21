"""Video understanding service — Phase 2.4.

Orchestrates:
  1. Video metadata inspection (existing FFprobe)
  2. Frame extraction (video_processor)
  3. Audio extraction (video_processor)
  4. Video understanding provider call
  5. Audio transcription (if audio present)
  6. Audio understanding (if audio present)
  7. Cleanup of all temporary files

Partial failures are recorded in MediaEvidence.processing_errors.
Successful results are never discarded.
"""

import json
from pathlib import Path
from typing import List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.base import ProviderConfigError, ProviderError
from app.providers.registry import (
    get_audio_understanding_provider,
    get_transcription_provider,
    get_video_provider,
)
from app.schemas.evidence import (
    AudioObservation,
    ConfidenceLevel,
    MediaEvidence,
    TranscriptionResult,
    VideoObservation,
)
from app.schemas.provider_requests import (
    AudioUnderstandingRequest,
    TranscriptionRequest,
    VideoRequest,
)
from app.services.video_processor import (
    FrameExtractionError,
    cleanup_audio,
    cleanup_frames,
    extract_frames,
)
from app.storage.local_storage import LocalStorage

logger = get_logger(__name__)


def _get_storage() -> LocalStorage:
    return LocalStorage()


def analyse_video(asset: dict, collection_id: str) -> MediaEvidence:
    """Analyse a video asset and return a MediaEvidence.

    Args:
        asset: dict with keys: media_id, storage_key, original_filename,
               metadata_json (JSON string from FFprobe)
        collection_id: the collection this asset belongs to

    Returns:
        MediaEvidence with video_observation, transcription, and
        audio_observation populated where possible.
    """
    settings = get_settings()
    storage = _get_storage()
    errors: List[str] = []

    media_id = asset["media_id"]
    storage_key = asset["storage_key"]

    # Resolve the absolute path to the stored file
    storage_path = Path(settings.STORAGE_DIR).resolve() / storage_key
    if not storage_path.exists():
        return MediaEvidence(
            collection_id=collection_id,
            collection_type="video",
            processing_status="failed",
            processing_errors=[f"Video file not found in storage: {storage_key}"],
        )

    # Parse existing metadata from FFprobe
    metadata = {}
    if asset.get("metadata_json"):
        try:
            metadata = json.loads(asset["metadata_json"])
        except Exception:
            pass

    has_audio = metadata.get("has_audio", False)
    duration = metadata.get("duration_seconds")
    ext = Path(asset["original_filename"]).suffix.lstrip(".").lower() or "mp4"

    video_observation: Optional[VideoObservation] = None
    transcription: Optional[TranscriptionResult] = None
    audio_observation: Optional[AudioObservation] = None

    frames = []
    audio_path: Optional[str] = None

    try:
        # --- Video understanding ---
        video_provider_name = settings.VIDEO_PROVIDER
        try:
            video_provider = get_video_provider(video_provider_name)
            video_request = VideoRequest(
                file_path=str(storage_path),
                filename=asset["original_filename"],
                media_id=media_id,
                extension=ext,
                has_audio=has_audio,
                duration_seconds=duration,
            )
            video_observation = video_provider.analyse(video_request)
            logger.info("Video understanding complete for %s", media_id)
        except ProviderConfigError as exc:
            logger.warning("Video provider not configured: %s", exc)
            errors.append(f"Video understanding skipped: {exc}")
        except ProviderError as exc:
            logger.error("Video provider error for %s: %s", media_id, exc)
            errors.append(f"Video understanding failed: {exc}")

        # --- Audio processing (only if video has audio) ---
        if has_audio:
            try:
                frames, audio_path = extract_frames(str(storage_path))
            except FrameExtractionError as exc:
                logger.warning("Frame/audio extraction failed for %s: %s", media_id, exc)
                errors.append(f"Audio extraction failed: {exc}")
                audio_path = None

            if audio_path:
                # Transcription
                transcription_provider_name = settings.AUDIO_TRANSCRIPTION_PROVIDER
                try:
                    transcription_provider = get_transcription_provider(transcription_provider_name)
                    transcription_request = TranscriptionRequest(
                        file_path=audio_path,
                        filename=f"{media_id}_audio.wav",
                        media_id=media_id,
                    )
                    transcription = transcription_provider.transcribe(transcription_request)
                    logger.info("Transcription complete for %s", media_id)
                except ProviderConfigError as exc:
                    logger.warning("Transcription provider not configured: %s", exc)
                    errors.append(f"Transcription skipped: {exc}")
                except ProviderError as exc:
                    logger.error("Transcription error for %s: %s", media_id, exc)
                    errors.append(f"Transcription failed: {exc}")

                # Audio understanding
                audio_understanding_provider_name = settings.AUDIO_UNDERSTANDING_PROVIDER
                try:
                    audio_provider = get_audio_understanding_provider(audio_understanding_provider_name)
                    audio_request = AudioUnderstandingRequest(
                        file_path=audio_path,
                        filename=f"{media_id}_audio.wav",
                        media_id=media_id,
                    )
                    audio_observation = audio_provider.analyse(audio_request)
                    logger.info("Audio understanding complete for %s", media_id)
                except ProviderConfigError as exc:
                    logger.warning("Audio understanding provider not configured: %s", exc)
                    errors.append(f"Audio understanding skipped: {exc}")
                except ProviderError as exc:
                    logger.error("Audio understanding error for %s: %s", media_id, exc)
                    errors.append(f"Audio understanding failed: {exc}")
        else:
            logger.info("Video %s has no audio track — skipping audio processing", media_id)

    finally:
        cleanup_frames(frames)
        cleanup_audio(audio_path)

    # Determine processing status
    has_any_result = any([video_observation, transcription, audio_observation])
    if not has_any_result:
        status = "failed"
    elif errors:
        status = "partial"
    else:
        status = "complete"

    providers_used = []
    if video_observation and video_observation.provider:
        providers_used.append(video_observation.provider)
    if transcription and transcription.provider:
        providers_used.append(transcription.provider)
    if audio_observation and audio_observation.provider:
        providers_used.append(audio_observation.provider)

    return MediaEvidence(
        collection_id=collection_id,
        collection_type="video",
        video_observation=video_observation,
        transcription=transcription,
        audio_observation=audio_observation,
        processing_status=status,
        processing_errors=errors,
        has_visual_evidence=video_observation is not None,
        has_audio_evidence=audio_observation is not None,
        has_transcription=transcription is not None and bool(transcription.full_text),
        providers_used=list(set(providers_used)),
    )
