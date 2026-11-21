# Provider Implementation Guide

**Phase:** 2  
**Status:** Implemented and tested (mocked). Live provider calls require API keys.

---

## Architecture

All AI calls go through abstract provider interfaces defined in `app/providers/base.py`. The application never calls a specific AI SDK directly from business logic.

```
Business Logic (services/)
    ↓
Provider Interface (providers/base.py)
    ↓
Concrete Implementation (providers/gemini/ or providers/openai/)
    ↓
External AI API
```

Swapping providers requires only:
1. A new implementation class in `app/providers/`
2. Registration in `app/providers/__init__.py`
3. A `.env` change to select the new provider

---

## Provider Interfaces

### VisionProvider
```python
class VisionProvider(ABC):
    def analyse(self, request: VisionRequest) -> List[ImageObservation]: ...
    def health_check(self) -> bool: ...
```

### VideoUnderstandingProvider
```python
class VideoUnderstandingProvider(ABC):
    def analyse(self, request: VideoRequest) -> VideoObservation: ...
    def health_check(self) -> bool: ...
```

### AudioTranscriptionProvider
```python
class AudioTranscriptionProvider(ABC):
    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult: ...
    def health_check(self) -> bool: ...
```

### AudioUnderstandingProvider
```python
class AudioUnderstandingProvider(ABC):
    def analyse(self, request: AudioUnderstandingRequest) -> AudioObservation: ...
    def health_check(self) -> bool: ...
```

---

## Implemented Providers

### Gemini (Google AI)

**Package:** `google-generativeai`  
**Model:** `gemini-2.0-flash` (default)  
**Configuration:**
```
GEMINI_API_KEY=your_key_here
GEMINI_VISION_MODEL=gemini-2.0-flash
GEMINI_VIDEO_MODEL=gemini-2.0-flash
GEMINI_AUDIO_MODEL=gemini-2.0-flash
```

**Implements:**
- `GeminiVisionProvider` — single image and carousel analysis
- `GeminiVideoProvider` — video understanding via File API
- `GeminiTranscriptionProvider` — speech transcription via native audio
- `GeminiAudioUnderstandingProvider` — general audio understanding

**Model selection rationale:**
- `gemini-2.0-flash` is the current stable Flash model as of 2025 (replaces `gemini-1.5-flash` from research phase)
- Native multi-image support for carousels (up to 3,600 images per request)
- Native video and audio support via File API
- Lowest cost among managed API options

**Get API key:** https://aistudio.google.com/app/apikey

### OpenAI Whisper

**Package:** `openai`  
**Model:** `whisper-1` (Whisper large-v2)  
**Configuration:**
```
OPENAI_API_KEY=your_key_here
OPENAI_WHISPER_MODEL=whisper-1
```

**Implements:**
- `OpenAIWhisperProvider` — speech transcription with segment timestamps

**Limitations:**
- 25 MB file size limit per request
- Segment-level timestamps only (not word-level)
- Does not detect code-mixed speech
- Does not provide per-segment confidence scores

**Get API key:** https://platform.openai.com/api-keys

---

## Provider Registry

Providers are registered by name in `app/providers/__init__.py`:

```python
register_vision_provider("gemini", GeminiVisionProvider)
register_transcription_provider("openai-whisper", OpenAIWhisperProvider)
```

Selection via `.env`:
```
VISION_PROVIDER=gemini
AUDIO_TRANSCRIPTION_PROVIDER=openai-whisper
```

### Adding a new provider

1. Create `app/providers/myprovider/provider.py` implementing the relevant abstract class.
2. Register in `app/providers/__init__.py`:
   ```python
   from app.providers.myprovider.provider import MyVisionProvider
   register_vision_provider("myprovider", MyVisionProvider)
   ```
3. Set in `.env`: `VISION_PROVIDER=myprovider`
4. Write tests in `tests/test_providers.py`.

---

## Error Handling

### ProviderConfigError
Raised when a required credential is missing. Not retryable. The application starts normally; only AI calls fail.

```python
raise ProviderConfigError("gemini", "GEMINI_API_KEY is not configured.")
```

### ProviderError
Raised on runtime failures (API errors, timeouts, invalid responses).

```python
raise ProviderError("gemini", "API timeout", retryable=True)
```

The pipeline catches both error types, records them in `MediaEvidence.processing_errors`, and continues with partial results where possible.

---

## Installing Provider Packages

The provider packages are optional dependencies. Install them when API keys are available:

```bash
pip install google-generativeai
pip install openai
```

Add to `requirements.txt` when ready for deployment.

---

## Testing Providers

All provider calls are mocked in automated tests. No paid API calls are made during `pytest`.

To test against a live provider:
1. Set the API key in `.env`
2. Run the manual test procedure in `PHASE_2_IMPLEMENTATION.md`
3. Use the `/api/v1/understanding/{collection_id}` endpoint with a real uploaded file
