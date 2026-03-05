from app.models.schemas import ArchitectureOutput, CanonicalArchitecture, Requirements
from app.services.delta_service import compute_delta


def test_delta_added_component():
    base_req = Requirements(domain="test")

    prev = ArchitectureOutput(
        requirements=base_req,
        assumptions=[],
        architecture_options=[],
        tradeoffs={},
        recommended={},
        diagram={"type": "mermaid", "content": "flowchart TB
A-->B"},
        implementation_plan={},
        canonical=CanonicalArchitecture(components=["API", "DB"], key_decisions=["Use Postgres"]),
        delta=None,
    )

    new = ArchitectureOutput(
        requirements=base_req,
        assumptions=[],
        architecture_options=[],
        tradeoffs={},
        recommended={},
        diagram={"type": "mermaid", "content": "flowchart TB
A-->B
B-->C"},
        implementation_plan={},
        canonical=CanonicalArchitecture(components=["API", "DB", "Cache"], key_decisions=["Use Postgres", "Add Redis"]),
        delta=None,
    )

    d = compute_delta(prev, new, 1, 2)
    assert "Cache" in d.new_components_added
