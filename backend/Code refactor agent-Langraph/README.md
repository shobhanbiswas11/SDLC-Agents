# Code Refactor Agent — LangGraph Edition

An AI-powered code refactoring agent that analyses code for smells and applies safe, automated refactors.

**This is the LangGraph rewrite** of the original Temporal-based agent.  
No Temporal server, no worker process — just Python.

---

## What Changed vs the Original

| Component | Original (Temporal) | This version (LangGraph) |
|---|---|---|
| Orchestration | Temporal Server (localhost:7233) | LangGraph StateGraph (in-process) |
| State persistence | Temporal history | SQLite (`checkpoints.db`) |
| Worker process | `python worker.py` (separate) | ❌ Not needed |
| Human-in-the-loop | `wait_condition` signal | `interrupt()` + `/answer` endpoint |
| `workflow.py` | `@workflow.defn` class | `graph.py` → `StateGraph` |
| `activities.py` | `@activity.defn` functions | `agent_node.py` → graph nodes |
| License cost | Temporal Cloud = paid | LangGraph = **free (MIT)** |

---

## Requirements

- Python 3.12+
- Azure OpenAI resource (API key **or** Service Principal)

---

## Setup

```bash
# 1. Enter the agent directory
cd "backend/Code Refactor Agent - LangGraph"

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

## Run

```bash
python api.py
```

The server starts on **http://localhost:18200** — no Temporal server, no worker needed.

Interactive API docs: **http://localhost:18200/docs**

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/sessions` | Create a new refactoring session |
| `GET` | `/sessions/{id}/status` | Poll agent status (idle / thinking / waiting_for_user) |
| `POST` | `/sessions/{id}/message` | Send a user message, run the agent |
| `POST` | `/sessions/{id}/answer` | Resume agent after an `ask_user` pause |
| `DELETE` | `/sessions/{id}` | Stop and remove a session |
| `GET` | `/health` | Health check |

---

## Project Structure

```
Code Refactor Agent - LangGraph/
├── api.py              ← FastAPI server (entry point)
├── graph.py            ← LangGraph StateGraph definition
├── agent_node.py       ← LLM node + Tool node implementations
├── tools.py            ← All 17 tool handlers (unchanged from original)
├── config_loader.py    ← YAML config loader (unchanged)
├── semantic_safety.py  ← AST-based semantic safety checks (unchanged)
├── checkpoints.db      ← SQLite state file (auto-created on first run)
├── requirements.txt
├── .env.example
└── config/
    ├── agent.yaml      ← System prompt + tool list
    └── tools/          ← 17 tool schema YAMLs
        ├── analyze_code.yaml
        ├── suggest_refactor.yaml
        ├── apply_refactor.yaml
        ├── diff_preview.yaml
        ├── run_tests.yaml
        ├── read_file.yaml
        ├── write_file.yaml
        ├── list_files.yaml
        ├── search_code.yaml
        ├── multi_refactor.yaml
        ├── navigate_to_file.yaml
        ├── ask_user.yaml
        ├── git_commit_push.yaml
        ├── github_put_file.yaml
        ├── find_references.yaml
        ├── apply_batch_refactor.yaml
        └── terminal_command.yaml
```

---

## How the ReAct Loop Works

```
User Message
    │
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

---

## Available Tools (unchanged from original)

| Tool | Description |
|---|---|
| `analyze_code` | Detect code smells using Tree-sitter AST |
| `suggest_refactor` | LLM-based refactoring suggestions |
| `apply_refactor` | Write refactored file to disk |
| `diff_preview` | Show unified diff of proposed changes |
| `run_tests` | Run pytest on the refactored file |
| `read_file` | Read any file in the workspace |
| `write_file` | Write or create a file |
| `list_files` | Recursively list workspace files |
| `search_code` | Search for patterns across the workspace |
| `multi_refactor` | Mass search-and-replace across files |
| `navigate_to_file` | Navigate frontend to a specific file |
| `ask_user` | Pause and ask the user a question |
| `git_commit_push` | Commit and push via Git CLI |
| `github_put_file` | Push a file via GitHub REST API |
| `find_references` | Find all references to a symbol |
| `apply_batch_refactor` | Apply refactors across multiple files |
| `terminal_command` | Run arbitrary shell commands |

---

## License

MIT
