"""Gemini text-generation adapter for Phase 4 caption generation."""

from app.core.config import get_settings
from app.providers.base import ProviderConfigError, ProviderError, TextGenerationProvider


class GeminiTextGenerationProvider(TextGenerationProvider):
    provider_name = "gemini"

    def health_check(self) -> bool:
        return bool(get_settings().GEMINI_API_KEY)

    def generate(self, prompt: str, timeout_seconds: int = 120) -> str:
        key = get_settings().GEMINI_API_KEY
        if not key:
            raise ProviderConfigError(
                self.provider_name,
                "GEMINI_API_KEY is not configured.",
            )
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise ProviderConfigError(
                self.provider_name,
                "google-generativeai package is not installed.",
            ) from exc

        genai.configure(api_key=key)
        model_name = get_settings().GEMINI_TEXT_MODEL or "gemini-2.0-flash"
        model = genai.GenerativeModel(model_name)
        try:
            response = model.generate_content(
                prompt,
                generation_config={"temperature": 0.7},
                request_options={"timeout": timeout_seconds},
            )
        except Exception as exc:
            raise ProviderError(
                self.provider_name,
                f"Gemini text generation failed: {exc}",
                retryable=True,
            ) from exc
        return (getattr(response, "text", "") or "").strip()
