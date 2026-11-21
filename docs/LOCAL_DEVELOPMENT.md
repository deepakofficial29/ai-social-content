# Local Development

Start the backend:

```powershell
cd backend
.\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --reload
```

Start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Frontend default: `http://localhost:5173`

Backend default: `http://localhost:8000`

Copy `frontend/.env.example` to `frontend/.env.local` to change the API base URL.
