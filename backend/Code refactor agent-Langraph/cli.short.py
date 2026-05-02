#!/usr/bin/env python3
"""
cli.short.py — Terminal-based chat interface for the Code Refactoring Agent (LangGraph Edition).

Simplified purely functional CLI. No external UI libraries.
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

# ── Helpers ───────────────────────────────────────────────────────────────────

def print_help():
    print("""
Available Commands:
  /exit, /quit    - End the session
  /clear          - Clear the screen
  /help           - Show this help
  /workspace      - Show current workspace path
  /multiline      - Toggle multi-line input mode
""")

def print_workspace_info(workspace_path: str, tool_names: list[str]):
    print(f"\n--- Session Info ---")
    print(f"Workspace: {workspace_path}")
    print(f"Tools:     {len(tool_names)} available")
    print(f"Session:   {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("Type /help for commands. Ctrl+C or /exit to quit.\n")

# ── VS Code Integration ───────────────────────────────────────────────────────

_VSCODE_CMD: str | None | bool = False

def _find_vscode_cmd() -> str | None:
    global _VSCODE_CMD
    if _VSCODE_CMD is not False: return _VSCODE_CMD 
    for name in ("code", "code.cmd"):
        found = shutil.which(name)
        if found:
            _VSCODE_CMD = found
            return found
    _VSCODE_CMD = None
    return None

def _open_vscode_bg(file_path: str) -> None:
    def _run() -> None:
        code_cmd = _find_vscode_cmd()
        if code_cmd:
            try:
                subprocess.Popen(
                    [code_cmd, "-r", file_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
            except FileNotFoundError:
                pass
    threading.Thread(target=_run, daemon=True).start()
    print(f"  [Opened in VS Code: {Path(file_path).name}]")

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
    
    try:
        async for event in graph.astream(input_state, config=config, stream_mode="updates"):
            for node_name, state_update in event.items():
                if node_name == "llm_node":
                    if state_update.get("pending_tool_calls"):
                        for tc in state_update["pending_tool_calls"]:
                            tools_used.append(tc["name"])
                            print(f"  Running {tc['name']}... ", end="", flush=True)
                elif node_name == "tool_node":
                    if state_update.get("history"):
                        print("[success]")
                        if state_update.get("navigated_file"):
                            _open_vscode_bg(state_update["navigated_file"])

        state_after = graph.get_state(config)
        while state_after and state_after.tasks and any(t.interrupts for t in state_after.tasks):
            task = next(t for t in state_after.tasks if t.interrupts)
            question = task.interrupts[0].value
            print(f"\nAgent Question: {question}")
            answer = input("Your answer: ")
            print("  ✓ Answer recorded")
            
            async for event in graph.astream(Command(resume=answer), config=config, stream_mode="updates"):
                pass 
            
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

    print(f"Cloning {url}...")
    try:
        subprocess.run(clone_cmd, check=True, capture_output=True, text=True, timeout=120)
    except subprocess.CalledProcessError as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"Clone failed: {(e.stderr or e.stdout or 'unknown error').strip()}")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print("Clone timed out after 120 seconds")
        sys.exit(1)

    print(f"Cloned to {tmp_dir}")
    return tmp_dir

# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Code Refactoring Agent (LangGraph)")
    parser.add_argument("--path", help="Path to a local project directory")
    parser.add_argument("--github", help="GitHub repository URL to clone")
    parser.add_argument("--branch", help="Branch to clone (default: default branch)")
    args = parser.parse_args()

    temp_dir = None
    workspace_path: str = ""

    print("\n--- Code Refactoring Agent (LangGraph) ---")

    if args.github:
        workspace_path = clone_github_repo(args.github, args.branch)
        temp_dir = workspace_path
    elif args.path:
        workspace_path = os.path.abspath(args.path)
        if not os.path.isdir(workspace_path):
            print(f"Error: '{workspace_path}' is not a directory")
            sys.exit(1)
    else:
        choice = input("Local path or GitHub URL: ").strip()
        if not choice:
            print("No path provided. Exiting.")
            sys.exit(1)

        if choice.startswith(("http://", "https://")) or "github.com" in choice:
            branch_in = input("Branch (Enter = default): ").strip() or None
            workspace_path = clone_github_repo(choice, branch_in)
            temp_dir = workspace_path
        else:
            workspace_path = os.path.abspath(choice)
            if not os.path.isdir(workspace_path):
                print(f"Error: '{workspace_path}' is not a directory")
                sys.exit(1)

    _, _, TOOL_NAMES = load_all_config()
    session_id = str(uuid.uuid4())

    print_workspace_info(workspace_path, TOOL_NAMES)

    session_start = time.monotonic()
    turn = 0
    total_tools_used: list[str] = []
    multiline_mode = False

    try:
        while True:
            elapsed_s = int(time.monotonic() - session_start)
            print(f"\n--- Turn {turn + 1} | {elapsed_s // 60}m {elapsed_s % 60}s ---")

            try:
                if multiline_mode:
                    print("(multiline mode, type '/submit' or press Ctrl-D to send)")
                    lines = []
                    while True:
                        try:
                            line = input("... ")
                            if line.strip().lower() == "/submit": break
                            lines.append(line)
                        except EOFError: break
                    user_input = "\n".join(lines).strip()
                else:
                    user_input = input("You ▸ ").strip()
            except EOFError: break

            if not user_input: continue

            if user_input.startswith("/") or user_input.lower() in ("exit", "quit"):
                cmd_parts = user_input.split(maxsplit=1)
                first_word = cmd_parts[0].lower()
                
                if first_word in ("exit", "quit", "/exit", "/quit"): break
                elif first_word == "/help": print_help()
                elif first_word == "/clear":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print_workspace_info(workspace_path, TOOL_NAMES)
                elif first_word == "/workspace": print(workspace_path)
                elif first_word == "/multiline":
                    multiline_mode = not multiline_mode
                    print(f"Multiline mode {'enabled' if multiline_mode else 'disabled'}")
                else:
                    print(f"Unknown command: {first_word}. Type /help for options.")
                continue

            turn += 1
            t_turn_start = time.monotonic()
            
            response, tools_this_turn = await process_message(
                user_input, workspace_path, session_id, turn
            )
            
            total_tools_used.extend(tools_this_turn)
            t_turn_ms = int((time.monotonic() - t_turn_start) * 1000)

            print(f"\nAgent ({t_turn_ms / 1000:.1f}s, {len(tools_this_turn)} tools):")
            print(response)

    except KeyboardInterrupt:
        pass
    finally:
        if temp_dir and os.path.exists(temp_dir):
            print(f"\nCleaning up {temp_dir}...")
            shutil.rmtree(temp_dir, ignore_errors=True)

    total_s = int(time.monotonic() - session_start)
    print("\n--- Session Summary ---")
    print(f"Duration:     {total_s // 60}m {total_s % 60}s")
    print(f"Turns:        {turn}")
    print(f"Tools called: {len(total_tools_used)}")
    print("Session ended. Goodbye!\n")

if __name__ == "__main__":
    asyncio.run(main())