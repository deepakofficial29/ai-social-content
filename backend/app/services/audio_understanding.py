"""Audio understanding service — Phase 2.5.

Orchestrates:
  1. Audio transcription (speech-to-text)
  2. General audio understanding (music, sounds, noise)

Both are independent capabilities.  The absence of speech does not mean
the absence of meaningful audio content.

Partial failures are recorded in MediaEvidence.processing_errors.
"""

from pathlib import Path
from typing import List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.base import ProviderConfigError, ProviderError
from app.providers.registry import (
    get_audio_understanding_provider,
    get_transcription_provider,
)
from app.schemas.evidence import (
    AudioObservation,
    MediaEvidence,
    TranscriptionResult,
)
from app.schemas.provider_requests import AudioUnderstandingRequest, TranscriptionRequest
from app.storage.local_storage import LocalStorage

logger = get_logger(__name__)


def _get_storage() -> LocalStorage:
    return LocalStorage()


def analyse_audio(asset: dict, collection_id: str) -> MediaEvidence:
    """Analyse a standalone audio asset and return a MediaEvidence.

    Args:
        asset: dict with keys: media_id, storage_key, original_filename
        collection_id: the collection this asset belongs to

    Returns:
        MediaEvidence with transcription and audio_observation populated
        where possible.
    """
    settings = get_settings()
    errors: List[str] = []

    media_id = asset["media_id"]
    storage_key = asset["storage_key"]

    storage_path = Path(settings.STORAGE_DIR).resolve() / storage_key
    if not storage_path.exists():
        return MediaEvidence(
            collection_id=collection_id,
            collection_type="audio",
            processing_status="failed",
            processing_errors=[f"Audio file not found in storage: {storage_key}"],
        )

    transcription: Optional[TranscriptionResult] = None
    audio_observation: Optional[AudioObservation] = None

    # --- Transcription ---
    transcription_provider_name = settings.AUDIO_TRANSCRIPTION_PROVIDER
    try:
        transcription_provider = get_transcription_provider(transcription_provider_name)
        transcription_request = TranscriptionRequest(
            file_path=str(storage_path),
            filename=asset["original_filename"],
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

    # --- General audio understanding ---
    audio_understanding_provider_name = settings.AUDIO_UNDERSTANDING_PROVIDER
    try:
        audio_provider = get_audio_understanding_provider(audio_understanding_provider_name)
        audio_request = AudioUnderstandingRequest(
            file_path=str(storage_path),
            filename=asset["original_filename"],
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

    # Determine status
    has_any = any([transcription, audio_observation])
    if not has_any:
        status = "failed"
    elif errors:
        status = "partial"
    else:
        status = "complete"

    providers_used = []
    if transcription and transcription.provider:
        providers_used.append(transcription.provider)
    if audio_observation and audio_observation.provider:
        providers_used.append(audio_observation.provider)

    return MediaEvidence(
        collection_id=collection_id,
        collection_type="audio",
        transcription=transcription,
        audio_observation=audio_observation,
        processing_status=status,
        processing_errors=errors,
        has_audio_evidence=audio_observation is not None,
        has_transcription=transcription is not None and bool(transcription.full_text),
        providers_used=list(set(providers_used)),
    )
