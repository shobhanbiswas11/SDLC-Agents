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

## Git Hygiene (Push Safety)

The root `.gitignore` excludes generated/runtime/sensitive files, including:

- `**/.env` and `**/.env.*` (except `.env.example`)
- `**/.venv/` and `**/venv/`
- `**/node_modules/`
- `**/__pycache__/`, test/build caches, and logs
