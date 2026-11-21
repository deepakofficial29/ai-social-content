"""Provider package — registers all available providers on import."""

from app.providers.registry import (
    register_audio_understanding_provider,
    register_transcription_provider,
    register_text_generation_provider,
    register_video_provider,
    register_vision_provider,
)


def _register_all() -> None:
    """Register all built-in providers.  Called once at application startup."""
    from app.core.config import get_settings
    if get_settings().MOCK_AI_PROVIDERS:
        from app.providers.mock.provider import (
            MockAudioUnderstandingProvider,
            MockTextGenerationProvider,
            MockTranscriptionProvider,
            MockVideoProvider,
            MockVisionProvider,
        )
        register_vision_provider("gemini", MockVisionProvider)
        register_vision_provider("gemini-flash", MockVisionProvider)
        register_video_provider("gemini", MockVideoProvider)
        register_video_provider("gemini-flash", MockVideoProvider)
        register_transcription_provider("gemini", MockTranscriptionProvider)
        register_transcription_provider("openai-whisper", MockTranscriptionProvider)
        register_audio_understanding_provider("gemini", MockAudioUnderstandingProvider)
        register_audio_understanding_provider("gemini-flash", MockAudioUnderstandingProvider)
        register_text_generation_provider("gemini", MockTextGenerationProvider)
        register_text_generation_provider("gemini-flash", MockTextGenerationProvider)
        return
    from app.providers.gemini.provider import (
        GeminiAudioUnderstandingProvider,
        GeminiTranscriptionProvider,
        GeminiVideoProvider,
        GeminiVisionProvider,
    )
    from app.providers.openai.provider import OpenAIWhisperProvider
    from app.providers.gemini.text_provider import GeminiTextGenerationProvider

    register_vision_provider("gemini", GeminiVisionProvider)
    register_vision_provider("gemini-flash", GeminiVisionProvider)

    register_video_provider("gemini", GeminiVideoProvider)
    register_video_provider("gemini-flash", GeminiVideoProvider)

    register_transcription_provider("gemini", GeminiTranscriptionProvider)
    register_transcription_provider("openai-whisper", OpenAIWhisperProvider)

    register_audio_understanding_provider("gemini", GeminiAudioUnderstandingProvider)
    register_audio_understanding_provider("gemini-flash", GeminiAudioUnderstandingProvider)
    register_text_generation_provider("gemini", GeminiTextGenerationProvider)
    register_text_generation_provider("gemini-flash", GeminiTextGenerationProvider)


_register_all()
