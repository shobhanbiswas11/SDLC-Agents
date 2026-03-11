# Product Planning Document

## AI Coding Standards Enforcer

**Version:** 1.0  
**Date:** 5 March 2026  
**Author:** Engineering Team  
**Status:** In Development

---

## 1. Executive Summary

The AI Coding Standards Enforcer is a developer productivity tool that combines static analysis with AI-powered code review to help Python developers detect, understand, and fix coding standard violations. The tool scans any public GitHub repository, identifies PEP 8 and Pyflakes violations, generates intelligent fix suggestions using GPT-4o, and auto-applies industry-standard formatters — all through an intuitive web interface with real-time feedback.

---

## 2. Vision & Goals

### Vision

Become the go-to tool for automated Python code quality enforcement, bridging the gap between static analysis (which tells you _what_ is wrong) and developer understanding (which explains _why_ it matters and _how_ to fix it).

### Strategic Goals

| Goal                     | Description                                                                                  |
| ------------------------ | -------------------------------------------------------------------------------------------- |
| **Automate code review** | Eliminate manual effort in catching and fixing formatting/style issues.                      |
| **Educate developers**   | Provide AI explanations that teach developers about coding standards, not just enforce them. |
| **Reduce review cycles** | Enable developers to self-service code cleanup before submitting PRs.                        |
| **Scale quality**        | Make coding standards enforcement accessible to any Python project with zero configuration.  |

---

## 3. Project Architecture

### 3.1 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                     │
│  ┌───────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Scan Form │  │  Log Panel   │  │  Violation Cards     │  │
│  │           │  │  (Streaming) │  │  (Diff View, Filter) │  │
│  └─────┬─────┘  └──────┬───────┘  └──────────┬───────────┘  │
│        │               │                     │              │
│  ┌─────┴───────────────┴─────────────────────┴───────────┐  │
│  │              HTTP API Calls (fetch)                   │  │
│  └───────────────────────┬───────────────────────────────┘  │
└──────────────────────────┼──────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  FastAPI    │
                    │  Backend    │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────▼─────┐   ┌─────▼─────┐   ┌──────▼──────┐
    │ Git Clone │   │  flake8   │   │ Azure OpenAI│
    │ (subprocess)  │  Scanner  │   │  (GPT-4o)   │
    └───────────┘   └───────────┘   └─────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────▼─────┐    ┌─────▼─────┐   ┌──────▼──────┐
    │ autoflake │    │ isort +   │   │   black     │
    │           │    │ autopep8  │   │             │
    └───────────┘    └───────────┘   └─────────────┘
