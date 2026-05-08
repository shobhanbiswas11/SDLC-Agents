

---

# Dependency Resolver Agent — PROJECT.md

**Version:** 0.0
**Date:** 2026-04-30
**Status:** Active Design

---

## 1. Overview

The Dependency Resolver Agent is a **conversational, stateful system** that resolves software dependencies through a unified chat interface.

Users can:

* Ask questions
* Paste dependency manifests
* Request analysis (e.g., changelogs, vulnerabilities)
* Guide resolution through natural language

The system dynamically interprets input and routes execution without requiring explicit modes or commands.

---

## 2. Core Objective

Design an agent that behaves like a conversational system while maintaining:

* Deterministic execution for critical operations
* Structured tool usage
* Persistent, resumable state
* Human-in-the-loop decision control

---

## 3. Interaction Model

### 3.1 Principle

> The user can type anything.
> The system must always respond correctly.

---

### 3.2 Input Handling Contract

Every input is classified into exactly one category:

| Category       | Description                | Execution Path    |
| -------------- | -------------------------- | ----------------- |
| Manifest Input | Dependency file or list    | Resolver pipeline |
| Tool Intent    | Information request        | Tool execution    |
| Control Intent | Modify or resume execution | Graph control     |
| Conversation   | General query              | LLM response      |

---

### 3.3 Priority Order

```text
1. Manifest Detection
2. Control Intent
3. Tool Intent
4. Conversation (fallback)
```

---

## 4. Architecture

### 4.1 High-Level Flow

```text
User Input
   ↓
Preprocessor (extract structured content)
   ↓
Deterministic Router
   ├── Manifest → Resolver Graph
   ├── Control → Resume / Retry
   └── LLM Layer
          ↓
     Tool Calling (if needed)
          ↓
     Tool Registry
```

---

### 4.2 Orchestration Layer

Implemented using LangGraph

Responsibilities:

* State transitions
* Execution loops
* Retry and backtracking
* Pause and resume

---

### 4.3 State Management

State is persisted as JSON:

```text
state/sessions/{session_id}.json
```

#### Example

```json
{
  "session_id": "abc123",
  "current_node": "resolve_versions",
  "dependencies": [],
  "resolved": {},
  "conflicts": [],
  "decisions": [],
  "history": [],
  "status": "running"
}
```

---

## 5. Execution Graph

### Nodes

| Node             | Responsibility        |
| ---------------- | --------------------- |
| parse_input      | Parse manifest        |
| fetch_registry   | Retrieve metadata     |
| resolve_versions | Compute versions      |
| detect_conflicts | Identify issues       |
| human_review     | Request user decision |
| finalize         | Generate output       |

---

### Workflow

```text
START
  ↓
parse_input
  ↓
fetch_registry
  ↓
resolve_versions
  ↓
detect_conflicts
  ↓
[if conflicts]
    ↓
  human_review
    ↓
  resolve_versions (retry loop)
  ↓
finalize
  ↓
END
```

---

## 6. Manifest Injection (Chat-Native Execution)

### Requirement

If a user pastes a dependency file at any point:

* Detect it deterministically
* Replace current session input
* Reset resolution state
* Trigger resolver immediately

---

### Behavior

```text
User pastes manifest
   ↓
Detect manifest (no LLM)
   ↓
Parse + validate
   ↓
Update session state
   ↓
Run resolver graph
```

---

## 7. Tool Usage Model

### 7.1 Purpose

Tools provide structured external data:

* Changelog retrieval
* Vulnerability lookup
* Registry queries

---

### 7.2 Tool Decision Strategy

| Task Type         | Decision Source |
| ----------------- | --------------- |
| Manifest handling | Deterministic   |
| Execution control | Deterministic   |
| Tool selection    | LLM             |
| Tool arguments    | LLM (validated) |
| Execution flow    | System          |

---

### 7.3 Tool Constraints

* Only registered tools may be called
* All arguments must be validated
* Invalid calls are rejected and retried

---

## 8. Human-in-the-Loop (HITL)

### Trigger Conditions

* Unresolvable conflicts
* Multiple valid strategies
* Explicit user override

---

### Example

```json
{
  "status": "waiting_for_human",
  "question": "Conflict detected between versions. Select resolution strategy."
}
```

---

### Resume

```text
POST /resume/{session_id}
```

---

## 9. LLM Responsibilities

The LLM is used for:

* Explaining conflicts
* Interpreting ambiguous queries
* Generating human-readable responses
* Selecting tools when appropriate

The LLM must not:

* Control execution flow
* Modify state without validation
* Select dependency versions

---

## 10. Streaming Behavior

Responses are streamed progressively:

* Execution progress
* Tool activity
* Final explanations

This ensures responsiveness and transparency.

---

## 11. Technology Stack

| Layer           | Technology      |
| --------------- | --------------- |
| API             | FastAPI         |
| Orchestration   | LangGraph       |
| State Storage   | JSON            |
| Execution Model | Async Python    |
| LLM             | OpenAI / Local  |
| Frontend        | React / Next.js |

---

## 12. Infrastructure Constraints

The system intentionally excludes:

* Celery
* Redis
* Distributed worker systems

Rationale:

* Simpler architecture
* Easier debugging
* Full control over execution

---

## 13. Project Structure

```text
dependency-resolver-agent/
│
├── app/
│   ├── main.py
│   └── routers/
│
├── agents/
│   └── resolver/
│       ├── graph.py
│       ├── state.py
│       ├── router.py
│       ├── nodes/
│       │   ├── parse.py
│       │   ├── fetch.py
│       │   ├── resolve.py
│       │   ├── conflict.py
│       │   └── human.py
│
├── tools/
│   ├── registry.py
│   ├── changelog.py
│   └── cve.py
│
├── state/
│   └── sessions/
│
└── PROJECT.md
```

---

## 14. Testing Strategy

* Unit tests for each node
* Routing tests for input classification
* End-to-end workflow tests
* Resume and recovery tests

---

## 15. Design Constraints

### Required

* Deterministic routing
* Explicit state transitions
* JSON-based persistence
* Modular node design

---

### Prohibited

* LLM-driven control flow
* Hidden system state
* Unvalidated tool execution
* Premature infrastructure complexity

---

## 16. Future Extensions

* Multi-ecosystem resolution
* Security scanning integration
* Dependency graph visualization
* CI/CD integration

---

## 17. Conclusion

This system combines:

* Deterministic execution
* Conversational interaction
* Structured tool usage
* Persistent state

to create a dependency resolver that behaves like a natural assistant while maintaining correctness, transparency, and control.

---

