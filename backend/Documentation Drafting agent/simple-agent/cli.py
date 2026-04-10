#!/usr/bin/env python3
"""
cli.py — Terminal interface for the DocuGenius Universal Agent

This script connects to the local Unified API (localhost:8002) and allows you to
interact with the Temporal Agent directly from your terminal.

Usage:
  python cli.py
  python cli.py --workspace /path/to/my/project
"""

import sys
import time
import json
import uuid
import argparse
import requests
import tempfile
import subprocess
import shutil
import os
import atexit
from textwrap import dedent

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


API_BASE = "http://127.0.0.1:8002"

def print_banner():
    if RICH_ENABLED:
        console = Console()
        banner = Panel(
            "[bold cyan]DocuGenius CLI[/bold cyan] - [dim]Powered by Temporal & Azure OpenAI[/dim]\n\n"
            "This universal agent can refactor code, generate docs, read files, and manage your repo.\n"
            "Type [bold red]exit[/bold red] to gracefully close the session.",
            border_style="cyan"
        )
        console.print(banner)
    else:
        print("="*60)
        print(" DocuGenius CLI - Powered by Temporal & Azure OpenAI")
        print(" Type 'exit' to gracefully close the session.")
        print(" (Install 'rich' via pip for a better UI experience)")
        print("="*60)


def start_workflow(workspace_path: str) -> str:
    """Start a new Temporal workflow session via the API."""
    try:
        response = requests.post(
            f"{API_BASE}/api/workflows",
            json={"agent_id": "reviewer", "workspace_path": workspace_path},
            timeout=100
        )
        response.raise_for_status()
        data = response.json()
        return data.get("workflow_id", "")
    except requests.exceptions.RequestException as e:
        if RICH_ENABLED:
            rprint(f"[bold red]❌ Error connecting to Unified API ({API_BASE}):[/bold red] {e}")
            rprint("[dim]Make sure 'uvicorn api:app' is running![/dim]")
        else:
            print(f"❌ Error connecting to API: {e}")
        sys.exit(1)


def delete_workflow(workflow_id: str):
    """Clean up the workflow session on the server."""
    try:
        requests.delete(f"{API_BASE}/api/workflows/{workflow_id}", timeout=60)
    except Exception:
        pass


def send_message(workflow_id: str, message: str):
    """Send a user message to the active workflow."""
    requests.post(
        f"{API_BASE}/api/workflows/{workflow_id}/messages",
        json={"message": message},
        timeout=100
    )


def render_response(text: str):
    """Render the AI response nicely."""
    if not text.strip():
        return
        
    if RICH_ENABLED:
        console = Console()
        console.print(Panel(Markdown(text), title="[bold green]Universal Agent[/bold green]", border_style="green", padding=(1, 2)))
    else:
        print(f"\n[Agent]:\n{text}\n")


def poll_until_response(workflow_id: str, initial_message_count: int) -> str:
    """Poll the API until the agent finishes thinking and returns a new response."""
    last_status = ""
    last_response = ""
    
    if RICH_ENABLED:
        console = Console()
        spinner = Spinner("dots")
        with Live(spinner, refresh_per_second=10, transient=True) as live:
            while True:
                try:
                    resp = requests.get(f"{API_BASE}/api/workflows/{workflow_id}/status", timeout=100)
                    resp.raise_for_status()
                    data = resp.json()
                    status_dict = data.get("status", {})
                    
                    status_str = status_dict.get("status", "idle")
                    msg_count = status_dict.get("message_count", 0)
                    last_response = status_dict.get("last_response", "")

                    if status_str != last_status:
                        if status_str == "gathering_context":
                            live.update(Panel("[cyan]⏳ Gathering Codebase Context (Reranking & Metadata)...[/cyan]"))
                        elif status_str == "thinking":
                            live.update(Panel("[yellow]🧠 Agent is thinking or executing tools...[/yellow]"))
                        elif status_str == "waiting_for_worker":
                            live.update(Panel("[red]⏳ Waiting for Temporal Worker. Please ensure worker.py is running.[/red]"))
                        last_status = status_str

                    # Condition for completion
                    if msg_count >= initial_message_count + 2 and status_str in ["idle", "waiting_for_user"]:
                        return last_response

                except Exception as e:
                    live.update(f"[red]Error polling status: {e}[/red]")
                    time.sleep(2)
                
                time.sleep(1)
    else:
        # Fallback for non-rich printing
        while True:
            try:
                resp = requests.get(f"{API_BASE}/api/workflows/{workflow_id}/status", timeout=100)
                data = resp.json().get("status", {})
                
                status_str = data.get("status", "idle")
                msg_count = data.get("message_count", 0)
                if status_str != last_status:
                    if status_str == "gathering_context":
                        print(" [⏳ Gathering Codebase Context (Reranking & Metadata)...]")
                    elif status_str == "thinking":
                        print(" [🧠 Agent is thinking or executing tools...]")
                    elif status_str == "waiting_for_worker":
                        print(" [⏳ Waiting for Temporal Worker. Please ensure worker.py is running.]")
                    else:
                        print(f" [...] Status changed to: {status_str}")
                    last_status = status_str

                if msg_count >= initial_message_count + 2 and status_str in ["idle", "waiting_for_user"]:
                    return data.get("last_response", "")
            except Exception:
                pass
            time.sleep(1.5)


