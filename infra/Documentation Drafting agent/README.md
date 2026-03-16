# Documentation Drafting Agent Infra

Docker setup for:
- `backend/Documentation Drafting agent/1st AI agent` (FastAPI, port 8000)
- `backend/Documentation Drafting agent/simple-agent` API + worker (FastAPI 8001 + Temporal worker)
- `apps/Documentation Drafting agent` frontend (Next.js, port 3000)

## Run

```bash
cd "infra/Documentation Drafting agent"
cp .env.example .env
docker compose up --build
```

## Endpoints

- Frontend: `http://localhost:13000`
- 1st AI API: `http://localhost:18100`
- Simple Agent API: `http://localhost:18101`
- Temporal UI/API transport: `localhost:8233`

## Stop

```bash
docker compose down
```

Use `docker compose down -v` to remove Temporal Postgres volume.
