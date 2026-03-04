import os
from langchain.tools import tool
from app.llm.factory import get_llm
from app.iac_writer import write_iac, read_iac

@tool
def generate_iac(prompt: str) -> str:
    """
    Generate Infrastructure as Code from a natural language prompt.
    Automatically determines the best IaC tool (Terraform, Kubernetes, Ansible, Docker Compose).
    """
    llm = get_llm()

    system_prompt = """You are a DevOps expert. Generate the appropriate Infrastructure as Code.
- Use Terraform for cloud infrastructure (AWS, GCP, Azure)
- Use Kubernetes YAML for container orchestration
- Use Ansible for configuration management
- Use Docker Compose for local multi-container setups
- Follow security best practices (no public access by default, least privilege)
- Never hardcode secrets or credentials
- Add comments explaining key decisions
Respond with ONLY the raw IaC code. No markdown fences. No explanation."""

    code = llm.generate(f"{system_prompt}\n\nRequest: {prompt}")
    iac_type = detect_iac_type(code, prompt)
    filepath = write_iac(code, iac_type)

    # Return with markdown code block formatting
    return f"Generated {iac_type} configuration at {filepath}.\n\n```{iac_type}\n{code}\n```"


@tool
def check_policies(_: str = "") -> str:
    """
    Evaluate the generated IaC against security and compliance policies.
    Returns STATUS: PASS or FAIL with violations and recommendations.
    """
    llm = get_llm()
    iac_content = read_iac()

    if not iac_content:
        return "No IaC content found to evaluate."

    policy_prompt = f"""You are a DevOps security auditor. Review this Infrastructure as Code and check for policy violations.

Check for:
1. Public access / open ports to 0.0.0.0/0
2. Overly permissive IAM roles or permissions
3. Unencrypted storage or databases
4. Missing resource tags
5. Hardcoded secrets or credentials
6. Oversized instance types (m5.xlarge and above without justification)
7. Missing health checks or readiness probes (Kubernetes)
8. Running containers as root
9. Missing resource limits/requests (Kubernetes)
10. Any other security or compliance concerns

IaC Code:
{iac_content}

Respond in this EXACT format:
STATUS: PASS or FAIL
VIOLATIONS:
- violation 1 (or "None" if no violations)
RECOMMENDATIONS:
- recommendation 1
"""

    return llm.generate(policy_prompt)


@tool
def fix_iac(violations: str) -> str:
    """
    Regenerate the IaC fixing all policy violations.
    Pass the violations and recommendations from check_policies as input.
    """
    llm = get_llm()
    original_code = read_iac()

    if not original_code:
        return "No IaC content found to fix."

    fix_prompt = f"""You are a DevOps expert. Fix the following Infrastructure as Code by addressing all violations and recommendations.

Original IaC:
{original_code}

Violations and Recommendations to fix:
{violations}

Rules:
- Fix ALL violations listed above
- Keep the same overall infrastructure intent
- Follow security best practices
- No public access by default
- Enable encryption where applicable
- Add proper tags
- No hardcoded secrets
Respond with ONLY the fixed raw IaC code. No markdown fences. No explanation."""

    fixed_code = llm.generate(fix_prompt)
    iac_type = detect_iac_type(fixed_code, "")
    filepath = write_iac(fixed_code, iac_type)

    # Return with markdown code block formatting
    return f"Fixed IaC written to {filepath}.\n\n```{iac_type}\n{fixed_code}\n```"


def detect_iac_type(code: str, prompt: str) -> str:
    code_lower = code.lower()
    prompt_lower = prompt.lower()

    if "apiversion" in code_lower or "kind:" in code_lower or "kubernetes" in prompt_lower or "k8s" in prompt_lower:
        return "kubernetes"
    elif "docker-compose" in code_lower or ("services:" in code_lower and "docker" in prompt_lower):
        return "docker-compose"
    elif "- name:" in code_lower and ("hosts:" in code_lower or "ansible" in prompt_lower):
        return "ansible"
    else:
        return "terraform"