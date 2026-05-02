#!/usr/bin/env python3
"""
cli.py — Entry point and presentation layer for the Docker AI Agent.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv
from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

load_dotenv()

console = Console()

BANNER = """
[bold cyan] ██████╗  ██████╗  ██████╗██╗  ██╗███████╗██████╗[/]
[bold cyan] ██╔══██╗██╔═══██╗██╔════╝██║ ██╔╝██╔════╝██╔══██╗[/]
[bold cyan] ██║  ██║██║   ██║██║     █████╔╝ █████╗  ██████╔╝[/]
[bold cyan] ██║  ██║██║   ██║██║     ██╔═██╗ ██╔══╝  ██╔══██╗[/]
[bold cyan] ██████╔╝╚██████╔╝╚██████╗██║  ██╗███████╗██║  ██║[/]
[bold cyan] ╚═════╝  ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝[/]
[dim]            AI-powered containerisation agent[/]
"""

AUTO_PROMPT = """\
Run the full containerisation pipeline on this project:
1. list_files → read key dependency/config files
2. analyze_project
3. generate_dockerfile + generate_compose
4. podman_build
5. If build fails → repair_build (repeat up to 5×)
6. podman_run
7. health_check
8. optimize_image
Report the final status concisely.\
"""

HELP_TEXT = """\
[bold]Commands[/]
  [cyan]/auto[/]    Run the full containerisation pipeline automatically
  [cyan]/clear[/]   Reset conversation history (keeps system prompt)
  [cyan]/help[/]    Show this message
  [cyan]/exit[/]    Quit
"""


def _print_banner() -> None:
    console.print(BANNER)
    console.print(Rule(style="dim cyan"))


def _print_response(text: str) -> None:
    console.print(Panel(
        Markdown(text),
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2),
    ))


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Docker AI Agent — AI-powered containerisation assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--path",  metavar="DIR",   help="Workspace directory (default: prompt)")
    parser.add_argument("--auto",  action="store_true", help="Run the full pipeline non-interactively")
    parser.add_argument("--model", metavar="NAME",  help="Override deployment/model name",
                        default=os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "gpt-4o"))
    args = parser.parse_args()

    _print_banner()

    # ── Resolve workspace ────────────────────────────────────────────────────
    if args.path:
        workspace = os.path.abspath(args.path)
    else:
        raw = console.input("  [cyan]Project path[/] [dim](leave blank for current dir)[/]: ").strip()
        workspace = os.path.abspath(raw) if raw else os.path.abspath(".")

    if not os.path.isdir(workspace):
        console.print(f"[red]Directory not found:[/] {workspace}")
        sys.exit(1)

    console.print(f"\n  [dim]Workspace:[/] [bold]{workspace}[/]")
    console.print(f"  [dim]Model:[/]     [bold]{args.model}[/]")
    console.print(f"  [dim]Runtime:[/]   [bold]{os.getenv('CONTAINER_RUNTIME', 'docker')}[/]\n")

    # ── Lazy imports (after env is loaded) ──────────────────────────────────
    from agent import load_system_prompt, run_agent

    system_prompt = load_system_prompt()
    history: list[dict] = [{"role": "system", "content": system_prompt}]

    # ── Non-interactive --auto mode ─────────────────────────────────────────
    if args.auto:
        console.print(Rule("[bold cyan]AUTO MODE[/]", style="cyan"))
        answer, tools_used = await run_agent(AUTO_PROMPT, history, workspace, args.model)
        _print_response(answer)
        console.print(Rule(style="dim"))
        console.print(f"  [dim]Tools used ({len(tools_used)}):[/] {', '.join(tools_used)}")
        return

    # ── Interactive REPL ─────────────────────────────────────────────────────
    console.print(HELP_TEXT)
    console.print(Rule(style="dim cyan"))

    while True:
        try:
            user_input = console.input("\n[bold green]You ▸[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Bye.[/]")
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd in ("/exit", "/quit"):
            console.print("[dim]Bye.[/]")
            break

        if cmd == "/help":
            console.print(HELP_TEXT)
            continue

        if cmd == "/clear":
            history = [{"role": "system", "content": system_prompt}]
            console.print("[dim]  ✓ Conversation history cleared.[/]")
            continue

        if cmd == "/auto":
            user_input = AUTO_PROMPT

        console.print()
        try:
            answer, tools_used = await run_agent(user_input, history, workspace, args.model)
        except KeyboardInterrupt:
            console.print("\n[yellow]  ⚠ Interrupted.[/]")
            continue

        _print_response(answer)
        if tools_used:
            console.print(f"  [dim]Tools: {', '.join(tools_used)}[/]")


if __name__ == "__main__":
    asyncio.run(main())
