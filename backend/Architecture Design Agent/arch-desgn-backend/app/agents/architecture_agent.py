from __future__ import annotations

from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents._llm import get_llm
from app.models.schemas import ArchitectureOutput, Requirements

PROMPT_PATH = Path(__file__).parent / "prompts" / "arch_system.md"


def generate_architecture(req: Requirements, assumptions: list[str]) -> ArchitectureOutput:
    system_text = PROMPT_PATH.read_text(encoding="utf-8")

    llm = get_llm(temperature=0.3).with_structured_output(ArchitectureOutput)
    messages = [
        SystemMessage(content=system_text),
        HumanMessage(
            content=(
                "Requirements JSON:\n"
                f"{req.model_dump_json(indent=2)}\n\n"
                "Assumptions:\n"
                f"{assumptions}\n\n"
                "Return ArchitectureOutput JSON now."
            )
        ),
    ]
    return llm.invoke(messages)
