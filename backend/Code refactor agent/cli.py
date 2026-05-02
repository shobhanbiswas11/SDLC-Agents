# #!/usr/bin/env python3
# """
# cli.py — Terminal-based chat interface for the Code Refactoring Agent.

# Same tools, same LLM, same workflow — runs directly without Temporal or the web UI.

# Usage:
#     python cli.py --path /local/project          # local repo
#     python cli.py --github https://github.com/u/r # clone and use
#     python cli.py                                  # interactive prompt
# """

# import argparse
# import asyncio
# import json
# import os
# import shutil
# import subprocess
# import sys
# import tempfile
# import time
# from datetime import datetime
# from pathlib import Path

# from dotenv import load_dotenv

# load_dotenv()

# from config_loader import load_all_config
# from tools import TOOL_HANDLERS
# from activities import _get_openai_client, _trim_history, _get_token_count

# from rich.console import Console
# from rich.panel import Panel
# from rich.markdown import Markdown
# from rich.table import Table
# from rich.rule import Rule
# from rich.text import Text
# from rich.columns import Columns
# from rich.align import Align
# from rich import box
# from rich.padding import Padding
# from rich.style import Style
# from rich.prompt import Prompt

# # ── Console & Theme ───────────────────────────────────────────────────────────

# console = Console()

# # Color palette
# C_BRAND    = "bold cyan"
# C_USER     = "bold green"
# C_AGENT    = "bold bright_green"
# C_TOOL_OK  = "green"
# C_TOOL_ERR = "red"
# C_TOOL_RUN = "blue"
# C_DIM      = "white dim"
# C_WARN     = "yellow"

# # Tool type → display config
# TOOL_META: dict[str, tuple[str, str]] = {
#     "analyze_code":      ("🔍", "cyan"),
#     "suggest_refactor":  ("💡", "yellow"),
#     "apply_refactor":    ("✏️",  "magenta"),
#     "diff_preview":      ("📊", "blue"),
#     "run_tests":         ("🧪", "green"),
#     "read_file":         ("📄", "cyan"),
#     "write_file":        ("💾", "yellow"),
#     "list_files":        ("📁", "blue"),
#     "ask_user":          ("❓", "yellow"),
#     "git_commit_push":   ("🚀", "magenta"),
#     "github_put_file":   ("🌐", "blue"),
#     "navigate_to_file":  ("🗺️",  "cyan"),
# }

# def _tool_meta(name: str) -> tuple[str, str]:
#     return TOOL_META.get(name, ("⚙️", "white"))


# # ── Banner ────────────────────────────────────────────────────────────────────

# ASCII_LOGO = """\
#  ██████╗ ███████╗███████╗ █████╗  ██████╗████████╗ ██████╗ ██████╗
#  ██╔══██╗██╔════╝██╔════╝██╔══██╗██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗
#  ██████╔╝█████╗  █████╗  ███████║██║        ██║   ██║   ██║██████╔╝
#  ██╔══██╗██╔══╝  ██╔══╝  ██╔══██║██║        ██║   ██║   ██║██╔══██╗
#  ██║  ██║███████╗██║      ██║  ██║╚██████╗  ██║   ╚██████╔╝██║  ██║
#  ╚═╝  ╚═╝╚══════╝╚═╝      ╚═╝  ╚═╝ ╚═════╝  ╚═╝    ╚═════╝ ╚═╝  ╚═╝"""

# def print_banner():
#     console.print()
#     console.print(Align.center(Text(ASCII_LOGO, style="bold cyan")))
#     console.print(Align.center(Text("✦  Code Refactoring Agent · Terminal Interface  ✦", style="bold white")))
#     console.print()


# def print_help():
#     tbl = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan",
#                 border_style="cyan", padding=(0, 2))
#     tbl.add_column("Command", style="bold yellow", no_wrap=True)
#     tbl.add_column("Description")
#     tbl.add_row("/exit, /quit", "End the session")
#     tbl.add_row("/clear",       "Clear the screen")
#     tbl.add_row("/help",        "Show this help")
#     tbl.add_row("/workspace",   "Show current workspace path")
#     tbl.add_row("/history",     "Show number of messages in history")
#     tbl.add_row("/multiline",   "Toggle multi-line input mode")
#     tbl.add_row("/save <file>", "Save chat history to a JSON file")
#     tbl.add_row("/load <file>", "Load chat history from a JSON file")
#     tbl.add_row("/undo",        "Revert the last turn")
#     tbl.add_row("/tokens",      "Show current token count")
#     tbl.add_row("/system",      "Show the system prompt")
#     tbl.add_row("/model <name>","Switch the LLM model deployment")
#     console.print(Panel(tbl, title="[bold cyan]Available Commands[/]", border_style="cyan"))


# def print_workspace_info(workspace_path: str, tool_names: list[str]):
#     tbl = Table(box=None, show_header=False, padding=(0, 2))
#     tbl.add_column("Key",   style="bold white",  no_wrap=True)
#     tbl.add_column("Value", style="white")
#     tbl.add_row("📂  Workspace", f"[cyan]{workspace_path}[/]")
#     tbl.add_row("🔧  Tools",     f"[dim]{len(tool_names)} available[/]")
#     tbl.add_row("📅  Session",   f"[dim]{datetime.now().strftime('%Y-%m-%d %H:%M')}[/]")
#     console.print(Panel(tbl, border_style="cyan", box=box.ROUNDED))
#     console.print("[dim]  Type [bold]/help[/] for commands.  Ctrl+C or /exit to quit.[/]\n")


# # ── Tool Rendering ────────────────────────────────────────────────────────────

# def render_tool_call(tool_name: str, tool_args: dict):
#     """Render a styled card for a tool invocation."""
#     icon, color = _tool_meta(tool_name)

