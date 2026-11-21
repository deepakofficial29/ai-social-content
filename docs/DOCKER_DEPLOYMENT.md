# Docker Deployment

Build and run:

```powershell
docker compose up --build
```

Open `http://localhost:8080`.

Override the frontend port:

```powershell
$env:FRONTEND_PORT="8090"
docker compose up --build
```

Stop without deleting persistent volumes:

```powershell
docker compose down
```

Delete uploaded media and the local SQLite database only with explicit approval:

```powershell
docker compose down -v
```

The frontend container serves the SPA and proxies `/api/` to the backend. Nested route refreshes are handled by the nginx fallback.
