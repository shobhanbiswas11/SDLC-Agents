# Code Refactoring Agent — Implementation Plan

> **Goal**: Pivot the existing `simple-agent` from a documentation/inline-comment agent into a  
> **Code Refactoring Agent** that suggests safe refactors to improve maintainability without changing behavior.

---

## Current Architecture (No Changes Needed)

These files remain **untouched** — they are already generic enough:

| File | Why It Stays |
|------|-------------|
| `api.py` | HTTP endpoints are agent-agnostic (start/message/status/stop) |
| `activities.py` | `llm_call` and `run_tool` are generic dispatchers |
| `worker.py` | Just registers workflow + activities with Temporal |
| `config_loader.py` | Only reads `name`, `description`, `parameters` from YAML → OpenAI schema |

---

## Phase 1: Agent Personality

### File: `config/agent.yaml`

**Action**: Replace the existing system prompt and update the tools list.

```yaml
# Code Refactoring Agent
# Analyzes code for smells and suggests safe refactors

id: refactoring-agent
name: Code Refactoring Agent
description: Expert AI agent that analyzes code for smells and suggests safe refactors to improve maintainability without changing behavior.

# Tools this agent can use
tools:
  - analyze_code
  - suggest_refactor
  - apply_refactor
  - diff_preview
  - run_tests
  - read_file
  - write_file
  - list_files
  - ask_user
  - github_inline_comment

system_prompt: |
  You are an expert Code Refactoring Agent. Your job is to analyze code for code smells,
  suggest safe refactors, and apply them — all without changing the code's external behavior.

  ## Core Principles
  1. **Safety First** — Never change public API signatures, return types, or observable behavior.
  2. **Explain Why** — Always explain why a refactor improves maintainability.
  3. **Risk Assessment** — Categorize every suggestion as LOW / MEDIUM / HIGH risk.
  4. **Confirm Before Apply** — ALWAYS use `ask_user` to show a diff and get approval before writing changes.
  5. **Test After Apply** — If a test command is known, run tests after every applied refactor.

  ## Your Tools
  1. **analyze_code** — Scan a file for code smells (long methods, deep nesting, duplicate code, magic numbers, god classes, dead code, poor naming). Returns structured JSON.
  2. **suggest_refactor** — Given a specific smell, generate a safe refactored version with before/after snippets.
  3. **diff_preview** — Show a unified diff comparing original vs refactored code.
  4. **apply_refactor** — Write the refactored code back to the file (local or GitHub). ALWAYS ask_user first.
  5. **run_tests** — Run the project's test suite to verify behavior is unchanged after refactoring.
  6. **read_file** — Read source files from the workspace.
  7. **write_file** — Write files to the workspace.
  8. **list_files** — List files in a directory.
  9. **ask_user** — Ask the user for clarification or confirmation. ALWAYS use before applying changes.
  10. **github_inline_comment** — Read/write/comment files on GitHub repos.

  ## Workflow
  When the user asks to refactor a file:
  1. Use `read_file` or `github_inline_comment` (action="read") to fetch the code.
  2. Use `analyze_code` to identify code smells.
  3. Present the findings to the user with risk levels.
  4. Use `suggest_refactor` to generate a safe refactored version.
  5. Use `diff_preview` to show the changes.
  6. Use `ask_user` to confirm: "Here is the diff. Approve this refactor? (yes/no)"
  7. If approved, use `apply_refactor` to write the changes.
  8. If a test command is available, use `run_tests` to verify.
  9. Report the result.

  ## Code Smell Types You Detect
  - `long_method` — Functions longer than ~30 lines
  - `deep_nesting` — More than 3 levels of indentation
  - `duplicate_code` — Repeated logic that can be extracted
  - `magic_numbers` — Hardcoded numeric/string literals
  - `god_class` — Classes doing too many things
  - `dead_code` — Unreachable or unused code
  - `poor_naming` — Variables/functions with unclear names
  - `complex_conditional` — Over-complicated if/else chains
  - `missing_error_handling` — Try/except blocks missing or too broad

  ## STRICT RULES
  - NEVER use markdown code blocks (triple backticks) in your final response.
  - NEVER change public API signatures unless the user explicitly requests it.
  - ALWAYS show a diff before applying any changes.
  - ALWAYS ask for user confirmation before modifying files.

settings:
  temperature: 0.2
  max_tokens: 4096
```

---

## Phase 2: Tool YAML Schemas