#     # Build args preview
#     lines = []
#     for k, v in tool_args.items():
#         if k == "workspace_path":
#             continue
#         val = str(v)
#         if len(val) > 60:
#             val = val[:57] + "…"
#         lines.append(f"  [dim]{k}:[/] [white]{val}[/]")

#     body = "\n".join(lines) if lines else "[dim]  (no args)[/]"
#     console.print(
#         Panel(
#             body,
#             title=f"[bold {color}]{icon}  {tool_name}[/]",
#             border_style=color,
#             box=box.MINIMAL_HEAVY_HEAD,
#             padding=(0, 1),
#         )
#     )


# def render_tool_result(tool_name: str, result: dict, elapsed_ms: int):
#     """Print a short status line after a tool completes."""
#     status = result.get("status", "")
#     icon, color = _tool_meta(tool_name)

#     if status == "success":
#         # Extract a meaningful snippet from the result if possible
#         snippet = ""
#         for key in ("summary", "message", "output", "diff", "content"):
#             raw = result.get(key)
#             if raw and isinstance(raw, str):
#                 snippet = raw[:80].replace("\n", " ")
#                 break
#         line = f"[{C_TOOL_OK}]✓ {tool_name}[/]"
#         if snippet:
#             line += f"  [dim]→ {snippet}[/]"
#         line += f"  [dim]({elapsed_ms}ms)[/]"
#         console.print(f"  {line}")
#     elif status == "error":
#         err = result.get("error", "")[:100]
#         console.print(f"  [{ C_TOOL_ERR }]✗ {tool_name}[/]  [dim]{err}[/]")
#     else:
#         console.print(f"  [{C_DIM}]• {tool_name} → {status}[/]")


# # ── VS Code Integration ───────────────────────────────────────────────────────

# def open_in_vscode(file_path: str):
#     """Open a file in the current VS Code window (non-blocking)."""
#     try:
#         subprocess.Popen(
#             ["code", "-r", file_path],
#             stdout=subprocess.DEVNULL,
#             stderr=subprocess.DEVNULL,
#         )
#         console.print(f"  [dim]📂 Opened in VS Code: {Path(file_path).name}[/]")
#     except FileNotFoundError:
#         pass


# # ── LLM Call ──────────────────────────────────────────────────────────────────

# async def llm_call(messages: list[dict], tool_schemas: list[dict], model: str | None = None) -> dict:
#     """Call Azure OpenAI — same logic as activities.py but without Temporal."""
#     client = _get_openai_client()
#     deployment = model or (
#         os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
#         or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
#     )

#     trimmed = _trim_history(messages)

#     try:
#         response = await client.chat.completions.create(
#             model=deployment,
#             messages=trimmed,
#             tools=tool_schemas,
#             tool_choice="auto",
#             temperature=0.2,
#             max_completion_tokens=4096,
#             timeout=90,
#         )
#     except Exception as e:
#         error_msg = str(e)
#         return {"content": f"⚠️ LLM call failed: {type(e).__name__}: {error_msg[:200]}"}

#     message = response.choices[0].message

#     if message.tool_calls:
#         return {
#             "tool_calls": [
#                 {
#                     "id": tc.id,
#                     "name": tc.function.name,
#                     "arguments": tc.function.arguments,
#                 }
#                 for tc in message.tool_calls
#             ]
#         }

#     return {"content": message.content or ""}


# # ── ReAct Loop ────────────────────────────────────────────────────────────────

# async def process_message(
#     user_message: str,
#     history: list[dict],
#     tool_schemas: list[dict],
#     workspace_path: str,
#     turn: int,
#     model: str = "gpt-4o",
# ) -> tuple[str, list[str]]:
#     """
#     Core think → act → observe loop.
#     Returns (response_text, list_of_tools_used).
#     """
#     history.append({"role": "user", "content": user_message})
#     max_steps = 15
#     tools_used: list[str] = []

#     SPINNERS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

#     with console.status("", spinner="dots") as spinner_status:
#         for step in range(max_steps):
#             spinner_status.update(
#                 f"[bold cyan]{SPINNERS[step % len(SPINNERS)]}[/]  "
#                 f"[bold blue]Thinking[/] [dim]· step {step + 1}/{max_steps}[/]"
#             )
#             llm_response = await llm_call(history, tool_schemas, model=model)

#             tool_calls = llm_response.get("tool_calls")
#             text_response = llm_response.get("content", "")

#             if not tool_calls:
#                 history.append({"role": "assistant", "content": text_response})
#                 return text_response or "I'm not sure how to help with that.", tools_used

#             # Log tool calls in history
#             history.append({
#                 "role": "assistant",
#                 "content": None,
#                 "tool_calls": [
#                     {
#                         "id": tc["id"],
#                         "type": "function",
#                         "function": {"name": tc["name"], "arguments": tc["arguments"]},
#                     }
#                     for tc in tool_calls
#                 ],
#             })

#             # Execute each tool
#             for tool_call in tool_calls:
#                 tool_name = tool_call["name"]

#                 # Parse arguments
#                 try:
#                     tool_args = json.loads(tool_call["arguments"])
#                 except json.JSONDecodeError as e:
#                     error_result = {
#                         "status": "error",
#                         "error": f"Invalid JSON arguments: {e}",
#                     }
#                     history.append({
#                         "role": "tool",
#                         "tool_call_id": tool_call["id"],
#                         "content": json.dumps(error_result),
#                     })
#                     spinner_status.stop()
#                     console.print(f"  [{C_TOOL_ERR}]✗ {tool_name}: invalid JSON args[/]")
#                     spinner_status.start()
#                     continue

