#!/usr/bin/env python3
"""
cli.py — Terminal-based chat interface for the Code Refactoring Agent.

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
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from config_loader import load_all_config
from tools import TOOL_HANDLERS
from activities import _get_openai_client, _trim_history, _get_token_count

# ── Helpers ───────────────────────────────────────────────────────────────────

def print_help():
    print("""
Available Commands:
  /exit, /quit    - End the session
  /clear          - Clear the screen
  /help           - Show this help
  /workspace      - Show current workspace path
  /history        - Show number of messages in history
  /multiline      - Toggle multi-line input mode
  /save <file>    - Save chat history to a JSON file
  /load <file>    - Load chat history from a JSON file
  /undo           - Revert the last turn
  /tokens         - Show current token count
  /system         - Show the system prompt
  /model <name>   - Switch the LLM model deployment
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
    if _VSCODE_CMD is not False:
        return _VSCODE_CMD 

    for name in ("code", "code.cmd"):
        found = shutil.which(name)
        if found:
            _VSCODE_CMD = found
            return found

    vscode_cli = os.environ.get("VSCODE_CLI")
    if vscode_cli and Path(vscode_cli).exists():
        _VSCODE_CMD = vscode_cli
        return vscode_cli

    if sys.platform == "win32":
        for env_var in ("LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)"):
            base = os.environ.get(env_var, "")
            if base:
                for candidate in [
                    Path(base) / "Programs" / "Microsoft VS Code" / "bin" / "code.cmd",
                    Path(base) / "Microsoft VS Code" / "bin" / "code.cmd",
                ]:
                    if candidate.exists():
                        _VSCODE_CMD = str(candidate)
                        return _VSCODE_CMD

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
        if sys.platform == "win32":
            try:
                os.startfile(file_path)
            except OSError:
                pass

    threading.Thread(target=_run, daemon=True).start()
    print(f"  [Opened in VS Code: {Path(file_path).name}]")

# ── LLM Call ──────────────────────────────────────────────────────────────────

async def llm_call(messages: list[dict], tool_schemas: list[dict], model: str | None = None) -> dict:
    client = _get_openai_client()
    deployment = model or (
        os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    )

    trimmed = _trim_history(messages)

    try:
        response = await client.chat.completions.create(
            model=deployment,
            messages=trimmed,
            tools=tool_schemas,
            tool_choice="auto",
            temperature=0.2,
            max_completion_tokens=4096,
            timeout=90,
        )
    except Exception as e:
        return {"content": f"LLM call failed: {type(e).__name__}: {str(e)[:200]}"}

    message = response.choices[0].message

    if getattr(message, "tool_calls", None):
        return {
            "tool_calls": [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
                for tc in message.tool_calls
            ]
        }

    return {"content": message.content or ""}

# ── ReAct Loop ────────────────────────────────────────────────────────────────

async def process_message(
    user_message: str,
    history: list[dict],
    tool_schemas: list[dict],
    workspace_path: str,
    turn: int,
    model: str = "gpt-4o",
) -> tuple[str, list[str]]:
    history.append({"role": "user", "content": user_message})
    max_steps = 15
    tools_used: list[str] = []

    for step in range(max_steps):
        print(f"  Thinking... (step {step + 1}/{max_steps})", end="\r")
        llm_response = await llm_call(history, tool_schemas, model=model)
        print(" " * 40, end="\r") # Clear thinking line

        tool_calls = llm_response.get("tool_calls")
        text_response = llm_response.get("content", "")

        if not tool_calls:
            history.append({"role": "assistant", "content": text_response})
            return text_response or "I'm not sure how to help with that.", tools_used

        history.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]},
                }
                for tc in tool_calls
            ],
        })

        for tool_call in tool_calls:
            tool_name = tool_call["name"]

            try:
                tool_args = json.loads(tool_call["arguments"])
            except json.JSONDecodeError as e:
                error_result = {"status": "error", "error": f"Invalid JSON args: {e}"}
                history.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(error_result),
                })
                print(f"  ✗ {tool_name}: invalid JSON args")
                continue

            if tool_name == "ask_user":
                question = tool_args.get("question", "")
                print(f"\nAgent Question: {question}")
                answer = input("Your answer: ")
                tool_result = {"status": "success", "answer": answer}
                print("  ✓ Answer recorded")
            else:
                print(f"  Running {tool_name}... ", end="", flush=True)
                t0 = time.monotonic()
                handler = TOOL_HANDLERS.get(tool_name)
                
                if handler is None:
                    tool_result = {"status": "error", "error": f"Unknown tool: '{tool_name}'"}
                else:
                    try:
                        tool_result = await handler(workspace_path=workspace_path, **tool_args)
                    except Exception as e:
                        tool_result = {"status": "error", "error": f"Tool error: {str(e)}"}

                elapsed = int((time.monotonic() - t0) * 1000)
                status = tool_result.get("status", "unknown")
                print(f"[{status}] ({elapsed}ms)")

                if status == "success" and tool_name in (
                    "read_file", "navigate_to_file", "analyze_code",
                    "write_file", "apply_refactor", "diff_preview",
                ):
                    file_to_open = (
                        tool_result.get("file_path")
                        or tool_result.get("resolved_path")
                        or tool_args.get("file_path", "")
                    )
                    if file_to_open:
                        fp = Path(file_to_open)
                        if not fp.is_absolute():
                            fp = Path(workspace_path) / fp
                        if fp.is_file():
                            _open_vscode_bg(str(fp))

            tools_used.append(tool_name)
            history.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(tool_result),
            })

    return "I was unable to complete the task within the allowed steps.", tools_used

