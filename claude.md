# Dependency Resolver Agent — Project Reference

> **Conversational dependency resolver** with HITL WebSocket orchestration + PubGrub solver
> **Stack**: FastAPI + asyncio + LangChain (Azure OpenAI) + Next.js/React

---

## Architecture

```
User (browser)
  ↓
Frontend (Next.js, localhost:3000)
  ├─ REST  POST /api/dependency_resolver/session       → create session
  └─ WS    /api/dependency_resolver/chat/{session_id}  → live HITL channel
              ↓
Backend (FastAPI, localhost:8000)
  └─ HITLOrchestrator (agents/dependency_resolver/hitl/orchestrator.py)
       ├─ Parser           → agents/dependency_resolver/parsers/
       ├─ DependencyGraph  → agents/dependency_resolver/resolver/graph.py
       ├─ PubGrubSolver    → agents/dependency_resolver/resolver/solver.py
       ├─ OSV CVE audit    → agents/dependency_resolver/security/osv_client.py
       ├─ License check    → agents/dependency_resolver/security/license_check.py
       ├─ LLM explainer    → agents/dependency_resolver/llm/explainer.py (Azure OpenAI)
       ├─ Approval gateway → agents/dependency_resolver/hitl/approval_gateway.py
       └─ Guardrails       → agents/dependency_resolver/hitl/guardrails.py
```

---

## Run

**Backend**
```bash
cd backend
python run.py        # → uvicorn launches main:app on :8000
# or: python main.py
```

**Frontend**
```bash
cd frontend
npm run dev          # → :3000
```

Visit http://localhost:8000/docs for the OpenAPI UI.

---

## Project Structure

```
backend/
├── main.py                         # FastAPI entry (production)
├── run.py                          # Convenience launcher
├── agents/
│   └── dependency_resolver/
│       ├── __init__.py             # FastAPI router (REST + WebSocket)
│       ├── agent.py                # Headless resolve/diff/audit
│       ├── schemas.py              # Pydantic models for all messages
│       ├── initialization.py       # App lifecycle hooks
│       ├── parsers/                # package.json, requirements.txt, Cargo.toml, pom.xml
│       ├── registry/               # PyPI, npm, crates, Maven clients
│       ├── resolver/               # DependencyGraph + PubGrub solver + conflict detection
│       ├── security/               # OSV CVE client + license checker
│       ├── llm/                    # Conflict explainer (Azure OpenAI streaming)
│       └── hitl/                   # WebSocket orchestrator + session store + guardrails
├── core/
│   └── llm/                        # Azure AD ClientSecretCredential wrapper
└── state/hitl/                     # Per-session JSON snapshots (auto-created)

frontend/
├── src/app/dependency-resolver/    # Main resolver page (setup + chat)
├── src/services/                   # API + WebSocket service (with reconnect)
├── src/store/slices/               # Redux state for session + connection
└── src/components/DependencyResolver/  # ChatPanel, ApprovalCard, SolverProgress
```

---

## Key Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/dependency_resolver/session` | Create HITL session |
| GET | `/api/dependency_resolver/session/{id}` | Get session + history |
| POST | `/api/dependency_resolver/session/{id}/approve` | REST fallback for approval |
| DELETE | `/api/dependency_resolver/session/{id}` | Close/abort session |
| WS | `/api/dependency_resolver/chat/{id}` | Live HITL channel (frames in `WSMessage` schema) |
| POST | `/api/dependency_resolver/resolve` | Headless resolve (CI use) |
| POST | `/api/dependency_resolver/diff` | Compare two manifests |
| POST | `/api/dependency_resolver/audit` | CVE + license audit only |
| GET | `/api/dependency_resolver/health` | Liveness check |

---

## WebSocket Frame Format

**Inbound (from client):**
```json
{ "type": "user_message",      "session_id": "…", "payload": { "text": "…" } }
{ "type": "approval_response", "session_id": "…", "payload": { "decision": "APPROVE" | "REJECT", "comment": "…" } }
```

**Outbound (from server):** see `agents/dependency_resolver/schemas.py::MessageType`
- `solver_event` — pipeline stage updates
- `agent_message` — LLM response (streamed; `payload.delta` per token)
- `search_event` — web search results
- `approval_request` — final lockfile awaiting human decision
- `system` — generic notices
- `error` — recoverable errors

---

## Resilience Features

- **Per-message error handling** in WS loop → bad JSON or handler errors send `error` frames; loop survives.
- **64KB payload limit** at both `ws_max_size` and explicit message size check.
- **Per-session pipeline lock** (`asyncio.Lock`) prevents concurrent solver runs.
- **Frontend auto-reconnect** with exponential backoff (1s → 30s, max 5 attempts).
- **History replay** on reconnect (orchestrator replays `session.messages`).

---

## Configuration

`backend/.env`:
```
AZURE_TENANT_ID=…
AZURE_CLIENT_ID=…
AZURE_CLIENT_SECRET=…
AZURE_OPENAI_ENDPOINT=…
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

CVE data comes from OSV.dev (no API key required). LLM service falls back to a no-op explainer if Azure credentials are missing.

---

## Notes

- Sessions persist as JSON in `backend/state/hitl/{session_id}.json` for debugging.
- The WS handler uses `receive_text()` + manual `json.loads()` for fine-grained error control — never `receive_json()` directly.
- All approval decisions are gated through `approval_gateway` to prevent the solver from auto-applying lockfiles.
