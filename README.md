# ITC AI Agent

Monorepo for AI agent applications and services.

## Repository Structure

- `apps/`
  - `Code refactor agent/refactor-agent-ui` — Next.js frontend
  - `Documentation Drafting agent/` — reserved for documentation agent app
- `backend/`
  - `Code refactor agent/refactor-agent` — FastAPI + Temporal backend and worker
  - `Documentation Drafting agent/` — reserved for documentation agent backend
- `infra/`
  - `Code refactor agent/` — infrastructure assets (Docker, compose, deployment)

## Quick Start

### Backend

```bash
cd "backend/Code refactor agent/refactor-agent"
pip install -r requirements.txt
python worker.py
python api.py
```

### Frontend

```bash
cd "apps/Code refactor agent/refactor-agent-ui"
pnpm install
pnpm run dev
```

## GitHub Readiness Notes

This repository intentionally ignores generated/runtime artifacts and secrets via the root `.gitignore`, including:

- Python virtual environments and caches
- Node modules and Next.js build output
- Local `.env` files
- Refactor-agent temporary clone/staging folders

Before pushing, ensure your infra files are complete if you plan to deploy from this repo:

- `infra/Code refactor agent/Dockerfile`
- `infra/Code refactor agent/docker-compose.yml`

## Refactor Agent Containers

The refactor agent now has a complete container setup in:

- `infra/Code refactor agent/README.md`

It includes:

- One compose stack (`docker-compose.yml`)
- Dedicated Dockerfiles for API, worker, and UI
- `.env.example` template for required Azure settings
