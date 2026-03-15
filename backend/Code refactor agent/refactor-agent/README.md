# Code Refactoring Agent — Backend

AI-powered code refactoring agent using Temporal.io + FastAPI + Azure OpenAI.

## Architecture

```
User → Frontend (port 3001) → FastAPI (port 8002) → Temporal → Worker → Azure OpenAI
```

## Tools

| Tool | Description |
|------|-------------|
| `analyze_code` | Scan a file for code smells (returns severity + findings) |
| `suggest_refactor` | Generate refactored code for a specific smell |
| `diff_preview` | Show unified diff of original vs refactored |
| `apply_refactor` | Write refactored code (requires user approval) |
| `run_tests` | Run project test suite |
| `read_file` | Read local files |
| `write_file` | Write local files |
| `list_files` | List directory contents |
| `ask_user` | Ask user for confirmation |
| `git_commit_push` | Commit and push changes to GitHub (after explicit approval) |
| `github_put_file` | Push a file via GitHub API (simple-agent style) |

## Source Modes

You can start a refactoring session in two modes:

- **Local**: provide `workspace_path` (existing behavior)
- **GitHub**: provide `source_type="github"` and `github_url` (optional `github_branch`)

When GitHub mode is used, the backend clones the repository into `.refactor_repos/<workflow-id>` and runs tools against that cloned workspace.

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start Temporal (in a separate terminal)
temporal server start-dev

# 3. Start the worker
python worker.py

# 4. Start the API server
python api.py
```

API runs on port **8002**.

## Cloud Deployment (so another computer can use it)

### Required environment variables

- `PORT` (optional, default: `8002`)
- `TEMPORAL_ADDRESS` (default: `localhost:7233`)
- `TEMPORAL_NAMESPACE` (default: `default`)
- `TEMPORAL_API_KEY` (optional for local; required for Temporal Cloud)
- `TEMPORAL_TLS` (`true`/`false`, optional)
- Azure OpenAI values in `.env` (already used by the app)

Example:

```bash
export PORT=8002
export TEMPORAL_ADDRESS=<your-temporal-host>:7233
export TEMPORAL_NAMESPACE=<your-namespace>
export TEMPORAL_API_KEY=<your-temporal-api-key>
export TEMPORAL_TLS=true
```

### Deploy components

You need 3 running parts:

1. Temporal server (Temporal Cloud or self-hosted)
2. Backend API (`python api.py`)
3. Worker (`python worker.py`)

The API and worker can run on the same VM/container, but both must be able to reach `TEMPORAL_ADDRESS`.

### Access from another computer

1. Deploy API+worker to a public cloud host (VM, Render, Railway, Fly.io, etc.).
2. Open your API port (or use HTTPS reverse proxy).
3. Use the public API URL in the frontend with `NEXT_PUBLIC_API_BASE_URL`.
4. Open the frontend URL from the second computer and start a session normally.

## Folder Structure

```
refactor-agent/
├── .env                    # Azure OpenAI credentials
├── api.py                  # FastAPI server (port 8002)
├── worker.py               # Temporal worker
├── workflow.py              # ReAct loop workflow
├── activities.py            # LLM call + tool execution
├── tools.py                 # All tool handlers
├── config_loader.py         # YAML → OpenAI schema converter
├── config/
│   ├── agent.yaml           # Agent prompt + tool list
│   └── tools/               # One YAML per tool
│       ├── analyze_code.yaml
│       ├── suggest_refactor.yaml
│       ├── apply_refactor.yaml
│       ├── diff_preview.yaml
│       ├── run_tests.yaml
│       ├── read_file.yaml
│       ├── write_file.yaml
│       ├── list_files.yaml
│       └── ask_user.yaml
└── requirements.txt
```
