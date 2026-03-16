import json
import re


def extract_json_from_text(text: str) -> dict:
    """
    Robustly extract a JSON object from LLM output text.

    Handles:
    - Clean JSON responses
    - JSON wrapped in markdown code fences (```json ... ```)
    - JSON embedded in surrounding prose
    """
    text = text.strip()

    # Attempt 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt 2: Strip markdown code fences
    fenced = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Attempt 3: Find outermost { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    # Attempt 4: Find outermost [ ... ] (for array responses)
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Failed to extract valid JSON from LLM response. "
        f"Response starts with: {text[:200]!r}"
    )
