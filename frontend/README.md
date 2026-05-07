# Coding Standards Enforcer — Frontend

Next.js (App Router) UI for the Coding Standards Enforcer agent. Provides a
Monaco-powered editor, repo browser, branch picker, file tree, and a diff
viewer for AI-generated fixes.

## Quick start

```bash
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                  # http://localhost:3000
```

## Stack

- Next.js 14 + React 18 + TypeScript
- Redux Toolkit (`@reduxjs/toolkit`, `react-redux`)
- Axios for the REST client
- Monaco editor (`@monaco-editor/react`)
- `react-diff-viewer-continued`
- Tailwind CSS (utilities available; original hand-rolled CSS preserved in
  `src/app/globals.css`)

## Layout

```
src/
├── app/                     # App Router entries + globals.css
├── components/agents/CodingStandardsEnforcer/   # main UI components
├── services/api/            # axios client + agent service
├── store/slices/            # Redux slices
├── types/                   # TS types mirroring backend Pydantic models
└── hooks/                   # typed Redux hooks
```
