# Documentation Drafting Agent — LangGraph Edition

An AI-powered universal documentation agent that analyzes code, understands folder structures, and writes technical documentation (READMEs, API Docs, Code Comments).

**This is the LangGraph rewrite** of the original Temporal-based agent.  
No Temporal server, no worker process — just Python.

---

## What Changed vs the Original

| Component | Original (Temporal) | This version (LangGraph) |
|---|---|---|
| Orchestration | Temporal Server (localhost:7233) | LangGraph StateGraph (in-process) |
| State persistence | Temporal history | SQLite (`checkpoints.db`) |
| Worker process | `python worker.py` (separate) | ❌ Not needed |
| Human-in-the-loop | `wait_condition` signal | `interrupt()` + `/sessions/{id}/answer` |
| `workflow.py` | `@workflow.defn` class | `graph.py` → `StateGraph` |
| `activities.py` | `@activity.defn` functions | `agent_node.py` → graph nodes |
| Legacy HTTP API | `/api/workflows` | Kept for backward compatibility |
| Direct RAG Chat | `/chat` & `/stream-chat` | Unchanged |

---

## Requirements

- Python 3.12+
- Azure OpenAI resource (API key **or** Service Principal)

---

## Setup

```bash
# 1. Enter the agent directory
cd "backend/Docuemtnation drafitgn agent -Langgraph"

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
copy .env.example .env
# Fill in your Azure OpenAI credentials in .env
```

---

## Run Server

```bash
python api.py
```

The server starts on **http://localhost:8002** — no Temporal server, no worker needed.

Interactive API docs: **http://localhost:8002/docs**

---

## Run CLI (Terminal interface)

The CLI bypasses the HTTP API entirely and runs the LangGraph engine directly in your terminal.

```bash
python cli.py
python cli.py --path /path/to/my/project
python cli.py --github owner/repo
```

---

## Project Structure

```
Docuemtnation drafitgn agent -Langgraph/
├── api.py              ← FastAPI server (entry point)
├── graph.py            ← LangGraph StateGraph definition
├── agent_node.py       ← RAG context + LLM node + Tool node
├── cli.py              ← Direct LangGraph Terminal UI
├── tools.py            ← All 20 tool handlers (unchanged)
├── config_loader.py    ← YAML config loader (unchanged)
├── requirements.txt
├── .env.example
├── config/             ← agent.yaml and 20 tool YAML schemas
├── parsers/            ← RAG: tree fetchers, metadata extractors, AST graph
└── intelligence/       ← RAG: semantic file rankers, prompt builders
```

---

## How the ReAct + RAG Loop Works

```
User Message
    │
    ▼
[gather_context_node]  ── (Runs ONCE per session) Scans workspace,
    │                     extracts metadata, semantically ranks files,
    │                     injects codebase context as system prompt.
    ▼
[llm_node]  ──── tool calls? ──── YES ──► [tool_node]
    │                                           │
    │ NO                                        │
    ▼                                           │
Final Answer ◄─────────────── loops back ◄─────┘
```

**ask_user special case:**
```
[tool_node] hits ask_user
    │
    ▼
interrupt(question)     ← LangGraph pauses here, saves state to checkpoints.db
    │
    │  Frontend calls POST /sessions/{id}/answer
    ▼
Command(resume=answer)  ← LangGraph resumes from exact pause point
    │
    ▼
[tool_node] continues
```