```

### 3.2 Directory Structure

```
coding-standards-enforcer/
├── backend/
│   ├── main.py                    # Entry point (uvicorn launch)
│   ├── pyproject.toml             # Python dependencies (uv)
│   ├── .env                       # Azure credentials
│   └── app/
│       ├── main.py                # FastAPI app, routes, CORS
│       ├── llm/
│       │   ├── llm_provider.py    # Azure OpenAI client (token caching)
│       │   └── prompts.py         # LangChain prompt templates
│       └── services/
│           ├── repo_service.py    # Git clone + URL sanitization
│           ├── scan_service.py    # flake8 runner + rule mapping (90+ rules)
│           ├── ai_service.py      # AI fix generation + response parsing
│           ├── diff_service.py    # Unified diff generation
│           ├── apply_service.py   # File-level fix application
│           └── git_service.py     # Branch, commit, push, PR creation
├── frontend/
│   ├── package.json               # React + Vite dependencies
│   ├── vite.config.js             # Dev server configuration
│   └── src/
│       ├── App.jsx                # Main SPA component (~686 lines)
│       ├── App.css                # Full UI styling (~1074 lines)
│       ├── main.jsx               # React DOM render
│       └── index.css              # Global styles
```

### 3.3 Technology Decisions

| Decision                 | Choice                      | Rationale                                                                          |
| ------------------------ | --------------------------- | ---------------------------------------------------------------------------------- |
| Backend framework        | FastAPI                     | Async-capable, native streaming support, auto-generated docs, Pydantic validation. |
| LLM provider             | Azure OpenAI (GPT-4o)       | Enterprise-grade, managed infrastructure, supports Azure AD auth.                  |
| LLM orchestration        | LangChain                   | Prompt templating, easy model swapping, chain composition.                         |
| Static analyzer          | flake8                      | De facto standard for Python linting, comprehensive PEP 8 + Pyflakes coverage.     |
| Frontend framework       | React 19                    | Component-based, large ecosystem, excellent developer experience.                  |
| Build tool               | Vite 7                      | Fast HMR, minimal config, modern ES module support.                                |
| Diff rendering           | react-diff-viewer-continued | Purpose-built split-view diff component with dark theme support.                   |
| Package manager (Python) | uv                          | Fast, modern Python package manager with lockfile support.                         |

---

## 4. Development Phases

### Phase 1: Core Scanning Engine (Completed)

**Objective:** Build the foundational scanning pipeline.

| Task                                             | Status |
| ------------------------------------------------ | ------ |
| Repository cloning with URL sanitization         | Done   |
| flake8 integration with output parsing           | Done   |
| Rule code to coding standard mapping (90+ rules) | Done   |
| Code snippet extraction (±5 lines context)       | Done   |
| Streaming scan endpoint (NDJSON)                 | Done   |
| Basic FastAPI server with CORS                   | Done   |

### Phase 2: AI Fix Generation (Completed)

**Objective:** Integrate AI-powered fix suggestions.

| Task                                                      | Status |
| --------------------------------------------------------- | ------ |
| Azure OpenAI integration via LangChain                    | Done   |
| Prompt engineering for violation explanations + fixes     | Done   |
| AI response parsing (explanation + fixed code extraction) | Done   |
| Parallel AI execution (ThreadPoolExecutor, 8 workers)     | Done   |
| Snippet deduplication to reduce redundant AI calls        | Done   |
| Unified diff generation (original vs. suggested)          | Done   |
| Token caching with auto-refresh before expiry             | Done   |

### Phase 3: Frontend Dashboard (Completed)

**Objective:** Build an interactive violation report UI.

| Task                                                   | Status |
| ------------------------------------------------------ | ------ |
| Scan form with URL input                               | Done   |
| Real-time log panel with streaming support             | Done   |
| Violation cards with expand/collapse                   | Done   |
| Side-by-side diff viewer integration                   | Done   |
| Coding standard filter chips                           | Done   |
| Severity classification (Error, High, Medium, Warning) | Done   |
| Files overview panel                                   | Done   |
| Expand All / Collapse All controls                     | Done   |
| Dark theme UI with glassmorphism design                | Done   |

### Phase 4: Auto-Fix & Export (Completed)

**Objective:** Enable automated code correction and export.

| Task                                                     | Status |
| -------------------------------------------------------- | ------ |
| autoflake integration (unused imports/variables removal) | Done   |
| isort integration (import sorting, Black-compatible)     | Done   |
| autopep8 integration (aggressive PEP 8 fixes)            | Done   |
| black integration (opinionated formatting)               | Done   |
| Post-linting re-scan for remaining violations            | Done   |
| Corrected file viewer with copy functionality            | Done   |
| Zip download of corrected repository                     | Done   |
| Linter result statistics (fixed vs. remaining)           | Done   |

### Phase 5: Polish & Hardening (Current)

**Objective:** Improve reliability, UX, and documentation.

| Task                                               | Status      |
| -------------------------------------------------- | ----------- |
| Error handling improvements                        | In Progress |
| Edge case handling (empty repos, non-Python repos) | In Progress |
| Performance optimization for large repositories    | Planned     |
| Documentation (PRD, planning docs, README)         | In Progress |
| Testing (unit tests, integration tests)            | Planned     |

### Phase 6: Advanced Features (Future)

**Objective:** Extend the platform with advanced capabilities.

| Task                                                     | Status        |
| -------------------------------------------------------- | ------------- |
| Git integration — auto-create branch, commit, push fixes | Backend Ready |
| Pull request creation via GitHub API                     | Backend Ready |
| Support for private repositories (GitHub token auth)     | Planned       |
| Multi-language support (JavaScript, TypeScript, etc.)    | Planned       |
| Custom rule configuration                                | Planned       |
| Scan history & persistent storage                        | Planned       |
| User authentication & multi-tenancy                      | Planned       |
| CI/CD pipeline integration                               | Planned       |
| Webhook-triggered scans on PR events                     | Planned       |

---

## 5. Data Flow

### 5.1 Scan Flow

```
User Input (repo URL)
    │
    ▼
sanitize_github_url()  ──→  Strip /tree/branch, append .git
    │
    ▼
clone_repository()     ──→  git clone → temp directory
    │
    ▼
run_flake8()           ──→  subprocess → parse stdout → structured violations
    │
    ▼
