# app/services/ai_service.py

from app.llm.llm_provider import get_llm
from app.llm.prompts import fix_prompt


def clean_markdown(code: str) -> str:
    code = code.strip()

    if code.startswith("```"):
        # Remove opening ```python or ``` line
        lines = code.split("\n")
        lines = lines[1:]  # drop the ``` line
        # Remove trailing ``` if present
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)

    # Also handle if the whole block is wrapped
    if code.startswith("```"):
        parts = code.split("```")
        if len(parts) >= 2:
            code = parts[1]

    return code.strip()


def generate_fix(
    code_snippet: str,
    violation_message: str,
    rule_code: str = "",
    rule_standard: str = "",
):
    try:
        llm = get_llm()

        chain = fix_prompt | llm

        response = chain.invoke(
            {
                "violation": violation_message,
                "rule_code": rule_code,
                "rule_standard": rule_standard,
                "code": code_snippet,
            }
        )

        content = response.content.strip()

        if "Fixed Code:" not in content:
            return {
                "explanation": "AI response malformed.",
                "fixed_code": code_snippet,
            }

        explanation_part = content.split("Fixed Code:")[0]
        fixed_part = content.split("Fixed Code:")[1]

        explanation = explanation_part.replace("Explanation:", "").strip()
        fixed_code = clean_markdown(fixed_part)

        if not fixed_code:
            fixed_code = code_snippet

        return {
            "explanation": explanation,
            "fixed_code": fixed_code,
        }

    except Exception as e:
        return {
            "explanation": f"AI failed: {str(e)}",
            "fixed_code": code_snippet,
        }
