"""
Fix prompts — single-violation (used by the deterministic Python pipeline) and
multi-violation (used by the agent for any language).
"""
from __future__ import annotations

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


fix_all_prompt = PromptTemplate(
    input_variables=["language", "language_context", "code", "violations_summary"],
    template="""You are a senior {language} engineer performing a final, definitive
clean-up. Your output will be checked again by a static analyser, so it MUST
be free of every coding-standard violation — not just the ones listed below.

{language_context}

Violations Currently Detected:
{violations_summary}

Original Code:
```{language}
{code}
```

REQUIREMENTS (read carefully — your output is verified):
1. Fix EVERY violation listed above.
2. Your output must contain ZERO violations of the standards above. Re-read
   your own output before responding and refactor anything that would still
   trigger a warning. This includes things you may not have been asked about
   explicitly: line length, indentation, blank lines between definitions,
   trailing whitespace, missing whitespace around operators, naming
   conventions, unused imports/variables, mutable default arguments, bare
   excepts, magic numbers, missing docstrings on public symbols when the
   language style guide requires them, etc.
3. Do NOT introduce new violations. Examples of what to avoid:
   - Adding `unused_var = 42` style placeholders.
   - Replacing `== None` with `== None` again — use `is None`.
   - Leaving lines longer than the language's recommended limit (Python: 79;
     others: per the relevant style guide).
4. Preserve the original behaviour and logic exactly. Only change style,
   naming, ordering, formatting, and idiomatic patterns. Do not add features
   or remove functionality.
5. Return the COMPLETE fixed file (or full snippet) — never an excerpt.

Respond in exactly this format (no markdown fencing around the code):

Explanation:
A brief summary of every category of change you made.

Fixed Code:
<the complete fixed code, no markdown fencing, ready to drop straight into a file>
""",
)
