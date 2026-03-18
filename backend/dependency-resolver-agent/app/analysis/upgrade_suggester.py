"""
AI-powered upgrade suggester — recommends version upgrades to resolve conflicts.
"""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.analysis.conflict_detector import ConflictReport
from app.llm.langchain_llm import get_langchain_llm
from app.resolver.dependency_resolver import ResolutionResult

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a dependency management expert.
Given dependency resolution data and conflicts, suggest specific version upgrades that would resolve the conflicts.
For each suggestion:
- State the package and current version(s)
- Recommend a target version or constraint
- Explain why this upgrade resolves the conflict
Be concise.  Use bullet points.  No markdown headers."""


def suggest_upgrades(
    result: ResolutionResult,
    conflict_report: ConflictReport,
) -> list[dict[str, str]]:
    """
    Generate AI-powered upgrade suggestions.

    Returns a list of {"package": ..., "suggestion": ...} dicts.
    Falls back to heuristic suggestions if LLM is unavailable.
    """
    if not conflict_report.conflicts:
        return []

    llm = get_langchain_llm()
    suggestions: list[dict[str, str]] = []

    if llm is None:
        # Fallback: heuristic suggestions
        for c in conflict_report.conflicts:
            suggestions.append({
                "package": c.package,
                "suggestion": (
                    f"Consider updating packages that depend on '{c.package}' "
                    f"to versions with compatible constraints. "
                    f"Current conflicting constraints: {', '.join(c.constraints)}"
                ),
            })
        return suggestions

    # Build context from resolution result
    dep_info = "\n".join(
        f"- {name}: {node.version or 'unknown'} (spec: {node.specifier or 'any'})"
        for name, node in result.resolved.items()
    )
    conflict_info = "\n".join(
        f"- {c.package}: constraints {c.constraints} from {c.sources}"
        for c in conflict_report.conflicts
    )

    try:
        response = llm.invoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"Current dependencies:\n{dep_info}\n\n"
                    f"Conflicts:\n{conflict_info}\n\n"
                    f"Suggest upgrades to resolve these conflicts."
                ),
            ),
        ])

        for c in conflict_report.conflicts:
            suggestions.append({
                "package": c.package,
                "suggestion": response.content,
            })
    except Exception:
        logger.exception("LLM upgrade suggestion failed — using fallback")
        for c in conflict_report.conflicts:
            suggestions.append({
                "package": c.package,
                "suggestion": (
                    f"Consider updating packages that depend on '{c.package}' "
                    f"to versions with compatible constraints."
                ),
            })

    return suggestions
