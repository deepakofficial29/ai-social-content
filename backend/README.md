# Multimodal AI Caption Generator — Backend

## Project Description

A production-oriented backend for a Multimodal AI Caption Generation Platform.
Phase 1 implements the foundation and media-intake pipeline.
Future phases will add computer vision, audio transcription, multimodal reasoning, and AI caption generation.

**Core principle: Understand first → Preserve evidence → Understand user intent → Generate → Verify.**

---

## Architecture Overview

```
FastAPI app
  │
  ├── API layer        – thin routes, no business logic
  ├── Pipeline layer   – orchestrates the processing stages
  ├── Service layer    – validation, metadata extraction, media management
  ├── Storage layer    – abstracted file storage (local now, S3-ready)
  └── Database layer   – SQLAlchemy 2.x models + repository pattern
```

---

## Folder Structure

```
backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── routes/
│   │   │   ├── health.py
│   │   │   ├── media.py
│   │   │   └── jobs.py
│   │   └── dependencies.py
│   ├── core/
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   ├── logging.py
│   │   └── security.py
│   ├── schemas/
│   │   ├── common.py
│   │   ├── media.py
│   │   └── job.py
│   ├── services/
│   │   ├── media_service.py
│   │   ├── validation_service.py
│   │   └── metadata_service.py
│   ├── pipelines/
│   │   └── media_pipeline.py
│   ├── storage/
│   │   ├── base.py
│   │   └── local_storage.py
│   ├── database/
│   │   ├── connection.py
│   │   ├── models.py
│   │   └── repository.py
│   └── utils/
│       ├── file_utils.py
│       └── media_utils.py
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   ├── test_media_upload.py
│   ├── test_validation.py
│   ├── test_metadata.py
│   └── test_ffprobe.py
├── storage/
│   └── .gitkeep
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Prerequisites

- Python 3.10+ (developed and tested on 3.10.11; compatible with 3.11+)
- FFmpeg with FFprobe — see installation below
- Git

---

## Python Environment Setup

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Environment Configuration

Copy the example file and edit it:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Then open `.env` and set values for your machine. The `.env` file is excluded from
Git via `.gitignore` and must never be committed.

### Key variables

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | `development`, `staging`, or `production` |
| `DEBUG` | `true` | Verbose logging and detailed error messages |
| `MAX_UPLOAD_SIZE_MB` | `100` | Maximum file size per upload |
| `STORAGE_DIR` | `storage` | Directory for uploaded files (outside web root) |
| `DATABASE_URL` | `sqlite:///./caption_generator.db` | SQLAlchemy connection string |
| `FFMPEG_PATH` | `ffmpeg` | Path to ffmpeg binary |
| `FFPROBE_PATH` | `ffprobe` | Path to ffprobe binary |
| `CORS_ORIGINS` | `["http://localhost:3000","http://localhost:5173"]` | Allowed CORS origins |

If FFmpeg is on your system PATH, the defaults (`ffmpeg` / `ffprobe`) work without
any changes. If it is installed to a custom location, set the full absolute paths:

```
FFMPEG_PATH=C:\path\to\ffmpeg.exe
FFPROBE_PATH=C:\path\to\ffprobe.exe
```

---

## FFmpeg Installation

FFmpeg is required for video and audio metadata extraction. Without it, video and
audio uploads will fail with a `FFPROBE_ERROR`. The readiness endpoint
(`GET /api/v1/ready`) reports FFprobe availability on every request.

### Windows

**Option A — Add to PATH (recommended for development)**

1. Download a full static build from https://www.gyan.dev/ffmpeg/builds/
   (choose `ffmpeg-release-full.7z`).
2. Extract to a permanent location, e.g. `C:\ffmpeg\`.
3. Add `C:\ffmpeg\bin` to your system PATH:
   - Open *System Properties → Advanced → Environment Variables*.
   - Edit the `Path` variable and add the `bin` directory.
4. Open a new terminal and verify: `ffprobe -version`

**Option B — Configure paths in `.env` (no PATH change needed)**

1. Download and extract as above.
2. Set the full paths in `.env`:
   ```
   FFMPEG_PATH=C:\ffmpeg\bin\ffmpeg.exe
   FFPROBE_PATH=C:\ffmpeg\bin\ffprobe.exe
   ```

### macOS

```bash
brew install ffmpeg
```

### Ubuntu / Debian

```bash
sudo apt update && sudo apt install ffmpeg
```

### Verify installation

```bash
ffprobe -version
# or, if using .env paths:
python -c "from app.core.config import get_settings; import subprocess; s=get_settings(); print(subprocess.run([s.FFPROBE_PATH,'-version'],capture_output=True).returncode)"
```

---

## Database Setup

Tables are created automatically on first startup. No migration tool is required
for Phase 1.

To switch to PostgreSQL for production:

```
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/caption_db
pip install psycopg2-binary
```

---

## Running the Backend

```bash
cd backend
# Activate the virtual environment first
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc
- Readiness check: http://localhost:8000/api/v1/ready

