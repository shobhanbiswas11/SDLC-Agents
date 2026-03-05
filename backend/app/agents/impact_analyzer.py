from __future__ import annotations

from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents._llm import get_llm
from app.models.schemas import ImpactAnalysis, Requirements

PROMPT_PATH = Path(__file__).parent / "prompts" / "impact_system.md"


def analyze_impact(prev_req: Requirements, new_req: Requirements, prev_arch_summary: str = "") -> ImpactAnalysis:
    system_text = PROMPT_PATH.read_text(encoding="utf-8")

    llm = get_llm(temperature=0.1).with_structured_output(ImpactAnalysis)
    messages = [
        SystemMessage(content=system_text),
        HumanMessage(
            content=(
                "Previous requirements JSON:\n"
                f"{prev_req.model_dump_json(indent=2)}\n\n"
                "Updated requirements JSON:\n"
                f"{new_req.model_dump_json(indent=2)}\n\n"
                "Previous architecture summary (optional):\n"
                f"{prev_arch_summary}\n\n"
                "Return ImpactAnalysis JSON now."
            )
        ),
    ]
    return llm.invoke(messages)
