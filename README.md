# Architecture Design Agent (Recursive)

An AI Architecture Consultant that iteratively gathers requirements, proposes architecture options, explains trade-offs, generates Mermaid diagrams, and supports continuous updates.

## Key Features
- Recursive requirements intake (user can keep adding requirements forever)
- Targeted clarifying questions (max 5) only when critical information is missing
- Impact analysis of requirement changes
- Patch architecture for LOW + MEDIUM impact changes (preserve continuity)
- Regenerate architecture for HIGH impact changes
- Delta View: what changed, new components, what stayed the same, migration steps
- Mermaid diagrams rendered in the UI

## Run locally

### Backend
```bash
cd backend
uv sync
# .env already exists at repo root; ensure it contains your Gemini/OpenAI key
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
pnpm install
pnpm dev
```

Open UI: http://localhost:5173
Backend: http://localhost:8000

## API
- POST /chat  -> recursive chat endpoint (returns questions or architecture)
- GET /health -> health endpoint

## Notes
- Session store is in-memory for MVP; move to Redis for multi-instance deployments.
- Add streaming later via SSE if desired.
