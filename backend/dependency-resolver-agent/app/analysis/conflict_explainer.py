"""
AI-powered conflict explainer — uses LLM to explain dependency conflicts.
"""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.analysis.conflict_detector import Conflict, ConflictReport
from app.llm.langchain_llm import get_langchain_llm

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a dependency management expert.
Given a list of dependency version conflicts, explain each conflict clearly:
- What the conflict is
- Why it happens (which packages require incompatible versions)
- The practical impact on the project
Be concise but thorough.  Use bullet points.  No markdown headers."""


def explain_conflicts(report: ConflictReport) -> list[dict[str, str]]:
    """
    Generate AI explanations for each detected conflict.

    Returns a list of {"package": ..., "explanation": ...} dicts.
    Falls back to rule-based explanations if LLM is unavailable.
    """
    if not report.conflicts:
        return []

    llm = get_langchain_llm()
    explanations: list[dict[str, str]] = []

    if llm is None:
        # Fallback: rule-based explanation
        for c in report.conflicts:
            explanations.append({
                "package": c.package,
                "explanation": _rule_based_explanation(c),
            })
        return explanations

    # Build prompt with all conflicts
    conflict_text = "\n".join(
        f"- {c.package}: constraints {c.constraints} (sources: {c.sources})"
        for c in report.conflicts
    )

    try:
        response = llm.invoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=f"Explain these dependency conflicts:\n{conflict_text}"),
        ])
        # Single response for all conflicts
        full_explanation = response.content

        # Attach the full explanation to each conflict
        for c in report.conflicts:
            explanations.append({
                "package": c.package,
                "explanation": full_explanation,
            })
    except Exception:
        logger.exception("LLM conflict explanation failed — using fallback")
        for c in report.conflicts:
            explanations.append({
                "package": c.package,
                "explanation": _rule_based_explanation(c),
            })

    return explanations


def _rule_based_explanation(c: Conflict) -> str:
    """Simple rule-based fallback explanation."""
    sources_str = ", ".join(c.sources) if c.sources else "the project root"
    constraints_str = " and ".join(c.constraints)
    return (
        f"Package '{c.package}' has conflicting version requirements: {constraints_str}. "
        f"These constraints are imposed by: {sources_str}. "
        f"This means no single version of '{c.package}' can satisfy all dependents simultaneously."
    )