extract_snippet()      ──→  Read file ±5 lines around violation
    │
    ▼
Deduplicate            ──→  Cache key = (snippet, rule_code)
    │
    ▼
generate_fix()  ×N     ──→  Parallel AI calls (8 workers)
    │                        │
    │                        ├─ LangChain prompt template
    │                        ├─ Azure OpenAI GPT-4o
    │                        └─ Parse: explanation + fixed_code
    │
    ▼
generate_diff()        ──→  difflib.unified_diff(original, fixed)
    │
    ▼
Stream Results         ──→  NDJSON: {type: "result", data: {...}}
```

### 5.2 Auto-Fix Flow

```
User clicks "Run Linters & Formatters"
    │
    ▼
autoflake              ──→  Remove unused imports & variables
    │
    ▼
isort                  ──→  Sort imports (Black-compatible profile)
    │
    ▼
autopep8               ──→  Fix PEP 8 issues (aggressive mode)
    │
    ▼
black                  ──→  Opinionated code formatting
    │
    ▼
run_flake8()           ──→  Re-scan to find remaining violations
    │
    ▼
Return report          ──→  { tools_applied, remaining_violations, violations }
```

---

## 6. Risk Assessment

| Risk                                                  | Impact | Likelihood | Mitigation                                                                                                                   |
| ----------------------------------------------------- | ------ | ---------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Azure OpenAI rate limiting / quota exhaustion         | High   | Medium     | Implement snippet deduplication, caching, and request batching. Max 8 concurrent workers.                                    |
| AI generating incorrect or harmful fixes              | High   | Low        | Fixes are suggestions only (diff view); linter auto-fix uses trusted tools (black, autopep8). AI fixes are not auto-applied. |
| Large repository causing timeouts                     | Medium | Medium     | Subprocess timeouts (120s per tool). Consider async processing for very large repos.                                         |
| Azure AD token expiration mid-scan                    | Medium | Low        | Token cached with 5-minute pre-expiry refresh.                                                                               |
| Cloned repos consuming disk space                     | Medium | Medium     | Repos cloned to OS temp directories; rely on OS cleanup. Consider explicit cleanup on scan completion.                       |
| Malicious repository URLs (path traversal, injection) | High   | Low        | URL sanitization, subprocess with direct args (no shell=True), temp directory isolation.                                     |
| Frontend performance with 500+ violation cards        | Low    | Medium     | Collapsible cards reduce DOM nodes. Consider virtualization for very large result sets.                                      |

---

## 7. Resource Requirements

### Development Team

| Role              | Count | Responsibility                                                    |
| ----------------- | ----- | ----------------------------------------------------------------- |
| Backend Engineer  | 1     | FastAPI services, flake8 integration, AI pipeline, Git operations |
| Frontend Engineer | 1     | React UI, streaming integration, diff viewer, UX                  |
| DevOps / Infra    | 0.5   | Azure OpenAI provisioning, deployment, environment setup          |

### Infrastructure

| Resource                         | Purpose                                     |
| -------------------------------- | ------------------------------------------- |
| Azure OpenAI (GPT-4o deployment) | AI fix generation                           |
| Azure AD App Registration        | Service principal for OpenAI authentication |
| Dev machine with Python 3.14+    | Backend runtime                             |
| Node.js 18+                      | Frontend build & dev server                 |

---

## 8. Dependencies

### External Services

| Dependency            | Purpose           | Fallback                                                        |
| --------------------- | ----------------- | --------------------------------------------------------------- |
| Azure OpenAI API      | AI fix generation | Graceful degradation — violations shown without AI explanations |
| GitHub (public repos) | Repository source | User-provided local paths (future enhancement)                  |

### Python Packages (Key)

| Package          | Version  | Purpose                  |
| ---------------- | -------- | ------------------------ |
| fastapi          | ≥0.133.1 | Web framework            |
| flake8           | ≥7.3.0   | Static analysis          |
| langchain        | ≥1.2.10  | LLM orchestration        |
| langchain-openai | ≥1.1.10  | Azure OpenAI integration |
| azure-identity   | ≥1.25.2  | Azure AD authentication  |
| black            | ≥26.1.0  | Code formatting          |
| autoflake        | ≥2.3.1   | Unused import removal    |
| isort            | ≥5.13.0  | Import sorting           |
| autopep8         | ≥2.0.4   | PEP 8 auto-fixing        |
| uvicorn          | ≥0.41.0  | ASGI server              |
| gitpython        | ≥3.1.46  | Git operations           |

### Frontend Packages (Key)

| Package                     | Version | Purpose                 |
| --------------------------- | ------- | ----------------------- |
| react                       | ^19.2.0 | UI framework            |
| react-diff-viewer-continued | ^4.1.2  | Side-by-side diff view  |
| vite                        | ^7.3.1  | Build tool & dev server |

---

## 9. Testing Strategy

### 9.1 Unit Tests (Planned)

| Module             | Test Cases                                                                                   |
| ------------------ | -------------------------------------------------------------------------------------------- |
| `repo_service.py`  | URL sanitization (strip /tree, /blob, add .git), edge cases (trailing slashes, already .git) |
| `scan_service.py`  | flake8 output parsing, rule code mapping, snippet extraction boundary conditions             |
| `ai_service.py`    | Markdown stripping, response parsing (valid, malformed, missing sections)                    |
| `diff_service.py`  | Diff generation for identical code, single-line changes, multi-line changes                  |
| `apply_service.py` | File fix application, original code not found handling                                       |

### 9.2 Integration Tests (Planned)

| Scenario          | Description                                                                              |
| ----------------- | ---------------------------------------------------------------------------------------- |
| End-to-end scan   | Scan a known test repo and verify violation count, rule codes, and AI response structure |
| Linter pipeline   | Apply all 4 linters and verify output format and violation reduction                     |
| Download endpoint | Verify zip file is valid and contains expected files                                     |
| Streaming         | Verify NDJSON stream contains log events followed by a result event                      |

### 9.3 Frontend Tests (Planned)

| Area                | Approach                                                         |
| ------------------- | ---------------------------------------------------------------- |
| Component rendering | Verify violation cards, filter chips, log panel render correctly |
| User interactions   | Test expand/collapse, filter selection, copy-to-clipboard        |
| Streaming           | Mock fetch responses and verify progressive UI updates           |

---

## 10. Deployment Plan

### Current (Development)

| Component | How                                                      |
| --------- | -------------------------------------------------------- |
| Backend   | `uv run uvicorn app.main:app --reload` on localhost:8000 |
| Frontend  | `npm run dev` (Vite) on localhost:5173                   |

### Future (Production)

| Step | Action                                                                         |
| ---- | ------------------------------------------------------------------------------ |
| 1    | Containerize backend (Docker) with all Python linter tools pre-installed       |
| 2    | Containerize frontend (nginx serving Vite build output)                        |
| 3    | Deploy via Docker Compose or Kubernetes                                        |
| 4    | Configure Azure OpenAI credentials via environment variables / secrets manager |
| 5    | Set up reverse proxy (nginx/Caddy) for unified domain                          |
| 6    | Add health check monitoring and logging aggregation                            |

---

## 11. Milestones & Timeline

| Milestone                   | Target Date | Status      |
| --------------------------- | ----------- | ----------- |
| M1: Core scanning pipeline  | Completed   | Done        |
| M2: AI fix generation       | Completed   | Done        |
| M3: Frontend dashboard      | Completed   | Done        |
| M4: Auto-fix & export       | Completed   | Done        |
| M5: Documentation & polish  | March 2026  | In Progress |
| M6: Testing suite           | April 2026  | Planned     |
| M7: Git/PR integration (UI) | April 2026  | Planned     |
| M8: Private repo support    | May 2026    | Planned     |
| M9: Multi-language support  | Q3 2026     | Planned     |
| M10: Production deployment  | Q3 2026     | Planned     |

---

## 12. Open Questions

| #   | Question                                                                                                  | Owner   |
| --- | --------------------------------------------------------------------------------------------------------- | ------- |
| Q1  | Should we add support for custom flake8 configuration (`.flake8` or `setup.cfg`) from the scanned repo?   | Backend |
| Q2  | Should the Git integration (branch + PR creation) be exposed via the UI? Backend services already exist.  | Product |
| Q3  | What is the retention policy for cloned repositories in temp directories? Should we add explicit cleanup? | Backend |
| Q4  | Should we support local file/folder uploads as an alternative to GitHub URLs?                             | Product |
| Q5  | Should we add a "Re-scan after AI fixes applied" flow where AI-suggested fixes are written to files?      | Product |
| Q6  | What rate limiting strategy should be applied for Azure OpenAI in a multi-user deployment?                | Infra   |
| Q7  | Should we consider supporting additional Python linting tools (pylint, mypy, ruff)?                       | Product |
