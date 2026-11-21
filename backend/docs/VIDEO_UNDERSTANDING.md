# Video Understanding

**Phase:** 2.4  
**Provider:** Gemini 2.0 Flash via File API (configurable)  
**Frame extraction:** FFmpeg (existing installation)  
**Status:** Implemented and tested (mocked). Requires GEMINI_API_KEY for live use.

---

## Processing Flow

```
Video file (in local storage)
    ↓
FFmpeg frame extraction (hybrid strategy)
    ├── Scene-change detection
    └── Uniform sampling fallback
    ↓
Audio extraction (if has_audio=True)
    ↓
Gemini File API (video understanding)
    ↓
AudioTranscriptionProvider (if audio extracted)
    ↓
AudioUnderstandingProvider (if audio extracted)
    ↓
MediaEvidence (video_observation + transcription + audio_observation)
    ↓
Cleanup all temp files
```

---

## Frame Extraction Strategy

The hybrid strategy balances coverage and cost:

1. **Scene-change detection** — extracts frames when the scene changes significantly (`select=gt(scene,0.3)`)
2. **Uniform sampling fallback** — extracts one frame every 5 seconds to ensure coverage in static scenes
3. **Merge and deduplicate** — frames closer than 1 second apart are deduplicated
4. **Cap** — maximum 50 frames per video (configurable)

All parameters are configurable via `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `VIDEO_MAX_DURATION_SECONDS` | 600 | Reject videos longer than this |
| `VIDEO_MAX_FRAMES` | 50 | Maximum frames sent to vision API |
| `VIDEO_FRAME_INTERVAL_SECONDS` | 5.0 | Uniform sampling interval |
| `VIDEO_SCENE_CHANGE_THRESHOLD` | 0.3 | FFmpeg scene filter threshold |
| `VIDEO_FRAME_WIDTH` | 1280 | Resize frames to this width |
| `VIDEO_PROCESSING_TIMEOUT_SECONDS` | 300 | Subprocess timeout |

---

## Timestamp Preservation

Each extracted frame carries its presentation timestamp in seconds. These timestamps are preserved in `FrameObservation.timestamp_seconds` and flow through to `MediaEvidence`.

```json
{
  "frame_observations": [
    {
      "timestamp_seconds": 0.0,
      "frame_index": 0,
      "observation": { ... }
    },
    {
      "timestamp_seconds": 5.0,
      "frame_index": 1,
      "observation": { ... }
    }
  ]
}
```

---

## Silent Video Handling

If `has_audio=False` (from FFprobe metadata stored during upload):
- Audio extraction is skipped.
- Transcription is skipped.
- Audio understanding is skipped.
- No errors are recorded for the absence of audio.
- `MediaEvidence.transcription` and `MediaEvidence.audio_observation` are `null`.

---

## Partial Failure Handling

If video analysis succeeds but transcription fails:
- `video_observation` is preserved in `MediaEvidence`.
- The transcription error is recorded in `processing_errors`.
- `processing_status` is set to `"partial"`.
- The successful visual evidence is never discarded.

---

## Temporary File Cleanup

All temporary files (extracted frames and audio WAV) are cleaned up in `finally` blocks:
- `cleanup_frames(frames)` — deletes all frame JPEG files
- `cleanup_audio(audio_path)` — deletes the extracted WAV file

Cleanup happens even if the provider call fails.

---

## Evidence Structure

```json
{
  "collection_id": "...",
  "collection_type": "video",
  "video_observation": {
    "media_id": "...",
    "overall_description": "A 30-second product demo showing a red sneaker",
    "key_events": ["product shown at 0s", "close-up at 10s", "brand logo at 25s"],
    "detected_activities": ["rotating product display"],
    "scene_transitions": ["cut at 10s", "fade at 25s"],
    "has_audio": true,
    "audio_description": "Upbeat background music with no speech",
    "frames_analysed": 6,
    "total_duration_seconds": 30.0,
    "provider": "gemini",
    "model_version": "gemini-2.0-flash"
  },
  "transcription": null,
  "audio_observation": {
    "has_speech": false,
    "has_music": true,
    "music_genre": "pop",
    "emotional_tone": "upbeat",
    "general_summary": "Upbeat pop music throughout"
  },
  "processing_status": "complete",
  "has_visual_evidence": true,
  "has_audio_evidence": true,
  "has_transcription": false
}
```

---

## Limitations

- Gemini's internal video sampling rate is approximately 1 fps. Fast-moving content between frames may be missed.
- Large video files (>50 MB) will have significant upload latency to Gemini servers.
- Maximum video duration is 600 seconds (10 minutes) by default. Longer videos are rejected with a clear error.
- The Gemini File API deletes uploaded files after processing. Files are not retained on Google servers.
- Frame extraction requires FFmpeg to be installed and configured via `FFMPEG_PATH`.
