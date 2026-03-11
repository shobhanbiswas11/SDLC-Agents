# Product Requirement Document (PRD)

## AI Coding Standards Enforcer

**Version:** 1.0  
**Date:** 5 March 2026  
**Author:** Engineering Team  
**Status:** In Development

---

## 1. Overview

The **AI Coding Standards Enforcer** is a full-stack web application that automates Python code quality enforcement. Users provide a GitHub repository URL, and the tool clones the repository, scans it for coding standard violations using static analysis (flake8), generates AI-powered fix suggestions using Azure OpenAI (GPT-4o), and provides automated formatting via industry-standard linters and formatters.

---

## 2. Problem Statement

Maintaining consistent coding standards across Python codebases is a manual, time-consuming, and error-prone process. Developers often:

- Miss subtle PEP 8 violations during code reviews.
- Lack clear explanations for _why_ a specific pattern violates a standard.
- Spend significant time manually fixing formatting, import ordering, and whitespace issues.
- Struggle to onboard new team members to project-specific coding conventions.

There is a need for an intelligent tool that not only detects violations but also **explains** them and **suggests or auto-applies fixes**.

---

## 3. Objectives

| #   | Objective                                                                                                            |
| --- | -------------------------------------------------------------------------------------------------------------------- |
| O1  | Automate detection of Python coding standard violations in any public GitHub repository.                             |
| O2  | Provide AI-generated explanations and fix suggestions for each violation.                                            |
| O3  | Allow one-click auto-formatting using industry-standard linters (autoflake, isort, autopep8, black).                 |
| O4  | Deliver a rich, interactive web UI with real-time scan progress, violation drill-downs, and side-by-side diff views. |
| O5  | Enable users to download the corrected codebase as a zip archive or copy corrected files directly from the browser.  |

---

## 4. Target Users

| Persona                     | Description                                                                                                  |
| --------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Individual Developers**   | Python developers who want to quickly audit and clean up their code against PEP 8 and Pyflakes standards.    |
| **Team Leads / Reviewers**  | Engineers who review pull requests and want an automated pre-check of coding standards before manual review. |
| **Students / Learners**     | Developers learning Python best practices who benefit from AI explanations of why code violates a standard.  |
| **Open-Source Maintainers** | Maintainers who want to enforce consistent style across community contributions.                             |

---

## 5. Functional Requirements

### 5.1 Repository Scanning

| ID   | Requirement                                                                                                                                                                         | Priority |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| FR-1 | The system shall accept a GitHub repository URL (HTTPS format) as input.                                                                                                            | P0       |
| FR-2 | The system shall sanitize GitHub URLs, stripping `/tree/<branch>`, `/blob/...` suffixes, and appending `.git` if missing.                                                           | P0       |
| FR-3 | The system shall clone the repository into a temporary directory on the server.                                                                                                     | P0       |
| FR-4 | The system shall run **flake8** static analysis on the cloned repository.                                                                                                           | P0       |
| FR-5 | The system shall parse flake8 output and extract file path, line number, column, rule code, and violation message for each issue.                                                   | P0       |
| FR-6 | Each violation shall be enriched with the coding standard name (e.g., "PEP 8 — Whitespace") and a human-readable rule description via an internal mapping of 90+ flake8 rule codes. | P1       |
| FR-7 | The system shall extract a surrounding code snippet (±5 lines of context) for each violation to provide to the AI model.                                                            | P0       |

### 5.2 AI-Powered Fix Suggestions

| ID    | Requirement                                                                                                                                  | Priority |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| FR-8  | The system shall send each violation's code snippet, violation message, rule code, and coding standard to Azure OpenAI GPT-4o via LangChain. | P0       |
| FR-9  | The AI shall return: (a) a 1–2 sentence **explanation** of why the code violates the standard, and (b) the **corrected code**.               | P0       |
| FR-10 | The system shall deduplicate identical snippets + rule code combinations to avoid redundant AI calls.                                        | P1       |
| FR-11 | AI calls shall be executed in parallel (up to 8 concurrent workers) for performance.                                                         | P1       |
| FR-12 | The system shall generate a unified diff between the original and AI-suggested code for each violation.                                      | P0       |

### 5.3 Automated Linting & Formatting

| ID    | Requirement                                                                                                             | Priority |
| ----- | ----------------------------------------------------------------------------------------------------------------------- | -------- |
| FR-13 | The system shall run **autoflake** to remove unused imports and variables.                                              | P0       |
| FR-14 | The system shall run **isort** (with Black-compatible profile) to sort and organize imports.                            | P0       |
| FR-15 | The system shall run **autopep8** (aggressive mode) to auto-fix PEP 8 violations.                                       | P0       |
| FR-16 | The system shall run **black** to apply opinionated code formatting.                                                    | P0       |
| FR-17 | After applying linters, the system shall re-scan with flake8 and report remaining violations that require manual fixes. | P0       |
| FR-18 | The system shall report which tools were successfully applied and the count of violations fixed vs. remaining.          | P1       |

