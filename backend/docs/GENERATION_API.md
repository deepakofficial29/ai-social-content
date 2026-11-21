# Generation API

Base: `/api/v1/generation`

- `POST /config/{media_id}` — save configuration for a collection.
- `POST /config` — save configuration containing `media_id`.
- `GET /config/{media_id}` — retrieve configuration.
- `POST /strategy/{media_id}` — build a generation strategy.
- `POST /captions/{media_id}` — generate and persist variants.
- `GET /{generation_id}` — retrieve generation history.
- `GET /{generation_id}/variants` — retrieve variants.
- `GET /{generation_id}/quality` — retrieve quality feedback.
- `GET /{generation_id}/grounding` — retrieve grounding results.
- `POST /{generation_id}/regenerate` — append a new generation request.

Generation is refused when the collection or evidence package is missing or contains no usable evidence.

All responses use the standard `APIResponse` envelope.
