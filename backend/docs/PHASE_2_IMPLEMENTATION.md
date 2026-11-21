# Phase 2 Implementation — Multimodal AI Understanding

**Status:** Complete  
**Test result:** 139 passed, 0 failed, 0 skipped  
**Python version:** 3.10.11  
**Phase 1 tests:** All 42 still passing (included in 139 total)

---

## Overview

Phase 2 adds a complete multimodal understanding layer on top of the Phase 1 media intake pipeline. It converts uploaded media into structured, traceable evidence (`MediaEvidence`) that will be consumed by the caption generator in Phase 3.

**Flow:**
```
Media Upload (Phase 1)
    ↓
Understanding Pipeline (Phase 2)
    ├── image/single   → GeminiVisionProvider
    ├── image/carousel → GeminiVisionProvider (ordered multi-image)
    ├── video          → GeminiVideoProvider + FFmpeg audio extraction
    │                    └── AudioTranscriptionProvider + AudioUnderstandingProvider
    └── audio          → AudioTranscriptionProvider + AudioUnderstandingProvider
    ↓
MediaEvidence (structured, traceable)
    ↓
Caption Generation (Phase 3 — not yet implemented)
```

---

## Phase 2.2 — Provider Abstractions and Schemas

### New files
- `app/providers/base.py` — Abstract base classes: `VisionProvider`, `VideoUnderstandingProvider`, `AudioTranscriptionProvider`, `AudioUnderstandingProvider`. Also `ProviderError` and `ProviderConfigError`.
- `app/providers/registry.py` — Provider registry with `register_*` and `get_*` functions. Provider selection via `.env`.
- `app/providers/__init__.py` — Registers all built-in providers on import.
- `app/schemas/evidence.py` — All multimodal schemas: `ImageObservation`, `VideoObservation`, `FrameObservation`, `TranscriptionResult`, `TranscriptionSegment`, `AudioObservation`, `MediaEvidence`, `ConfidenceLevel`, `DetectedObject`, `ExtractedText`, `BoundingBox`.
- `app/schemas/provider_requests.py` — Provider input schemas: `VisionRequest`, `ImageInput`, `VideoRequest`, `TranscriptionRequest`, `AudioUnderstandingRequest`.

### Design decisions
- All AI calls go through abstract interfaces — swapping providers requires only a new implementation class.
- `ProviderConfigError` (not retryable) is distinct from `ProviderError` (may be retryable).
- Observed facts (detected objects, extracted text, timestamps) are kept separate from model interpretations (scene descriptions, mood).
- All AI-populated fields are `Optional` — the system functions correctly when a provider is unavailable.

---

## Phase 2.3 — Image and Carousel Understanding

### New files
- `app/providers/gemini/provider.py` — `GeminiVisionProvider`: single image and carousel analysis. Sends all carousel images in one API call to preserve sequence context.
- `app/services/image_understanding.py` — `analyse_images()`: loads image bytes from storage, builds `VisionRequest`, calls provider, aggregates OCR, returns `MediaEvidence`.

### Carousel handling
- All images in a carousel are sent to Gemini in a single API call with their sequence indices.
- The model is instructed to return a JSON array with one entry per image, keyed by `sequence_index`.
- Missing observations are filled with empty `ImageObservation` entries and a warning.
- Results are sorted by `sequence_index` before being stored in `MediaEvidence`.

---

## Phase 2.4 — Video Understanding

### New files
- `app/services/video_processor.py` — `extract_frames()`: hybrid scene-change + uniform sampling using FFmpeg. Returns `List[ExtractedFrame]` and optional audio WAV path. `cleanup_frames()` and `cleanup_audio()` for reliable temp file cleanup.
- `app/providers/gemini/provider.py` — `GeminiVideoProvider`: uploads video via Gemini File API, returns `VideoObservation`. Deletes uploaded file from Gemini servers in a `finally` block.
- `app/services/video_understanding.py` — `analyse_video()`: orchestrates video provider + audio extraction + transcription + audio understanding. Partial failures are recorded without discarding successful results.

### Frame extraction strategy
1. Scene-change detection (`select=gt(scene,0.3)`)
2. Uniform sampling fallback (`fps=1/5`)
3. Merge and deduplicate (minimum 1-second gap between frames)
4. Cap at `VIDEO_MAX_FRAMES` (default 50)

All temp files (frames + extracted audio) are cleaned up in `finally` blocks, including on failure.

### Silent video handling
If `has_audio=False` (from FFprobe metadata), audio processing is skipped entirely. No errors are recorded for the absence of audio.

---

## Phase 2.5 — Audio Understanding