### File: `config/tools/analyze_code.yaml` (CREATE)

```yaml
# Analyze Code Tool
# Scans a file for code smells and returns structured results

name: analyze_code
description: |
  Analyze a source code file for code smells and maintainability issues.
  Returns a structured JSON report with smell type, affected lines, severity, and description.
  Use this when asked to "analyze", "scan", "review", or "find code smells" in a file.

parameters:
  type: object
  properties:
    file_path:
      type: string
      description: "Path to the file to analyze (relative to workspace or repo path like 'src/App.jsx')"
    source:
      type: string
      description: "Where to read the file from"
      enum: [local, github]
      default: local
    github_repo:
      type: string
      description: "GitHub repository in 'owner/repo' format. Required when source='github'."
      default: ""
    focus_areas:
      type: string
      description: |
        Comma-separated list of smell types to focus on.
        Options: long_method, deep_nesting, duplicate_code, magic_numbers, god_class, dead_code, poor_naming, complex_conditional, missing_error_handling.
        Leave empty to check for all types.
      default: ""
  required:
    - file_path

activity:
  name: analyze_code_activity
  timeout_seconds: 120
  retry_policy:
    max_attempts: 2
    initial_interval_seconds: 5
```

### File: `config/tools/suggest_refactor.yaml` (CREATE)

```yaml
# Suggest Refactor Tool
# Generates a safe refactored version of code for a specific smell

name: suggest_refactor
description: |
  Given a specific code smell, generate a safe refactored version of the code.
  Returns the refactored code that fixes the identified smell without changing behavior.
  The refactored code preserves the same public API and return values.

parameters:
  type: object
  properties:
    file_path:
      type: string
      description: "Path to the file being refactored"
    code_content:
      type: string
      description: "The original source code to refactor"
    smell_type:
      type: string
      description: "The type of code smell to fix"
      enum: [long_method, deep_nesting, duplicate_code, magic_numbers, god_class, dead_code, poor_naming, complex_conditional, missing_error_handling]
    instructions:
      type: string
      description: "Additional instructions for how to refactor (optional)"
      default: ""
  required:
    - file_path
    - code_content
    - smell_type

activity:
  name: suggest_refactor_activity
  timeout_seconds: 120
  retry_policy:
    max_attempts: 2
    initial_interval_seconds: 5
```

### File: `config/tools/apply_refactor.yaml` (CREATE)

```yaml
# Apply Refactor Tool
# Writes refactored code back to a file (local or GitHub)

name: apply_refactor
description: |
  Apply a refactored version of code to a file. Writes the new code back to the file.
  For GitHub sources, commits and pushes the change.
  IMPORTANT: Always show a diff and get user confirmation via ask_user BEFORE calling this tool.

parameters:
  type: object
  properties:
    file_path:
      type: string
      description: "Path to the file to update"
    refactored_code:
      type: string
      description: "The complete refactored source code to write"
    source:
      type: string
      description: "Where the file lives"
      enum: [local, github]
      default: local
    github_repo:
      type: string
      description: "GitHub repository in 'owner/repo' format. Required when source='github'."
      default: ""
    commit_message:
      type: string
      description: "Custom commit message for the GitHub push"
      default: "refactor: safe refactor applied via Code Refactoring Agent"
  required:
    - file_path
    - refactored_code

activity:
  name: apply_refactor_activity
  timeout_seconds: 120
  retry_policy:
    max_attempts: 2
    initial_interval_seconds: 5
```

### File: `config/tools/diff_preview.yaml` (CREATE)

```yaml
# Diff Preview Tool
# Shows a unified diff between original and refactored code

name: diff_preview
description: |
  Generate a unified diff comparing original code with refactored code.
  Use this to show the user exactly what changes will be made before applying a refactor.

parameters:
  type: object
  properties:
    original_code:
      type: string
      description: "The original source code"
    refactored_code:
      type: string
      description: "The refactored source code"
    file_path:
      type: string
      description: "Filename for the diff header (e.g. 'src/App.jsx')"
      default: "file"
  required:
    - original_code
    - refactored_code

activity:
  name: diff_preview_activity
  timeout_seconds: 30
  retry_policy:
    max_attempts: 1
    initial_interval_seconds: 1
```

### File: `config/tools/run_tests.yaml` (CREATE)