# ── GitHub Clone ──────────────────────────────────────────────────────────────

def clone_github_repo(url: str, branch: str | None = None) -> str:
    tmp_dir = tempfile.mkdtemp(prefix="refactor-cli-")
    clone_cmd = ["git", "clone", "--depth", "1"]
    if branch:
        clone_cmd.extend(["--branch", branch])
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
    parser = argparse.ArgumentParser(description="Code Refactoring Agent")
    parser.add_argument("--path", help="Path to a local project directory")
    parser.add_argument("--github", help="GitHub repository URL to clone")
    parser.add_argument("--branch", help="Branch to clone (default: default branch)")
    args = parser.parse_args()

    temp_dir = None
    workspace_path: str = ""

    print("\n--- Code Refactoring Agent ---")

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

    SYSTEM_PROMPT, TOOL_SCHEMAS, TOOL_NAMES = load_all_config()
    history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    print_workspace_info(workspace_path, TOOL_NAMES)

    session_start = time.monotonic()
    turn = 0
    total_tools_used: list[str] = []
    multiline_mode = False
    current_model = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

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
                            if line.strip().lower() == "/submit":
                                break
                            lines.append(line)
                        except EOFError:
                            break
                    user_input = "\n".join(lines).strip()
                else:
                    user_input = input("You ▸ ").strip()
            except EOFError:
                break

            if not user_input:
                continue

            if user_input.startswith("/") or user_input.lower() in ("exit", "quit"):
                cmd_parts = user_input.split(maxsplit=1)
                first_word = cmd_parts[0].lower()
                arg = cmd_parts[1].strip() if len(cmd_parts) > 1 else ""

                if first_word in ("exit", "quit", "/exit", "/quit"):
                    break
                elif first_word == "/help":
                    print_help()
                elif first_word == "/clear":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print_workspace_info(workspace_path, TOOL_NAMES)
                elif first_word == "/workspace":
                    print(workspace_path)
                elif first_word == "/history":
                    print(f"{len(history)} messages in context")
                elif first_word == "/multiline":
                    multiline_mode = not multiline_mode
                    print(f"Multiline mode {'enabled' if multiline_mode else 'disabled'}")
                elif first_word == "/system":
                    print(f"\nSystem Prompt:\n{SYSTEM_PROMPT}")
                elif first_word == "/tokens":
                    try:
                        tokens = _get_token_count(history)
                        print(f"Context contains {len(history)} messages, ~{tokens} tokens")
                    except ImportError:
                        print("Token counting not available.")
                elif first_word == "/undo":
                    popped = 0
                    while len(history) > 1 and history[-1]["role"] != "user":
                        history.pop()
                        popped += 1
                    if len(history) > 1 and history[-1]["role"] == "user":
                        history.pop()
                        popped += 1
                    print(f"Removed last turn ({popped} messages). Context size: {len(history)}")
                elif first_word == "/model":
                    if arg:
                        current_model = arg
                        print(f"Model set to {current_model}")
                    else:
                        print(f"Current model is {current_model}")
                elif first_word == "/save":
                    if arg:
                        try:
                            with open(arg, "w") as f: json.dump(history, f, indent=2)
                            print(f"Saved history to {arg}")
                        except Exception as e: print(f"Error saving: {e}")
                    else:
                        print("Usage: /save <filename.json>")
                elif first_word == "/load":
                    if arg:
                        try:
                            with open(arg, "r") as f: history = json.load(f)
                            print(f"Loaded history from {arg} ({len(history)} messages)")
                        except Exception as e: print(f"Error loading: {e}")
                    else:
                        print("Usage: /load <filename.json>")
                else:
                    print(f"Unknown command: {first_word}. Type /help for options.")
                continue

            turn += 1
            t_turn_start = time.monotonic()
            
            response, tools_this_turn = await process_message(
                user_input, history, TOOL_SCHEMAS, workspace_path, turn, current_model
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