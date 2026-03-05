from __future__ import annotations

from typing import List

from app.models.schemas import ArchitectureOutput, DeltaView


def _set(xs: List[str]) -> set[str]:
    return set([x.strip() for x in xs if x and x.strip()])


def compute_delta(prev_arch: ArchitectureOutput, new_arch: ArchitectureOutput, version_from: int, version_to: int) -> DeltaView:
    prev = prev_arch.canonical
    curr = new_arch.canonical

    prev_components = _set(prev.components)
    curr_components = _set(curr.components)

    added = sorted(curr_components - prev_components)
    removed = sorted(prev_components - curr_components)
    unchanged = sorted(curr_components & prev_components)

    prev_decisions = _set(prev.key_decisions)
    curr_decisions = _set(curr.key_decisions)
    decisions_changed = sorted((curr_decisions - prev_decisions) | (prev_decisions - curr_decisions))

    what_changed = []
    if added:
        what_changed.append(f"Added components: {', '.join(added)}")
    if removed:
        what_changed.append(f"Removed components: {', '.join(removed)}")
    if decisions_changed:
        what_changed.append(f"Updated decisions: {', '.join(decisions_changed)}")

    diagram_changes = []
    if prev_arch.diagram.get("content") != new_arch.diagram.get("content"):
        diagram_changes.append("Diagram updated to reflect new components/flows.")

    migration_steps = []
    for c in added:
        migration_steps.append(f"Introduce {c} behind a feature flag; deploy and validate.")
    if removed:
        migration_steps.append("Deprecate removed components gradually; migrate traffic/data; then remove.")

    return DeltaView(
        version_from=version_from,
        version_to=version_to,
        what_changed=what_changed,
        new_components_added=added,
        components_removed=removed,
        unchanged_components=unchanged,
        decisions_changed=decisions_changed,
        diagram_changes=diagram_changes,
        migration_steps=migration_steps,
        risk_notes=[],
    )
