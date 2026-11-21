# Technical Decisions — Multimodal AI Caption Generator

**Phase:** 2 — Implementation complete  
**Status:** Updated with actual implementation decisions.

This document records significant technical decisions, the options considered, the rationale for the choice made, and the conditions under which the decision should be revisited.

---

## TD-001: Primary Vision Provider — Gemini 2.0 Flash

**Decision date:** Phase 2.1 (proposed), Phase 2 (implemented)  
**Status:** Implemented

### Options considered
- Gemini 1.5 Flash / Gemini 2.0 Flash (Google)
- GPT-4o (OpenAI)
- Claude 3.5 Sonnet (Anthropic)
- Qwen2-VL-72B (self-hosted)

### Decision
Use `gemini-2.0-flash` as the primary vision provider for MVP.

**Model version update from Phase 2.1 research:** The research document referenced `gemini-1.5-flash`. During Phase 2 implementation, `gemini-2.0-flash` was verified as the current stable Flash model (2025). The implementation uses `gemini-2.0-flash` as the default. The model name is configurable via `GEMINI_VISION_MODEL` so it can be updated without code changes.

---

## TD-002: Video Processing Strategy — Gemini File API + FFmpeg Frame Extraction

**Decision date:** Phase 2.1 (proposed), Phase 2 (implemented)  
**Status:** Implemented

### Decision
Implemented both approaches:
- `GeminiVideoProvider` uses the Gemini File API for full video understanding
- `video_processor.py` implements hybrid FFmpeg frame extraction (scene-change + uniform sampling) for audio extraction and frame-level evidence

In Phase 2, the Gemini File API is the primary video understanding path. FFmpeg is used for audio extraction from videos with audio tracks.

---

## TD-003: Audio Transcription — OpenAI Whisper API (default), Gemini (alternative)

**Decision date:** Phase 2.1 (proposed), Phase 2 (implemented)  
**Status:** Implemented

### Decision
Implemented both `OpenAIWhisperProvider` and `GeminiTranscriptionProvider`. Default is `openai-whisper`. Switchable via `AUDIO_TRANSCRIPTION_PROVIDER` in `.env`.

For video audio tracks, the same `AUDIO_TRANSCRIPTION_PROVIDER` is used on the extracted WAV file.

---

## TD-004: Provider Independence — Abstract Interface Pattern

**Decision date:** Phase 2.1 (proposed), Phase 2 (implemented)  
**Status:** Implemented

### Decision
Implemented abstract base classes in `app/providers/base.py` and a registry in `app/providers/registry.py`. Provider selection is via `.env` variables (`VISION_PROVIDER`, `VIDEO_PROVIDER`, `AUDIO_TRANSCRIPTION_PROVIDER`, `AUDIO_UNDERSTANDING_PROVIDER`).

---

## TD-005: Evidence Structure — Separate Observed Facts from Inferences

**Decision date:** Phase 2.1  
**Status:** Accepted

### Decision
The `MediaEvidence` structure explicitly separates directly observed facts (detected objects, extracted text, timestamps) from model interpretations (scene descriptions, mood, inferences).

### Rationale
1. Caption hallucination is a known problem with vision-language models
2. Separating facts from interpretations allows the caption validator (Phase 3) to check claims against evidence
3. Confidence levels (`HIGH`, `MEDIUM`, `LOW`) allow the caption generator to hedge appropriately
4. This separation also makes the system more auditable — a user can see what the model actually observed vs. what it inferred

### Risks
- The boundary between "observed" and "inferred" is not always clear
- Models may not reliably distinguish their own confidence levels

---

## TD-006: Dual-Provider MVP

**Decision date:** Phase 2.1 (proposed), Phase 2 (implemented)  
**Status:** Implemented

### Decision
Implemented dual-provider MVP: Gemini 2.0 Flash for vision/video/audio understanding, OpenAI Whisper API for standalone audio transcription. Both providers are registered and switchable via `.env`.

---

## TD-007: No GPU Requirement for MVP

**Decision date:** Phase 2.1  
**Status:** Accepted

### Decision
The MVP will not require a GPU. All AI processing will use managed cloud APIs.