### New files
- `app/providers/openai/provider.py` — `OpenAIWhisperProvider`: calls OpenAI Whisper API (`whisper-1`), returns `TranscriptionResult` with segment timestamps.
- `app/providers/gemini/provider.py` — `GeminiTranscriptionProvider` and `GeminiAudioUnderstandingProvider`: use Gemini File API for audio.
- `app/services/audio_understanding.py` — `analyse_audio()`: runs transcription and audio understanding independently. Partial failures are recorded without discarding successful results.

### Transcription vs. audio understanding
These are separate capabilities:
- **Transcription** (`AudioTranscriptionProvider`): speech-to-text with timestamps.
- **Audio understanding** (`AudioUnderstandingProvider`): music, environmental sounds, noise, emotional tone.

The absence of a transcript does not mean the absence of meaningful audio content.

---

## API Endpoints

### New endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/understanding/{collection_id}` | Run understanding pipeline (synchronous) |
| GET | `/api/v1/evidence/{collection_id}` | Retrieve evidence (re-runs pipeline in Phase 2) |

### Existing endpoints (unchanged)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/media/upload` | Upload media files |
| GET | `/api/v1/media/{media_id}` | Get media metadata |
| DELETE | `/api/v1/media/{media_id}` | Delete media |
| GET | `/api/v1/jobs/{job_id}` | Get job status |
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/ready` | Readiness check |

### Synchronous processing limitation
Phase 2 processes media synchronously within the HTTP request. For videos this may take 30–120 seconds. Clients must use a timeout of at least 180 seconds. A background job queue will be introduced in Phase 3.

---

## Environment Variables

See `.env.example` for the full list. New variables added in Phase 2:

```
VISION_PROVIDER=gemini
VIDEO_PROVIDER=gemini
AUDIO_TRANSCRIPTION_PROVIDER=openai-whisper
AUDIO_UNDERSTANDING_PROVIDER=gemini

GEMINI_API_KEY=
GEMINI_VISION_MODEL=gemini-2.0-flash
GEMINI_VIDEO_MODEL=gemini-2.0-flash
GEMINI_AUDIO_MODEL=gemini-2.0-flash

OPENAI_API_KEY=
OPENAI_WHISPER_MODEL=whisper-1

VIDEO_MAX_DURATION_SECONDS=600
VIDEO_MAX_FRAMES=50
VIDEO_FRAME_INTERVAL_SECONDS=5.0
VIDEO_SCENE_CHANGE_THRESHOLD=0.3
VIDEO_FRAME_WIDTH=1280
VIDEO_PROCESSING_TIMEOUT_SECONDS=300
```

---

## Missing Credentials Behaviour

If `GEMINI_API_KEY` or `OPENAI_API_KEY` is not set:
- The application starts normally.
- Health and readiness endpoints continue to work.
- Media upload and retrieval continue to work.
- Calling `POST /api/v1/understanding/{collection_id}` returns HTTP 422 with a clear error message identifying the missing credential.
- No exception propagates to the client.

---

## Known Limitations

1. **Synchronous processing** — understanding runs in the HTTP request. Long videos block the connection. Phase 3 must introduce a background job queue.
2. **Evidence not persisted** — `MediaEvidence` is returned directly but not stored in the database. Each call to `/evidence/{collection_id}` re-runs the pipeline. Persistence is planned for Phase 3.
3. **Gemini video 1 fps sampling** — Gemini's internal frame sampling rate is approximately 1 fps. Fast-moving content between frames may be missed. The FFmpeg frame extraction fallback (`video_processor.py`) is available for cases requiring explicit frame-level evidence.
4. **Whisper 25 MB limit** — The OpenAI Whisper API has a 25 MB file size limit. Audio files larger than this will fail with a clear error. Chunking is not yet implemented.
5. **Code-mixed speech** — No provider publishes WER on Hinglish or Tanglish. Accuracy on code-mixed speech is unverified. See `MODEL_EVALUATION_PLAN.md`.
6. **No retry logic** — `ProviderError(retryable=True)` is flagged but not automatically retried. Retry logic should be added in Phase 3.
7. **google-generativeai and openai packages not yet installed** — These are optional dependencies. The application starts without them; only AI calls fail. Install them when API keys are available.

---

## Remaining Work Before Phase 3

1. Install `google-generativeai` and `openai` packages and add to `requirements.txt`.
2. Add API keys to `.env` and run live provider tests.
3. Run the evaluation plan from `MODEL_EVALUATION_PLAN.md` on real content.
4. Persist `MediaEvidence` to the database (new table or JSON column).
5. Introduce a background job queue (Celery or FastAPI BackgroundTasks) for video processing.
6. Add retry logic for retryable `ProviderError` instances.
7. Add audio chunking for files exceeding the Whisper 25 MB limit.
8. Tune `VIDEO_SCENE_CHANGE_THRESHOLD` and `VIDEO_FRAME_INTERVAL_SECONDS` based on evaluation results.
