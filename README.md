# ITC AI Agent

Monorepo for two AI agent systems:

1. **Code Refactor Agent**
2. **Documentation Drafting Agent**

## Repository Structure

- `apps/`
  - `Code refactor agent/refactor-agent-ui` — frontend for Code Refactor Agent
  - `Documentation Drafting agent` — frontend for Documentation Drafting Agent
- `backend/`
  - `Code refactor agent/refactor-agent` — FastAPI + Temporal backend/worker
  - `Documentation Drafting agent/1st AI agent` — README drafting API service
  - `Documentation Drafting agent/simple-agent` — FastAPI + Temporal backend/worker
- `infra/`
  - `Code refactor agent` — Docker/compose for Code Refactor Agent
  - `Documentation Drafting agent` — Docker/compose for Documentation Drafting Agent

## Agent Entry Points

### Code Refactor Agent

- Frontend: `apps/Code refactor agent/refactor-agent-ui`
- Backend: `backend/Code refactor agent/refactor-agent`
- Infra: `infra/Code refactor agent`

### Documentation Drafting Agent

- Frontend: `apps/Documentation Drafting agent`
- Backends:
  - `backend/Documentation Drafting agent/1st AI agent`
  - `backend/Documentation Drafting agent/simple-agent`
- Infra: `infra/Documentation Drafting agent`

## Quick Start

Use each agent's own README for exact commands:

- Code Refactor backend: `backend/Code refactor agent/refactor-agent/README.md`
- Code Refactor infra: `infra/Code refactor agent/README.md`
- Documentation Drafting infra: `infra/Documentation Drafting agent/README.md`

## Docker Guide (Both Agents)

You can run each agent stack in 2 ways:

1. **Docker Compose (recommended)**
2. **Build each Dockerfile manually**

### 1) Docker Compose (recommended)

#### Code Refactor Agent stack

```bash
cd "infra/Code refactor agent"
cp .env.example .env
docker compose up --build -d
```

#### Documentation Drafting Agent stack

```bash
cd "infra/Documentation Drafting agent"
cp .env.example .env
docker compose up --build -d
```

### 2) Build Dockerfiles manually (advanced)

From repository root:

#### Code Refactor Agent images

```bash
docker build -f "infra/Code refactor agent/Dockerfile" -t refactor-api:local .
docker build -f "infra/Code refactor agent/worker.Dockerfile" -t refactor-worker:local .
docker build -f "infra/Code refactor agent/ui.Dockerfile" -t refactor-ui:local .
```

#### Documentation Drafting Agent images

```bash
docker build -f "infra/Documentation Drafting agent/Dockerfile.first-ai" -t doc-first-ai-api:local .
docker build -f "infra/Documentation Drafting agent/Dockerfile.simple-api" -t doc-simple-api:local .
docker build -f "infra/Documentation Drafting agent/Dockerfile.simple-worker" -t doc-simple-worker:local .
docker build -f "infra/Documentation Drafting agent/Dockerfile.ui" -t doc-ui:local .
```

## Ports to Open

If you deploy on a VM/firewall, open these **host ports**.

### Frontend ports (most important)

- **3001** → Code Refactor Agent UI
- **13100** → Documentation Drafting Agent UI

### Backend/API ports

- **8002** → Refactor API
- **18100** → Documentation 1st AI API
- **18101** → Documentation Simple Agent API

### Temporal transport ports

- **7233** → Refactor stack Temporal
- **8233** → Documentation stack Temporal

### Quick URL check

- Refactor UI: `http://localhost:3001`
- Refactor API: `http://localhost:8002/docs`
- Documentation UI: `http://localhost:13100`
- Documentation 1st AI API: `http://localhost:18100/docs`
- Documentation Simple API: `http://localhost:18101/docs`

## Git Hygiene (Push Safety)

The root `.gitignore` excludes generated/runtime/sensitive files, including:

- `**/.env` and `**/.env.*` (except `.env.example`)
- `**/.venv/` and `**/venv/`
- `**/node_modules/`
- `**/__pycache__/`, test/build caches, and logs
