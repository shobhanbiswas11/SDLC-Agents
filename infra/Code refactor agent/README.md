# Refactor Agent Infra

This folder contains container setup for the **Code Refactor Agent** only.

## Files

- `docker-compose.yml` → orchestrates all services
- `Dockerfile` → backend API image
- `worker.Dockerfile` → Temporal worker image
- `ui.Dockerfile` → Next.js frontend image
- `.env.example` → environment template for Azure OpenAI values

## Why multiple Dockerfiles?

Each service has different runtime needs:

- API: Python + FastAPI + exposed port `8002`
- Worker: Python background process (no public port)
- UI: Node.js + Next.js + exposed port `3001`

`docker-compose` can build each service from a different Dockerfile.

## Run with Temporal Cloud

From this folder:

```bash
cp .env.example .env
# fill Azure + Temporal Cloud values in .env

docker compose -f docker-compose.yml up --build
```

Services:

- UI: `http://localhost:3001`
- API: `http://localhost:8002`

Required Temporal values in `.env`:

- `TEMPORAL_ADDRESS=your-namespace.tmprl.cloud:7233`
- `TEMPORAL_NAMESPACE=default` (or your namespace)
- `TEMPORAL_API_KEY=<your-temporal-cloud-api-key>`
- `TEMPORAL_TLS=true`

If ports are already in use on your machine, set these in `.env` before running:

- `API_HOST_PORT` (default `8002`)
- `UI_HOST_PORT` (default `3001`)

## Stop

```bash
docker compose -f docker-compose.yml down
```

## Notes

- API and worker mount repo root (`../../`) to `/workspace` so local-path refactoring can access your files.
- `NEXT_PUBLIC_API_BASE_URL` is set to `http://localhost:8002` so browser requests hit your host-exposed API port.
