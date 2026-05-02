# Documentation Drafting Agent Infra

Docker setup for:
- `backend/Documentation Drafting agent/1st AI agent` (FastAPI, port 8000)
- `backend/Documentation Drafting agent/simple-agent` API + worker (FastAPI 8001 + Temporal worker)
- `apps/Documentation Drafting agent` frontend (Next.js, port 3000)

## Run

```bash
cd "infra/Documentation Drafting agent"
cp .env.example .env
# fill Azure + Temporal Cloud values in .env
docker compose up --build
```

Required Temporal values in `.env`:

- `TEMPORAL_ADDRESS=your-namespace.tmprl.cloud:7233`
- `TEMPORAL_NAMESPACE=default` (or your namespace)
- `TEMPORAL_API_KEY=<your-temporal-cloud-api-key>`
- `TEMPORAL_TLS=true`

## Endpoints

- Frontend: `http://localhost:13100`
- 1st AI API: `http://localhost:18100`
- Simple Agent API: `http://localhost:18101`

## Stop

```bash
docker compose down
```