### 5.4 File Download & Viewing

| ID    | Requirement                                                                                                                 | Priority |
| ----- | --------------------------------------------------------------------------------------------------------------------------- | -------- |
| FR-19 | The system shall provide a downloadable `.zip` archive of the corrected repository.                                         | P0       |
| FR-20 | The system shall expose corrected Python file contents via API for in-browser viewing.                                      | P1       |
| FR-21 | The frontend shall display corrected files in expandable panels with a "Copy" button for each file and a "Copy All" option. | P1       |

### 5.5 Real-Time Progress Streaming

| ID    | Requirement                                                                                                                                                   | Priority |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| FR-22 | The `/scan` endpoint shall stream progress as newline-delimited JSON (NDJSON) with event types: `log`, `result`, and `error`.                                 | P0       |
| FR-23 | The frontend shall display a live log panel showing timestamped progress messages with auto-scroll.                                                           | P0       |
| FR-24 | Progress updates shall include: clone status, violation count, snippet preparation count, and AI fix generation progress (e.g., "AI fixes generated: 15/42"). | P1       |

### 5.6 Frontend UI

| ID    | Requirement                                                                                                                          | Priority |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------ | -------- |
| FR-25 | The UI shall be a single-page application with a dark-themed, modern design.                                                         | P1       |
| FR-26 | Violations shall be displayed as collapsible cards showing severity badge, rule code, file location, and standard tag in the header. | P0       |
| FR-27 | Expanded violation cards shall show: rule info, AI explanation, and a side-by-side diff view (using `react-diff-viewer-continued`).  | P0       |
| FR-28 | The UI shall provide filter chips to filter violations by coding standard (e.g., "PEP 8 — Whitespace", "Pyflakes — Imports").        | P1       |
| FR-29 | The UI shall show a "Files Affected" overview listing all files and their violation counts.                                          | P1       |
| FR-30 | The UI shall support "Expand All" and "Collapse All" controls for violation cards.                                                   | P2       |
| FR-31 | Violations shall display a severity level (Error, High, Medium, Warning) derived from the rule code prefix.                          | P1       |

---

## 6. Non-Functional Requirements

| ID    | Requirement                                                                                                                      | Category    |
| ----- | -------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| NFR-1 | The backend API shall respond to scan requests with streamed output within 2 seconds of receiving the request (first log event). | Performance |
| NFR-2 | AI fix generation shall process up to 8 violations concurrently to minimize total scan time.                                     | Performance |
| NFR-3 | The system shall handle repositories up to 10,000 Python files without crashing.                                                 | Scalability |
| NFR-4 | Azure AD tokens for OpenAI shall be cached and refreshed 5 minutes before expiry to avoid authentication failures.               | Reliability |
| NFR-5 | The frontend shall render smoothly with up to 500 violation cards without noticeable lag.                                        | Performance |
| NFR-6 | The backend shall sanitize all file paths and repository URLs to prevent path traversal or injection attacks.                    | Security    |
| NFR-7 | Cloned repositories shall be stored in OS-managed temp directories and are ephemeral.                                            | Security    |
| NFR-8 | CORS shall be restricted to allowed frontend origins (`localhost:5173`).                                                         | Security    |
| NFR-9 | The application shall gracefully handle and report errors (malformed URLs, clone failures, AI failures) without crashing.        | Reliability |

---

## 7. Tech Stack

### Backend

| Component          | Technology                        |
| ------------------ | --------------------------------- |
| Web Framework      | FastAPI (Python)                  |
| Static Analysis    | flake8                            |
| Auto-formatters    | autoflake, isort, autopep8, black |
| AI / LLM           | Azure OpenAI GPT-4o via LangChain |
| Authentication     | Azure AD (ClientSecretCredential) |
| Git Operations     | subprocess (`git clone`)          |
| Package Management | uv (with `pyproject.toml`)        |
| Server             | Uvicorn (ASGI)                    |

### Frontend

| Component   | Technology                  |
| ----------- | --------------------------- |
| Framework   | React 19                    |
| Build Tool  | Vite 7                      |
| Diff Viewer | react-diff-viewer-continued |
| Linting     | ESLint                      |

---

## 8. API Specification

### 8.1 `GET /`

**Description:** Health check endpoint.  
**Response:** `{ "status": "Backend running" }`

### 8.2 `POST /scan`

**Description:** Clone a GitHub repository, run flake8 analysis, generate AI fix suggestions, and stream results.  
**Request Body:**

```json
{ "repo_url": "https://github.com/user/repo" }
```

**Response:** Streamed NDJSON with `log`, `result`, and `error` events.  
**Result payload:**

