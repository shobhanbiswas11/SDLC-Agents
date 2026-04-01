"""
agent.py — Core: Azure OpenAI client, history management, tool schemas, ReAct loop.
Replaces the old orchestrator.py + activities.py + config_loader.py.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import yaml
from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console()

# ---------------------------------------------------------------------------
# Azure OpenAI client (cached, refreshed every 30 min)
# ---------------------------------------------------------------------------
_client = None
_client_ts = 0.0
_CLIENT_TTL = 1800


def get_client():
    global _client, _client_ts
    if _client and (time.time() - _client_ts) < _CLIENT_TTL:
        return _client

    from openai import AsyncAzureOpenAI
    from azure.identity import ClientSecretCredential

    endpoint   = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_ver    = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    tenant_id  = os.getenv("AZURE_TENANT_ID", "")
    client_id  = os.getenv("AZURE_CLIENT_ID", "")
    secret     = os.getenv("AZURE_CLIENT_SECRET", "")

    if tenant_id and client_id and secret:
        cred   = ClientSecretCredential(tenant_id, client_id, secret)
        token  = cred.get_token("https://cognitiveservices.azure.com/.default")
        client = AsyncAzureOpenAI(azure_endpoint=endpoint, api_version=api_ver, api_key=token.token)
    else:
        client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_version=api_ver,
            api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        )

    _client, _client_ts = client, time.time()
    return client


# ---------------------------------------------------------------------------
# Token-aware history trimmer
# ---------------------------------------------------------------------------

def _count_tokens(messages: list[dict], model: str = "gpt-4o") -> int:
    try:
        import tiktoken
        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        n = 3
        for m in messages:
            n += 3
            for v in m.values():
                if v is not None:
                    n += len(enc.encode(str(v)))
        return n
    except ImportError:
        return sum(len(str(v)) for m in messages for v in m.values() if v) // 4


def trim_history(messages: list[dict], max_tokens: int = 120_000) -> list[dict]:
    system   = [m for m in messages if m.get("role") == "system"]
    rest     = [m for m in messages if m.get("role") != "system"]
    while len(rest) > 1 and _count_tokens(system + rest) > max_tokens:
        dropped = rest.pop(0)
        # Remove orphaned tool-result messages that followed the dropped turn
        if dropped.get("role") == "assistant" and dropped.get("tool_calls"):
            while rest and rest[0].get("role") == "tool":
                rest.pop(0)
        while rest and rest[0].get("role") == "tool":
            rest.pop(0)
    return system + rest


# ---------------------------------------------------------------------------
# System prompt loader
# ---------------------------------------------------------------------------

def load_system_prompt() -> str:
    cfg_path = Path(__file__).parent / "config" / "agent.yaml"
    with open(cfg_path, encoding="utf-8-sig") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("system_prompt", "You are a helpful AI assistant.")


# ---------------------------------------------------------------------------
# Tool schemas (inline — no YAML config directory needed)
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the full text content of a file inside the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file (relative to workspace or absolute)."},
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or overwrite a file inside the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Destination path (relative to workspace or absolute)."},
                    "content":   {"type": "string", "description": "Full file content to write."},
                },
                "required": ["file_path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Recursively list all files in a directory (skips venv, node_modules, .git, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Sub-directory to list (default: workspace root '.')."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_user",
            "description": "Pause execution and ask the user a question when you are blocked or need clarification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The question to ask the user."},
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_project",
            "description": "Use AI to analyse the project's tech stack from the file listing and key file contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_listing":       {"type": "string", "description": "Output of list_files."},
                    "key_files_content":  {"type": "string", "description": "Concatenated content of key files (package.json, requirements.txt, etc.)."},
                },
                "required": ["file_listing"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_dockerfile",
            "description": "Generate a production-ready Dockerfile and .dockerignore and write them to the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis": {"type": "string", "description": "JSON string returned by analyze_project."},
                },
                "required": ["analysis"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_compose",
            "description": "Generate a docker-compose.yml and write it to the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis": {"type": "string", "description": "JSON string returned by analyze_project."},
                },
                "required": ["analysis"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "podman_build",
            "description": "Build a container image from the workspace Dockerfile. Streams build output to the terminal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_name": {"type": "string", "description": "Name[:tag] for the resulting image."},
                },
                "required": ["image_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "podman_run",
            "description": "Run a previously built container image.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_name": {"type": "string", "description": "Image name to run."},
                    "ports":      {"type": "string", "description": "Port mapping, e.g. '8080:8080'."},
                    "detach":     {"type": "boolean", "description": "Run in the background (default true)."},
                },
                "required": ["image_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "podman_logs",
            "description": "Fetch logs from a running or stopped container.",
            "parameters": {
                "type": "object",
                "properties": {
                    "container_id": {"type": "string", "description": "Container ID or name."},
                    "tail":         {"type": "string", "description": "Number of log lines to fetch (default '100')."},
                },
                "required": ["container_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "podman_stop",
            "description": "Stop and remove a running container.",
            "parameters": {
                "type": "object",
                "properties": {
                    "container_id": {"type": "string", "description": "Container ID or name to stop."},
                },
                "required": ["container_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "repair_file",
            "description": "Use AI to fix a source file based on a build or runtime error log.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path of the file to repair."},
                    "error_log": {"type": "string", "description": "The error output from the failed build or run."},
                },
                "required": ["file_path", "error_log"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "repair_build",
            "description": (
                "Atomic repair-and-rebuild: fixes a broken file using the error log, then immediately "
                "retries `podman_build`. Use this instead of calling `repair_file` + `podman_build` separately."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path":  {"type": "string", "description": "File to repair (e.g. 'Dockerfile')."},
                    "error_log":  {"type": "string", "description": "Error output from the previous failed build."},
                    "image_name": {"type": "string", "description": "Image name to rebuild after the repair."},
                },
                "required": ["file_path", "error_log", "image_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_image",
            "description": "Rewrite the Dockerfile to use multi-stage builds and Alpine base images to shrink the image.",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_image_name": {"type": "string", "description": "Name of the current built image (for reference)."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "health_check",
            "description": "Poll a TCP port until the application responds or the timeout expires.",
            "parameters": {
                "type": "object",
                "properties": {
                    "port":    {"type": "integer", "description": "TCP port to check."},
                    "timeout": {"type": "integer", "description": "Max seconds to wait (default 30)."},
                },
                "required": ["port"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "terminal_command",
            "description": "Run an arbitrary shell command inside the workspace directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command":     {"type": "string", "description": "Shell command to execute."},
                    "explanation": {"type": "string", "description": "Human-readable reason for running this command."},
                },
                "required": ["command"],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Tool display metadata  {name: (emoji, rich_colour)}
# ---------------------------------------------------------------------------

TOOL_META: dict[str, tuple[str, str]] = {
    "read_file":         ("📄", "cyan"),
    "write_file":        ("💾", "yellow"),
    "list_files":        ("📁", "blue"),
    "ask_user":          ("❓", "yellow"),
    "analyze_project":   ("🔍", "cyan"),
    "generate_dockerfile":("📝", "magenta"),
    "generate_compose":  ("📋", "magenta"),
    "podman_build":      ("🔨", "blue"),
    "podman_run":        ("🚀", "green"),
    "podman_logs":       ("📃", "dim"),
    "podman_stop":       ("🛑", "red"),
    "repair_file":       ("🔧", "yellow"),
    "repair_build":      ("⚡", "orange3"),
    "optimize_image":    ("✨", "green"),
    "health_check":      ("❤️",  "green"),
    "terminal_command":  ("💻", "white"),
}


def _meta(name: str) -> tuple[str, str]:
    return TOOL_META.get(name, ("⚙️", "white"))


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

async def call_llm(messages: list[dict], model: str) -> dict:
    client  = get_client()
    trimmed = trim_history(messages)
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=trimmed,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.2,
            max_completion_tokens=4096,
            timeout=90,
        )
        msg = resp.choices[0].message
        if msg.tool_calls:
            return {
                "tool_calls": [
                    {"id": tc.id, "name": tc.function.name, "arguments": tc.function.arguments}
                    for tc in msg.tool_calls
                ]
            }
        return {"content": msg.content or ""}
    except Exception as exc:
        return {"content": f"[LLM error: {exc}]"}


# ---------------------------------------------------------------------------
# ReAct loop
# ---------------------------------------------------------------------------

async def run_agent(
    prompt: str,
    history: list[dict],
    workspace: str,
    model: str,
) -> tuple[str, list[str]]:
    """
    Drive the ReAct loop. Returns (final_text, tools_used).
    history is modified in-place so the caller retains full conversation state.
    """
    from tools import TOOL_HANDLERS  # local import to avoid circular dep at module load

    history.append({"role": "user", "content": prompt})
    tools_used: list[str] = []

    with console.status("", spinner="dots") as status:
        for step in range(40):
            status.update(f"[bold cyan]⠋[/]  [bold blue]Thinking[/] [dim]· step {step + 1}[/]")

            resp = await call_llm(history, model)

            # ── Final text response ──────────────────────────────────────
            if not resp.get("tool_calls"):
                text = resp.get("content", "Done.")
                history.append({"role": "assistant", "content": text})
                return text, tools_used

            # ── Tool calls ───────────────────────────────────────────────
            tcs = resp["tool_calls"]
            history.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": tc["arguments"]}}
                    for tc in tcs
                ],
            })

            for tc in tcs:
                name = tc["name"]
                args = json.loads(tc["arguments"])
                status.stop()

                # ── Display tool invocation ──────────────────────────────
                if name not in ("ask_user", "podman_build", "repair_build"):
                    emoji, col = _meta(name)
                    param_lines = "\n".join(
                        f"  [dim]{k}:[/] {str(v)[:80]}"
                        for k, v in args.items()
                        if k != "workspace_path"
                    )
                    console.print(Panel(
                        param_lines or "[dim](no params)[/]",
                        title=f"[bold {col}]{emoji} {name}[/]",
                        border_style=col,
                        box=box.MINIMAL_HEAVY_HEAD,
                    ))

                # ── Execute ──────────────────────────────────────────────
                if name == "ask_user":
                    answer = console.input(f"\n[bold yellow]❓  {args.get('question', '')}[/]\n> ")
                    result = {"status": "success", "answer": answer}
                else:
                    t0      = time.monotonic()
                    handler = TOOL_HANDLERS.get(name)
                    if handler:
                        result = await handler(workspace_path=workspace, **args)
                    else:
                        result = {"status": "error", "error": f"Unknown tool: {name}"}

                    elapsed = int((time.monotonic() - t0) * 1000)
                    emoji, col = _meta(name)
                    if result.get("status") == "success":
                        console.print(f"  [bold green]✓[/] [green]{emoji} {name}[/] [dim]({elapsed}ms)[/]")
                    else:
                        console.print(f"  [bold red]✗[/] [red]{emoji} {name}[/] [dim]{result.get('error', '')} ({elapsed}ms)[/]")

                tools_used.append(name)
                history.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(result)})
                status.start()

    return "Max steps reached.", tools_used
