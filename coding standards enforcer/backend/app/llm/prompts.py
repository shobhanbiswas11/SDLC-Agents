from langchain_core.prompts import PromptTemplate

fix_prompt = PromptTemplate(
    input_variables=["violation", "code"],
    template="""
You are a senior Python engineer enforcing strict PEP8 and clean code standards.

Violation:
{violation}

Code:
{code}

Respond strictly in this format:

Explanation:
<short explanation>

Fixed Code:
<corrected code only>
"""
)