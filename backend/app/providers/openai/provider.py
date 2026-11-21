"""OpenAI Whisper API transcription provider.

Uses the openai SDK (openai package).
Model: whisper-1 (Whisper large-v2 hosted by OpenAI).

Configuration (via .env):
  OPENAI_API_KEY          — required
  OPENAI_WHISPER_MODEL    — default: whisper-1

If OPENAI_API_KEY is missing the provider raises ProviderConfigError on
first use.  The application starts normally; only transcription calls fail.

Limitations:
  - 25 MB file size limit per request
  - Timestamps are segment-level (not word-level) via the verbose_json format
  - Code-mixed speech accuracy is not guaranteed
"""

import time
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.base import (
    AudioTranscriptionProvider,
    ProviderConfigError,
    ProviderError,
)
from app.schemas.evidence import ConfidenceLevel, TranscriptionResult, TranscriptionSegment
from app.schemas.provider_requests import TranscriptionRequest

logger = get_logger(__name__)

_PROVIDER_NAME = "openai-whisper"
_MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB Whisper API limit


def _get_api_key() -> str:
    key = get_settings().OPENAI_API_KEY
    if not key:
        raise ProviderConfigError(
            _PROVIDER_NAME,
            "OPENAI_API_KEY is not configured. "
            "Set it in .env to enable OpenAI Whisper transcription.",
        )
    return key


def _get_client():
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        raise ProviderConfigError(
            _PROVIDER_NAME,
            "openai package is not installed. Run: pip install openai",
        )
    return OpenAI(api_key=_get_api_key())


def _whisper_model() -> str:
    return get_settings().OPENAI_WHISPER_MODEL or "whisper-1"


class OpenAIWhisperProvider(AudioTranscriptionProvider):
    """OpenAI Whisper API transcription provider."""

    def health_check(self) -> bool:
        try:
            _get_api_key()
            return True
        except ProviderConfigError:
            return False

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        file_path = Path(request.file_path)
        if not file_path.exists():
            raise ProviderError(_PROVIDER_NAME, f"Audio file not found: {request.file_path}")

        file_size = file_path.stat().st_size
        if file_size > _MAX_FILE_SIZE_BYTES:
            raise ProviderError(
                _PROVIDER_NAME,
                f"Audio file ({file_size / 1024 / 1024:.1f} MB) exceeds the 25 MB Whisper API limit. "
                "Consider chunking the audio before transcription.",
            )

        client = _get_client()
        model_name = _whisper_model()
        start = time.monotonic()

        try:
            with open(file_path, "rb") as f:
                response = client.audio.transcriptions.create(
                    model=model_name,
                    file=f,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                    language=request.language_hint,
                    timeout=120,
                )
        except Exception as exc:
            # Distinguish rate limit (retryable) from other errors
            err_str = str(exc).lower()
            retryable = "rate" in err_str or "429" in err_str or "timeout" in err_str
            raise ProviderError(_PROVIDER_NAME, f"Whisper API call failed: {exc}", retryable=retryable)

        elapsed_ms = int((time.monotonic() - start) * 1000)

        # Parse segments
        segments = []
        raw_segments = getattr(response, "segments", None) or []
        for seg in raw_segments:
            text = getattr(seg, "text", "") or ""
            start_s = float(getattr(seg, "start", 0))
            end_s = float(getattr(seg, "end", 0))
            if text.strip():
                segments.append(
                    TranscriptionSegment(
                        text=text.strip(),
                        start_seconds=start_s,
                        end_seconds=end_s,
                        confidence=ConfidenceLevel.MEDIUM,  # Whisper API does not return per-segment confidence
                        language=getattr(seg, "language", None),
                    )
                )

        detected_language = getattr(response, "language", None)
        full_text = getattr(response, "text", "") or ""

        return TranscriptionResult(
            media_id=request.media_id,
            full_text=full_text.strip(),
            segments=segments,
            detected_language=detected_language,
            detected_languages=[detected_language] if detected_language else [],
            is_code_mixed=False,  # Whisper API does not detect code-mixing
            provider=_PROVIDER_NAME,
            model_version=model_name,
            processing_time_ms=elapsed_ms,
            warnings=[
                "Whisper API does not provide per-segment confidence scores.",
                "Code-mixed speech detection is not supported by this provider.",
            ],
        )
