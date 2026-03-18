"""
CLI interface — `resolver scan <repo_url>`
"""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from app.analysis.conflict_detector import detect_conflicts
from app.analysis.conflict_explainer import explain_conflicts
from app.analysis.upgrade_suggester import suggest_upgrades
from app.parser.node_parser import parse_node_deps
from app.parser.python_parser import parse_python_deps
from app.reports.report_generator import format_report_text, generate_report
from app.resolver.dependency_resolver import resolve_node, resolve_python
from app.resolver.graph_builder import build_graph, get_dependency_tree
from app.services.repo_service import Ecosystem, cleanup_repo, load_repo

app = typer.Typer(
    name="resolver",
    help="Dependency Resolver Agent — analyse and resolve repository dependencies.",
)
console = Console()


def _render_tree(tree_data: dict, parent: Tree | None = None) -> Tree:
    """Recursively render a dependency tree using Rich."""
    label = tree_data["name"]
    version = tree_data.get("version", "")
    if version:
        label += f" [dim]{version}[/dim]"

    if parent is None:
        node = Tree(f"[bold cyan]{label}[/bold cyan]")
    else:
        node = parent.add(label)

    for child in tree_data.get("children", []):
        _render_tree(child, node)

    return node


async def _scan(repo_url: str) -> None:
    """Core scan logic (async)."""
    with console.status("[bold green]Loading repository…"):
        repo_info = load_repo(repo_url)

    console.print(
        Panel(
            f"[bold]Ecosystems detected:[/bold] {', '.join(e.value for e in repo_info.ecosystems)}",
            title="Repository Info",
            border_style="blue",
        )
    )

    for eco in repo_info.ecosystems:
        dep_files = repo_info.dependency_files.get(eco, [])

        with console.status(f"[bold green]Parsing {eco.value} dependencies…"):
            if eco == Ecosystem.PYTHON:
                deps = parse_python_deps(dep_files)
                console.print(f"  Parsed [cyan]{len(deps)}[/cyan] Python dependencies")
            elif eco == Ecosystem.NODE:
                deps = parse_node_deps(dep_files)
                console.print(f"  Parsed [cyan]{len(deps)}[/cyan] Node dependencies")
            else:
                continue

        with console.status(f"[bold green]Resolving {eco.value} dependencies…"):
            if eco == Ecosystem.PYTHON:
                result = await resolve_python(deps)
            else:
                result = await resolve_node(deps)

        G = build_graph(result)
        conflict_report = detect_conflicts(G)

        # ── Root Dependencies ──
        root_table = Table(title=f"Root Dependencies ({eco.value})", show_header=True)
        root_table.add_column("Package", style="cyan")
        root_table.add_column("Specifier", style="green")
        for d in deps:
            root_table.add_row(d.name, d.specifier or "any")
        console.print(root_table)

        # ── Dependency Tree ──
        console.print(f"\n[bold]Dependency Tree[/bold] ({G.number_of_nodes()} packages)")
        for root_name in result.root_dependencies:
            tree_data = get_dependency_tree(G, root_name)
            tree_widget = _render_tree(tree_data)
            console.print(tree_widget)

        # ── Conflicts ──
        if conflict_report.conflicts:
            conflict_table = Table(title="⚠  Conflicts", show_header=True, border_style="red")
            conflict_table.add_column("Package", style="red bold")
            conflict_table.add_column("Constraints")
            conflict_table.add_column("Sources")
            for c in conflict_report.conflicts:
                conflict_table.add_row(
                    c.package,
                    ", ".join(c.constraints),
                    ", ".join(c.sources) if c.sources else "root",
                )
            console.print(conflict_table)
        else:
            console.print("[bold green]✓ No conflicts detected[/bold green]")

        # ── AI Explanations ──
        explanations = explain_conflicts(conflict_report)
        suggestions = suggest_upgrades(result, conflict_report)

        if explanations:
            console.print("\n[bold]AI Explanations[/bold]")
            for ex in explanations:
                console.print(
                    Panel(ex["explanation"], title=f"[bold]{ex['package']}[/bold]", border_style="yellow")
                )

        if suggestions:
            console.print("\n[bold]AI Upgrade Suggestions[/bold]")
            for s in suggestions:
                console.print(
                    Panel(s["suggestion"], title=f"[bold]{s['package']}[/bold]", border_style="green")
                )

    cleanup_repo(repo_info)
    console.print("\n[bold green]✓ Scan complete[/bold green]")


@app.callback()
def callback():
    """Dependency Resolver Agent CLI"""
    pass

@app.command()
def scan(
    repo_url: str = typer.Argument(..., help="Repository URL or local path to scan"),
) -> None:
    """Scan a repository and resolve all dependencies."""
    asyncio.run(_scan(repo_url))

if __name__ == "__main__":
    app()
