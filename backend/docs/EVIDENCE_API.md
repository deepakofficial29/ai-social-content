# Evidence API

All evidence endpoints use `/api/v1/evidence/{collection_id}`.

- `GET /api/v1/evidence/{collection_id}`: complete package.
- `GET /api/v1/evidence/{collection_id}/items`: evidence items.
- `GET /api/v1/evidence/{collection_id}/provenance`: items with source provenance.
- `GET /api/v1/evidence/{collection_id}/relationships`: fusion relationships.
- `GET /api/v1/evidence/{collection_id}/conflicts`: contradiction records.
- `GET /api/v1/evidence/{collection_id}/quality`: quality assessment.
- `GET /api/v1/evidence/{collection_id}/summary`: grounded content summary.
- `POST /api/v1/evidence/{collection_id}/rebuild`: explicit rebuild.
- `GET /api/v1/evidence/review/{collection_id}`: temporary review interface.

Responses use the standard `APIResponse` envelope.  Missing collections return `MEDIA_NOT_FOUND`; missing packages return `EVIDENCE_NOT_FOUND`.