### Rationale
1. GPU infrastructure adds significant operational complexity and cost for an MVP
2. Managed APIs (Gemini, OpenAI Whisper) provide sufficient capability for initial validation
3. The provider interface design allows switching to local GPU-based models (Faster-Whisper, LLaVA) later without changing the pipeline

### Revisit if
- API costs become prohibitive at scale
- Data privacy requirements prevent sending media to cloud APIs
- Latency requirements cannot be met by cloud APIs

---

## TD-008: Deferred Decisions

The following decisions are intentionally deferred until evaluation results are available:

| Decision | Deferred Until |
|---|---|
| Final vision provider selection | After Phase 2.1 evaluation on our test set |
| Transcription provider for code-mixed speech | After measuring WER on Hinglish samples |
| Frame extraction strategy for long videos | After testing Gemini native video on 5–10 minute videos |
| Caption generation model selection | Phase 3 planning |
| Caption validation approach | Phase 3 planning |
| Database schema changes for evidence storage | Phase 2 implementation |
| Async job queue introduction | Phase 3 (when processing time exceeds 30 seconds) |

---

## TD-009: Python Version — Remain on 3.10.11 for Now

**Decision date:** Phase 2.1  
**Status:** Accepted

### Decision
Continue using Python 3.10.11 for Phase 2. Do not upgrade to 3.11+ until Phase 2 integration is complete and stable.

### Rationale
1. The existing test suite (42/42 passing) is verified on 3.10.11
2. No code incompatibilities with 3.11+ have been identified, but upgrading mid-phase introduces unnecessary risk
3. All planned dependencies (google-generativeai, openai) support Python 3.10+

### Revisit if
- A required dependency drops Python 3.10 support
- A 3.11+ feature is needed for performance or correctness

---

## TD-010: FFmpeg Frame Extraction Parameters

**Decision date:** Phase 2.1 (proposed), Phase 2 (implemented)  
**Status:** Implemented with configurable defaults

| Parameter | Implemented Value | Config Variable |
|---|---|---|
| Scene change threshold | 0.3 | `VIDEO_SCENE_CHANGE_THRESHOLD` |
| Maximum frame interval | 5 seconds | `VIDEO_FRAME_INTERVAL_SECONDS` |
| Minimum frame gap (dedup) | 1 second | hardcoded in `_merge_and_deduplicate` |
| Output format | JPEG, `-q:v 3` | hardcoded |
| Maximum frames per video | 50 | `VIDEO_MAX_FRAMES` |
| Frame width | 1280px | `VIDEO_FRAME_WIDTH` |
| Processing timeout | 300 seconds | `VIDEO_PROCESSING_TIMEOUT_SECONDS` |

All configurable parameters are in `.env.example`. Tuning based on evaluation results is deferred to Phase 3.

---

## TD-011: Synchronous Processing in Phase 2

**Decision date:** Phase 2  
**Status:** Accepted with documented limitation

### Decision
Phase 2 processes media synchronously within the HTTP request. No background job queue is introduced.

### Rationale
1. A background job queue (Celery, RQ, FastAPI BackgroundTasks) adds significant operational complexity.
2. For MVP validation, synchronous processing is sufficient — most test media is short.
3. The API response clearly documents the synchronous limitation and recommends a 180-second client timeout.

### Revisit if
- Video processing regularly exceeds 30 seconds
- Multiple concurrent users are expected
- Phase 3 caption generation adds further latency

---

## TD-012: Evidence Not Persisted in Phase 2

**Decision date:** Phase 2  
**Status:** Accepted with documented limitation

### Decision
`MediaEvidence` is returned directly from the pipeline but not stored in the database. Each call to `GET /evidence/{collection_id}` re-runs the pipeline.

### Rationale
1. Adding a new database table for evidence requires schema migration planning.
2. For Phase 2 validation, re-running the pipeline on each request is acceptable.
3. The limitation is clearly documented in the API and in `PHASE_2_IMPLEMENTATION.md`.

### Revisit if
- Evidence persistence is needed for Phase 3 caption generation
- Re-running the pipeline on each request becomes too expensive