```yaml
# Run Tests Tool
# Executes the project's test suite to verify behavior is unchanged

name: run_tests
description: |
  Run the project's test suite to verify that a refactor did not break any behavior.
  Executes a shell command (e.g. 'pytest', 'npm test') and returns pass/fail with output.
  Use this after applying a refactor to confirm safety.

parameters:
  type: object
  properties:
    test_command:
      type: string
      description: "The shell command to run tests (e.g. 'pytest', 'npm test', 'python -m unittest')"
    working_directory:
      type: string
      description: "Directory to run the command in (default: workspace root)"
      default: "."
    timeout_seconds:
      type: integer
      description: "Maximum time in seconds to wait for tests to finish"
      default: 120
  required:
    - test_command

activity:
  name: run_tests_activity
  timeout_seconds: 180
  retry_policy:
    max_attempts: 1
    initial_interval_seconds: 1
```

### Existing Tools to KEEP as-is

| File | Status |
|------|--------|
| `read_file.yaml` | Keep — still needed to fetch code |
| `write_file.yaml` | Keep — fallback for writing |
| `list_files.yaml` | Keep — browse project structure |
| `ask_user.yaml` | Keep — confirmation gate |
| `delete_file.yaml` | Keep — may need to remove dead code files |
| `rename_file.yaml` | Keep — renaming is a valid refactor |
| `github_inline_comment.yaml` | Keep — still useful for reading/writing GitHub files |
| `grep_search.yaml` | Keep — useful for finding duplicate code |

---

## Phase 3: Tool Handlers

### File: `tools.py`

Add these 5 new handler functions and update `TOOL_HANDLERS`.

### 3.1 — `handle_analyze_code()`

```python
async def handle_analyze_code(
    file_path: str,
    source: str = "local",
    github_repo: str = "",
    focus_areas: str = "",
    workspace_path: str = ".",
    **_
) -> dict:
    """
    Fetch a file and analyze it for code smells using the LLM.
    Returns structured JSON with smell_type, line_range, severity, description.
    """
    # Step 1: Fetch the code (reuse existing helpers)
    if source == "github":
        token = os.getenv("GITHUB_TOKEN") or os.getenv("YOUR_GITHUB_ACCESS_TOKEN", "")
        resolved = await _resolve_file_path(github_repo, file_path, token)
        if not resolved:
            return {"status": "error", "error": f"Could not find '{file_path}' in repo '{github_repo}'."}
        raw_code, _ = await _fetch_github_file(github_repo, resolved, token)
        if raw_code is None:
            return {"status": "error", "error": f"Failed to fetch '{resolved}' from GitHub."}
        file_path = resolved
    else:
        path = Path(file_path) if Path(file_path).is_absolute() else Path(workspace_path) / file_path
        if not path.exists():
            return {"status": "error", "error": f"File not found: {path}"}
        raw_code = path.read_text(encoding="utf-8")

    # Step 2: Call the LLM with a smell-detection prompt
    result = _call_llm_for_refactoring(
        code=raw_code,
        file_path=file_path,
        action="analyze",
        focus_areas=focus_areas
    )

    return {
        "status": "success",
        "file_path": file_path,
        "analysis": result,
        "line_count": len(raw_code.splitlines())
    }
```

### 3.2 — `handle_suggest_refactor()`

```python
async def handle_suggest_refactor(
    file_path: str,
    code_content: str,
    smell_type: str,
    instructions: str = "",
    workspace_path: str = ".",
    **_
) -> dict:
    """
    Given a code smell type, generate a safe refactored version of the code.
    """
    result = _call_llm_for_refactoring(
        code=code_content,
        file_path=file_path,
        action="refactor",
        smell_type=smell_type,
        instructions=instructions
    )

    return {
        "status": "success",
        "file_path": file_path,
        "smell_type": smell_type,
        "refactored_code": result
    }
```

### 3.3 — `handle_apply_refactor()`

