# Evidence Schema

`UnifiedMediaEvidence` is the Phase 3 package:

- `package_id`, `schema_version`, collection and asset references.
- `evidence_items`: atomic evidence with category, observation type, value, source, confidence, uncertainty, and supporting IDs.
- `cross_modal_relationships`: agreement, complementary, duplicate, overlap, and other relationships.
- `conflicts`: unresolved or acknowledged potential contradictions.
- `quality`: qualitative source, completeness, timestamp, provenance, agreement, and processing dimensions.
- `content_summary`: grounded observations and interpretations with evidence IDs.

Evidence sources preserve media ID, collection ID, media type, modality, image index, video/frame position, audio segment, provider, model, and optional processing job.

No numerical quality score is used.  Status labels are designed for human review and explicitly remain conservative.
