# API Contract – Multimodal Caption Generator v0.1.0

Base URL: `http://localhost:8000/api/v1`

All responses follow the envelope:
```json
{
  "success": true | false,
  "message": "Human-readable message",
  "data": { ... } | null,
  "error": { "code": "ERROR_CODE", "details": {} } | null
}
```

---

## Health

### GET /health
**Response 200**
```json
{
  "success": true,
  "message": "Service is healthy",
  "data": {
    "status": "healthy",
    "service": "multimodal-caption-generator",
    "version": "0.1.0"
  }
}
```

### GET /ready
**Response 200** – all checks pass  
**Response 503** – one or more checks fail
```json
{
  "success": true,
  "message": "Ready",
  "data": {
    "checks": {
      "database": "ok",
      "storage": "ok"
    }
  }
}
```

---

## Media

### POST /media/upload
**Content-Type:** `multipart/form-data`  
**Field:** `files` (one or more files)

**Response 201**
```json
{
  "success": true,
  "message": "Media uploaded successfully",
  "data": {
    "collection_id": "uuid",
    "media": [
      {
        "media_id": "uuid",
        "filename": "photo.jpg",
        "media_type": "image",
        "file_size": 123456,
        "metadata": {
          "width": 1920,
          "height": 1080,
          "format": "JPEG",
          "mode": "RGB"
        },
        "processing_status": "uploaded",
        "sequence_index": 0
      }
    ]
  }
}
```

Video metadata shape:
```json
{
  "width": 1920, "height": 1080,
  "duration_seconds": 12.5,
  "frame_rate": 29.97,
  "video_codec": "h264",
  "has_audio": true,
  "audio_codec": "aac",
  "file_size": 5000000
}
```

Audio metadata shape:
```json
{
  "duration_seconds": 30.0,
  "codec": "mp3",
  "sample_rate": 44100,
  "channels": 2,
  "file_size": 480000
}
```

### GET /media/{media_id}
**Response 200**
```json
{
  "success": true,
  "message": "Media retrieved",
  "data": {
    "media_id": "uuid",
    "filename": "photo.jpg",
    "media_type": "image",
    "mime_type": "image/jpeg",
    "file_size": 123456,
    "metadata": { ... },
    "collection_id": "uuid",
    "sequence_index": 0,
    "processing_status": "uploaded",
    "created_at": "2024-01-01T00:00:00+00:00"
  }
}
```

### DELETE /media/{media_id}
**Response 200**
```json
{ "success": true, "message": "Media deleted successfully" }
```

---

## Jobs

### GET /jobs/{job_id}
**Response 200**
```json
{
  "success": true,
  "message": "Job retrieved",
  "data": {
    "job_id": "uuid",
    "status": "queued",
    "asset_id": "uuid",
    "collection_id": "uuid",
    "error_message": null,
    "created_at": "2024-01-01T00:00:00+00:00",
    "updated_at": "2024-01-01T00:00:00+00:00"
  }
}
```

Job statuses: `queued` | `processing` | `completed` | `failed`

---

## Evidence (Phase 3)

### GET /evidence/{collection_id}
Returns the persisted unified evidence package.  Reading does not rerun AI providers.

### GET /evidence/{collection_id}/items
Returns atomic evidence items.

### GET /evidence/{collection_id}/provenance
Returns evidence items with their complete source references.

### GET /evidence/{collection_id}/relationships
Returns cross-modal, duplicate, and overlap relationships.

### GET /evidence/{collection_id}/conflicts
Returns potential contradiction records.  Conflicts remain unresolved and do not select a winner.

### GET /evidence/{collection_id}/quality
Returns qualitative evidence quality assessment.

### GET /evidence/{collection_id}/summary
Returns the grounded content summary and supporting evidence IDs.

### POST /evidence/{collection_id}/rebuild
Explicitly reruns Phase 2 understanding and replaces the evidence package, incrementing its version.

### GET /evidence/review/{collection_id}
Returns the temporary HTML evidence review interface.

---

## Generation (Phase 4)

- `POST /generation/config/{media_id}` saves generation preferences.
- `POST /generation/config` accepts a request whose `media_id` identifies the collection.
- `GET /generation/config/{media_id}` retrieves preferences.
- `POST /generation/strategy/{media_id}` returns a grounded generation plan.
- `POST /generation/captions/{media_id}` creates and persists caption variants.
- `GET /generation/{generation_id}` retrieves a complete generation request.
- `GET /generation/{generation_id}/variants` retrieves variants.
- `GET /generation/{generation_id}/quality` retrieves quality feedback.
- `GET /generation/{generation_id}/grounding` retrieves grounding results.
- `POST /generation/{generation_id}/regenerate` creates a new generation record.

Generation requires an existing collection and usable evidence package. Provider failures return conservative fallback variants with warnings and separate grounding status where applicable.

---

## Error Codes

| HTTP | Code | Cause |
|---|---|---|
| 413 | `FILE_TOO_LARGE` | File exceeds `MAX_UPLOAD_SIZE_MB` |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | Extension or MIME type not allowed |
| 422 | `EMPTY_FILE` | Zero-byte file uploaded |
| 422 | `CORRUPTED_MEDIA` | File content fails integrity check |
| 422 | `VALIDATION_ERROR` | General validation failure |
| 404 | `MEDIA_NOT_FOUND` | `media_id` does not exist |
| 404 | `JOB_NOT_FOUND` | `job_id` does not exist |
| 404 | `EVIDENCE_NOT_FOUND` | Evidence package or requested assessment is unavailable |
| 500 | `STORAGE_ERROR` | Filesystem read/write failure |
| 500 | `FFPROBE_ERROR` | FFprobe not found or returned an error |
| 500 | `DATABASE_ERROR` | Database operation failed |
| 500 | `INTERNAL_ERROR` | Unexpected server error |
| 503 | `SERVICE_UNAVAILABLE` | Readiness check failed |
