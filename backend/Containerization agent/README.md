# 🐳 Docker AI Agent

An AI-powered containerisation agent that analyses any software project, generates production-ready Docker artefacts, builds and repairs images automatically, and optimises the final result — all from a single command.

---

## Features

| Capability | Details |
|---|---|
| **Project Analysis** | Detects language, framework, port, entry-point, and service dependencies automatically |
| **Dockerfile Generation** | Produces a multi-stage Alpine Dockerfile and `.dockerignore` |
| **Compose Generation** | Generates a `docker-compose.yml` for multi-service projects (DB, Redis, etc.) |
| **Automated Build** | Streams `docker`/`podman build` output live to the terminal |
| **Self-Healing** | `repair_build` fixes broken files and retries the build atomically (up to 5×) |
| **Health Check** | Polls the container's TCP port until the app is ready |
| **Image Optimisation** | Rewrites the Dockerfile with multi-stage builds and Alpine bases to shrink size |
| **Interactive REPL** | Full conversation loop with `/auto`, `/clear`, `/help` commands |

---

## Requirements

- Python 3.12+
- Docker **or** Podman installed and on your `PATH`
- An Azure OpenAI resource (API key **or** Service Principal)

---

## Setup

```bash
# 1. Clone the repo and enter the agent directory
cd "backend/Containerization agent"

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
copy .env.example .env
# Open .env and fill in your Azure OpenAI credentials
```

### Environment Variables (`.env`)

| Variable | Required | Description |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | ✅ | Your Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_VERSION` | ✅ | API version (e.g. `2025-01-01-preview`) |
| `AZURE_OPENAI_CHATGPT_DEPLOYMENT` | ✅ | Deployment name (e.g. `gpt-4o`) |
| `AZURE_OPENAI_API_KEY` | ✅* | API key (*or* use Service Principal below) |
| `AZURE_TENANT_ID` | ✅* | Service Principal tenant ID |
| `AZURE_CLIENT_ID` | ✅* | Service Principal client ID |
| `AZURE_CLIENT_SECRET` | ✅* | Service Principal client secret |
| `CONTAINER_RUNTIME` | optional | `docker` (default) or `podman` |

---

## Usage

### Interactive Mode (default)

```bash
python cli.py
```

You will be prompted for the project path, then dropped into an interactive REPL:

```
You ▸ /auto          # run the full pipeline automatically
You ▸ /clear         # reset conversation history
You ▸ /help          # show available commands
You ▸ /exit          # quit
```

### Non-interactive / CI Mode

```bash
# Run the full pipeline on a project directory, no prompts
python cli.py --path /path/to/your/project --auto

# Override the model deployment
python cli.py --path . --auto --model gpt-4o-mini
```

---

## Full Pipeline (`/auto`)

When you run `/auto` the agent executes these steps in sequence:

```
1. list_files          → scan project file tree
2. read_file           → read key dependency files
3. analyze_project     → detect stack (language, port, entry-point…)
4. generate_dockerfile → write Dockerfile + .dockerignore
5. generate_compose    → write docker-compose.yml (if multi-service)
6. podman_build        → build the image (streams output live)
   └─ on failure → repair_build × up to 5  (fix + rebuild atomically)
7. podman_run          → start the container
8. health_check        → poll the port until the app responds
9. optimize_image      → produce a leaner multi-stage Alpine image
```

---

## Project Structure

```
Containerization agent/
├── cli.py                  # Entry point — argument parsing, REPL, banner
├── agent.py                # Azure OpenAI client, ReAct loop, token trimmer
├── tools.py                # All tool handler implementations
├── requirements.txt        # Pip dependencies
├── pyproject.toml          # Project metadata
├── .env.example            # Environment variable template
└── config/
    ├── agent.yaml          # Agent identity, tool list, and system prompt
    └── tools/              # One YAML per tool (schema + activity settings)
        ├── read_file.yaml
        ├── write_file.yaml
        ├── list_files.yaml
        ├── ask_user.yaml
        ├── analyze_project.yaml
        ├── generate_dockerfile.yaml
        ├── generate_compose.yaml
        ├── podman_build.yaml
        ├── podman_run.yaml
        ├── podman_logs.yaml
        ├── podman_stop.yaml
        ├── repair_file.yaml
        ├── repair_build.yaml
        ├── optimize_image.yaml
        ├── health_check.yaml
        └── terminal_command.yaml
```

---

## Available Tools

| Tool | Description |
|---|---|
| `read_file` | Read any file in the workspace |
| `write_file` | Write or overwrite any file |
| `list_files` | Recursively list all project files |
| `ask_user` | Pause and ask the user a question |
| `analyze_project` | AI-detect the tech stack from the file tree |
| `generate_dockerfile` | Generate Dockerfile + `.dockerignore` |
| `generate_compose` | Generate `docker-compose.yml` |
| `podman_build` | Build the container image (streamed output) |
| `podman_run` | Run the built container |
| `podman_logs` | Fetch container logs |
| `podman_stop` | Stop and remove a container |
| `repair_file` | AI-fix a broken file from an error log |
| `repair_build` | Atomic fix + rebuild (preferred over repair_file alone) |
| `optimize_image` | Rewrite Dockerfile with multi-stage + Alpine |
| `health_check` | Poll a TCP port until the app responds |
| `terminal_command` | Run an arbitrary shell command in the workspace |

---

## Development

```bash
# Lint
pip install ruff
ruff check .

# Format
ruff format .
```

---

## License

MIT
