#!/usr/bin/env python3
"""
cli.py — Terminal-based chat interface for the Code Refactoring Agent (LangGraph Edition).

Usage:
    python cli.py --path /local/project          # local repo
    python cli.py --github https://github.com/u/r # clone and use
    python cli.py                                  # interactive prompt
"""

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

from config_loader import load_all_config
from graph import graph, SYSTEM_PROMPT
from agent_node import _augment_message_with_github_paths
from langgraph.types import Command

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.rule import Rule
from rich.text import Text
from rich.align import Align
from rich import box

# ── Console & Theme ───────────────────────────────────────────────────────────

console = Console()

C_BRAND    = "bold cyan"
C_USER     = "bold green"
C_AGENT    = "bold bright_green"
C_TOOL_OK  = "green"
C_TOOL_ERR = "red"
C_TOOL_RUN = "blue"
C_DIM      = "white dim"
C_WARN     = "yellow"

TOOL_META: dict[str, tuple[str, str]] = {
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
    return TOOL_META.get(name, ("⚙️", "white"))

# ── Banner ────────────────────────────────────────────────────────────────────

ASCII_LOGO = """\
 ██████╗ ███████╗███████╗ █████╗  ██████╗████████╗ ██████╗ ██████╗
 ██╔══██╗██╔════╝██╔════╝██╔══██╗██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗
 ██████╔╝█████╗  █████╗  ███████║██║        ██║   ██║   ██║██████╔╝
 ██╔══██╗██╔══╝  ██╔══╝  ██╔══██║██║        ██║   ██║   ██║██╔══██╗
 ██║  ██║███████╗██║      ██║  ██║╚██████╗  ██║   ╚██████╔╝██║  ██║
 ╚═╝  ╚═╝╚══════╝╚═╝      ╚═╝  ╚═╝ ╚═════╝  ╚═╝    ╚═════╝ ╚═╝  ╚═╝"""

def print_banner():
    console.print()
    console.print(Align.center(Text(ASCII_LOGO, style="bold cyan")))
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

def print_workspace_info(workspace_path: str, tool_names: list[str]):
    tbl = Table(box=None, show_header=False, padding=(0, 2))
    tbl.add_column("Key",   style="bold white",  no_wrap=True)
    tbl.add_column("Value", style="white")
    tbl.add_row("📂  Workspace", f"[cyan]{workspace_path}[/]")
    tbl.add_row("🔧  Tools",     f"[dim]{len(tool_names)} available[/]")
    tbl.add_row("📅  Session",   f"[dim]{datetime.now().strftime('%Y-%m-%d %H:%M')}[/]")
    console.print(Panel(tbl, border_style="cyan", box=box.ROUNDED))
    console.print("[dim]  Type [bold]/help[/] for commands.  Ctrl+C or /exit to quit.[/]\n")

# ── Tool Rendering ────────────────────────────────────────────────────────────

def render_tool_call(tool_name: str, tool_args: dict):
    icon, color = _tool_meta(tool_name)
    lines = []
    for k, v in tool_args.items():
        if k == "workspace_path": continue
        val = str(v)
        if len(val) > 60: val = val[:57] + "…"
        lines.append(f"  [dim]{k}:[/] [white]{val}[/]")
    body = "\n".join(lines) if lines else "[dim]  (no args)[/]"
    console.print(Panel(body, title=f"[bold {color}]{icon}  {tool_name}[/]", border_style=color, box=box.MINIMAL_HEAVY_HEAD, padding=(0, 1)))

def render_tool_result(tool_name: str, result: dict):
    status = result.get("status", "")
    icon, color = _tool_meta(tool_name)
    if status == "success":
        snippet = ""
        for key in ("summary", "message", "output", "diff", "content"):
            raw = result.get(key)
            if raw and isinstance(raw, str):
                snippet = raw[:80].replace("\n", " ")
                break
        line = f"[{C_TOOL_OK}]✓ {tool_name}[/]"
        if snippet: line += f"  [dim]→ {snippet}[/]"
        console.print(f"  {line}")
    elif status == "error":
        err = result.get("error", "")[:100]
        console.print(f"  [{ C_TOOL_ERR }]✗ {tool_name}[/]  [dim]{err}[/]")
    else:
        console.print(f"  [{C_DIM}]• {tool_name} → {status}[/]")

# ── VS Code Integration ───────────────────────────────────────────────────────

_VSCODE_CMD: str | None | bool = False

def _find_vscode_cmd() -> str | None:
    global _VSCODE_CMD
    if _VSCODE_CMD is not False: return _VSCODE_CMD  # type: ignore
    for name in ("code", "code.cmd"):
        found = shutil.which(name)
        if found:
            _VSCODE_CMD = found
            return found
    _VSCODE_CMD = None
    return None

def open_in_vscode(file_path: str):
    def _run():
        cmd = _find_vscode_cmd()
        if cmd:
            try:
                subprocess.Popen([cmd, "-r", file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                console.print(f"  [dim]📂 Opened in VS Code: {Path(file_path).name}[/]")
            except: pass
    threading.Thread(target=_run, daemon=True).start()

# ── Graph Loop ────────────────────────────────────────────────────────────────

async def process_message(
    user_message: str,
    workspace_path: str,
    session_id: str,
    turn: int,
) -> tuple[str, list[str]]:
    
    config = {"configurable": {"thread_id": session_id}}
    augmented = _augment_message_with_github_paths(user_message, workspace_path)
    
    existing = graph.get_state(config)
    if existing and existing.values:
        prev_history = existing.values.get("history", [])
        new_history  = prev_history + [{"role": "user", "content": augmented}]
        input_state  = {"history": new_history, "workspace_path": workspace_path}
    else:
        input_state = {
            "history": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": augmented},
            ],
            "workspace_path": workspace_path,
        }

    tools_used = []
    
    with console.status("[bold cyan]Thinking...[/]", spinner="dots") as spinner_status:
        try:
            async for event in graph.astream(input_state, config=config, stream_mode="updates"):
                for node_name, state_update in event.items():
                    if node_name == "llm_node":
                        if state_update.get("pending_tool_calls"):
                            spinner_status.stop()
                            for tc in state_update["pending_tool_calls"]:
                                tools_used.append(tc["name"])
                                try:
                                    args = json.loads(tc["arguments"])
                                    render_tool_call(tc["name"], args)
                                except json.JSONDecodeError:
                                    console.print(f"  [{C_TOOL_ERR}]✗ {tc['name']}: invalid JSON args[/]")
                            spinner_status.start()
                    elif node_name == "tool_node":
                        if state_update.get("history"):
                            spinner_status.stop()
                            console.print(f"  [{C_TOOL_OK}]✓ Tool(s) completed[/]")
                            # Try to open created/navigated files
                            if state_update.get("navigated_file"):
                                open_in_vscode(state_update["navigated_file"])
                            spinner_status.start()

            state_after = graph.get_state(config)
            while state_after and state_after.tasks and any(t.interrupts for t in state_after.tasks):
                spinner_status.stop()
                task = next(t for t in state_after.tasks if t.interrupts)
                question = task.interrupts[0].value
                console.print()
                console.print(Panel(f"[bold yellow]{question}[/]", title="[bold yellow]❓ Agent Question[/]", border_style="yellow", box=box.ROUNDED))
                answer = console.input(f"  [{C_USER}]Your answer ▸[/] ")
                console.print(f"  [{C_TOOL_OK}]✓ Answer recorded[/]")
                spinner_status.start()
                
                async for event in graph.astream(Command(resume=answer), config=config, stream_mode="updates"):
                    pass # Similar rendering could be added here if tools are called after answer
                
                state_after = graph.get_state(config)
                
            final_state = graph.get_state(config)
            response = final_state.values.get("last_response", "No response.")
            return response, tools_used

        except Exception as e:
            return f"Error: {e}", []

# ── GitHub Clone ──────────────────────────────────────────────────────────────

def clone_github_repo(url: str, branch: str | None = None) -> str:
    tmp_dir = tempfile.mkdtemp(prefix="refactor-cli-")
    clone_cmd = ["git", "clone", "--depth", "1"]
    if branch: clone_cmd.extend(["--branch", branch])
    clone_cmd.extend([url, tmp_dir])

    console.print(f"  [cyan]📦 Cloning {url}...[/]")
    try:
        subprocess.run(clone_cmd, check=True, capture_output=True, text=True, timeout=120)
    except subprocess.CalledProcessError as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        console.print(f"  [{C_TOOL_ERR}]✗ Clone failed: {(e.stderr or e.stdout or 'unknown error').strip()}[/]")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        console.print(f"  [{C_TOOL_ERR}]✗ Clone timed out after 120 seconds[/]")
        sys.exit(1)

    console.print(f"  [{C_TOOL_OK}]✓ Cloned to {tmp_dir}[/]")
    return tmp_dir

# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Code Refactoring Agent (LangGraph) — Terminal Chat")
    parser.add_argument("--path",   help="Path to a local project directory")
    parser.add_argument("--github", help="GitHub repository URL to clone")
    parser.add_argument("--branch", help="Branch to clone (default: default branch)")
    args = parser.parse_args()

    temp_dir = None
    workspace_path: str = ""

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

    _, _, TOOL_NAMES = load_all_config()
    session_id = str(uuid.uuid4())

    console.print(Rule("[bold cyan]Session[/]", style="cyan"))
    print_workspace_info(workspace_path, TOOL_NAMES)

    session_start = time.monotonic()
    turn = 0
    total_tools_used: list[str] = []
    multiline_mode = False

    try:
        while True:
            elapsed_s = int(time.monotonic() - session_start)
            elapsed_fmt = f"{elapsed_s // 60}m {elapsed_s % 60}s"
            console.print(Rule(f"[dim]Turn {turn + 1}  ·  {elapsed_fmt} elapsed[/]", style="dim"))

            try:
                if multiline_mode:
                    console.print(f"  [{C_USER}]You ▸[/] [dim](multiline mode, type '/submit' or press Ctrl-D to send)[/]")
                    lines = []
                    while True:
                        try:
                            line = console.input("  ... ")
                            if line.strip().lower() == "/submit": break
                            lines.append(line)
                        except EOFError: break
                    user_input = "\n".join(lines).strip()
                else:
                    user_input = console.input(f"  [{C_USER}]You ▸[/]  ").strip()
            except EOFError: break

            if not user_input: continue

            if user_input.startswith("/") or user_input.lower() in ("exit", "quit"):
                cmd_parts = user_input.split(maxsplit=1)
                first_word = cmd_parts[0].lower()
                
                if first_word in ("exit", "quit", "/exit", "/quit"): break
                if first_word == "/help": print_help(); continue
                if first_word == "/clear":
                    console.clear(); print_banner(); print_workspace_info(workspace_path, TOOL_NAMES)
                    continue
                if first_word == "/workspace": console.print(f"  [cyan]{workspace_path}[/]"); continue
                if first_word == "/multiline":
                    multiline_mode = not multiline_mode
                    status = "enabled" if multiline_mode else "disabled"
                    console.print(f"  [cyan]Multiline mode {status}[/]")
                    continue
                
                console.print(f"  [red]Unknown command: {first_word}. Type /help for options.[/]")
                continue

            turn += 1
            console.print()

            t_turn_start = time.monotonic()
            response, tools_this_turn = await process_message(
                user_input, workspace_path, session_id, turn
            )
            total_tools_used.extend(tools_this_turn)
            t_turn_ms = int((time.monotonic() - t_turn_start) * 1000)

            console.print()
            console.print(
                Panel(
                    Markdown(response),
                    title=f"[{C_AGENT}]✦ Agent Response[/]  [dim]({t_turn_ms / 1000:.1f}s)[/]",
                    border_style="bright_green", box=box.ROUNDED, padding=(1, 3),
                )
            )

    except KeyboardInterrupt:
        console.print()
    finally:
        if temp_dir and os.path.exists(temp_dir):
            console.print(f"\n  [dim]🧹 Cleaning up {temp_dir}...[/]")
            shutil.rmtree(temp_dir, ignore_errors=True)

    total_s = int(time.monotonic() - session_start)
    console.print()
    console.print(Rule("[bold cyan]Session Summary[/]", style="cyan"))
    summary_tbl = Table(box=None, show_header=False, padding=(0, 2))
    summary_tbl.add_column("Key",   style="bold white", no_wrap=True)
    summary_tbl.add_column("Value", style="white")
    summary_tbl.add_row("⏱  Duration", f"{total_s // 60}m {total_s % 60}s")
    summary_tbl.add_row("💬  Turns", str(turn))
    console.print(summary_tbl)
    console.print()
    console.print(Align.center(Text("✅  Session ended. Goodbye!", style="bold green")))
    console.print()

if __name__ == "__main__":
    asyncio.run(main())