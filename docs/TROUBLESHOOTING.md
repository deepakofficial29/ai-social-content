# Troubleshooting

## Backend unavailable

- Check `docker compose ps`.
- Inspect `docker compose logs backend`.
- Confirm database and storage paths are writable.
- Open `http://localhost:8080/api/v1/health`.
- Open `/api/v1/ready`.

## Provider unavailable

Readiness reports whether configured provider credentials exist without making expensive AI calls. Set the matching Gemini/OpenAI environment variable and restart the backend.

## Upload rejected

The backend returns a structured error for:

- unsupported extension or MIME
- empty or corrupted media
- upload/request size
- image dimension/pixel limits
- video/audio duration limits
- mixed media types

## FFmpeg unavailable

The Docker backend installs FFmpeg. Native deployments must place `ffmpeg` and `ffprobe` on `PATH` or set full paths.
