#!/usr/bin/env python3
"""
cli.py — Terminal interface for the Documentation Drafting Agent (LangGraph)

This script runs the LangGraph StateGraph directly in the terminal without 
needing an external API server or Temporal worker.

Usage:
  python cli.py
  python cli.py --path /path/to/my/project
  python cli.py --github owner/repo
"""

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from config_loader import load_all_config
from graph import graph, SYSTEM_PROMPT
from langgraph.types import Command

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.spinner import Spinner
    from rich.live import Live
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich import print as rprint
    RICH_ENABLED = True
except ImportError:
    RICH_ENABLED = False


def print_banner():
    if RICH_ENABLED:
        console = Console()
        banner = Panel(
            "[bold cyan]Documentation Drafting Agent[/bold cyan] - [dim]Powered by LangGraph & Azure OpenAI[/dim]\n\n"
            "This agent can generate READMEs, document APIs, explain folder structures, and draw diagrams.\n"
            "Type [bold red]exit[/bold red] to gracefully close the session.",
            border_style="cyan"
        )
        console.print(banner)
    else:
        print("="*60)
        print(" Documentation Drafting Agent - Powered by LangGraph & Azure OpenAI")
        print(" Type 'exit' to gracefully close the session.")
        print(" (Install 'rich' via pip for a better UI experience)")
        print("="*60)


def clone_github_repo(url: str) -> str:
    tmp_dir = tempfile.mkdtemp(prefix="doc-agent-cli-")
    
    if not url.startswith("http"):
        url = f"https://github.com/{url}"

    clone_cmd = ["git", "clone", "--depth", "1", url, tmp_dir]
    if RICH_ENABLED:
        rprint(f"[cyan]Cloning {url}...[/cyan]")
    else:
        print(f"Cloning {url}...")

    try:
        subprocess.run(clone_cmd, check=True, capture_output=True, text=True, timeout=120)
    except subprocess.CalledProcessError as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        err = e.stderr or e.stdout or "unknown error"
        if RICH_ENABLED:
            rprint(f"[bold red]Clone failed:[/bold red] {err.strip()}")
        else:
            print(f"Clone failed: {err.strip()}")
        sys.exit(1)

    if RICH_ENABLED:
        rprint(f"[green]Cloned to {tmp_dir}[/green]")
    else:
        print(f"Cloned to {tmp_dir}")
        
    return tmp_dir


def render_response(text: str):
    if not text.strip():
        return
    if RICH_ENABLED:
        console = Console()
        console.print(Panel(Markdown(text), title="[bold green]Documentation Agent[/bold green]", border_style="green", padding=(1, 2)))
    else:
        print(f"\n[Agent]:\n{text}\n")


