# Security and Operations

## Security boundaries

- Provider API keys remain in backend environment variables.
- Frontend bundles contain no secrets.
- Upload validation checks extension, MIME, media signature, integrity, dimensions and duration limits.
- Uploaded storage keys are server-generated and use safe joins.
- Production CORS origins are explicit and `*` is rejected.
- Internal errors are not exposed in production.
- Logs use structured JSON and correlation IDs. Provider keys and prompts are not logged.

## Authentication

Authentication and authorization are not implemented. Do not expose this deployment to an untrusted network until access control is added.

## Backups

Persist and back up:

- `backend_data/caption_generator.db`
- `media_data`
- Environment configuration outside source control

Test restoration before relying on a backup.