```python
async def handle_apply_refactor(
    file_path: str,
    refactored_code: str,
    source: str = "local",
    github_repo: str = "",
    commit_message: str = "refactor: safe refactor applied via Code Refactoring Agent",
    workspace_path: str = ".",
    **_
) -> dict:
    """
    Write the refactored code back to the file.
    For GitHub: fetches the current SHA, then pushes the update.
    For local: writes directly to disk.
    """
    if source == "github":
        token = os.getenv("GITHUB_TOKEN") or os.getenv("YOUR_GITHUB_ACCESS_TOKEN", "")
        if not github_repo:
            return {"status": "error", "error": "github_repo is required when source='github'."}

        resolved = await _resolve_file_path(github_repo, file_path, token)
        if not resolved:
            return {"status": "error", "error": f"Could not find '{file_path}' in repo '{github_repo}'."}

        # Need the current SHA to update
        _, sha = await _fetch_github_file(github_repo, resolved, token)
        if sha is None:
            return {"status": "error", "error": f"Failed to get SHA for '{resolved}'."}

        # Push with custom commit message
        payload = {
            "message": commit_message,
            "content": base64.b64encode(refactored_code.encode()).decode(),
            "sha": sha
        }
        async with aiohttp.ClientSession() as session:
            url = f"https://api.github.com/repos/{github_repo}/contents/{resolved.lstrip('/')}"
            async with session.put(url, headers=_github_headers(token), json=payload) as r:
                if r.status in (200, 201):
                    return {"status": "success", "file_path": resolved, "message": f"Refactored '{resolved}' pushed to GitHub."}
                return {"status": "error", "error": f"GitHub push failed with status {r.status}."}
    else:
        path = Path(file_path) if Path(file_path).is_absolute() else Path(workspace_path) / file_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(refactored_code, encoding="utf-8")
        return {"status": "success", "file_path": str(path), "message": f"Refactored '{path.name}' saved locally."}
```

### 3.4 — `handle_diff_preview()`

```python
import difflib

async def handle_diff_preview(
    original_code: str,
    refactored_code: str,
    file_path: str = "file",
    **_
) -> dict:
    """
    Generate a unified diff between original and refactored code.
    Uses Python's difflib — no external dependencies.
    """
    original_lines = original_code.splitlines(keepends=True)
    refactored_lines = refactored_code.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        refactored_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm=""
    )

    diff_text = "\n".join(diff)

    if not diff_text.strip():
        return {"status": "success", "diff": "", "message": "No changes detected."}

    # Count additions and deletions
    additions = sum(1 for line in diff_text.splitlines() if line.startswith("+") and not line.startswith("+++"))
    deletions = sum(1 for line in diff_text.splitlines() if line.startswith("-") and not line.startswith("---"))

    return {
        "status": "success",
        "diff": diff_text,
        "additions": additions,
        "deletions": deletions,
        "message": f"Diff: +{additions} -{deletions} lines"
    }
```

### 3.5 — `handle_run_tests()`

```python
import subprocess

async def handle_run_tests(
    test_command: str,
    working_directory: str = ".",
    timeout_seconds: int = 120,
    workspace_path: str = ".",
    **_
) -> dict:
    """
    Run the project's test suite and capture the output.
    Returns pass/fail with stdout/stderr.
    """
    work_dir = Path(working_directory) if Path(working_directory).is_absolute() else Path(workspace_path) / working_directory

    if not work_dir.exists():
        return {"status": "error", "error": f"Directory not found: {work_dir}"}

    try:
        result = subprocess.run(
            test_command,
            shell=True,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=timeout_seconds
        )

        passed = result.returncode == 0
        output = result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout  # Truncate long output
        error_output = result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr

        return {
            "status": "success",
            "passed": passed,
            "return_code": result.returncode,
            "stdout": output,
            "stderr": error_output,
            "message": "All tests passed." if passed else f"Tests FAILED (exit code {result.returncode})."
        }

    except subprocess.TimeoutExpired:
        return {"status": "error", "error": f"Tests timed out after {timeout_seconds} seconds."}
    except Exception as e:
        return {"status": "error", "error": f"Failed to run tests: {str(e)}"}
```

### 3.6 — Refactoring-Specific LLM Prompt Function

Add this new function alongside the existing `_call_llm_for_comments`:

