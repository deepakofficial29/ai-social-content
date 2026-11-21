"""Provider registry — select providers via configuration.

Provider selection is controlled by environment variables:
  VISION_PROVIDER, VIDEO_PROVIDER,
  AUDIO_TRANSCRIPTION_PROVIDER, AUDIO_UNDERSTANDING_PROVIDER

Switching providers requires only a .env change, not code changes.
"""

from typing import Dict, Optional, Type

from app.core.logging import get_logger
from app.providers.base import (
    AudioTranscriptionProvider,
    AudioUnderstandingProvider,
    ProviderConfigError,
    TextGenerationProvider,
    VideoUnderstandingProvider,
    VisionProvider,
)

logger = get_logger(__name__)

_vision_registry: Dict[str, Type[VisionProvider]] = {}
_video_registry: Dict[str, Type[VideoUnderstandingProvider]] = {}
_transcription_registry: Dict[str, Type[AudioTranscriptionProvider]] = {}
_audio_understanding_registry: Dict[str, Type[AudioUnderstandingProvider]] = {}
_text_generation_registry: Dict[str, Type[TextGenerationProvider]] = {}


def register_vision_provider(name: str, cls: Type[VisionProvider]) -> None:
    _vision_registry[name] = cls


def register_video_provider(name: str, cls: Type[VideoUnderstandingProvider]) -> None:
    _video_registry[name] = cls


def register_transcription_provider(name: str, cls: Type[AudioTranscriptionProvider]) -> None:
    _transcription_registry[name] = cls


def register_audio_understanding_provider(
    name: str, cls: Type[AudioUnderstandingProvider]
) -> None:
    _audio_understanding_registry[name] = cls


def register_text_generation_provider(name: str, cls: Type[TextGenerationProvider]) -> None:
    _text_generation_registry[name] = cls


def get_vision_provider(name: str) -> VisionProvider:
    if name not in _vision_registry:
        raise ProviderConfigError(
            name,
            f"Unknown vision provider '{name}'. Available: {list(_vision_registry)}",
        )
    return _vision_registry[name]()


def get_video_provider(name: str) -> VideoUnderstandingProvider:
    if name not in _video_registry:
        raise ProviderConfigError(
            name,
            f"Unknown video provider '{name}'. Available: {list(_video_registry)}",
        )
    return _video_registry[name]()


def get_transcription_provider(name: str) -> AudioTranscriptionProvider:
    if name not in _transcription_registry:
        raise ProviderConfigError(
            name,
            f"Unknown transcription provider '{name}'. Available: {list(_transcription_registry)}",
        )
    return _transcription_registry[name]()


def get_audio_understanding_provider(name: str) -> AudioUnderstandingProvider:
    if name not in _audio_understanding_registry:
        raise ProviderConfigError(
            name,
            f"Unknown audio understanding provider '{name}'. "
            f"Available: {list(_audio_understanding_registry)}",
        )
    return _audio_understanding_registry[name]()


def get_text_generation_provider(name: str) -> TextGenerationProvider:
    if name not in _text_generation_registry:
        raise ProviderConfigError(
            name,
            f"Unknown text generation provider '{name}'. "
            f"Available: {list(_text_generation_registry)}",
        )
    return _text_generation_registry[name]()


def list_registered_providers() -> Dict[str, list]:
    return {
        "vision": list(_vision_registry),
        "video": list(_video_registry),
        "transcription": list(_transcription_registry),
        "audio_understanding": list(_audio_understanding_registry),
        "text_generation": list(_text_generation_registry),
    }
