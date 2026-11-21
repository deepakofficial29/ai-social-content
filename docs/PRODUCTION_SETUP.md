# Production Setup

This repository supports a provider-neutral container deployment for local controlled operation.

## Requirements

- Docker Engine and Docker Compose
- Persistent volume support
- FFmpeg/FFprobe, supplied inside the backend image
- Gemini and/or OpenAI API keys if provider processing is enabled

## Configuration

Copy `.env.example` to `.env`, set provider keys, and choose the frontend port.

The backend accepts environment variables documented in `backend/.env.example`.
Set `APP_ENV=production`, `DEBUG=false`, explicit `CORS_ORIGINS`, a persistent database URL and persistent `STORAGE_DIR`.

The compose deployment persists SQLite and uploaded media in named volumes. SQLite is suitable for controlled single-instance deployment, but it is not horizontally scalable. Use a managed database and shared object storage before multi-instance operation.
