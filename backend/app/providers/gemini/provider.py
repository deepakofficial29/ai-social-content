"""Google Gemini provider — vision, video, and audio understanding.

Uses the google-generativeai SDK (google-genai package).
Model: gemini-2.0-flash (current stable Flash model as of 2025).

Configuration (via .env):
  GEMINI_API_KEY      — required
  GEMINI_VISION_MODEL — default: gemini-2.0-flash
  GEMINI_VIDEO_MODEL  — default: gemini-2.0-flash
  GEMINI_AUDIO_MODEL  — default: gemini-2.0-flash

If GEMINI_API_KEY is missing the provider raises ProviderConfigError on
first use.  The application starts normally; only AI calls fail.
"""

import base64
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.base import (
    AudioTranscriptionProvider,
    AudioUnderstandingProvider,
    ProviderConfigError,
    ProviderError,
    VideoUnderstandingProvider,
    VisionProvider,
)
from app.schemas.evidence import (
    AudioObservation,
    ConfidenceLevel,
    DetectedObject,
    ExtractedText,
    FrameObservation,
    ImageObservation,
    TranscriptionResult,
    TranscriptionSegment,
    VideoObservation,
)
from app.schemas.provider_requests import (
    AudioUnderstandingRequest,
    TranscriptionRequest,
    VideoRequest,
    VisionRequest,
)

logger = get_logger(__name__)

_PROVIDER_NAME = "gemini"


def _get_api_key() -> str:
    key = get_settings().GEMINI_API_KEY
    if not key:
        raise ProviderConfigError(
            _PROVIDER_NAME,
            "GEMINI_API_KEY is not configured. "
            "Set it in .env to enable Gemini-based understanding.",
        )
    return key


def _get_client():
    """Return a configured google.generativeai GenerativeModel client."""
    try:
        import google.generativeai as genai  # type: ignore
    except ImportError:
        raise ProviderConfigError(
            _PROVIDER_NAME,
            "google-generativeai package is not installed. "
            "Run: pip install google-generativeai",
        )
    genai.configure(api_key=_get_api_key())
    return genai


def _model(name: str):
    genai = _get_client()
    import google.generativeai as genai_mod  # type: ignore
    return genai_mod.GenerativeModel(name)


def _vision_model_name() -> str:
    return get_settings().GEMINI_VISION_MODEL or "gemini-2.0-flash"


def _video_model_name() -> str:
    return get_settings().GEMINI_VIDEO_MODEL or "gemini-2.0-flash"


def _audio_model_name() -> str:
    return get_settings().GEMINI_AUDIO_MODEL or "gemini-2.0-flash"


# ---------------------------------------------------------------------------
# Response parsing helpers
# ---------------------------------------------------------------------------

_IMAGE_ANALYSIS_PROMPT = """Analyse this image carefully and respond with a JSON object.

Return ONLY valid JSON with this exact structure:
{
  "scene_description": "detailed description of what is shown",
  "detected_objects": [{"label": "object name", "confidence": "high|medium|low"}],
  "activities": ["list of activities or actions visible"],
  "extracted_text": [{"text": "visible text", "confidence": "high|medium|low", "language": "en"}],
  "dominant_colours": ["colour names or hex codes"],
  "estimated_setting": "indoor|outdoor|studio|unknown",
  "mood_or_tone": "description of mood or atmosphere",
  "notable_details": ["important details worth noting"],
  "spatial_relationships": ["e.g. person standing in front of product"],
  "overall_confidence": "high|medium|low"
}

Rules:
- Only describe what is actually visible. Do not invent details.
- If text is not visible, return an empty extracted_text array.
- Use confidence "low" when you are uncertain about a detail.
- Do not include markdown fences in your response."""

_CAROUSEL_SYSTEM_PROMPT = """You are analysing a sequence of images from a social media carousel post.
The images are provided in their original order (first image is index 0).
Analyse each image individually, then provide an overall carousel summary.
Preserve the sequence — the order of images matters."""

_VIDEO_ANALYSIS_PROMPT = """Analyse this video carefully and respond with a JSON object.

Return ONLY valid JSON with this exact structure:
{
  "overall_description": "comprehensive description of the video content",
  "key_events": ["ordered list of notable events with approximate timestamps"],
  "detected_activities": ["activities visible in the video"],
  "scene_transitions": ["descriptions of major scene changes"],
  "has_audio": true,
  "audio_description": "description of audio content (speech, music, sounds)",
  "overall_confidence": "high|medium|low",
  "warnings": []
}

Rules:
- Describe events in chronological order.
- Distinguish between what is visible and what is heard.
- Do not claim events occurred between frames unless supported by evidence.
- If there is no audio, set has_audio to false and audio_description to null."""