#                 # ask_user → pause spinner, read input
#                 if tool_name == "ask_user":
#                     question = tool_args.get("question", "")
#                     spinner_status.stop()
#                     console.print()
#                     console.print(
#                         Panel(
#                             f"[bold yellow]{question}[/]",
#                             title="[bold yellow]❓ Agent Question[/]",
#                             border_style="yellow",
#                             box=box.ROUNDED,
#                         )
#                     )
#                     answer = console.input(f"  [{C_USER}]Your answer ▸[/] ")
#                     tool_result = {"status": "success", "answer": answer}
#                     console.print(f"  [{C_TOOL_OK}]✓ Answer recorded[/]")
#                     spinner_status.start()
#                 else:
#                     # Render the tool call card (pause spinner to avoid flicker)
#                     spinner_status.stop()
#                     render_tool_call(tool_name, tool_args)

#                     t0 = time.monotonic()
#                     handler = TOOL_HANDLERS.get(tool_name)
#                     if handler is None:
#                         tool_result = {
#                             "status": "error",
#                             "error": f"Unknown tool: '{tool_name}'",
#                         }
#                     else:
#                         try:
#                             tool_result = await handler(
#                                 workspace_path=workspace_path, **tool_args
#                             )
#                         except Exception as e:
#                             tool_result = {
#                                 "status": "error",
#                                 "error": f"Tool error: {str(e)}",
#                             }

#                     elapsed = int((time.monotonic() - t0) * 1000)
#                     render_tool_result(tool_name, tool_result, elapsed)
#                     spinner_status.start()

#                     # Auto-open files in VS Code
#                     if tool_result.get("status") == "success" and tool_name in (
#                         "read_file", "navigate_to_file", "analyze_code",
#                         "write_file", "apply_refactor", "diff_preview",
#                     ):
#                         file_to_open = (
#                             tool_result.get("file_path")
#                             or tool_result.get("resolved_path")
#                             or tool_args.get("file_path", "")
#                         )
#                         if file_to_open:
#                             fp = Path(file_to_open)
#                             if not fp.is_absolute():
#                                 fp = Path(workspace_path) / fp
#                             if fp.is_file():
#                                 spinner_status.stop()
#                                 open_in_vscode(str(fp))
#                                 spinner_status.start()

#                     tools_used.append(tool_name)

#                 history.append({
#                     "role": "tool",
#                     "tool_call_id": tool_call["id"],
#                     "content": json.dumps(tool_result),
#                 })

#     return "I was unable to complete the task within the allowed steps.", tools_used


# # ── GitHub Clone ──────────────────────────────────────────────────────────────

# def clone_github_repo(url: str, branch: str | None = None) -> str:
#     """Shallow-clone a GitHub repo to a temp directory. Returns the path."""
#     tmp_dir = tempfile.mkdtemp(prefix="refactor-cli-")
#     clone_cmd = ["git", "clone", "--depth", "1"]
#     if branch:
#         clone_cmd.extend(["--branch", branch])
#     clone_cmd.extend([url, tmp_dir])

#     console.print(f"  [cyan]📦 Cloning {url}...[/]")
#     try:
#         subprocess.run(clone_cmd, check=True, capture_output=True, text=True, timeout=120)
#     except subprocess.CalledProcessError as e:
#         shutil.rmtree(tmp_dir, ignore_errors=True)
#         console.print(f"  [{C_TOOL_ERR}]✗ Clone failed: {(e.stderr or e.stdout or 'unknown error').strip()}[/]")
#         sys.exit(1)
#     except subprocess.TimeoutExpired:
#         shutil.rmtree(tmp_dir, ignore_errors=True)
#         console.print(f"  [{C_TOOL_ERR}]✗ Clone timed out after 120 seconds[/]")
#         sys.exit(1)

#     console.print(f"  [{C_TOOL_OK}]✓ Cloned to {tmp_dir}[/]")
#     return tmp_dir


# # ── Main ──────────────────────────────────────────────────────────────────────

# async def main():
#     parser = argparse.ArgumentParser(
#         description="Code Refactoring Agent — Terminal Chat",
#         formatter_class=argparse.RawDescriptionHelpFormatter,
#         epilog=(
#             "Examples:\n"
#             "  python cli.py --path ./my-project\n"
#             "  python cli.py --github https://github.com/user/repo\n"
#             "  python cli.py --github https://github.com/user/repo --branch main\n"
#         ),
#     )
#     parser.add_argument("--path",   help="Path to a local project directory")
#     parser.add_argument("--github", help="GitHub repository URL to clone")
#     parser.add_argument("--branch", help="Branch to clone (default: default branch)")
#     args = parser.parse_args()

#     temp_dir = None
#     workspace_path: str = ""

#     # ── Workspace Resolution ──────────────────────────────────────────────────
#     print_banner()

#     if args.github:
#         temp_dir = clone_github_repo(args.github, args.branch)
#         workspace_path = temp_dir
#     elif args.path:
#         workspace_path = os.path.abspath(args.path)
#         if not os.path.isdir(workspace_path):
#             console.print(f"[{C_TOOL_ERR}]Error: '{workspace_path}' is not a directory[/]")
#             sys.exit(1)
#     else:
#         console.print(Rule("[bold cyan]Setup[/]", style="cyan"))
#         console.print()
#         choice = console.input(
#             f"  [{C_BRAND}]📂 Local path or GitHub URL:[/]  "
#         ).strip()
#         if not choice:
#             console.print(f"  [{C_TOOL_ERR}]No path provided. Exiting.[/]")
#             sys.exit(1)