def main():
    parser = argparse.ArgumentParser(description="Universal Agent CLI")
    parser.add_argument("--workspace", default=".", help="Absolute or relative path to the codebase to analyze.")
    args = parser.parse_args()

    print_banner()

    # Prompt the user to confirm or enter the workspace path
    if RICH_ENABLED:
        workspace_input = Prompt.ask(
            "\n[bold cyan]Enter workspace path[/bold cyan]", 
            default=args.workspace
        )
    else:
        ans = input(f"\nEnter workspace path (default: '{args.workspace}'): ").strip()
        workspace_input = ans if ans else args.workspace

    workspace_input = workspace_input.strip()

    if workspace_input.startswith("http://") or workspace_input.startswith("https://") or workspace_input.startswith("git@"):
        if not shutil.which("git"):
            if RICH_ENABLED:
                rprint("[bold red]Git is required to clone remote repositories. Please install Git.[/bold red]")
            else:
                print("Git is required to clone remote repositories. Please install Git.")
            sys.exit(1)
            
        temp_dir = tempfile.mkdtemp(prefix="docugenius_repo_")
        if RICH_ENABLED:
            rprint(f"[cyan]Cloning remote repository into temporary workspace: {temp_dir}[/cyan]")
        else:
            print(f"Cloning remote repository into temporary workspace: {temp_dir}")
            
        res = subprocess.run(["git", "clone", workspace_input, temp_dir], capture_output=True, text=True)
        if res.returncode != 0:
            if RICH_ENABLED:
                rprint(f"[bold red]Failed to clone repository:[/bold red]\n{res.stderr}")
            else:
                print(f"Failed to clone repository:\n{res.stderr}")
            sys.exit(1)
            
        args.workspace = temp_dir
        
        def cleanup_temp_dir():
            try:
                def onerror(func, path, exc_info):
                    import stat
                    if not os.access(path, os.W_OK):
                        os.chmod(path, stat.S_IWUSR)
                        func(path)
                    else:
                        raise
                shutil.rmtree(temp_dir, onerror=onerror)
            except Exception:
                pass
        atexit.register(cleanup_temp_dir)
    else:
        args.workspace = workspace_input

    if RICH_ENABLED:
        rprint(f"[dim]Starting session bound to workspace: [bold]{args.workspace}[/bold] ...[/dim]")
    else:
        print(f"Starting session bound to workspace: {args.workspace} ...")
        
    workflow_id = start_workflow(args.workspace)
    
    if RICH_ENABLED:
        rprint(f"[dim]Session started! (Temporal ID: {workflow_id})[/dim]\n")
    else:
        print(f"Session started: {workflow_id}\n")

    message_count = 0 

    try:
        while True:
            # 1. Get input
            if RICH_ENABLED:
                user_msg = Prompt.ask("\n[bold blue]You[/bold blue]")
            else:
                user_msg = input("\nYou: ")
                
            user_msg = user_msg.strip()
            if not user_msg:
                continue
                
            if user_msg.lower() in ["exit", "quit", "q"]:
                break

            # 2. Get current initial state to know when the agent finishes appending its response
            try:
                state_resp = requests.get(f"{API_BASE}/api/workflows/{workflow_id}/status", timeout=60).json()
                message_count = state_resp.get("status", {}).get("message_count", 0)
            except Exception:
                message_count = 0 

            # 3. Send message
            send_message(workflow_id, user_msg)
            
            # 4. Wait for LLM
            final_response = poll_until_response(workflow_id, message_count)

            # 5. Render
            render_response(final_response)

    except KeyboardInterrupt:
        sys.exit(1)
    finally:
        if RICH_ENABLED:
            rprint("\n[dim]Cleaning up Temporal workflow session...[/dim]")
        else:
            print("\nCleaning up session...")
        delete_workflow(workflow_id)
        if RICH_ENABLED:
            rprint("[bold green]Goodbye![/bold green]")
        else:
            print("Goodbye!")
            
if __name__ == "__main__":
    main()