---

## Supported Media Formats

| Type | Extensions | Notes |
|---|---|---|
| Image | jpg, jpeg, png, webp | Validated with Pillow |
| Video | mp4, mov, avi, mkv, webm | Inspected with FFprobe |
| Audio | wav, mp3, m4a, aac | Inspected with FFprobe |

Configurable via `ALLOWED_IMAGE_TYPES`, `ALLOWED_VIDEO_TYPES`, `ALLOWED_AUDIO_TYPES`
in `.env`.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Liveness check |
| `GET` | `/api/v1/ready` | Readiness check (database, storage, ffprobe) |
| `POST` | `/api/v1/media/upload` | Upload one or more media files |
| `GET` | `/api/v1/media/{media_id}` | Retrieve media metadata |
| `DELETE` | `/api/v1/media/{media_id}` | Delete media asset and file |
| `GET` | `/api/v1/jobs/{job_id}` | Get processing job status |

---

## Example Upload Requests

### Single image
```bash
curl -X POST http://localhost:8000/api/v1/media/upload \
  -F "files=@photo.jpg"
```

### Multiple images (carousel — order is preserved)
```bash
curl -X POST http://localhost:8000/api/v1/media/upload \
  -F "files=@slide1.png" \
  -F "files=@slide2.png" \
  -F "files=@slide3.png"
```

### Video
```bash
curl -X POST http://localhost:8000/api/v1/media/upload \
  -F "files=@video.mp4"
```

### Audio
```bash
curl -X POST http://localhost:8000/api/v1/media/upload \
  -F "files=@recording.mp3"
```

---

## Running Tests

```bash
cd backend
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux

python -m pytest tests/ -v
```

Tests use an isolated SQLite database and a temporary storage directory.
No external services or AI APIs are required.

FFprobe-dependent tests (`test_ffprobe.py`) are skipped automatically when
FFprobe is not reachable via the configured `FFPROBE_PATH`. With FFprobe
configured, all 42 tests run and pass.

### Verified test results (Phase 1.6)

```
42 passed, 0 skipped, 0 failed
Python 3.10.11 | FFmpeg 9.0.2
```

---

## Troubleshooting

### `FFPROBE_ERROR` on video/audio upload

The readiness endpoint reports the exact problem:

```bash
curl http://localhost:8000/api/v1/ready
```

If `ffprobe` shows `unavailable`, either:
- FFmpeg is not installed, or
- `FFPROBE_PATH` in `.env` points to the wrong location.

### Tests still skipped after configuring FFprobe

`ffprobe_available()` in `conftest.py` reads `FFPROBE_PATH` from Settings, which
reads from `.env`. Ensure `.env` exists in the `backend/` directory and contains
the correct `FFPROBE_PATH` value.

### `PermissionError` on test database cleanup (Windows)

This is a known Windows file-locking behaviour. The test database file
(`test_caption.db`) is cleaned up on the next test run. It does not affect test
correctness.

### SQLite `check_same_thread` warning

Expected in development. Use `DATABASE_URL` with PostgreSQL in production.

---

## Current Limitations

- No authentication or authorisation (planned for Phase 2).
- No asynchronous job processing (Celery/Redis planned for Phase 3).
- Video and audio metadata extraction requires FFprobe.
- No AI vision, transcription, or caption generation (Phase 2+).
- Single-process only; not horizontally scalable yet.
- Storage is local filesystem only; S3 adapter is planned.
- Python 3.10.11 is the tested runtime; 3.11+ is compatible but untested in CI.

---

## Planned Future Integrations

| Phase | Feature |
|---|---|
| 2 | Authentication (JWT / API keys) |
| 2 | Computer vision — image understanding |
| 2 | Audio transcription (Whisper) |
| 3 | Multimodal reasoning and caption generation |
| 3 | Caption validation and quality evaluation |
| 3 | Async job queue (Celery + Redis) |
| 4 | S3 / GCS storage adapter |
| 4 | PostgreSQL production deployment |
| 4 | Horizontal scaling and containerisation |
