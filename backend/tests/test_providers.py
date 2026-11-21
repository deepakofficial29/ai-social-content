"""Tests for provider abstractions, registry, and error types — Phase 2.2."""

import pytest

from app.providers.base import (
    AudioTranscriptionProvider,
    AudioUnderstandingProvider,
    ProviderConfigError,
    ProviderError,
    VideoUnderstandingProvider,
    VisionProvider,
)
from app.providers.registry import (
    get_audio_understanding_provider,
    get_transcription_provider,
    get_video_provider,
    get_vision_provider,
    list_registered_providers,
    register_vision_provider,
)


# ---------------------------------------------------------------------------
# ProviderError
# ---------------------------------------------------------------------------

def test_provider_error_message():
    err = ProviderError("gemini", "something went wrong")
    assert "[gemini]" in str(err)
    assert "something went wrong" in str(err)
    assert err.retryable is False


def test_provider_error_retryable():
    err = ProviderError("gemini", "rate limit", retryable=True)
    assert err.retryable is True


def test_provider_config_error_not_retryable():
    err = ProviderConfigError("gemini", "missing API key")
    assert err.retryable is False
    assert isinstance(err, ProviderError)


# ---------------------------------------------------------------------------
# Abstract base classes cannot be instantiated
# ---------------------------------------------------------------------------

def test_vision_provider_is_abstract():
    with pytest.raises(TypeError):
        VisionProvider()


def test_video_provider_is_abstract():
    with pytest.raises(TypeError):
        VideoUnderstandingProvider()


def test_transcription_provider_is_abstract():
    with pytest.raises(TypeError):
        AudioTranscriptionProvider()


def test_audio_understanding_provider_is_abstract():
    with pytest.raises(TypeError):
        AudioUnderstandingProvider()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def test_registered_providers_include_gemini():
    providers = list_registered_providers()
    assert "gemini" in providers["vision"]
    assert "gemini" in providers["video"]
    assert "gemini" in providers["transcription"]
    assert "gemini" in providers["audio_understanding"]


def test_registered_providers_include_openai_whisper():
    providers = list_registered_providers()
    assert "openai-whisper" in providers["transcription"]


def test_get_unknown_vision_provider_raises():
    with pytest.raises(ProviderConfigError) as exc_info:
        get_vision_provider("nonexistent-provider")
    assert "nonexistent-provider" in str(exc_info.value)


def test_get_unknown_video_provider_raises():
    with pytest.raises(ProviderConfigError):
        get_video_provider("nonexistent-provider")


def test_get_unknown_transcription_provider_raises():
    with pytest.raises(ProviderConfigError):
        get_transcription_provider("nonexistent-provider")


def test_get_unknown_audio_understanding_provider_raises():
    with pytest.raises(ProviderConfigError):
        get_audio_understanding_provider("nonexistent-provider")


def test_register_custom_vision_provider():
    """Custom providers can be registered and retrieved."""

    class _MockVision(VisionProvider):
        def analyse(self, request):
            return []

        def health_check(self):
            return True

    register_vision_provider("mock-test-vision", _MockVision)
    provider = get_vision_provider("mock-test-vision")
    assert isinstance(provider, _MockVision)
    assert provider.health_check() is True


# ---------------------------------------------------------------------------
# Provider health_check with missing credentials
# ---------------------------------------------------------------------------

def test_gemini_vision_health_check_false_without_key(monkeypatch):
    """GeminiVisionProvider.health_check() returns False when key is missing."""
    from app.providers.gemini.provider import GeminiVisionProvider
    monkeypatch.setattr("app.providers.gemini.provider._get_api_key", lambda: (_ for _ in ()).throw(
        ProviderConfigError("gemini", "no key")
    ))
    provider = GeminiVisionProvider()
    assert provider.health_check() is False


def test_openai_whisper_health_check_false_without_key(monkeypatch):
    """OpenAIWhisperProvider.health_check() returns False when key is missing."""
    from app.providers.openai.provider import OpenAIWhisperProvider
    monkeypatch.setattr("app.providers.openai.provider._get_api_key", lambda: (_ for _ in ()).throw(
        ProviderConfigError("openai-whisper", "no key")
    ))
    provider = OpenAIWhisperProvider()
    assert provider.health_check() is False
