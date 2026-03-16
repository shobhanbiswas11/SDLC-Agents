# Documentation Drafting Agent — 1st AI Backend

FastAPI service that generates and streams README drafts from repository content.

## Run (local Python)

```bash
cd "backend/Documentation Drafting agent/1st AI agent"
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Required environment variables

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_CHATGPT_DEPLOYMENT`
- `AZURE_OPENAI_API_KEY` (recommended)
- `YOUR_GITHUB_ACCESS_TOKEN` (for GitHub content access)

Optional Entra auth fields:

- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`

## API

- Base URL: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`

## Docker

This service is also included in the infra compose stack:

- `infra/Documentation Drafting agent/docker-compose.yml`