#         if choice.startswith(("http://", "https://")) or "github.com" in choice:
#             branch_in = console.input(
#                 f"  [{C_BRAND}]🌿 Branch (Enter = default):[/]  "
#             ).strip() or None
#             temp_dir = clone_github_repo(choice, branch_in)
#             workspace_path = temp_dir
#         else:
#             workspace_path = os.path.abspath(choice)
#             if not os.path.isdir(workspace_path):
#                 console.print(f"  [{C_TOOL_ERR}]Error: '{workspace_path}' is not a directory[/]")
#                 sys.exit(1)

#     if not workspace_path:
#         console.print(f"[{C_TOOL_ERR}]Error: Workspace path could not be determined.[/]")
#         sys.exit(1)

#     # ── Load Config ───────────────────────────────────────────────────────────
#     SYSTEM_PROMPT, TOOL_SCHEMAS, TOOL_NAMES = load_all_config()
#     history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

#     # ── Session Info ──────────────────────────────────────────────────────────
#     console.print(Rule("[bold cyan]Session[/]", style="cyan"))
#     print_workspace_info(workspace_path, TOOL_NAMES)

#     session_start = time.monotonic()
#     turn = 0
#     total_tools_used: list[str] = []

#     multiline_mode = False
#     current_model = (
#         os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
#         or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
#     )

#     # ── Chat Loop ─────────────────────────────────────────────────────────────
#     try:
#         while True:
#             # ── Prompt ───────────────────────────────────────────────────────
#             elapsed_s = int(time.monotonic() - session_start)
#             elapsed_fmt = f"{elapsed_s // 60}m {elapsed_s % 60}s"
#             console.print(
#                 Rule(
#                     f"[dim]Turn {turn + 1}  ·  {elapsed_fmt} elapsed[/]",
#                     style="dim",
#                 )
#             )

#             try:
#                 if multiline_mode:
#                     console.print(f"  [{C_USER}]You ▸[/] [dim](multiline mode, type '/submit' or press Ctrl-D to send)[/]")
#                     lines = []
#                     while True:
#                         try:
#                             line = console.input("  ... ")
#                             if line.strip().lower() == "/submit":
#                                 break
#                             lines.append(line)
#                         except EOFError:
#                             break
#                     user_input = "\n".join(lines).strip()
#                 else:
#                     user_input = console.input(f"  [{C_USER}]You ▸[/]  ").strip()
#             except EOFError:
#                 break

#             if not user_input:
#                 continue

#             # ── Slash Commands ────────────────────────────────────────────────
#             if user_input.startswith("/") or user_input.lower() in ("exit", "quit"):
#                 cmd_parts = user_input.split(maxsplit=1)
#                 first_word = cmd_parts[0].lower()
#                 arg = cmd_parts[1].strip() if len(cmd_parts) > 1 else ""

#                 if first_word in ("exit", "quit", "/exit", "/quit"):
#                     break
#                 if first_word == "/help":
#                     print_help()
#                     continue
#                 if first_word == "/clear":
#                     console.clear()
#                     print_banner()
#                     print_workspace_info(workspace_path, TOOL_NAMES)
#                     continue
#                 if first_word == "/workspace":
#                     console.print(f"  [cyan]{workspace_path}[/]")
#                     continue
#                 if first_word == "/history":
#                     console.print(f"  [dim]{len(history)} messages in context[/]")
#                     continue
#                 if first_word == "/multiline":
#                     multiline_mode = not multiline_mode
#                     status = "enabled" if multiline_mode else "disabled"
#                     console.print(f"  [cyan]Multiline mode {status}[/]")
#                     continue
#                 if first_word == "/system":
#                     console.print(Panel(Markdown(SYSTEM_PROMPT), title="[bold cyan]System Prompt[/]", border_style="cyan"))
#                     continue
#                 if first_word == "/tokens":
#                     try:
#                         from activities import _get_token_count
#                         tokens = _get_token_count(history)
#                         console.print(f"  [cyan]Context contains {len(history)} messages, ~{tokens} tokens[/]")
#                     except ImportError:
#                         console.print("  [red]Token counting not available.[/]")
#                     continue
#                 if first_word == "/undo":
#                     popped = 0
#                     while len(history) > 1 and history[-1]["role"] != "user":
#                         history.pop()
#                         popped += 1
#                     if len(history) > 1 and history[-1]["role"] == "user":
#                         history.pop()
#                         popped += 1
#                     console.print(f"  [cyan]Removed last turn ({popped} messages). Context size: {len(history)}[/]")
#                     continue
#                 if first_word == "/model":
#                     if arg:
#                         current_model = arg
#                         console.print(f"  [cyan]Model set to {current_model}[/]")
#                     else:
#                         console.print(f"  [cyan]Current model is {current_model}[/]")
#                     continue
#                 if first_word == "/save":
#                     if arg:
#                         try:
#                             with open(arg, "w") as f:
#                                 json.dump(history, f, indent=2)
#                             console.print(f"  [green]Saved history to {arg}[/]")
#                         except Exception as e:
#                             console.print(f"  [red]Error saving to {arg}: {e}[/]")
#                     else:
#                         console.print(f"  [red]Usage: /save <filename.json>[/]")
#                     continue
#                 if first_word == "/load":
#                     if arg:
#                         try:
#                             with open(arg, "r") as f:
#                                 history = json.load(f)
#                             console.print(f"  [green]Loaded history from {arg} ({len(history)} messages)[/]")
#                         except Exception as e:
#                             console.print(f"  [red]Error loading from {arg}: {e}[/]")
#                     else:
#                         console.print(f"  [red]Usage: /load <filename.json>[/]")
#                     continue
                
#                 if user_input.startswith("/"):
#                     console.print(f"  [red]Unknown command: {first_word}. Type /help for options.[/]")
#                     continue

#             # ── Agent Turn ────────────────────────────────────────────────────
#             turn += 1
#             console.print()

