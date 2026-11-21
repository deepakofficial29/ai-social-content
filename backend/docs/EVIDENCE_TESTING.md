# Evidence Testing

Run backend tests with:

```powershell
.\\.venv\\Scripts\\python.exe -m pytest -q
```

Run the Phase 3 test subset with:

```powershell
.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_phase3_evidence.py
```

Tests use deterministic mock Phase 2 structures and the isolated SQLite test database.  Automated tests do not call paid external AI providers.

Reviewed areas include normalization, provenance, duplicate relationships, complementary evidence, contradictions, quality, grounded summaries, persistence/versioning, missing packages, API routes, and review interface delivery.
