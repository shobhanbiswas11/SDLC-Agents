We'll build all the SDLC agents here.

## Docker Setup

### Development

1. Copy `.env.example` to `.env` and fill Azure credentials.
2. Run:

```bash
docker compose up --build
```

Services:

- Backend: `http://localhost:8000`
- Frontend (Vite dev): `http://localhost:5173`

### Production

Run production profile (no backend autoreload, frontend served by nginx):

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

Services:

- Backend: `http://localhost:8000`
- Frontend (nginx): `http://localhost:8080`

Environment keys are documented in `.env.example`, including `VITE_API_BASE_URL` used by the frontend build.
