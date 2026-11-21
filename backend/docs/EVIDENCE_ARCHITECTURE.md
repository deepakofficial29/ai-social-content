# Evidence Architecture

Phase 3 converts Phase 2 provider results into a traceable evidence package.  Provider calls remain in the understanding pipeline; evidence modules do not call AI providers.

## Modules

- `app/schemas/unified_evidence.py`: evidence package and data structures.
- `app/evidence/normalizers.py`: converts Phase 2 observations to atomic evidence items.
- `app/evidence/fusion.py`: duplicate relationships, cross-modal relationships, and contradiction records.
- `app/evidence/quality.py`: qualitative quality assessment and grounded summary.
- `app/evidence/pipeline.py`: orchestration and persistence entry point.
- `app/database/models.py`: evidence package and child-table persistence.
- `app/api/routes/understanding.py`: package retrieval, review, and rebuild endpoints.

Direct observations are separate from interpretations and inferences.  Contradictions are records, never winners chosen by confidence.
