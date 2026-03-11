# app/llm/prompts.py
from langchain_core.prompts import PromptTemplate

fix_prompt = PromptTemplate(
    input_variables=["violation", "rule_code", "rule_standard", "code"],
    template="""You are a senior Python engineer. Your task is to fix exactly one coding standard violation in the given code snippet.

Violation Details:
- Rule: {rule_code} ({rule_standard})
- Message: {violation}

Code Snippet:
{code}

Instructions:
- Fix ONLY the specific violation described above.
- Do NOT refactor, rename variables, reorder imports, or alter any unrelated code.
- Preserve all original logic, comments, and formatting on unaffected lines.
- Return the complete corrected snippet, not just the changed line(s).

Respond in exactly this format:

Explanation:
A 1-2 sentence explanation of why this violates {rule_standard} and what was changed to fix it.

Fixed Code:
The full corrected code snippet with no markdown fencing, no backticks, and no extra commentary.
""",
)