# Code Refactoring Agent — Frontend

Next.js frontend for the Code Refactoring Agent.

## Features

- Dark-themed chat interface
- Severity badges (HIGH / MEDIUM / LOW) for code smell findings
- Inline diff viewer with color-coded additions/deletions
- Approval flow — agent asks before applying changes
- Quick action buttons for common tasks
- Source selection: Local path or GitHub repository
- Workspace/GitHub configuration on session start

## Setup

```bash
# 1. Install dependencies
pnpm install

# 2. Start dev server (port 3001)
pnpm run dev
```

Connects to the backend API at `http://localhost:8002`.

## Cloud / Remote Usage

Set the backend URL before starting the frontend:

```bash
export NEXT_PUBLIC_API_BASE_URL=https://<your-backend-domain>
pnpm run build
pnpm run start
```

If you run locally in dev mode with a cloud backend:

```bash
export NEXT_PUBLIC_API_BASE_URL=https://<your-backend-domain>
pnpm run dev
```

From another computer, open the frontend URL (or your server IP:3001) and it will call the configured backend URL.

## Session Source Options

- **Local Path**: point to an existing project directory on disk.
- **GitHub Repository**: provide a repo URL and optional branch; backend clones it automatically for the session.

## Startup Order

1. `temporal server start-dev` — Temporal on port 7233
2. `cd refactor-agent && python worker.py` — Worker
3. `cd refactor-agent && python api.py` — API on port 8002
4. `cd refactor-agent-ui && pnpm run dev` — Frontend on port 3001