_AUDIO_TRANSCRIPTION_PROMPT = """Transcribe all speech in this audio file.

Return ONLY valid JSON with this exact structure:
{
  "full_text": "complete transcript of all speech",
  "detected_language": "ISO 639-1 language code (e.g. en, hi, ta)",
  "detected_languages": ["list of all languages detected"],
  "is_code_mixed": false,
  "segments": [
    {
      "text": "segment text",
      "start_seconds": 0.0,
      "end_seconds": 2.5,
      "confidence": "high|medium|low",
      "language": "en"
    }
  ],
  "warnings": []
}

Rules:
- If there is no speech, return full_text as empty string and segments as empty array.
- Mark is_code_mixed as true if multiple languages are mixed within sentences.
- Use confidence "low" for unclear or uncertain segments."""

_AUDIO_UNDERSTANDING_PROMPT = """Analyse the non-speech audio content of this file.

Return ONLY valid JSON with this exact structure:
{
  "has_speech": true,
  "has_music": false,
  "music_genre": null,
  "ambient_sounds": ["list of environmental or background sounds"],
  "sound_events": ["list of distinct sound events"],
  "emotional_tone": "description of emotional tone or atmosphere",
  "background_noise_level": "low|medium|high|none",
  "general_summary": "overall description of the audio content",
  "warnings": []
}

Rules:
- Focus on non-speech audio (music, sounds, noise, atmosphere).
- If the file contains only silence, note that in general_summary.
- Do not transcribe speech here — that is handled separately."""