async def process_message(
    user_message: str,
    workspace_path: str,
    session_id: str,
    turn: int,
):
    config = {"configurable": {"thread_id": session_id}}
    
    existing = graph.get_state(config)
    if existing and existing.values:
        prev_history = existing.values.get("history", [])
        new_history  = prev_history + [{"role": "user", "content": user_message}]
        input_state  = {"history": new_history, "workspace_path": workspace_path}
    else:
        input_state = {
            "history": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            "workspace_path": workspace_path,
        }

    live = None
    spinner = None
    if RICH_ENABLED:
        spinner = Spinner("dots")
        live = Live(spinner, refresh_per_second=10, transient=True)
        live.start()

    try:
        async for event in graph.astream(input_state, config=config, stream_mode="updates"):
            for node_name, state_update in event.items():
                if live:
                    if node_name == "gather_context_node":
                        live.update(Panel("[cyan]⏳ Gathering Codebase Context (Reranking & Metadata)...[/cyan]"))
                    elif node_name == "llm_node":
                        if state_update.get("pending_tool_calls"):
                            live.update(Panel("[yellow]🧠 Agent is deciding which tools to run...[/yellow]"))
                    elif node_name == "tool_node":
                        live.update(Panel("[green]🛠️  Agent is executing tools...[/green]"))
                else:
                    if node_name == "gather_context_node":
                        print(" [⏳ Gathering Codebase Context (Reranking & Metadata)...]")
                    elif node_name == "llm_node" and state_update.get("pending_tool_calls"):
                        print(" [🧠 Agent is deciding which tools to run...]")
                    elif node_name == "tool_node":
                        print(" [🛠️  Agent is executing tools...]")

        # Check for ask_user interrupt
        state_after = graph.get_state(config)
        while state_after and state_after.tasks and any(t.interrupts for t in state_after.tasks):
            if live: live.stop()
            
            task = next(t for t in state_after.tasks if t.interrupts)
            question = task.interrupts[0].value
            
            if RICH_ENABLED:
                answer = Prompt.ask(f"\n[bold magenta]Agent Question:[/bold magenta] {question}")
            else:
                print(f"\nAgent Question: {question}")
                answer = input("Your answer: ")
                
            if live: live.start()
            
            # Resume graph with user answer
            async for event in graph.astream(Command(resume=answer), config=config, stream_mode="updates"):
                pass 
                
            state_after = graph.get_state(config)

        if live: live.stop()

        final_state = graph.get_state(config)
        response = final_state.values.get("last_response", "No response.")
        render_response(response)

    except Exception as e:
        if live: live.stop()
        if RICH_ENABLED:
            rprint(f"[bold red]Error:[/bold red] {e}")
        else:
            print(f"Error: {e}")


async def main():
    parser = argparse.ArgumentParser(description="Documentation Drafting Agent (LangGraph)")
    parser.add_argument("--path", help="Path to a local project directory")
    parser.add_argument("--github", help="GitHub repository URL to clone")
    args = parser.parse_args()

    temp_dir = None
    workspace_path = ""

    print_banner()

    if args.github:
        workspace_path = clone_github_repo(args.github)
        temp_dir = workspace_path
    elif args.path:
        workspace_path = os.path.abspath(args.path)
        if not os.path.isdir(workspace_path):
            print(f"Error: '{workspace_path}' is not a directory")
            sys.exit(1)
    else:
        if RICH_ENABLED:
            choice = Prompt.ask("\n[bold cyan]Enter workspace path or GitHub URL[/bold cyan]", default=".")
        else:
            choice = input("\nEnter workspace path or GitHub URL (default: '.'): ").strip() or "."
            
        if choice.startswith("http") or "github.com" in choice:
            workspace_path = clone_github_repo(choice)
            temp_dir = workspace_path
        else:
            workspace_path = os.path.abspath(choice)
            if not os.path.isdir(workspace_path):
                print(f"Error: '{workspace_path}' is not a directory")
                sys.exit(1)

    session_id = str(uuid.uuid4())
    
    if RICH_ENABLED:
        rprint(f"[dim]Starting session bound to workspace: [bold]{workspace_path}[/bold] ...[/dim]")
        rprint(f"[dim]Session ID: {session_id}[/dim]\n")
    else:
        print(f"Starting session bound to workspace: {workspace_path} ...\n")

    turn = 0

    try:
        while True:
            if RICH_ENABLED:
                user_input = Prompt.ask("\n[bold blue]You[/bold blue]")
            else:
                user_input = input("\nYou ▸ ")
                
            user_input = user_input.strip()
            if not user_input: continue

            if user_input.lower() in ("exit", "quit", "q", "/exit", "/quit"):
                break

            turn += 1
            await process_message(user_input, workspace_path, session_id, turn)

    except KeyboardInterrupt:
        pass
    finally:
        if temp_dir and os.path.exists(temp_dir):
            if RICH_ENABLED:
                rprint(f"\n[dim]Cleaning up {temp_dir}...[/dim]")
            else:
                print(f"\nCleaning up {temp_dir}...")
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        if RICH_ENABLED:
            rprint("[bold green]Goodbye![/bold green]")
        else:
            print("Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