```json
{
  "repo_path": "/tmp/xxx",
  "total_violations": 42,
  "violations": [
    {
      "file": "/tmp/xxx/module.py",
      "file_relative": "module.py",
      "line": 10,
      "column": 5,
      "snippet_start_line": 5,
      "rule_code": "E225",
      "rule_standard": "PEP 8 — Whitespace",
      "rule_description": "Missing whitespace around operator",
      "violation": "E225 missing whitespace around operator",
      "explanation": "PEP 8 requires spaces around binary operators for readability.",
      "original_code": "x=1+2",
      "suggested_code": "x = 1 + 2",
      "diff": "--- \n+++ \n@@ ... @@\n-x=1+2\n+x = 1 + 2"
    }
  ]
}
```

### 8.3 `POST /apply-linters`

**Description:** Run autoflake, isort, autopep8, and black on a previously cloned repository, then re-scan.  
**Request Body:**

```json
{ "repo_path": "/tmp/xxx" }
```

**Response:**

```json
{
  "tools_applied": ["autoflake", "isort", "autopep8", "black"],
  "remaining_violations": 3,
  "violations": [...]
}
```

### 8.4 `GET /download-fixed?repo_path=...`

**Description:** Download the corrected repository as a `.zip` file.

### 8.5 `GET /corrected-files?repo_path=...`

**Description:** Return the contents of all Python files in the corrected repository for in-browser viewing.  
**Response:**

```json
{
  "files": {
    "module.py": "import os\n...",
    "utils/helper.py": "def greet(): ..."
  }
}
```

---

## 9. User Flow

```
1. User enters a GitHub repository URL in the input field
2. User clicks "Scan Repository"
3. Live log panel shows real-time progress:
   a. Cloning repository
   b. Running flake8 analysis
   c. Extracting code snippets
   d. Generating AI fixes (with progress counter)
4. Scan results appear:
   a. Standards filter chips (clickable to filter)
   b. Files overview showing affected files
   c. Violation cards (collapsible) with severity, rule, location
5. User expands a violation card to see:
   a. Rule details and coding standard reference
   b. AI-generated explanation
   c. Side-by-side diff (original vs. fixed code)
6. User clicks "Run Linters & Formatters" (Step 2)
7. System applies autoflake → isort → autopep8 → black
8. Results show violations fixed vs. remaining
9. Corrected file contents auto-load in expandable panels
10. User can:
    a. Copy individual files or all files
    b. Download corrected repo as .zip
```

---

## 10. Assumptions & Constraints

| #   | Item                                                                                                                                                |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| A1  | Only **public** GitHub repositories are supported for scanning (no authentication for cloning).                                                     |
| A2  | The tool currently supports **Python** files only (`.py`, `.pyw`).                                                                                  |
| A3  | AI fix generation requires valid **Azure AD credentials** (tenant ID, client ID, client secret) configured via environment variables.               |
| A4  | The Azure OpenAI deployment uses **GPT-4o** model.                                                                                                  |
| A5  | Cloned repositories are ephemeral — stored in OS temp directories with no persistence across server restarts.                                       |
| A6  | The tool runs linters via subprocess, requiring `flake8`, `autoflake`, `isort`, `autopep8`, and `black` to be installed in the backend environment. |
| A7  | The application is designed for single-user / local development use and does not currently include authentication, multi-tenancy, or rate limiting. |

---

## 11. Out of Scope (v1.0)

- Support for languages other than Python.
- Integration with CI/CD pipelines.
- User authentication and authorization.
- Persistent storage of scan results or history.
- Git branch creation, commit, and pull request automation from the UI (backend services exist but are not exposed via API endpoints).
- Custom linting rule configuration by users.
- Support for private repositories.
- Multi-tenancy and concurrent user support at scale.

---

## 12. Success Metrics

| Metric               | Target                                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------------------ |
| Scan completion rate | ≥ 95% of valid GitHub URLs should complete scanning without errors.                                    |
| AI fix accuracy      | ≥ 80% of AI-suggested fixes should resolve the flagged violation without introducing new issues.       |
| Linter fix rate      | autoflake + isort + autopep8 + black should resolve ≥ 70% of detected violations automatically.        |
| Scan latency         | A repository with ~100 violations should complete full scan (clone + analyze + AI) in under 3 minutes. |
| User satisfaction    | Users should be able to understand violations and their fixes without external documentation.          |

---

## 13. Glossary

| Term             | Definition                                                                                              |
| ---------------- | ------------------------------------------------------------------------------------------------------- |
| **PEP 8**        | Python Enhancement Proposal 8 — the official style guide for Python code.                               |
| **flake8**       | A Python linting tool that checks for PEP 8 compliance, Pyflakes logical errors, and McCabe complexity. |
| **autoflake**    | A tool that removes unused imports and variables from Python code.                                      |
| **isort**        | A Python utility to sort and organize imports according to PEP 8.                                       |
| **autopep8**     | A tool that automatically formats Python code to conform to PEP 8.                                      |
| **black**        | An opinionated Python code formatter that enforces a consistent style.                                  |
| **NDJSON**       | Newline-Delimited JSON — a format for streaming JSON objects, one per line.                             |
| **LangChain**    | A framework for building applications powered by large language models (LLMs).                          |
| **Azure OpenAI** | Microsoft's cloud-hosted OpenAI API service.                                                            |
