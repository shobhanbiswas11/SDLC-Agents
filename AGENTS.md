# AGENTS.md

## 🧠 PURPOSE

This project is a **Build Orchestration Agent System**.

The system uses an **Orchestrator → Sub-Agent architecture** where:

* A central orchestrator interprets user intent
* Delegates tasks to specialized agents
* Executes async pipelines using Celery
* Maintains state using Redis
* Logs history in PostgreSQL

The goal is to:

* Fix builds
* Resolve dependencies
* Analyze pipelines
* Automate debugging workflows

---

## 🏗️ ARCHITECTURE OVERVIEW

Backend stack:

* FastAPI → API + WebSockets
* Celery → async task execution
* Redis → broker + state
* PostgreSQL → logs + history
* LLM (LangChain/OpenAI) → reasoning + orchestration

Architecture pattern:

User Request → FastAPI → Orchestrator Agent
→ Sub-Agent Selection → Celery Task Pipeline
→ Redis (state) → PostgreSQL (logs)

---

## 🤖 AGENT SYSTEM DESIGN

### 1. Orchestrator Agent

Responsibilities:

* Parse user input
* Identify intent (fix build, analyze logs, etc.)
* Select appropriate sub-agent(s)
* Create execution plan (pipeline)
* Trigger Celery workflows

---

### 2. Sub-Agents

#### Dependency Resolver Agent

* Parses dependency errors
* Suggests version fixes
* Uses registry APIs if needed

#### Build Fix Agent

* Analyzes build logs
* Identifies root cause
* Suggests or applies fixes

#### Pipeline Agent

* Handles CI/CD pipeline orchestration
* Breaks tasks into steps
* Monitors execution state

#### Log Analysis Agent

* Processes logs
* Extracts errors
* Summarizes issues

---

### 3. Worker Layer (Celery)

* Executes long-running tasks
* Each agent can map to a task queue
* Tasks must be idempotent and retry-safe

---

## 📁 PROJECT STRUCTURE

backend/build-orchestration-agent/

app/
api/                # FastAPI routes
agents/             # Orchestrator + sub-agents
services/           # Business logic
workers/            # Celery tasks
core/               # config, settings
models/             # DB models
schemas/            # Pydantic schemas

---

## ⚙️ DEVELOPMENT SETUP

### Install dependencies

pip install -r requirements.txt

### Run FastAPI

uvicorn app.main:app --reload

### Run Redis

redis-server

### Run Celery worker

celery -A app.workers.celery_app worker --loglevel=info

### Run DB migrations

alembic upgrade head

---

## 🐳 DOCKER REQUIREMENT

All services MUST run via Docker.

Services:

* fastapi
* redis
* postgres
* celery_worker

Agents must ensure:

* No local-only dependencies
* Everything works via docker-compose

---

## 🔐 CONFIGURATION RULES

* Use environment variables ONLY
* Never hardcode:

  * DB URLs
  * API keys
  * Redis URLs

Required env:

* DATABASE_URL
* REDIS_URL
* OPENAI_API_KEY

---

## ⚡ CODING RULES

### General

* Use Python 3.10+
* Follow async-first design
* Keep functions small and modular

### FastAPI

* Use dependency injection
* Separate routes from logic

### Celery

* Tasks must be retry-safe
* No blocking operations

### Database

* Use SQLAlchemy ORM
* Use Alembic for migrations

---

## 🔁 PIPELINE EXECUTION RULES

* All long tasks → Celery
* Orchestrator should NOT block
* Maintain pipeline state in Redis
* Persist final results in PostgreSQL

---

## 🧠 LLM USAGE RULES

* Use LLM only for reasoning (not execution)
* Keep prompts structured
* Avoid hallucination by validating outputs

---

## 🧪 TESTING RULES

* Add unit tests for:

  * agents
  * services
  * workers

Run tests:
pytest

---

## 🚫 ANTI-PATTERNS (STRICTLY FORBIDDEN)

* ❌ Running everything in one process
* ❌ Using in-memory state
* ❌ Blocking FastAPI threads
* ❌ Hardcoding configs
* ❌ Mixing agent logic with API layer

---

## ✅ EXPECTED OUTPUT FROM AGENTS

Agents should:

1. Create full backend structure
2. Implement orchestrator logic
3. Implement sub-agents
4. Implement Celery pipelines
5. Integrate Redis + PostgreSQL
6. Provide working Docker setup

---

## 🧭 EXECUTION STRATEGY FOR CODEX

When starting a task:

1. Understand user intent
2. Map to agent(s)
3. Generate required modules
4. Wire dependencies correctly
5. Ensure system runs end-to-end

Always prioritize:

* correctness
* modularity
* scalability

---

## 🏁 FINAL GOAL

A fully working system where:

User → "Fix my build"

System:

* Understands request
* Runs agent pipeline
* Fixes issue or suggests solution
* Returns structured response

---

END OF FILE
