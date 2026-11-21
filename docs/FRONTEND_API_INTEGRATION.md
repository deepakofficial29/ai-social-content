# Frontend API Integration

The frontend reads `VITE_API_BASE_URL`, defaulting to `http://localhost:8000/api/v1`.

Integrated APIs cover media upload/listing, understanding, evidence retrieval/rebuild, generation configuration/strategy/captions/regeneration, and generation history.

No API keys are stored in the frontend. Uploads use multipart form data. Backend response messages and timeout failures are shown in the UI.

Frontend support endpoints added to the backend:

- `GET /api/v1/media/collections`
- `GET /api/v1/generation`
