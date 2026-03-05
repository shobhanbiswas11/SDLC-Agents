from __future__ import annotations

from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents._llm import get_llm
from app.models.schemas import ArchitectureOutput, Requirements

PROMPT_PATH = Path(__file__).parent / "prompts" / "arch_patch_system.md"


def patch_architecture(prev_arch: ArchitectureOutput, req: Requirements, assumptions: list[str], impact_reasons: list[str]) -> ArchitectureOutput:
    system_text = PROMPT_PATH.read_text(encoding="utf-8")

    llm = get_llm(temperature=0.2).with_structured_output(ArchitectureOutput)
    messages = [
        SystemMessage(content=system_text),
        HumanMessage(
            content=(
                "Previous ArchitectureOutput JSON:\n"
                f"{prev_arch.model_dump_json(indent=2)}\n\n"
                "Updated Requirements JSON:\n"
                f"{req.model_dump_json(indent=2)}\n\n"
                "Assumptions:\n"
                f"{assumptions}\n\n"
                "Impact reasons:\n"
                f"{impact_reasons}\n\n"
                "Return updated ArchitectureOutput JSON now."
            )
        ),
    ]
    return llm.invoke(messages)