#             t_turn_start = time.monotonic()
#             response, tools_this_turn = await process_message(
#                 user_input, history, TOOL_SCHEMAS, workspace_path, turn, current_model
#             )
#             total_tools_used.extend(tools_this_turn)
#             t_turn_ms = int((time.monotonic() - t_turn_start) * 1000)

#             # ── Agent Response ────────────────────────────────────────────────
#             console.print()
#             console.print(
#                 Panel(
#                     Markdown(response),
#                     title=f"[{C_AGENT}]✦ Agent Response[/]  "
#                           f"[dim]({t_turn_ms / 1000:.1f}s · {len(tools_this_turn)} tools)[/]",
#                     border_style="bright_green",
#                     box=box.ROUNDED,
#                     padding=(1, 3),
#                 )
#             )

#     except KeyboardInterrupt:
#         console.print()

#     finally:
#         if temp_dir and os.path.exists(temp_dir):
#             console.print(f"\n  [dim]🧹 Cleaning up {temp_dir}...[/]")
#             shutil.rmtree(temp_dir, ignore_errors=True)

#     # ── Session Summary ───────────────────────────────────────────────────────
#     total_s = int(time.monotonic() - session_start)
#     console.print()
#     console.print(Rule("[bold cyan]Session Summary[/]", style="cyan"))

#     summary_tbl = Table(box=None, show_header=False, padding=(0, 2))
#     summary_tbl.add_column("Key",   style="bold white", no_wrap=True)
#     summary_tbl.add_column("Value", style="white")
#     summary_tbl.add_row("⏱  Duration",    f"{total_s // 60}m {total_s % 60}s")
#     summary_tbl.add_row("💬  Turns",       str(turn))
#     summary_tbl.add_row("🔧  Tools called", str(len(total_tools_used)))
#     if total_tools_used:
#         from collections import Counter
#         top = Counter(total_tools_used).most_common(3)
#         summary_tbl.add_row("📈  Top tools", ", ".join(f"{n}({c})" for n, c in top))

#     console.print(summary_tbl)
#     console.print()
#     console.print(Align.center(Text("✅  Session ended. Goodbye!", style="bold green")))
#     console.print()


# if __name__ == "__main__":
#     asyncio.run(main())






from rich.text import Text
 