```python
def _call_llm_for_refactoring(
    code: str,
    file_path: str,
    action: str,
    smell_type: str = "",
    focus_areas: str = "",
    instructions: str = ""
) -> str:
    """
    Call Azure OpenAI with refactoring-specific prompts.
    Similar to _call_llm_for_comments but for code analysis and refactoring.
    """
    from openai import AzureOpenAI
    from azure.identity import ClientSecretCredential

    # --- Azure client setup (same as _call_llm_for_comments) ---
    tenant_id = os.getenv("AZURE_TENANT_ID", "")
    client_id = os.getenv("AZURE_CLIENT_ID", "")
    client_secret = os.getenv("AZURE_CLIENT_SECRET", "")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    deployment = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")

    if tenant_id and client_id and client_secret:
        cred = ClientSecretCredential(tenant_id, client_id, client_secret)
        token_obj = cred.get_token("https://cognitiveservices.azure.com/.default")
        client = AzureOpenAI(azure_endpoint=endpoint, api_version=api_version, api_key=token_obj.token)
    else:
        client = AzureOpenAI(azure_endpoint=endpoint, api_version=api_version, api_key=os.getenv("AZURE_OPENAI_API_KEY", ""))

    # --- Build prompt based on action ---
    if action == "analyze":
        focus_instruction = ""
        if focus_areas:
            focus_instruction = f"\nFocus only on these smell types: {focus_areas}"

        system_msg = (
            "You are a code quality analyst. Analyze the given code for code smells and "
            "maintainability issues. Return ONLY a valid JSON array (no markdown fences, no explanation).\n"
            "Each item must have these fields:\n"
            '  - "smell_type": one of [long_method, deep_nesting, duplicate_code, magic_numbers, '
            "god_class, dead_code, poor_naming, complex_conditional, missing_error_handling]\n"
            '  - "line_start": integer line number where the issue begins\n'
            '  - "line_end": integer line number where the issue ends\n'
            '  - "severity": one of ["low", "medium", "high"]\n'
            '  - "description": brief explanation of the issue and why it matters\n'
            '  - "suggestion": one-line suggestion for how to fix it\n'
            "If no smells are found, return an empty array: []"
        )
        user_msg = f"Analyze this {Path(file_path).suffix} file for code smells:{focus_instruction}\n\n{code}"

    elif action == "refactor":
        system_msg = (
            "You are a code refactoring expert. Apply a safe refactor to fix the specified code smell.\n"
            "RULES:\n"
            "1. Do NOT change the public API (function signatures, class interfaces, return types).\n"
            "2. Do NOT change observable behavior.\n"
            "3. Keep the same imports unless adding new internal helpers.\n"
            "4. Return ONLY the refactored code — no markdown fences, no explanation."
        )
        extra = f"\nAdditional instructions: {instructions}" if instructions else ""
        user_msg = (
            f"Refactor this code to fix the '{smell_type}' code smell.{extra}\n\n"
            f"Original code:\n{code}"
        )

    elif action == "verify":
        system_msg = (
            "You are a code safety reviewer. Compare the original and refactored code.\n"
            "Check:\n"
            "1. Same public API (function/class signatures unchanged)\n"
            "2. Same return values for all inputs\n"
            "3. No new side effects\n"
            "4. No removed error handling\n"
            'Return ONLY a JSON object: {"safe": true/false, "reason": "explanation"}'
        )
        user_msg = f"Original:\n{code}\n\nRefactored:\n{instructions}"

    else:
        return code

    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.2
    )
    return response.choices[0].message.content or code
```

### 3.7 — Updated `TOOL_HANDLERS` Dict

```python
TOOL_HANDLERS = {
    # --- Refactoring tools (new) ---
    "analyze_code": handle_analyze_code,
    "suggest_refactor": handle_suggest_refactor,
    "apply_refactor": handle_apply_refactor,
    "diff_preview": handle_diff_preview,
    "run_tests": handle_run_tests,

    # --- Existing tools (keep) ---
    "github_inline_comment": handle_github_inline_comment,
    "read_file": handle_read_file,
    "write_file": handle_write_file,
    "rename_file": handle_rename_file,
    "delete_file": handle_delete_file,
    "list_files": handle_list_files,
    "ask_user": handle_ask_user,
}
```

---

## Phase 4: Workflow Adjustments

### File: `workflow.py`

### 4.1 — Increase `max_steps`

Refactoring involves more tool calls than simple documentation:
analyze → suggest → diff → ask_user → apply → run_tests → report = ~7 steps minimum.

```python
# Change in _process_message():
max_steps = 15  # Was 10, now 15 for refactoring workflows
```

### 4.2 — Add Confirmation Gate for `apply_refactor`

Inside the tool execution loop in `_process_message()`, add a safety check before `apply_refactor`:

