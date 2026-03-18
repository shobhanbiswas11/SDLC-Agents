# Dependency Resolver Agent

> Analyses repositories, resolves dependencies recursively, detects version conflicts, and generates AI-explained reports.

**Ecosystems (MVP):** Python (PyPI) · Node.js (npm)

---

## Quick Start

### Backend (Python)

```bash
cd backend/dependency-resolver-agent

# Create virtualenv & install deps (requires uv)
uv sync

# Copy env template
cp .env.example .env    # fill in Azure OpenAI creds if you want AI features

# Run the API server
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend (React)

```bash
cd apps/dependency-resolver-agent

npm install
npm run dev   # → http://localhost:5174
```

### CLI

```bash
cd backend/dependency-resolver-agent

uv run resolver scan https://github.com/fastapi/fastapi
```

### Docker Compose

```bash
cd Infra/dependency-resolver-agent

# Make sure backend/.env exists
docker compose up --build
# Backend → http://localhost:8001
# Frontend → http://localhost:5174
```

---

## API

| Method | Path       | Body                                        | Response                                           |
|--------|------------|---------------------------------------------|----------------------------------------------------|
| `GET`  | `/health`  | —                                           | `{ "status": "ok", "service": "..." }`             |
| `POST` | `/resolve` | `{ "repo_url": "<url or path>" }`           | `{ "dependencies": [], "conflicts": [], "graph": {} }` |

---

## Project Structure

```
SDLC-Agents-…-dependency-resolver-agent/
├── apps/dependency-resolver-agent/     # React frontend (Vite)
├── backend/dependency-resolver-agent/  # Python backend (FastAPI)
│   └── app/
│       ├── main.py                     # FastAPI server
│       ├── config.py                   # Pydantic settings
│       ├── cli/cli.py                  # Typer CLI
│       ├── services/repo_service.py    # Git clone + ecosystem detection
│       ├── parser/                     # Python & Node parsers
│       ├── metadata/                   # PyPI & npm registry clients
│       ├── resolver/                   # DFS resolver, graph builder, constraint solver
│       ├── analysis/                   # Conflict detector, AI explainer, upgrade suggester
│       ├── reports/                    # Report generator
│       ├── llm/                        # Azure OpenAI + LangChain
│       └── utils/                      # HTTP client, version utils, cache
├── Infra/dependency-resolver-agent/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
├── prd.md
└── README.md
```

---

## Environment Variables

| Variable                              | Required | Description                        |
|---------------------------------------|----------|------------------------------------|
| `AZURE_TENANT_ID`                     | No       | Azure AD tenant                    |
| `AZURE_CLIENT_ID`                     | No       | Service principal client ID        |
| `AZURE_CLIENT_SECRET`                 | No       | Service principal secret           |
| `AZURE_OPENAI_ENDPOINT`              | No       | Azure OpenAI endpoint URL          |
| `AZURE_OPENAI_API_VERSION`           | No       | API version (default: `2024-12-01-preview`) |
| `AZURE_OPENAI_CHATGPT_DEPLOYMENT`   | No       | Chat model deployment name         |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`  | No       | Embedding deployment name          |

> AI features (conflict explanations & upgrade suggestions) degrade gracefully to rule-based fallbacks when Azure OpenAI is not configured.

---

## Tech Stack

| Layer          | Technology                                                                 |
|----------------|---------------------------------------------------------------------------|
| Backend        | Python 3.14, FastAPI, uv                                                  |
| Backend libs   | httpx, networkx, packaging, pydantic, typer, rich, diskcache, langchain   |
| Frontend       | React, Vite, JavaScript                                                   |
| Infrastructure | Docker, Docker Compose                                                    |

---

## License

Internal — SDLC Agents platform.