#!/usr/bin/env python3
"""
cli.py — Terminal-based chat interface for the Code Refactoring Agent.
 
Same tools, same LLM, same workflow — runs directly without Temporal or the web UI.
 
Usage:
python cli.py --path /local/project # local repo
python cli.py --github https://github.com/u/r # clone and use
python cli.py # interactive prompt
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
 
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.rule import Rule
from rich.text import Text
from rich.columns import Columns
from rich.align import Align
from rich import box
from rich.padding import Padding
from rich.style import Style
from rich.prompt import Prompt
 
# ── Console & Theme ───────────────────────────────────────────────────────────
 
console = Console()
 
# Color palette
C_BRAND = "bold cyan"
C_USER = "bold green"
C_AGENT = "bold bright_green"
C_TOOL_OK = "green"
C_TOOL_ERR = "red"
C_TOOL_RUN = "blue"
C_DIM = "white dim"
C_WARN = "yellow"
 
# Tool type → display config
TOOL_META: dict[str, tuple[str, str]] = {
    "analyze_code": ("🔍", "cyan"),
    "suggest_refactor": ("💡", "yellow"),
    "apply_refactor": ("✏️", "magenta"),
    "diff_preview": ("📊", "blue"),
    "run_tests": ("🧪", "green"),
    "read_file": ("📄", "cyan"),
    "write_file": ("💾", "yellow"),
    "list_files": ("📁", "blue"),
    "ask_user": ("❓", "yellow"),
    "git_commit_push": ("🚀", "magenta"),
    "github_put_file": ("🌐", "blue"),
    "navigate_to_file": ("🗺️", "cyan"),
}
 
def _tool_meta(name: str) -> tuple[str, str]:
    return TOOL_META.get(name, ("⚙️", "white"))
 
 
# ── Banner ────────────────────────────────────────────────────────────────────
 
ASCII_LOGO = """\
██████╗ ███████╗███████╗ █████╗ ██████╗████████╗ ██████╗ ██████╗
██╔══██╗██╔════╝██╔════╝██╔══██╗██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗
██████╔╝█████╗ █████╗ ███████║██║     ██║     ██║██████╔╝
██╔══██╗██╔══╝ ██╔══╝ ██╔══██║██║     ██║     ██║██╔══██╗
██║  ██║███████╗██║     ██║  ██║╚██████╗ ██║     ╚██████╔╝██║  ██║
╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝      ╚═════╝ ╚═╝  ╚═╝"""
 
def print_banner():
    console.print()
    console.print(Align.center(Text(ASCII_LOGO, style="bold cyan")))
    console.print(Align.center(Text("✦ Code Refactoring Agent · Terminal Interface ✦", style="bold white")))
    console.print()
 
 
def print_help():
    tbl = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold cyan",
        border_style="cyan",
        padding=(0, 2),
    )
    tbl.add_column("Command", style="bold yellow", no_wrap=True)
    tbl.add_column("Description")
    tbl.add_row("/exit, /quit", "End the session")
    tbl.add_row("/clear", "Clear the screen")
    tbl.add_row("/help", "Show this help")
    tbl.add_row("/workspace", "Show current workspace path")
    tbl.add_row("/history", "Show number of messages in history")
    tbl.add_row("/multiline", "Toggle multi-line input mode")
    tbl.add_row("/retry", "Re-run the last user message")
    tbl.add_row("/save <file>", "Save chat history to a JSON file")
    tbl.add_row("/load <file>", "Load chat history from a JSON file")
    tbl.add_row("/undo", "Revert the last turn")
    tbl.add_row("/tokens", "Show current token count")
    tbl.add_row("/system", "Show the system prompt")
    tbl.add_row("/model <name>", "Switch the LLM model deployment")
    console.print(Panel(tbl, title="[bold cyan]Available Commands[/]", border_style="cyan"))
 
 
def print_workspace_info(workspace_path: str, tool_names: list[str]):
    tbl = Table(box=None, show_header=False, padding=(0, 2))
    tbl.add_column("Key", style="bold white", no_wrap=True)
    tbl.add_column("Value", style="white")
    tbl.add_row("📂 Workspace", f"[cyan]{workspace_path}[/]")
    tbl.add_row("🔧 Tools", f"[dim]{len(tool_names)} available[/]")
    tbl.add_row("📅 Session", f"[dim]{datetime.now().strftime('%Y-%m-%d %H:%M')}[/]")
    console.print(Panel(tbl, border_style="cyan", box=box.ROUNDED))
    console.print("[dim] Type [bold]/help[/] for commands. Ctrl+C or /exit to quit.[/]\n")
 
 
# ── Tool Rendering ────────────────────────────────────────────────────────────
 
def render_tool_call(tool_name: str, tool_args: dict):
    """Render a styled card for a tool invocation."""
    icon, color = _tool_meta(tool_name)
 
    # Build args preview
    lines = []
    for k, v in tool_args.items():
        if k == "workspace_path":
            continue
        val = str(v)
        if len(val) > 60:
            val = val[:57] + "…"
        lines.append(f" [dim]{k}:[/] [white]{val}[/]")
 
    body = "\n".join(lines) if lines else "[dim] (no args)[/]"
    console.print(
        Panel(
            body,
            title=f"[bold {color}]{icon} {tool_name}[/]",
            border_style=color,
            box=box.MINIMAL_HEAVY_HEAD,
            padding=(0, 1),
        )
    )
 
 
def render_tool_result(tool_name: str, result: dict, elapsed_ms: int):
    """Print a short status line after a tool completes."""
    status = result.get("status", "")
    _, color = _tool_meta(tool_name)
 
    if status == "success":
        # Extract a meaningful snippet from the result if possible
        snippet = ""
        for key in ("summary", "message", "output", "diff", "content"):
            raw = result.get(key)
            if raw and isinstance(raw, str):
                snippet = raw[:80].replace("\n", " ")
                break
        line = f"[{C_TOOL_OK}]✓ {tool_name}[/]"
        if snippet:
            line += f" [dim]→ {snippet}[/]"
        # show elapsed in dim parentheses
        line += f" [dim]({elapsed_ms}ms)[/]"
        console.print(f" {line}")
    elif status == "error":
        err = result.get("error", "")[:100]
        console.print(f" [{C_TOOL_ERR}]✗ {tool_name}[/] [dim]{err}[/]")
    else:
        console.print(f" [{C_DIM}]• {tool_name} → {status}[/]")
 
 
# ── VS Code Integration ───────────────────────────────────────────────────────

# Cache the VS Code command so we only pay the shutil.which cost once.
_VSCODE_CMD: str | None | bool = False  # False = not yet resolved


def _find_vscode_cmd() -> str | None:
    """Find the VS Code executable. Result is cached after the first call."""
    global _VSCODE_CMD
    if _VSCODE_CMD is not False:
        return _VSCODE_CMD  # type: ignore[return-value]

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
    """Open a file in VS Code in a background daemon thread (never blocks the CLI)."""
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
                os.startfile(file_path)  # type: ignore[attr-defined]
            except OSError:
                pass

    threading.Thread(target=_run, daemon=True).start()
    console.print(f" [dim]📂 Opening in VS Code: {Path(file_path).name}[/]")
 
 
# ── LLM Call ──────────────────────────────────────────────────────────────────
 
async def llm_call(messages: list[dict], tool_schemas: list[dict], model: str | None = None) -> dict:
    """Call Azure OpenAI — same logic as activities.py but without Temporal."""
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
        error_msg = str(e)
        return {"content": f"⚠️ LLM call failed: {type(e).__name__}: {error_msg[:200]}"}
 
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
    """
    Core think → act → observe loop.
    Returns (response_text, list_of_tools_used).
    """
    history.append({"role": "user", "content": user_message})
    max_steps = 15
    tools_used: list[str] = []
 
    SPINNERS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
 
    with console.status("", spinner="dots") as spinner_status:
        for step in range(max_steps):
            spinner_status.update(
                f"[bold cyan]{SPINNERS[step % len(SPINNERS)]}[/] "
                f"[bold blue]Thinking[/] [dim]· step {step + 1}/{max_steps}[/]"
            )
            llm_response = await llm_call(history, tool_schemas, model=model)
 
            tool_calls = llm_response.get("tool_calls")
            text_response = llm_response.get("content", "")
 
            if not tool_calls:
                history.append({"role": "assistant", "content": text_response})
                return text_response or "I'm not sure how to help with that.", tools_used
 
            # Log tool calls in history
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
 
            # Execute each tool
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
 
                # Parse arguments
                try:
                    tool_args = json.loads(tool_call["arguments"])
                except json.JSONDecodeError as e:
                    error_result = {
                        "status": "error",
                        "error": f"Invalid JSON arguments: {e}",
                    }
                    history.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(error_result),
                    })
                    spinner_status.stop()
                    console.print(f" [{C_TOOL_ERR}]✗ {tool_name}[/] [dim]invalid JSON args: {e}[/]")
                    spinner_status.start()
                    continue
 
                # ask_user → pause spinner, read input
                if tool_name == "ask_user":
                    question = tool_args.get("question", "")
                    spinner_status.stop()
                    console.print()
                    console.print(
                        Panel(
                            f"[bold yellow]{question}[/]",
                            title="[bold yellow]❓ Agent Question[/]",
                            border_style="yellow",
                            box=box.ROUNDED,
                        )
                    )
                    answer = console.input(f" [{C_USER}]Your answer ▸[/] ")
                    tool_result = {"status": "success", "answer": answer}
                    console.print(f" [{C_TOOL_OK}]✓ Answer recorded[/]")
                    spinner_status.start()
                else:
                    # Render the tool call card (pause spinner to avoid flicker)
                    spinner_status.stop()
                    render_tool_call(tool_name, tool_args)
 
                    t0 = time.monotonic()
                    handler = TOOL_HANDLERS.get(tool_name)
                    if handler is None:
                        tool_result = {
                            "status": "error",
                            "error": f"Unknown tool: '{tool_name}'",
                        }
                    else:
                        try:
                            tool_result = await handler(
                                workspace_path=workspace_path, **tool_args
                            )
                        except Exception as e:
                            tool_result = {
                                "status": "error",
                                "error": f"Tool error: {str(e)}",
                            }
 
                    elapsed = int((time.monotonic() - t0) * 1000)
                    render_tool_result(tool_name, tool_result, elapsed)
                    spinner_status.start()
 
                    # Auto-open files in VS Code
                    if tool_result.get("status") == "success" and tool_name in (
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
    """Shallow-clone a GitHub repo to a temp directory. Returns the path."""
    tmp_dir = tempfile.mkdtemp(prefix="refactor-cli-")
    clone_cmd = ["git", "clone", "--depth", "1"]
    if branch:
        clone_cmd.extend(["--branch", branch])
    clone_cmd.extend([url, tmp_dir])
 
    console.print(f" [cyan]📦 Cloning {url}...[/]")
    try:
        subprocess.run(clone_cmd, check=True, capture_output=True, text=True, timeout=120)
    except subprocess.CalledProcessError as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        console.print(f" [{C_TOOL_ERR}]✗ Clone failed: {(e.stderr or e.stdout or 'unknown error').strip()}[/]")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        console.print(f" [{C_TOOL_ERR}]✗ Clone timed out after 120 seconds[/]")
        sys.exit(1)
 
    console.print(f" [{C_TOOL_OK}]✓ Cloned to {tmp_dir}[/]")
    return tmp_dir
 
 
# ── Main ──────────────────────────────────────────────────────────────────────
 
async def main():
    parser = argparse.ArgumentParser(
        description="Code Refactoring Agent — Terminal Chat",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            " python cli.py --path ./my-project\n"
            " python cli.py --github https://github.com/user/repo\n"
            " python cli.py --github https://github.com/user/repo --branch main\n"
        ),
    )
    parser.add_argument("--path", help="Path to a local project directory")
    parser.add_argument("--github", help="GitHub repository URL to clone")
    parser.add_argument("--branch", help="Branch to clone (default: default branch)")
    args = parser.parse_args()
 
    temp_dir = None
    workspace_path: str = ""
 
    # ── Workspace Resolution ──────────────────────────────────────────────────
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
        choice = console.input(
            f" [{C_BRAND}]📂 Local path or GitHub URL:[/] "
        ).strip()
        if not choice:
            console.print(f" [{C_TOOL_ERR}]No path provided. Exiting.[/]")
            sys.exit(1)
 
        if choice.startswith(("http://", "https://")) or "github.com" in choice:
            branch_in = console.input(
                f" [{C_BRAND}]🌿 Branch (Enter = default):[/] "
            ).strip() or None
            temp_dir = clone_github_repo(choice, branch_in)
            workspace_path = temp_dir
        else:
            workspace_path = os.path.abspath(choice)
            if not os.path.isdir(workspace_path):
                console.print(f" [{C_TOOL_ERR}]Error: '{workspace_path}' is not a directory[/]")
                sys.exit(1)
 
    if not workspace_path:
        console.print(f"[{C_TOOL_ERR}]Error: Workspace path could not be determined.[/]")
        sys.exit(1)
 
    # ── Load Config ───────────────────────────────────────────────────────────
    SYSTEM_PROMPT, TOOL_SCHEMAS, TOOL_NAMES = load_all_config()
    history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
 
    # ── Session Info ──────────────────────────────────────────────────────────
    console.print(Rule("[bold cyan]Session[/]", style="cyan"))
    print_workspace_info(workspace_path, TOOL_NAMES)
 
    session_start = time.monotonic()
    turn = 0
    total_tools_used: list[str] = []
 
    multiline_mode = False
    last_user_input: str = ""
    current_model = (
        os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    )
 
    # ── Chat Loop ─────────────────────────────────────────────────────────────
    try:
        while True:
            # ── Prompt ───────────────────────────────────────────────────────
            elapsed_s = int(time.monotonic() - session_start)
            elapsed_fmt = f"{elapsed_s // 60}m {elapsed_s % 60}s"
            console.print(
                Rule(
                    f"[dim]Turn {turn + 1} · {elapsed_fmt} elapsed[/]",
                    style="dim",
                )
            )
 
            try:
                if multiline_mode:
                    console.print("[dim]Multiline mode enabled — type '/submit' or press Ctrl-D to send[/]")
                    lines = []
                    while True:
                        try:
                            line = console.input(" ... ")
                            if line.strip().lower() == "/submit":
                                break
                            lines.append(line)
                        except EOFError:
                            break
                    user_input = "\n".join(lines).strip()
                else:
                    user_input = console.input(f" [{C_USER}]You ▸[/] ").strip()
            except EOFError:
                break
 
            if not user_input:
                continue
 
            # ── Slash Commands ────────────────────────────────────────────────
            if user_input.startswith("/") or user_input.lower() in ("exit", "quit"):
                cmd_parts = user_input.split(maxsplit=1)
                first_word = cmd_parts[0].lower()
                arg = cmd_parts[1].strip() if len(cmd_parts) > 1 else ""
 
                if first_word in ("exit", "quit", "/exit", "/quit"):
                    break
                if first_word == "/help":
                    print_help()
                    continue
                if first_word == "/clear":
                    console.clear()
                    print_banner()
                    print_workspace_info(workspace_path, TOOL_NAMES)
                    continue
                if first_word == "/workspace":
                    console.print(f" [cyan]{workspace_path}[/]")
                    continue
                if first_word == "/history":
                    console.print(f" [dim]{len(history)} messages in context[/]")
                    continue
                if first_word == "/multiline":
                    multiline_mode = not multiline_mode
                    status = "enabled" if multiline_mode else "disabled"
                    console.print(f" [cyan]Multiline mode {status}[/]")
                    continue
                if first_word == "/system":
                    console.print(Panel(Markdown(SYSTEM_PROMPT), title="[bold cyan]System Prompt[/]", border_style="cyan"))
                    continue
                if first_word == "/tokens":
                    try:
                        tokens = _get_token_count(history)
                        console.print(f" [cyan]Context contains {len(history)} messages, ~{tokens} tokens[/]")
                    except ImportError:
                        console.print(" [red]Token counting not available.[/]")
                    continue
                if first_word == "/undo":
                    popped = 0
                    while len(history) > 1 and history[-1]["role"] != "user":
                        history.pop()
                        popped += 1
                    if len(history) > 1 and history[-1]["role"] == "user":
                        history.pop()
                        popped += 1
                    console.print(f" [cyan]Removed last turn ({popped} messages). Context size: {len(history)}[/]")
                    continue
                if first_word == "/model":
                    if arg:
                        current_model = arg
                        console.print(f" [cyan]Model set to {current_model}[/]")
                    else:
                        console.print(f" [cyan]Current model is {current_model}[/]")
                    continue
                if first_word == "/save":
                    if arg:
                        try:
                            with open(arg, "w") as f:
                                json.dump(history, f, indent=2)
                            console.print(f" [green]Saved history to {arg}[/]")
                        except Exception as e:
                            console.print(f" [red]Error saving to {arg}: {e}[/]")
                    else:
                        console.print(f" [red]Usage: /save <filename.json>[/]")
                    continue
                if first_word == "/load":
                    if arg:
                        try:
                            with open(arg, "r") as f:
                                history = json.load(f)
                            console.print(f" [green]Loaded history from {arg} ({len(history)} messages)[/]")
                        except Exception as e:
                            console.print(f" [red]Error loading from {arg}: {e}[/]")
                    else:
                        console.print(f" [red]Usage: /load <filename.json>[/]")
                    continue
 
                if first_word == "/retry":
                    if not last_user_input:
                        console.print("  [red]Nothing to retry — no previous message.[/]")
                        continue
                    user_input = last_user_input
                    console.print(f"  [cyan]↻ Retrying: {user_input[:80]}{'…' if len(user_input) > 80 else ''}[/]")
                    # Fall through to agent turn below
                else:
                    if user_input.startswith("/"):
                        console.print(f" [red]Unknown command: {first_word}. Type /help for options.[/]")
                        continue
 
            # ── Agent Turn ────────────────────────────────────────────────────
            last_user_input = user_input
            turn += 1
            console.print()
 
            t_turn_start = time.monotonic()
            response, tools_this_turn = await process_message(
                user_input, history, TOOL_SCHEMAS, workspace_path, turn, current_model
            )
            total_tools_used.extend(tools_this_turn)
            t_turn_ms = int((time.monotonic() - t_turn_start) * 1000)
           
            # ── Agent Response ────────────────────────────────────────────────
            title_text = Text.assemble(
                ("✦ Agent Response  ", C_AGENT),
                (f"{t_turn_ms / 1000:.1f}s · {len(tools_this_turn)} tools", "dim"),
            )

            console.print()
            console.print(
                Panel(
                    Markdown(response),
                    title=title_text,
                    border_style="bright_green",
                    box=box.ROUNDED,
                    padding=(1, 3),
                )
            )
            console.print()
 
 
    except KeyboardInterrupt:
        console.print()
 
    finally:
        if temp_dir and os.path.exists(temp_dir):
            console.print(f"\n [dim]🧹 Cleaning up {temp_dir}...[/]")
            shutil.rmtree(temp_dir, ignore_errors=True)
 
    # ── Session Summary ───────────────────────────────────────────────────────
    total_s = int(time.monotonic() - session_start)
    console.print()
    console.print(Rule("[bold cyan]Session Summary[/]", style="cyan"))
 
    summary_tbl = Table(box=None, show_header=False, padding=(0, 2))
    summary_tbl.add_column("Key", style="bold white", no_wrap=True)
    summary_tbl.add_column("Value", style="white")
    summary_tbl.add_row("⏱ Duration", f"{total_s // 60}m {total_s % 60}s")
    summary_tbl.add_row("💬 Turns", str(turn))
    summary_tbl.add_row("🔧 Tools called", str(len(total_tools_used)))
    if total_tools_used:
        from collections import Counter
        top = Counter(total_tools_used).most_common(3)
        summary_tbl.add_row("📈 Top tools", ", ".join(f"{n}({c})" for n, c in top))
 
    console.print(summary_tbl)
    console.print()
    console.print(Align.center(Text("✅ Session ended. Goodbye!", style="bold green")))
    console.print()
 
 
if __name__ == "__main__":
    asyncio.run(main())