```python
# Inside the for loop that processes tool_calls:

if tool_name == "ask_user":
    # ... existing ask_user logic (unchanged) ...

elif tool_name == "apply_refactor":
    # SAFETY GATE: If the workflow hasn't gotten user approval yet,
    # force an ask_user step. The system prompt already instructs the
    # LLM to always ask first, but this is a code-level backup.
    if not self._user_approved_refactor:
        self._status = "waiting_for_user"
        self._waiting_for_user = True
        self._last_response = "⚠️ A refactor is about to be applied. Approve? (yes/no)"

        await workflow.wait_condition(
            lambda: not self._waiting_for_user,
            timeout=timedelta(hours=1)
        )
        self._status = "thinking"

        if self._user_answer.strip().lower() not in ("yes", "y", "approve"):
            tool_result = {"status": "cancelled", "message": "Refactor was rejected by the user."}
        else:
            self._user_approved_refactor = True
            tool_result = await workflow.execute_activity(
                "run_tool",
                args=[tool_name, tool_args, self._workspace_path],
                start_to_close_timeout=timedelta(seconds=300),
            )
    else:
        tool_result = await workflow.execute_activity(
            "run_tool",
            args=[tool_name, tool_args, self._workspace_path],
            start_to_close_timeout=timedelta(seconds=300),
        )
    # Reset approval flag after each apply
    self._user_approved_refactor = False

else:
    # ... existing generic tool execution ...
```

### 4.3 — Add `_user_approved_refactor` to `__init__`

```python
def __init__(self):
    # ... existing fields ...
    self._user_approved_refactor: bool = False
```

---

## Phase 5: UI Adjustments

### File: `docu-agent-ui/src/app/page.tsx`

### 5.1 — Rename Tab

```tsx
// Change the operations tab definition:
{ id: "operations", Icon: TerminalIcon, label: "Refactoring Agent" },
```

### 5.2 — Update Placeholder Text

```tsx
// In the Agent Operations form:
<TextField
  placeholder="e.g., Analyze App.jsx from owner/repo for code smells"
  ...
/>
```

### 5.3 — Add Diff Renderer

Install a diff viewer package:

```bash
cd docu-agent-ui
npm install react-diff-viewer-continued
```

Then add a diff detection component inside the message renderer:

```tsx
import ReactDiffViewer from 'react-diff-viewer-continued';

// Inside the opsMessages.map() renderer:
// Detect if the AI message contains a unified diff
const isDiff = msg.text.startsWith("---") || msg.text.includes("@@");

{isDiff ? (
  <ReactDiffViewer
    oldValue={extractOriginal(msg.text)}
    newValue={extractRefactored(msg.text)}
    splitView={false}
    useDarkTheme={themeMode === 'dark'}
  />
) : (
  <ReactMarkdown ...>{msg.text}</ReactMarkdown>
)}
```

### 5.4 — Add Approval Buttons

When `waiting_for_user` is detected during polling, show approve/reject buttons:

```tsx
// When the last message starts with "⚠️" or "❓" and contains "Approve":
{msg.text.includes("Approve") && (
  <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
    <Button
      variant="contained"
      color="success"
      onClick={() => {
        setOpsInput("yes");
        handleOpsSubmit({ preventDefault: () => {} });
      }}
    >
      ✅ Approve Refactor
    </Button>
    <Button
      variant="outlined"
      color="error"
      onClick={() => {
        setOpsInput("no");
        handleOpsSubmit({ preventDefault: () => {} });
      }}
    >
      ❌ Reject
    </Button>
  </Stack>
)}
```

### 5.5 — Add Risk Badges

Parse severity from AI responses and show colored chips:

```tsx
// Helper to detect severity keywords in AI messages
const severityBadge = (text: string) => {
  const badges = [];
  if (text.includes('"high"') || text.includes('HIGH'))
    badges.push(<Chip label="HIGH" size="small" sx={{ bgcolor: 'rgba(239,68,68,0.2)', color: '#ef4444' }} />);
  if (text.includes('"medium"') || text.includes('MEDIUM'))
    badges.push(<Chip label="MEDIUM" size="small" sx={{ bgcolor: 'rgba(245,158,11,0.2)', color: '#f59e0b' }} />);
  if (text.includes('"low"') || text.includes('LOW'))
    badges.push(<Chip label="LOW" size="small" sx={{ bgcolor: 'rgba(16,185,129,0.2)', color: '#10b981' }} />);
  return badges;
};
```

---

## Phase 6: Dependencies

### File: `requirements.txt`

No new dependencies needed — `difflib` and `subprocess` are Python stdlib.

**Optional** (if you want static analysis without LLM):
```
radon          # Cyclomatic complexity scoring for Python
```

### File: `docu-agent-ui/package.json`