def _parse_json_response(text: str, provider: str) -> Dict[str, Any]:
    """Extract JSON from model response, stripping markdown fences if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove opening fence (```json or ```)
        lines = lines[1:]
        # Remove closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderError(provider, f"Model returned invalid JSON: {exc}\nRaw: {text[:500]}")


def _confidence(raw: Any) -> ConfidenceLevel:
    mapping = {"high": ConfidenceLevel.HIGH, "medium": ConfidenceLevel.MEDIUM, "low": ConfidenceLevel.LOW}
    return mapping.get(str(raw).lower(), ConfidenceLevel.MEDIUM)


def _parse_image_observation(data: Dict[str, Any], media_id: str, sequence_index: int, model_version: str, elapsed_ms: int) -> ImageObservation:
    objects = [
        DetectedObject(label=o.get("label", ""), confidence=_confidence(o.get("confidence")))
        for o in data.get("detected_objects", [])
        if isinstance(o, dict) and o.get("label")
    ]
    texts = [
        ExtractedText(
            text=t.get("text", ""),
            confidence=_confidence(t.get("confidence")),
            language=t.get("language"),
        )
        for t in data.get("extracted_text", [])
        if isinstance(t, dict) and t.get("text")
    ]
    return ImageObservation(
        media_id=media_id,
        sequence_index=sequence_index,
        detected_objects=objects,
        extracted_text=texts,
        dominant_colours=data.get("dominant_colours", []),
        estimated_setting=data.get("estimated_setting"),
        scene_description=data.get("scene_description"),
        activities=data.get("activities", []),
        mood_or_tone=data.get("mood_or_tone"),
        notable_details=data.get("notable_details", []),
        spatial_relationships=data.get("spatial_relationships", []),
        confidence=_confidence(data.get("overall_confidence", "medium")),
        provider=_PROVIDER_NAME,
        model_version=model_version,
        processing_time_ms=elapsed_ms,
        warnings=data.get("warnings", []),
    )


# ---------------------------------------------------------------------------
# Vision provider
# ---------------------------------------------------------------------------


class GeminiVisionProvider(VisionProvider):
    """Gemini-based image understanding provider."""

    def health_check(self) -> bool:
        try:
            _get_api_key()
            return True
        except ProviderConfigError:
            return False

    def analyse(self, request: VisionRequest) -> List[ImageObservation]:
        import google.generativeai as genai  # type: ignore

        _get_client()  # validates key + import
        model_name = _vision_model_name()
        model = _model(model_name)

        observations: List[ImageObservation] = []

        if len(request.images) == 1:
            observations.append(self._analyse_single(model, request.images[0], model_name))
        else:
            observations.extend(self._analyse_carousel(model, request, model_name))

        return observations

    def _analyse_single(self, model, image_input, model_name: str) -> ImageObservation:
        import google.generativeai as genai  # type: ignore

        start = time.monotonic()
        try:
            image_part = {"mime_type": image_input.mime_type, "data": image_input.data}
            response = model.generate_content(
                [_IMAGE_ANALYSIS_PROMPT, image_part],
                generation_config={"temperature": 0.1},
                request_options={"timeout": 60},
            )
        except Exception as exc:
            raise ProviderError(_PROVIDER_NAME, f"Gemini API call failed: {exc}", retryable=True)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        data = _parse_json_response(response.text, _PROVIDER_NAME)
        return _parse_image_observation(data, image_input.media_id, image_input.sequence_index, model_name, elapsed_ms)

    def _analyse_carousel(self, model, request: VisionRequest, model_name: str) -> List[ImageObservation]:
        """Send all carousel images in one API call to preserve sequence context."""
        import google.generativeai as genai  # type: ignore

        # Build a multi-image prompt
        n = len(request.images)
        prompt = (
            f"{_CAROUSEL_SYSTEM_PROMPT}\n\n"
            f"There are {n} images in this carousel (index 0 to {n - 1}).\n"
            "Analyse each image and return a JSON array where each element follows this structure:\n"
            '{"sequence_index": 0, "scene_description": "...", "detected_objects": [], '
            '"activities": [], "extracted_text": [], "dominant_colours": [], '
            '"estimated_setting": "...", "mood_or_tone": "...", "notable_details": [], '
            '"spatial_relationships": [], "overall_confidence": "medium"}\n\n'
            "Return ONLY a valid JSON array. No markdown fences."
        )

        parts = [prompt]
        for img in sorted(request.images, key=lambda x: x.sequence_index):
            parts.append({"mime_type": img.mime_type, "data": img.data})

        start = time.monotonic()
        try:
            response = model.generate_content(
                parts,
                generation_config={"temperature": 0.1},
                request_options={"timeout": 120},
            )
        except Exception as exc:
            raise ProviderError(_PROVIDER_NAME, f"Gemini carousel API call failed: {exc}", retryable=True)

        elapsed_ms = int((time.monotonic() - start) * 1000)

        raw = response.text.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw = "\n".join(lines).strip()

        try:
            items = json.loads(raw)
            if not isinstance(items, list):
                items = [items]
        except json.JSONDecodeError as exc:
            raise ProviderError(_PROVIDER_NAME, f"Carousel response invalid JSON: {exc}")

        # Map results back to original images by sequence_index
        index_map = {img.sequence_index: img for img in request.images}
        observations: List[ImageObservation] = []

        for item in items:
            seq = item.get("sequence_index", 0)
            img_input = index_map.get(seq)
            media_id = img_input.media_id if img_input else f"unknown_{seq}"
            observations.append(
                _parse_image_observation(item, media_id, seq, model_name, elapsed_ms)
            )

        # Ensure all images have an observation (fill gaps with empty)
        observed_indices = {o.sequence_index for o in observations}
        for img in request.images:
            if img.sequence_index not in observed_indices:
                logger.warning("No observation returned for image index %d", img.sequence_index)
                observations.append(
                    ImageObservation(
                        media_id=img.media_id,
                        sequence_index=img.sequence_index,
                        provider=_PROVIDER_NAME,
                        model_version=model_name,
                        warnings=["No observation returned by model for this image"],
                    )
                )

        return sorted(observations, key=lambda o: o.sequence_index)


# ---------------------------------------------------------------------------
# Video understanding provider
# ---------------------------------------------------------------------------


class GeminiVideoProvider(VideoUnderstandingProvider):
    """Gemini-based video understanding using the File API."""

    def health_check(self) -> bool:
        try:
            _get_api_key()
            return True
        except ProviderConfigError:
            return False

    def analyse(self, request: VideoRequest) -> VideoObservation:
        import google.generativeai as genai  # type: ignore

        _get_client()
        model_name = _video_model_name()

        file_path = Path(request.file_path)
        if not file_path.exists():
            raise ProviderError(_PROVIDER_NAME, f"Video file not found: {request.file_path}")

        start = time.monotonic()

        # Upload via File API
        try:
            uploaded = genai.upload_file(str(file_path), mime_type=f"video/{request.extension}")
        except Exception as exc:
            raise ProviderError(_PROVIDER_NAME, f"Gemini file upload failed: {exc}", retryable=True)

        try:
            model = _model(model_name)
            response = model.generate_content(
                [_VIDEO_ANALYSIS_PROMPT, uploaded],
                generation_config={"temperature": 0.1},
                request_options={"timeout": 300},
            )
        except Exception as exc:
            raise ProviderError(_PROVIDER_NAME, f"Gemini video analysis failed: {exc}", retryable=True)
        finally:
            # Clean up uploaded file from Gemini servers
            try:
                genai.delete_file(uploaded.name)
            except Exception:
                pass

        elapsed_ms = int((time.monotonic() - start) * 1000)
        data = _parse_json_response(response.text, _PROVIDER_NAME)

        return VideoObservation(
            media_id=request.media_id,
            overall_description=data.get("overall_description"),
            key_events=data.get("key_events", []),
            detected_activities=data.get("detected_activities", []),
            scene_transitions=data.get("scene_transitions", []),
            has_audio=data.get("has_audio", request.has_audio),
            audio_description=data.get("audio_description"),
            total_duration_seconds=request.duration_seconds,
            provider=_PROVIDER_NAME,
            model_version=model_name,
            processing_time_ms=elapsed_ms,
            warnings=data.get("warnings", []),
        )


# ---------------------------------------------------------------------------
# Audio understanding provider (Gemini native)
# ---------------------------------------------------------------------------


class GeminiAudioUnderstandingProvider(AudioUnderstandingProvider):
    """Gemini-based general audio understanding."""

    def health_check(self) -> bool:
        try:
            _get_api_key()
            return True
        except ProviderConfigError:
            return False

    def analyse(self, request: AudioUnderstandingRequest) -> AudioObservation:
        import google.generativeai as genai  # type: ignore

        _get_client()
        model_name = _audio_model_name()

        file_path = Path(request.file_path)
        if not file_path.exists():
            raise ProviderError(_PROVIDER_NAME, f"Audio file not found: {request.file_path}")

        start = time.monotonic()

        try:
            uploaded = genai.upload_file(str(file_path))
        except Exception as exc:
            raise ProviderError(_PROVIDER_NAME, f"Gemini audio upload failed: {exc}", retryable=True)

        try:
            model = _model(model_name)
            response = model.generate_content(
                [_AUDIO_UNDERSTANDING_PROMPT, uploaded],
                generation_config={"temperature": 0.1},
                request_options={"timeout": 120},
            )
        except Exception as exc:
            raise ProviderError(_PROVIDER_NAME, f"Gemini audio analysis failed: {exc}", retryable=True)
        finally:
            try:
                genai.delete_file(uploaded.name)
            except Exception:
                pass

        elapsed_ms = int((time.monotonic() - start) * 1000)
        data = _parse_json_response(response.text, _PROVIDER_NAME)

        return AudioObservation(
            media_id=request.media_id,
            has_speech=data.get("has_speech"),
            has_music=data.get("has_music"),
            music_genre=data.get("music_genre"),
            ambient_sounds=data.get("ambient_sounds", []),
            sound_events=data.get("sound_events", []),
            emotional_tone=data.get("emotional_tone"),
            background_noise_level=data.get("background_noise_level"),
            general_summary=data.get("general_summary"),
            provider=_PROVIDER_NAME,
            model_version=model_name,
            processing_time_ms=elapsed_ms,
            warnings=data.get("warnings", []),
        )


# ---------------------------------------------------------------------------
# Gemini transcription provider (uses native audio understanding)
# ---------------------------------------------------------------------------


class GeminiTranscriptionProvider(AudioTranscriptionProvider):
    """Gemini-based speech transcription via native audio understanding."""

    def health_check(self) -> bool:
        try:
            _get_api_key()
            return True
        except ProviderConfigError:
            return False

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        import google.generativeai as genai  # type: ignore

        _get_client()
        model_name = _audio_model_name()

        file_path = Path(request.file_path)
        if not file_path.exists():
            raise ProviderError(_PROVIDER_NAME, f"Audio file not found: {request.file_path}")

        start = time.monotonic()

        try:
            uploaded = genai.upload_file(str(file_path))
        except Exception as exc:
            raise ProviderError(_PROVIDER_NAME, f"Gemini audio upload failed: {exc}", retryable=True)

        try:
            model = _model(model_name)
            response = model.generate_content(
                [_AUDIO_TRANSCRIPTION_PROMPT, uploaded],
                generation_config={"temperature": 0.0},
                request_options={"timeout": 120},
            )
        except Exception as exc:
            raise ProviderError(_PROVIDER_NAME, f"Gemini transcription failed: {exc}", retryable=True)
        finally:
            try:
                genai.delete_file(uploaded.name)
            except Exception:
                pass

        elapsed_ms = int((time.monotonic() - start) * 1000)
        data = _parse_json_response(response.text, _PROVIDER_NAME)

        segments = [
            TranscriptionSegment(
                text=s.get("text", ""),
                start_seconds=float(s.get("start_seconds", 0)),
                end_seconds=float(s.get("end_seconds", 0)),
                confidence=_confidence(s.get("confidence", "medium")),
                language=s.get("language"),
            )
            for s in data.get("segments", [])
            if isinstance(s, dict) and s.get("text")
        ]

        return TranscriptionResult(
            media_id=request.media_id,
            full_text=data.get("full_text", ""),
            segments=segments,
            detected_language=data.get("detected_language"),
            detected_languages=data.get("detected_languages", []),
            is_code_mixed=data.get("is_code_mixed", False),
            provider=_PROVIDER_NAME,
            model_version=model_name,
            processing_time_ms=elapsed_ms,
            warnings=data.get("warnings", []),
        )
