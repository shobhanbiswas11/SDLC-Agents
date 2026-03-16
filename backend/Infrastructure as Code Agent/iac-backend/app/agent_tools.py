import os
from langchain_core.tools import tool
from app.llm.factory import get_llm
from app.iac_writer import write_iac, read_iac
from app.policy_engine import evaluate_policies

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
    Uses a two-layer approach:
    1. Rule-based policy engine (deterministic regex checks, 40+ rules)
    2. LLM-based semantic analysis (deeper contextual review)
    Returns STATUS: PASS or FAIL with violations and recommendations.
    """
    iac_content = read_iac()

    if not iac_content:
        return "No IaC content found to evaluate."

    # ── Layer 1: Rule-based policy engine (fast, deterministic) ──
    iac_type = detect_iac_type(iac_content, "")
    engine_result = evaluate_policies(iac_content, iac_type)

    # ── Layer 2: LLM-based semantic analysis (deeper insights) ──
    llm = get_llm()
    llm_prompt = f"""You are a pragmatic senior DevOps architect reviewing Infrastructure as Code.
A rule-based policy engine has already checked for pattern-based issues (hardcoded secrets, open CIDRs, missing tags, privileged containers, blocked instance types, etc.).

Your job is to review the code from an architectural and operational perspective.
Be practical — do NOT recommend things just for the sake of recommending. Only flag issues that would genuinely cause problems in a real production environment or significantly improve the infrastructure.

Consider:
- Architectural flaws (single points of failure, missing disaster recovery)
- Incorrect resource configurations (wrong AMI for region, misconfigured networking)
- Missing critical components (no state backend, no logging where it matters)
- Service dependencies that could cause deployment failures
- Obvious cost waste (oversized resources for the workload)
- Networking design issues that would break connectivity

If the code is well-written and production-ready, simply say so. Do not manufacture issues.

IaC Code:
{iac_content}

Respond in this EXACT format:
LLM RECOMMENDATIONS:
- recommendation 1 (or "None — the configuration looks production-ready." if the code is solid)
"""
    llm_analysis = llm.generate(llm_prompt)

    # ── Combine both layers ──
    violations = engine_result["violations"]
    warnings = engine_result["warnings"]
    status = engine_result["status"]

    parts = [f"STATUS: {status}"]

    if violations:
        parts.append("\nVIOLATIONS (Rule Engine):")
        for v in violations:
            parts.append(f"  - {v}")

    if warnings:
        parts.append("\nWARNINGS (Rule Engine):")
        for w in warnings:
            parts.append(f"  - {w}")

    if not violations and not warnings:
        parts.append("\nRule Engine: All checks passed")

    parts.append(f"\n--- LLM Analysis ---\n{llm_analysis}")

    return "\n".join(parts)


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