"""
Mermaid diagram sanitization and fallback generation.

The LLM frequently wraps Mermaid output in markdown fences, includes HTML
entities, uses wrong casing (SubGraph), or produces other artifacts that
break the Mermaid parser.  This module strips those problems and, as a
last resort, builds a simple diagram from canonical component data so the
frontend always has *something* to render.
"""

from __future__ import annotations

import re
from typing import List, Optional

# Valid Mermaid diagram opening keywords (lowercase)
_VALID_STARTS = (
    "flowchart",
    "graph",
    "sequencediagram",
    "classdiagram",
    "statediagram",
    "erdiagram",
    "gantt",
    "pie",
    "journey",
    "gitgraph",
    "mindmap",
    "timeline",
    "quadrantchart",
    "sankey",
    "xychart",
    "block",
    "c4context",
    "c4container",
    "c4component",
    "c4deployment",
    "%%{",
)

_FENCE_RE = re.compile(
    r"^```(?:mermaid|mmd)?\s*\n?", re.MULTILINE | re.IGNORECASE
)
_CLOSE_FENCE_RE = re.compile(r"\n?```\s*$", re.MULTILINE)
_HTML_ENTITIES = {
    "&gt;": ">",
    "&lt;": "<",
    "&amp;": "&",
    "&quot;": '"',
    "&#39;": "'",
    "&nbsp;": " ",
}

# Fix "SubGraph" → "subgraph" (case-insensitive)
_SUBGRAPH_RE = re.compile(r"^\s*SubGraph\b", re.MULTILINE | re.IGNORECASE)

# Fix unquoted multi-word subgraph labels:
# "subgraph AWS Cloud" → "subgraph AWSCloud["AWS Cloud"]"
# Uses [ \t] instead of \s to avoid matching across newlines
_SUBGRAPH_LABEL_RE = re.compile(
    r'^(\s*subgraph[ \t]+)([A-Za-z0-9][\w]*(?:[ \t]+[\w]+)+)[ \t]*$',
    re.MULTILINE
)


def _fix_subgraph_label(m: re.Match) -> str:
    """Convert `subgraph AWS Cloud` → `subgraph AWSCloud["AWS Cloud"]`"""
    prefix = m.group(1)  # "  subgraph "
    raw_label = m.group(2).strip()  # "AWS Cloud"
    # Already has brackets → leave alone
    if "[" in raw_label or '"' in raw_label:
        return m.group(0)
    node_id = re.sub(r"[^a-zA-Z0-9]", "", raw_label)
    return f'{prefix}{node_id}["{raw_label}"]'


def sanitize_mermaid(raw: str) -> str:
    """Clean up LLM-produced Mermaid code so it can be parsed reliably.

    Handles:
    - Markdown code fences (```mermaid … ```)
    - HTML entities (&gt; → >)
    - Stray backticks
    - Leading/trailing whitespace
    - Smart quotes → straight quotes
    - Wrong casing: SubGraph → subgraph
    - Unquoted subgraph labels with spaces
    - Parentheses in node labels without quotes
    """
    if not raw:
        return ""

    text = raw

    # 1. Strip markdown fences
    text = _FENCE_RE.sub("", text)
    text = _CLOSE_FENCE_RE.sub("", text)

    # 2. Remove any remaining stray backticks (triple or single)
    text = text.replace("```", "")
    text = text.replace("`", "")

    # 3. Replace HTML entities
    for entity, char in _HTML_ENTITIES.items():
        text = text.replace(entity, char)

    # 4. Fix smart quotes
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")

    # 5. Fix arrows that LLM sometimes mangles
    text = text.replace("\u2014>", "-->")   # em-dash arrow
    text = text.replace("- >", "-->")

    # 6. Fix "SubGraph" → "subgraph" (Mermaid is case-sensitive for keywords)
    text = _SUBGRAPH_RE.sub(lambda m: m.group(0).lower().replace("subgraph", "subgraph"), text)
    # Simpler: just do a line-by-line replacement
    lines = text.split("\n")
    fixed_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.lower().startswith("subgraph") and not stripped.startswith("subgraph"):
            indent = line[:len(line) - len(stripped)]
            line = indent + "subgraph" + stripped[8:]
        fixed_lines.append(line)
    text = "\n".join(fixed_lines)

    # 7. Fix unquoted multi-word subgraph labels
    text = _SUBGRAPH_LABEL_RE.sub(_fix_subgraph_label, text)

    # 8. Strip leading/trailing whitespace
    text = text.strip()

    # 9. Validate it starts with a known Mermaid keyword
    first_line = text.split("\n", 1)[0].strip().lower()
    starts_ok = any(first_line.startswith(kw) for kw in _VALID_STARTS)

    if not starts_ok and text:
        # Try to find a valid start somewhere in the text
        all_lines = text.split("\n")
        for line_idx, line in enumerate(all_lines):
            stripped = line.strip().lower()
            if any(stripped.startswith(kw) for kw in _VALID_STARTS):
                text = "\n".join(all_lines[line_idx:])
                break
        else:
            # If we can't find any valid Mermaid syntax, wrap as flowchart
            text = "flowchart TB\n" + text

    return text


def build_fallback_diagram(
    components: Optional[List[str]] = None,
    data_stores: Optional[List[str]] = None,
    style: Optional[str] = None,
) -> str:
    """Build a simple but valid Mermaid flowchart from canonical architecture
    data.  This guarantees the frontend always has *something* to render."""
    comps = components or []
    stores = data_stores or []

    if not comps and not stores:
        return "flowchart TB\n  User([User]) --> App[Application]"

    lines = ["flowchart TB"]

    # Sanitize node IDs: remove spaces & special chars
    def node_id(name: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]", "", name)

    # Always start with a User node
    lines.append("  User([User])")

    prev_id = "User"
    for comp in comps:
        nid = node_id(comp)
        label = comp.replace('"', "'")
        lines.append(f'  {prev_id} --> {nid}["{label}"]')
        prev_id = nid

    # Connect data stores to the last component
    for store in stores:
        sid = node_id(store)
        label = store.replace('"', "'")
        lines.append(f'  {prev_id} --> {sid}[("{label}")]')

    return "\n".join(lines)
