# Coding Standards Enforcer — Backend

FastAPI service that analyses code against language-specific coding standards
(PEP 8, Google style guides, ESLint rules, Effective Go, Clippy, etc.) and
generates AI-powered fixes via Azure OpenAI.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in Azure credentials
python run.py         # uvicorn on :8000
```

## Layout

- `agents/coding_standards_enforcer/` — agent code (router, schemas, agent
  logic, language detection, linters, prompts, git client).
- `core/` — shared infrastructure (config, providers, services, exceptions).
- `main.py` — FastAPI entry point that wires everything together.
- `core_router.py` — top-level `/` and `/health`.
- `dependencies.py` — DI helpers for the agent endpoints.

See the project root README for full documentation.
