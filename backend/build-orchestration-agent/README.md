# Build Orchestration Agent

Docker-first FastAPI, Celery, Redis, and PostgreSQL implementation of the orchestrator/sub-agent system described in `AGENTS.md`.

## Run

```bash
docker compose up --build
```

The app runs at:

- Frontend: `http://localhost:5173`
- API: `http://localhost:8000/api`
- Health: `http://localhost:8000/api/health`

## Migrations

```bash
docker compose run --rm fastapi alembic upgrade head
```

## Tests

```bash
docker compose run --rm fastapi pytest
```

## Configuration

All runtime configuration is read from environment variables. Copy `.env.example` to `.env`, then fill Azure OpenAI or OpenRouter credentials when external model reasoning is needed.
