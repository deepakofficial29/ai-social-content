# Generation Testing

Run all backend tests:

```powershell
.\\.venv\\Scripts\\python.exe -m pytest -q
```

Run Phase 4 tests:

```powershell
.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_phase4_generation.py
```

Tests use mocked text providers and isolated SQLite persistence. No paid external AI calls are made by the test suite.

Coverage includes configuration validation, strategy plans, grounded and unsupported claims, quality separation, persistence, provider fallback, and missing package/API behavior.
