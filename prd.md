# Dependency Resolver Agent — PRD
**Platform:** SDLC Agents | **Ecosystems (MVP):** Python (PyPI), Node.js (npm)

---

## 1. Overview

Analyzes a repository and resolves all dependencies recursively by: parsing dependency files → fetching registry metadata → building a dependency graph → detecting version conflicts → generating AI-explained reports.

---

## 2. Goals

**In scope (MVP)**
- Parse, resolve, and graph dependencies
- Detect version conflicts
- AI-generated conflict explanations and upgrade suggestions
- REST API + CLI interface

**Out of scope (MVP)**
- Security/vulnerability scanning
- Auto PR generation
- Multi-language support (beyond Python + Node)

---

## 3. Target Users
Developers, DevOps engineers, AI-driven SDLC pipelines — for CI dependency validation and automated repository analysis.

---

## 4. Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.14, uv, FastAPI |
| Backend libs | requests, httpx, networkx, packaging, pydantic, typer, rich, diskcache, langchain, langchain-openai, azure-identity, openai |
| Frontend | React, Vite, TypeScript, pnpm |
| Infrastructure | Docker, Docker Compose |

---

## 5. Monorepo Structure

```
SDLC-Agents-…-dependency-resolver-agent
├── apps/dependency-resolver-agent       # React frontend
├── backend/dependency-resolver-agent    # Python backend
├── Infra/dependency-resolver-agent
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
└── README.md
```

---

## 6. Backend Architecture

```
Repo URL → Repo Loader → Dependency Parser (Python | Node)
→ Registry Metadata Fetcher (PyPI | npm)
→ Recursive Dependency Resolver
→ Graph Builder → Constraint Solver → Conflict Detector
→ AI Explanation Layer → Report
```

---

## 7. Registry APIs

**PyPI** `GET https://pypi.org/pypi/{package}/{version}/json`
Fields: `info.requires_dist`, `info.requires_python`

**npm** `GET https://registry.npmjs.org/{package}/{version}`
Fields: `dependencies`, `peerDependencies`, `engines`

---

## 8. Backend Project Structure

```
backend/dependency-resolver-agent/
├── app/
│   ├── main.py / config.py
│   ├── services/repo_service.py
│   ├── parser/python_parser.py, node_parser.py
│   ├── metadata/pypi_client.py, npm_client.py
│   ├── resolver/dependency_resolver.py, graph_builder.py, constraint_solver.py
│   ├── analysis/conflict_detector.py, conflict_explainer.py, upgrade_suggester.py
│   ├── reports/report_generator.py
│   ├── llm/azure_client.py, langchain_llm.py
│   ├── cli/cli.py
│   └── utils/http.py, version_utils.py, cache.py
├── tests/
├── pyproject.toml
└── .python-version
```

---

## 9. Core Algorithms

**Resolution** — recursive DFS with visited-set guard, disk-cached metadata, concurrent fetching via `httpx`:
```
resolve(pkg): if visited → return; fetch metadata; add node; for dep in metadata: resolve(dep)
```

**Graph** — `networkx.DiGraph`

**Constraint solver** — `packaging.specifiers` + `packaging.version`; intersect all constraints per package, flag non-intersecting sets as conflicts.

**Conflict format:**
```json
{ "package": "pydantic", "constraints": ["<2", ">=2"], "status": "conflict" }
```

---

## 10. Azure OpenAI Integration

**Auth:** Azure Entra ID (`azure-identity` + `langchain-openai`)

**Env vars:** `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_CHATGPT_DEPLOYMENT`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`

**LLM tasks:** explain conflicts · suggest upgrade paths · generate developer-friendly report prose

---

## 11. API

```
GET  /health
POST /resolve   body: { "repo_url": "<url or local path>" }
                resp: { "dependencies": [], "conflicts": [], "graph": {} }
```

---

## 12. CLI

```bash
resolver scan <repo_url>
# Output: Root Dependencies · Resolved Tree · Conflicts · AI Suggestions
```

---

## 13. Frontend

**Location:** `apps/dependency-resolver-agent` — single-page app, `App.jsx` as root orchestrator.

```
src/
├── App.jsx / main.jsx
├── components/Sidebar.jsx, RepoScanner.jsx, DependencyGraph.jsx,
│             ConflictPanel.jsx, AISuggestions.jsx
├── pages/Dashboard.jsx
└── services/api.js
```

**Design:** GitHub-inspired — sidebar nav, repo scanner panel, card-based conflict display, monospace code blocks.

```
| Sidebar | Repo Scanner      | Results Panel  |
|         | Dependency Graph  | Conflict Cards |
|         |                   | AI Suggestions |
```

---

## 14. Docker

| Service | Base image | Port |
|---|---|---|
| Backend | `python:3.14-slim` | 8001 |
| Frontend | `node:22` | 5174 |

Files in `Infra/dependency-resolver-agent/`: `Dockerfile.backend`, `Dockerfile.frontend`, `docker-compose.yml`

---

## 15. Implementation Phases

| Phase | Deliverable |
|---|---|
| 1 | Monorepo scaffold (uv + pnpm init) |
| 2 | Repo loader (clone + ecosystem detection) |
| 3 | Dependency parsers (Python + Node) |
| 4 | Registry metadata clients (PyPI + npm) |
| 5 | Recursive resolver |
| 6 | Graph builder |
| 7 | Constraint solver |
| 8 | Conflict detector |
| 9 | FastAPI server |
| 10 | CLI interface |
| 11 | Azure OpenAI integration |
| 12 | AI reasoning modules |

---

## 16. Acceptance Criteria

- [ ] Dependency scan, graph generation, and conflict detection working end-to-end
- [ ] AI explanations generated for conflicts
- [ ] `resolver scan` CLI command functional
- [ ] `POST /resolve` API endpoint functional
- [ ] Docker Compose brings up both services cleanly

---

## 17. Example Output

```
Dependency Resolution Report

Root:  fastapi 0.112 · uvicorn 0.30

Tree:
fastapi
 ├ pydantic 2.7
 │ └ typing-extensions
 └ starlette 0.37

Conflicts: None
AI:  Upgrade uvicorn 0.22 → 0.30
```