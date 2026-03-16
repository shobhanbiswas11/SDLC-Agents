from __future__ import annotations

from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents._llm import get_llm
from app.models.schemas import IntakeDecision, Requirements

PROMPT_PATH = Path(__file__).parent / "prompts" / "intake_system.md"


def patch_requirements(user_message: str, current: Requirements) -> IntakeDecision:
    system_text = PROMPT_PATH.read_text(encoding="utf-8")

    llm = get_llm(temperature=0.2).with_structured_output(IntakeDecision)
    messages = [
        SystemMessage(content=system_text),
        HumanMessage(
            content=(
                "Current Requirements JSON:\n"
                f"{current.model_dump_json(indent=2)}\n\n"
                "User message:\n"
                f"{user_message}\n\n"
                "Return IntakeDecision JSON now."
            )
        ),
    ]
    return llm.invoke(messages)
