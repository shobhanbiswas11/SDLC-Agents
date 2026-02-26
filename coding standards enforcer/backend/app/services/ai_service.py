from app.llm.llm_provider import get_llm
from langchain_core.prompts import PromptTemplate

fix_prompt = PromptTemplate.from_template("""
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
""")

def generate_fix(snippet: str, violation_message: str):
    llm = get_llm()

    chain = fix_prompt | llm

    response = chain.invoke({
        "violation": violation_message,
        "code": snippet
    })

    content = response.content

    explanation = content.split("Fixed Code:")[0].replace("Explanation:", "").strip()
    # fixed_code = content.split("Fixed Code:")[-1].strip()

    fixed_code = fixed_code.strip()

    # Remove markdown code fences if present
    if fixed_code.startswith("```"):
        fixed_code = fixed_code.split("```")[1]

    fixed_code = fixed_code.strip()

    return {
        "explanation": explanation,
        "fixed_code": fixed_code
    }