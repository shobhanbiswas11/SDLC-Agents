# Documentation Drafting Agent — Frontend

Next.js frontend for the Documentation Drafting Agent.

## Run (local dev)

```bash
cd "apps/Documentation Drafting agent"
pnpm install
pnpm run dev
```

Default local URL: `http://localhost:3000`.

## API base URLs

Set these before running if backend services are on custom hosts/ports:

- `NEXT_PUBLIC_DOC_FIRST_API_BASE_URL` (default expected host: `http://localhost:18100`)
- `NEXT_PUBLIC_DOC_SIMPLE_API_BASE_URL` (default expected host: `http://localhost:18101`)

## Docker

In Docker Compose, this UI is exposed at:

- `http://localhost:13100`

using `infra/Documentation Drafting agent/docker-compose.yml`.
