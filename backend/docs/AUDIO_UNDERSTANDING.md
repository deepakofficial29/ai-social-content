# Audio Understanding

**Phase:** 2.5  
**Transcription provider:** OpenAI Whisper API (default) or Gemini (configurable)  
**Audio understanding provider:** Gemini 2.0 Flash (configurable)  
**Status:** Implemented and tested (mocked). Requires API keys for live use.

---

## Two Separate Capabilities

Speech transcription and general audio understanding are **separate capabilities** handled by separate providers.

| Capability | Provider | Output |
|------------|----------|--------|
| Speech-to-text | `AudioTranscriptionProvider` | `TranscriptionResult` |
| General audio understanding | `AudioUnderstandingProvider` | `AudioObservation` |

The absence of a transcript does not mean the absence of meaningful audio. A file may contain music, environmental sounds, or silence — all of which are captured by the audio understanding provider.

---

## Supported Formats

- WAV
- MP3
- M4A
- AAC

---

## Transcription (OpenAI Whisper API)

**Model:** `whisper-1` (Whisper large-v2)  
**Configuration:** `OPENAI_API_KEY`, `OPENAI_WHISPER_MODEL=whisper-1`

**Returns:**
- Full transcript text
- Segment-level timestamps (start and end seconds per segment)
- Detected language (ISO 639-1)
- List of all detected languages

**Limitations:**
- 25 MB file size limit per request
- Segment-level timestamps only (not word-level)
- Does not detect code-mixed speech (`is_code_mixed` is always `false`)
- Does not provide per-segment confidence scores (all segments marked `medium`)
- Code-mixed speech (Hinglish, Tanglish) accuracy is unverified — see `MODEL_EVALUATION_PLAN.md`

**Alternative:** Set `AUDIO_TRANSCRIPTION_PROVIDER=gemini` to use Gemini's native audio transcription. Gemini provides approximate timestamps and may handle code-mixed speech better, but this is unverified.

---

## General Audio Understanding (Gemini)

**Model:** `gemini-2.0-flash`  
**Configuration:** `GEMINI_API_KEY`, `GEMINI_AUDIO_MODEL=gemini-2.0-flash`

**Returns:**
- Whether speech is present
- Whether music is present
- Music genre (if applicable)
- Ambient sounds (list)
- Sound events (list with approximate timestamps)
- Emotional tone
- Background noise level (low / medium / high / none)
- General summary

**Handles gracefully:**
- Speech-only audio
- Music-only audio
- Environmental sound recordings
- Silence
- Noisy recordings

---

## Evidence Structure

### With speech
```json
{
  "transcription": {
    "media_id": "...",
    "full_text": "Welcome to our product demo. Today we are showing...",
    "segments": [
      {
        "text": "Welcome to our product demo.",
        "start_seconds": 0.0,
        "end_seconds": 2.5,
        "confidence": "medium",
        "language": "en"
      }
    ],
    "detected_language": "en",
    "detected_languages": ["en"],
    "is_code_mixed": false,
    "provider": "openai-whisper",
    "model_version": "whisper-1"
  },
  "audio_observation": {
    "has_speech": true,
    "has_music": false,
    "ambient_sounds": ["light background noise"],
    "background_noise_level": "low",
    "general_summary": "Clear voiceover narration with minimal background noise",
    "provider": "gemini",
    "model_version": "gemini-2.0-flash"
  }
}
```

### Music only (no speech)
```json
{
  "transcription": {
    "full_text": "",
    "segments": [],
    "detected_language": null
  },
  "audio_observation": {
    "has_speech": false,
    "has_music": true,
    "music_genre": "pop",
    "emotional_tone": "upbeat",
    "background_noise_level": "none",
    "general_summary": "Upbeat pop music, no speech"
  }
}
```

### Silence
```json
{
  "transcription": {
    "full_text": "",
    "segments": []
  },
  "audio_observation": {
    "has_speech": false,
    "has_music": false,
    "ambient_sounds": [],
    "background_noise_level": "none",
    "general_summary": "The recording is silent"
  }
}
```

---

## Partial Failure Handling

If transcription fails but audio understanding succeeds:
- `transcription` is `null` in `MediaEvidence`
- `audio_observation` is populated
- `processing_status` is `"partial"`
- The error is recorded in `processing_errors`

The reverse is also true — if audio understanding fails, the transcription is preserved.

---

## Video Audio Integration

For videos with audio tracks:
1. FFmpeg extracts the audio to a temporary WAV file (16 kHz, mono)
2. The WAV file is passed to both `AudioTranscriptionProvider` and `AudioUnderstandingProvider`
3. Results are stored in `MediaEvidence.transcription` and `MediaEvidence.audio_observation`
4. The temporary WAV file is deleted in a `finally` block

For silent videos, steps 1–4 are skipped entirely.

---

## Indian Language Support

| Language | Whisper API | Gemini |
|----------|-------------|--------|
| English (Indian accent) | Good | Good |
| Hindi | Good | Good |
| Tamil | Good | Good |
| Telugu | Good | Good |
| Bengali | Good | Good |
| Code-mixed (Hinglish) | Unverified | Unverified |

These assessments are based on published benchmarks, not our own evaluation. See `MODEL_EVALUATION_PLAN.md` for the planned evaluation procedure.
