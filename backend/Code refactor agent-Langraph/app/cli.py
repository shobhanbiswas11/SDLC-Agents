"""
app/cli.py — Terminal-based chat interface for the Code Refactoring Agent.

Usage:
    python -m app.cli --path /local/project
    python -m app.cli --github https://github.com/owner/repo
    python -m app.cli                       # interactive workspace prompt
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from agent.graph import build_graph
from agent.utils.github_utils import augment_message_with_github_paths
from core.config_loader import load_all_config
from core.logging import get_logger
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from rich import box
from rich.align import Align
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

logger = get_logger(__name__)

# ── Console & Theme ────────────────────────────────────────────────────────────
console = Console()

C_BRAND    = "bold cyan"
C_USER     = "bold green"
C_AGENT    = "bold bright_green"
C_TOOL_OK  = "green"
C_TOOL_ERR = "red"
C_DIM      = "white dim"

TOOL_ICONS: dict[str, tuple[str, str]] = {
    "analyze_code":      ("🔍", "cyan"),
    "suggest_refactor":  ("💡", "yellow"),
    "apply_refactor":    ("✏️",  "magenta"),
    "diff_preview":      ("📊", "blue"),
    "run_tests":         ("🧪", "green"),
    "read_file":         ("📄", "cyan"),
    "write_file":        ("💾", "yellow"),
    "list_files":        ("📁", "blue"),
    "ask_user":          ("❓", "yellow"),
    "git_commit_push":   ("🚀", "magenta"),
    "github_put_file":   ("🌐", "blue"),
    "navigate_to_file":  ("🗺️",  "cyan"),
}

def _tool_meta(name: str) -> tuple[str, str]:
    return TOOL_ICONS.get(name, ("⚙️", "white"))

# ── Banner ─────────────────────────────────────────────────────────────────────
_LOGO = """\
 ██████╗ ███████╗███████╗ █████╗  ██████╗████████╗ ██████╗ ██████╗
 ██╔══██╗██╔════╝██╔════╝██╔══██╗██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗
 ██████╔╝█████╗  █████╗  ███████║██║        ██║   ██║   ██║██████╔╝
 ██╔══██╗██╔══╝  ██╔══╝  ██╔══██║██║        ██║   ██║   ██║██╔══██╗
 ██║  ██║███████╗██║      ██║  ██║╚██████╗  ██║   ╚██████╔╝██║  ██║
 ╚═╝  ╚═╝╚══════╝╚═╝      ╚═╝  ╚═╝ ╚═════╝  ╚═╝    ╚═════╝ ╚═╝  ╚═╝"""


def print_banner():
    console.print()
    console.print(Align.center(Text(_LOGO, style="bold cyan")))
    console.print(Align.center(Text("✦  Code Refactoring Agent · LangGraph CLI  ✦", style="bold white")))
    console.print()


def print_help():
    tbl = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan",
                border_style="cyan", padding=(0, 2))
    tbl.add_column("Command", style="bold yellow", no_wrap=True)
    tbl.add_column("Description")
    tbl.add_row("/exit, /quit", "End the session")
    tbl.add_row("/clear",       "Clear the screen")
    tbl.add_row("/help",        "Show this help")
    tbl.add_row("/workspace",   "Show current workspace path")
    tbl.add_row("/multiline",   "Toggle multi-line input mode")
    console.print(Panel(tbl, title="[bold cyan]Available Commands[/]", border_style="cyan"))


def print_workspace_info(workspace_path: str, tool_count: int):
    tbl = Table(box=None, show_header=False, padding=(0, 2))
    tbl.add_column("Key",  style="bold white", no_wrap=True)
    tbl.add_column("Value", style="white")
    tbl.add_row("📂  Workspace", f"[cyan]{workspace_path}[/]")
    tbl.add_row("🔧  Tools",     f"[dim]{tool_count} available[/]")
    tbl.add_row("📅  Session",   f"[dim]{datetime.now().strftime('%Y-%m-%d %H:%M')}[/]")
    console.print(Panel(tbl, border_style="cyan", box=box.ROUNDED))
    console.print("[dim]  Type [bold]/help[/] for commands.  Ctrl+C or /exit to quit.[/]\n")


# ── Tool rendering ─────────────────────────────────────────────────────────────

def render_tool_call(tool_name: str, tool_args: dict):
    icon, color = _tool_meta(tool_name)
    lines = []
    for k, v in tool_args.items():
        if k == "workspace_path":
            continue
        val = str(v)
        if len(val) > 60:
            val = val[:57] + "…"
        lines.append(f"  [dim]{k}:[/] [white]{val}[/]")
    body = "\n".join(lines) if lines else "[dim]  (no args)[/]"
    console.print(Panel(
        body,
        title=f"[bold {color}]{icon}  {tool_name}[/]",
        border_style=color,
        box=box.MINIMAL_HEAVY_HEAD,
        padding=(0, 1),
    ))


# ── VS Code integration ────────────────────────────────────────────────────────

_vscode_cmd: str | None | bool = False


def _find_vscode():
    global _vscode_cmd
    if _vscode_cmd is not False:
        return _vscode_cmd
    for name in ("code", "code.cmd"):
        found = shutil.which(name)
        if found:
            _vscode_cmd = found
            return found
    _vscode_cmd = None
    return None


def open_in_vscode(file_path: str):
    def _run():
        cmd = _find_vscode()
        if cmd:
            try:
                subprocess.Popen([cmd, "-r", file_path],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                console.print(f"  [dim]📂 Opened in VS Code: {Path(file_path).name}[/]")
            except Exception:
                pass
    threading.Thread(target=_run, daemon=True).start()


# ── GitHub clone ───────────────────────────────────────────────────────────────

def clone_github_repo(url: str, branch: str | None = None) -> str:
    tmp = tempfile.mkdtemp(prefix="refactor-cli-")
    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd.extend(["--branch", branch])
    cmd.extend([url, tmp])
    console.print(f"  [cyan]📦 Cloning {url}...[/]")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(tmp, ignore_errors=True)
        console.print(f"  [{C_TOOL_ERR}]✗ Clone failed: {(exc.stderr or exc.stdout or 'unknown').strip()}[/]")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        shutil.rmtree(tmp, ignore_errors=True)
        console.print(f"  [{C_TOOL_ERR}]✗ Clone timed out after 120 seconds[/]")
        sys.exit(1)
    console.print(f"  [{C_TOOL_OK}]✓ Cloned to {tmp}[/]")
    return tmp


# ── Graph loop ─────────────────────────────────────────────────────────────────

async def process_message(
    graph,
    system_prompt: str,
    user_message: str,
    workspace_path: str,
    session_id: str,
) -> tuple[str, list[str]]:
    config = {"configurable": {"thread_id": session_id}}
    augmented = augment_message_with_github_paths(user_message, workspace_path)

    existing = graph.get_state(config)
    if existing and existing.values:
        input_state = {
            **existing.values,
            "history": existing.values.get("history", []) + [{"role": "user", "content": augmented}],
            "workspace_path": workspace_path,
        }
    else:
        input_state = {
            "history": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": augmented},
            ],
            "workspace_path": workspace_path,
        }

    tools_used: list[str] = []

    with console.status("[bold cyan]Thinking...[/]", spinner="dots") as spinner:
        try:
            async for event in graph.astream(input_state, config=config, stream_mode="updates"):
                for node_name, state_update in event.items():
                    if node_name == "llm_node" and state_update.get("pending_tool_calls"):
                        spinner.stop()
                        for tc in state_update["pending_tool_calls"]:
                            tools_used.append(tc["name"])
                            try:
                                render_tool_call(tc["name"], json.loads(tc["arguments"]))
                            except json.JSONDecodeError:
                                console.print(f"  [{C_TOOL_ERR}]✗ {tc['name']}: invalid JSON args[/]")
                        spinner.start()
                    elif node_name == "tool_node" and state_update.get("history"):
                        spinner.stop()
                        console.print(f"  [{C_TOOL_OK}]✓ Tool(s) completed[/]")
                        if state_update.get("navigated_file"):
                            open_in_vscode(state_update["navigated_file"])
                        spinner.start()

            # Handle ask_user interrupts
            state_after = graph.get_state(config)
            while state_after and state_after.tasks and any(t.interrupts for t in state_after.tasks):
                spinner.stop()
                task = next(t for t in state_after.tasks if t.interrupts)
                question = task.interrupts[0].value
                console.print()
                console.print(Panel(
                    f"[bold yellow]{question}[/]",
                    title="[bold yellow]❓ Agent Question[/]",
                    border_style="yellow",
                    box=box.ROUNDED,
                ))
                answer = console.input(f"  [{C_USER}]Your answer ▸[/] ")
                spinner.start()
                async for _ in graph.astream(Command(resume=answer), config=config, stream_mode="updates"):
                    pass
                state_after = graph.get_state(config)

            final_state = graph.get_state(config)
            response = final_state.values.get("last_response", "No response.")
            return response, tools_used

        except Exception as exc:
            logger.exception("process_message error")
            return f"Error: {exc}", []


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Code Refactoring Agent (LangGraph) — Terminal Chat")
    parser.add_argument("--path",   help="Path to a local project directory")
    parser.add_argument("--github", help="GitHub repository URL to clone")
    parser.add_argument("--branch", help="Branch to clone (default: repo default)")
    args = parser.parse_args()

    temp_dir: str | None = None
    workspace_path = ""

    print_banner()

    if args.github:
        temp_dir = clone_github_repo(args.github, args.branch)
        workspace_path = temp_dir
    elif args.path:
        workspace_path = os.path.abspath(args.path)
        if not os.path.isdir(workspace_path):
            console.print(f"[{C_TOOL_ERR}]Error: '{workspace_path}' is not a directory[/]")
            sys.exit(1)
    else:
        console.print(Rule("[bold cyan]Setup[/]", style="cyan"))
        console.print()
        choice = console.input(f"  [{C_BRAND}]📂 Local path or GitHub URL:[/]  ").strip()
        if not choice:
            console.print(f"  [{C_TOOL_ERR}]No path provided. Exiting.[/]")
            sys.exit(1)
        if choice.startswith(("http://", "https://")) or "github.com" in choice:
            branch_in = console.input(f"  [{C_BRAND}]🌿 Branch (Enter = default):[/]  ").strip() or None
            temp_dir = clone_github_repo(choice, branch_in)
            workspace_path = temp_dir
        else:
            workspace_path = os.path.abspath(choice)
            if not os.path.isdir(workspace_path):
                console.print(f"  [{C_TOOL_ERR}]Error: '{workspace_path}' is not a directory[/]")
                sys.exit(1)

    system_prompt, _, tool_names = load_all_config()
    session_id = str(uuid.uuid4())

    # Compile graph with sync SQLite saver for the CLI
    db_path = os.getenv("CHECKPOINT_DB_PATH", "checkpoints.db")
    import sqlite3
    conn = sqlite3.connect(db_path, check_same_thread=False)
    memory = SqliteSaver(conn)
    graph = build_graph().compile(checkpointer=memory)

    console.print(Rule("[bold cyan]Session[/]", style="cyan"))
    print_workspace_info(workspace_path, len(tool_names))

    session_start = time.monotonic()
    turn = 0
    total_tools: list[str] = []
    multiline_mode = False

    try:
        while True:
            elapsed_s = int(time.monotonic() - session_start)
            console.print(Rule(
                f"[dim]Turn {turn + 1}  ·  {elapsed_s // 60}m {elapsed_s % 60}s elapsed[/]",
                style="dim",
            ))

            try:
                if multiline_mode:
                    console.print(f"  [{C_USER}]You ▸[/] [dim](multiline — type '/submit' to send)[/]")
                    lines = []
                    while True:
                        try:
                            line = console.input("  ... ")
                            if line.strip().lower() == "/submit":
                                break
                            lines.append(line)
                        except EOFError:
                            break
                    user_input = "\n".join(lines).strip()
                else:
                    user_input = console.input(f"  [{C_USER}]You ▸[/]  ").strip()
            except EOFError:
                break

            if not user_input:
                continue

            # Handle slash commands
            if user_input.startswith("/") or user_input.lower() in ("exit", "quit"):
                cmd = user_input.split(maxsplit=1)[0].lower()
                if cmd in ("exit", "quit", "/exit", "/quit"):
                    break
                if cmd == "/help":
                    print_help()
                elif cmd == "/clear":
                    console.clear()
                    print_banner()
                    print_workspace_info(workspace_path, len(tool_names))
                elif cmd == "/workspace":
                    console.print(f"  [cyan]{workspace_path}[/]")
                elif cmd == "/multiline":
                    multiline_mode = not multiline_mode
                    console.print(f"  [cyan]Multiline mode {'enabled' if multiline_mode else 'disabled'}[/]")
                else:
                    console.print(f"  [red]Unknown command: {cmd}. Type /help for options.[/]")
                continue

            turn += 1
            console.print()
            t0 = time.monotonic()
            response, tools_this_turn = await process_message(
                graph, system_prompt, user_input, workspace_path, session_id
            )
            total_tools.extend(tools_this_turn)
            elapsed_ms = int((time.monotonic() - t0) * 1000)

            console.print()
            console.print(Panel(
                Markdown(response),
                title=f"[{C_AGENT}]✦ Agent Response[/]  [dim]({elapsed_ms / 1000:.1f}s)[/]",
                border_style="bright_green",
                box=box.ROUNDED,
                padding=(1, 3),
            ))

    except KeyboardInterrupt:
        console.print()
    finally:
        if temp_dir and os.path.exists(temp_dir):
            console.print(f"\n  [dim]🧹 Cleaning up {temp_dir}...[/]")
            shutil.rmtree(temp_dir, ignore_errors=True)
        try:
            conn.close()
        except Exception:
            pass

    total_s = int(time.monotonic() - session_start)
    console.print()
    console.print(Rule("[bold cyan]Session Summary[/]", style="cyan"))
    summary = Table(box=None, show_header=False, padding=(0, 2))
    summary.add_column("Key",   style="bold white", no_wrap=True)
    summary.add_column("Value", style="white")
    summary.add_row("⏱  Duration", f"{total_s // 60}m {total_s % 60}s")
    summary.add_row("💬  Turns",   str(turn))
    summary.add_row("🔧  Tools",   str(len(total_tools)))
    console.print(summary)
    console.print()
    console.print(Align.center(Text("✅  Session ended. Goodbye!", style="bold green")))
    console.print()


if __name__ == "__main__":
    asyncio.run(main())
