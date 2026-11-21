# Evidence Pipeline

Processing sequence:

1. Phase 2 understanding pipeline.
2. Image, carousel, frame, transcription, OCR, and audio normalization.
3. Conservative duplicate relationship detection.
4. Cross-modal relationship detection.
5. Potential contradiction detection.
6. Qualitative evidence assessment.
7. Grounded summary construction.
8. Package persistence.

Persisted packages are returned directly by retrieval APIs.  Provider AI calls are not repeated for reads.  The rebuild endpoint explicitly reruns understanding and replaces the package while incrementing its package version.

Partial provider results remain traceable.  Processing errors are retained as warnings and influence quality status.
