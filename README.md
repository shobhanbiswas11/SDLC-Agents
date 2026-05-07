# Coding Standards Enforcer Agent

Multi-language AI agent that detects coding-standard violations and produces
AI-generated fixes for Python, C++, Java, JavaScript, TypeScript, Go, and Rust.

This project follows the GENAICOE-Agents structure: a FastAPI backend with
agent + core split, and a Next.js (App Router) frontend with Redux and
TypeScript.

## Project Structure

```
CODING STANDARDS ENFORCER/
├── backend/
│   ├── agents/
│   │   └── coding_standards_enforcer/
│   │       ├── __init__.py            # FastAPI router
│   │       ├── agent.py               # analyze / fix / scan orchestration
│   │       ├── schemas.py             # Pydantic request/response models
│   │       ├── initialization.py      # startup hooks
│   │       ├── parsers/               # language detection
│   │       ├── prompts/               # LangChain prompt templates + standards data
│   │       ├── linters/               # flake8 + autoflake/isort/autopep8/black
│   │       └── repo/                  # git clone + branch listing
│   ├── core/
│   │   ├── config/                    # Settings (Pydantic)
│   │   ├── providers/                 # AzureOpenAIProvider (AAD or API key)
│   │   ├── services/                  # LLMService singleton
│   │   ├── schemas/                   # Cross-agent schemas (placeholder)
│   │   ├── exceptions.py
│   │   ├── logging.py
│   │   ├── config.py                  # Legacy compatibility shim
│   │   └── DATABASE_USAGE.md
│   ├── data/                          # Runtime data
│   ├── prompts/                       # (reserved for shared prompts)
│   ├── main.py                        # FastAPI entry point
│   ├── core_router.py                 # / and /health
│   ├── dependencies.py                # FastAPI DI helpers
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── run.py                         # `python run.py` shortcut
│   └── .env / .env.example
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── coding-standards-enforcer/page.tsx
│       │   ├── agents/page.tsx        # agent index
│       │   ├── globals.css            # ports App.css + index.css verbatim
│       │   ├── layout.tsx
│       │   ├── page.tsx               # redirects to /coding-standards-enforcer
│       │   └── providers.tsx          # Redux Provider
│       ├── components/
│       │   ├── agents/CodingStandardsEnforcer/
│       │   │   ├── LiveEditor.tsx
│       │   │   ├── FileTree.tsx
│       │   │   ├── icons.tsx
│       │   │   ├── sampleCode.ts
│       │   │   └── index.ts
│       │   └── ui/                    # (placeholder for shared UI primitives)
│       ├── services/api/
│       │   ├── api.ts                 # axios client
│       │   ├── codingStandardsService.ts
│       │   └── index.ts
│       ├── store/
│       │   ├── index.ts               # configureStore
│       │   └── slices/
│       │       ├── codingStandardsSlice.ts
│       │       └── uiSlice.ts
│       ├── types/
│       │   ├── codingStandards.ts
│       │   └── index.ts
│       └── hooks/index.ts             # typed useAppDispatch / useAppSelector
└── Infra/
    └── coding-standards-enforcer/
        ├── Dockerfile.backend
        ├── Dockerfile.frontend
        └── docker-compose.yml
```

## Running locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in Azure credentials
python run.py         # → uvicorn on http://localhost:8000
```

OpenAPI docs at http://localhost:8000/docs.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                  # → http://localhost:3000
```

## Docker

```bash
cd Infra/coding-standards-enforcer
docker compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:3000

## Backend API Surface

All routes are prefixed with `/api/coding_standards_enforcer/`.

| Method | Path                  | Purpose |
|--------|-----------------------|---------|
| GET    | `/health`             | liveness check |
| GET    | `/languages`          | supported languages with standards/categories |
| POST   | `/repo-files`         | clone repo + return file tree for the editor |
| POST   | `/repo-branches`      | list remote branches |
| POST   | `/analyze`            | LLM analysis of a code blob |
| POST   | `/fix`                | LLM fix-all + diff |
| POST   | `/scan`               | streaming repo scan (NDJSON) |
| POST   | `/apply-linters`      | autoflake → isort → autopep8 → black + re-scan |
| GET    | `/download-fixed`     | zip the corrected repo |
| GET    | `/corrected-files`    | return all source files as JSON |

## Configuration

`backend/.env`:

```
AZURE_TENANT_ID=…
AZURE_CLIENT_ID=…
AZURE_CLIENT_SECRET=…
AZURE_OPENAI_ENDPOINT=https://openaidev-westus.openai.azure.com/
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_CHATGPT_DEPLOYMENT=gpt-4o
```

`frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Notes

- The `/scan` endpoint mixes a deterministic Python pipeline (flake8 + parallel
  per-snippet AI fixes via `ThreadPoolExecutor`) with a per-file LLM agent for
  every other supported language.
- `/apply-linters` is Python-only (it runs flake8 at the end).
- All LLM access flows through `core.services.llm_service.get_llm()`, which is
  cached and refreshes its Azure AD token 5 minutes before expiry.