```bash
npm install react-diff-viewer-continued
```

---

## Implementation Order (Checklist)

```
[ ] 1. config/agent.yaml              — New system prompt + updated tools list
[ ] 2. config/tools/analyze_code.yaml  — Create
[ ] 3. config/tools/suggest_refactor.yaml — Create
[ ] 4. config/tools/apply_refactor.yaml   — Create
[ ] 5. config/tools/diff_preview.yaml     — Create
[ ] 6. config/tools/run_tests.yaml        — Create
[ ] 7. tools.py — Add _call_llm_for_refactoring()
[ ] 8. tools.py — Add handle_analyze_code()
[ ] 9. tools.py — Add handle_suggest_refactor()
[ ] 10. tools.py — Add handle_apply_refactor()
[ ] 11. tools.py — Add handle_diff_preview()
[ ] 12. tools.py — Add handle_run_tests()
[ ] 13. tools.py — Update TOOL_HANDLERS dict
[ ] 14. workflow.py — Increase max_steps to 15
[ ] 15. workflow.py — Add _user_approved_refactor flag
[ ] 16. workflow.py — Add confirmation gate for apply_refactor
[ ] 17. page.tsx — Rename tab to "Refactoring Agent"
[ ] 18. page.tsx — Update placeholder text
[ ] 19. page.tsx — Install react-diff-viewer-continued
[ ] 20. page.tsx — Add diff renderer component
[ ] 21. page.tsx — Add approve/reject buttons
[ ] 22. page.tsx — Add severity badges
[ ] 23. End-to-end test with a real repo
```

---

## Example User Flow

```
User: "Analyze src/utils.py from ArifRahaman/blog-website for code smells"

→ LLM calls: analyze_code(file_path="src/utils.py", source="github", github_repo="ArifRahaman/blog-website")
→ Tool fetches file from GitHub, sends to LLM with smell-detection prompt
→ Returns JSON:
  [
    {"smell_type": "long_method", "line_start": 45, "line_end": 120, "severity": "high", "description": "Function 'process_data' is 75 lines long", "suggestion": "Extract validation and transformation into separate functions"},
    {"smell_type": "magic_numbers", "line_start": 23, "line_end": 23, "severity": "low", "description": "Hardcoded value 86400", "suggestion": "Extract to SECONDS_PER_DAY constant"}
  ]

Agent: "Found 2 issues:
  🔴 HIGH — long_method at lines 45-120: Function 'process_data' is 75 lines long
  🟢 LOW — magic_numbers at line 23: Hardcoded value 86400
  Would you like me to refactor the high-severity issue first?"

User: "Yes, fix the long method"

→ LLM calls: suggest_refactor(file_path="src/utils.py", code_content="...", smell_type="long_method")
→ Returns refactored code

→ LLM calls: diff_preview(original_code="...", refactored_code="...", file_path="src/utils.py")
→ Returns unified diff: +12 -75 lines

→ LLM calls: ask_user(question="Here is the diff. Approve? (yes/no)")
→ Workflow pauses

User: "yes"

→ LLM calls: apply_refactor(file_path="src/utils.py", refactored_code="...", source="github", github_repo="ArifRahaman/blog-website")
→ Pushes to GitHub

→ LLM calls: run_tests(test_command="pytest", working_directory=".")
→ Returns: {"passed": true, "message": "All tests passed."}

Agent: "Refactored 'src/utils.py' — extracted 3 helper functions from process_data().
  Pushed to GitHub. All tests passing."
```

---

## Files Changed Summary

| File | Action |
|------|--------|
| `config/agent.yaml` | EDIT — new system prompt, updated tools list |
| `config/tools/analyze_code.yaml` | CREATE |
| `config/tools/suggest_refactor.yaml` | CREATE |
| `config/tools/apply_refactor.yaml` | CREATE |
| `config/tools/diff_preview.yaml` | CREATE |
| `config/tools/run_tests.yaml` | CREATE |
| `tools.py` | EDIT — 5 new handlers + 1 new LLM prompt function + updated TOOL_HANDLERS |
| `workflow.py` | EDIT — max_steps=15, confirmation gate, new flag |
| `page.tsx` | EDIT — tab rename, placeholder, diff viewer, approve buttons, badges |
| `activities.py` | NO CHANGE |
| `worker.py` | NO CHANGE |
| `api.py` | NO CHANGE |
| `config_loader.py` | NO CHANGE |
