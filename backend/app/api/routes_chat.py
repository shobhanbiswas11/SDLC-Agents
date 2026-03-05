from __future__ import annotations

import logging
import traceback
from copy import deepcopy
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.agents.architecture_agent import generate_architecture
from app.agents.architecture_patch_agent import patch_architecture
from app.agents.impact_analyzer import analyze_impact
from app.agents.requirements_patch_agent import patch_requirements
from app.models.schemas import ChatRequest, ChatResponse, ChangeEntry, ClarifyingQuestion
from app.services.delta_service import compute_delta
from app.services.mermaid_sanitizer import sanitize_mermaid, build_fallback_diagram
from app.services.session_service import session_store

logger = logging.getLogger(__name__)
router = APIRouter()


def _sanitize_arch_diagram(arch):
    """Post-process architecture diagram to guarantee valid Mermaid output."""
    try:
        raw = arch.diagram.get("content", "") if isinstance(arch.diagram, dict) else ""
    except Exception:
        raw = ""

    cleaned = sanitize_mermaid(raw)

    if not cleaned.strip():
        # Last-resort fallback: build diagram from canonical components
        try:
            cleaned = build_fallback_diagram(
                components=arch.canonical.components if arch.canonical else None,
                data_stores=arch.canonical.data_stores if arch.canonical else None,
                style=arch.canonical.style if arch.canonical else None,
            )
        except Exception:
            cleaned = "flowchart TB\n  User([User]) --> App[Application]"

    arch.diagram = {"type": "mermaid", "content": cleaned}
    return arch


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        return _handle_chat(req)
    except Exception as e:
        logger.error("Unhandled error in /chat: %s\n%s", e, traceback.format_exc())
        # Return a graceful error response instead of 500
        session_id = req.session_id or "error"
        return JSONResponse(
            status_code=200,
            content={
                "session_id": session_id,
                "stage": "intake",
                "intake": {
                    "status": "need_more_info",
                    "extracted": {},
                    "missing_critical": [],
                    "questions": [
                        {
                            "key": "error_retry",
                            "question": f"Something went wrong internally ({type(e).__name__}). Could you rephrase or simplify your input?",
                            "reason": str(e)[:200],
                            "options": [],
                        }
                    ],
                    "assumptions": [],
                    "fields_changed": [],
                },
                "impact": None,
                "architecture": None,
            },
        )


def _handle_chat(req: ChatRequest):
    session_id, state = session_store.get_or_create(req.session_id)

    prev_req = deepcopy(state.requirements)
    prev_arch = deepcopy(state.last_architecture)

    # 1) Patch requirements
    intake = patch_requirements(req.message, state.requirements)
    state.requirements = intake.extracted

    # Versioning and change log
    meta = state.requirements.meta
    meta.version += 1
    meta.last_updated = datetime.utcnow()
    meta.change_log.append(
        ChangeEntry(
            version=meta.version,
            timestamp=meta.last_updated,
            user_message=req.message,
            summary=intake.change_summary or "Updated requirements",
            fields_changed=intake.fields_changed,
        )
    )

    # merge assumptions
    state.assumptions = list(dict.fromkeys(state.assumptions + intake.assumptions))

    # keep history
    state.requirements_history.append(prev_req)

    # 2) Iterative intake: ensure we never proceed with missing critical fields
    #    Case A: LLM says need_more_info but gives no questions → inject fallback
    #    Case B: LLM says ready but critical fields are still empty → override
    fallback_qs = _fill_missing_questions(state.requirements)

    if intake.status == "need_more_info" and not intake.questions:
        if fallback_qs:
            intake.questions = fallback_qs
            logger.info("Injected %d fallback questions (LLM gave none)", len(fallback_qs))
        else:
            logger.info("No missing fields — treating as ready")
            intake.status = "ready"

    if intake.status == "ready" and fallback_qs:
        # LLM said ready but critical fields are still empty — keep asking
        intake.status = "need_more_info"
        intake.questions = fallback_qs
        logger.info("Overriding premature 'ready' — %d critical fields still missing", len(fallback_qs))

    if intake.status == "need_more_info":
        state.stage = "intake"
        session_store.update(session_id, state)
        return ChatResponse(
            session_id=session_id,
            stage="intake",
            intake=intake,
            impact=None,
            architecture=state.last_architecture,
        )

    # 3) If no architecture yet: generate
    if state.last_architecture is None:
        arch = generate_architecture(state.requirements, state.assumptions)
        arch = _sanitize_arch_diagram(arch)
        state.last_architecture = arch
        state.last_arch_summary = _arch_summary(arch)
        state.stage = "architecture"
        session_store.update(session_id, state)
        return ChatResponse(session_id=session_id, stage="architecture", intake=intake, impact=None, architecture=arch)

    # 4) Impact analysis
    impact = analyze_impact(prev_req, state.requirements, state.last_arch_summary)

    # Map policy: Patch on LOW + MEDIUM, regenerate on HIGH
    if impact.impact in ["low", "medium"]:
        new_arch = patch_architecture(state.last_architecture, state.requirements, state.assumptions, impact.reasons)
        new_arch = _sanitize_arch_diagram(new_arch)

        # Ensure delta exists (fallback if model omitted)
        if new_arch.delta is None and prev_arch is not None:
            new_arch.delta = compute_delta(prev_arch, new_arch, version_from=prev_req.meta.version, version_to=state.requirements.meta.version)

        state.last_architecture = new_arch
        state.last_arch_summary = _arch_summary(new_arch)
        state.stage = "architecture"
        session_store.update(session_id, state)
        return ChatResponse(session_id=session_id, stage="architecture", intake=intake, impact=impact, architecture=new_arch)

    if impact.impact == "high":
        new_arch = generate_architecture(state.requirements, state.assumptions)
        new_arch = _sanitize_arch_diagram(new_arch)
        if new_arch.delta is None and prev_arch is not None:
            new_arch.delta = compute_delta(prev_arch, new_arch, version_from=prev_req.meta.version, version_to=state.requirements.meta.version)

        state.last_architecture = new_arch
        state.last_arch_summary = _arch_summary(new_arch)
        state.stage = "architecture"
        session_store.update(session_id, state)
        return ChatResponse(session_id=session_id, stage="architecture", intake=intake, impact=impact, architecture=new_arch)

    # impact == none
    state.stage = "architecture"
    session_store.update(session_id, state)
    return ChatResponse(session_id=session_id, stage="architecture", intake=intake, impact=impact, architecture=state.last_architecture)


def _arch_summary(arch) -> str:
    try:
        rec = arch.recommended
        name = rec.get("name", "")
        rationale = rec.get("rationale", [])
        if isinstance(rationale, list):
            rationale = " ".join(rationale)
        return f"{name} {rationale}".strip()
    except Exception:
        return ""


def _fill_missing_questions(req) -> list:
    """Inspect requirements and generate interactive questions for unfilled critical fields.

    Returns a list of ClarifyingQuestion objects with pre-built options,
    limited to 3 at a time so the UI isn't overwhelming.
    """
    questions = []

    # Cloud preference
    if not req.preferences.cloud:
        questions.append(ClarifyingQuestion(
            key="preferences.cloud",
            question="Which cloud provider do you prefer?",
            reason="Determines available services, pricing, and deployment strategies",
            options=["AWS", "Azure", "GCP", "No preference"],
        ))

    # Expected scale
    if not req.users_and_scale.expected_users:
        questions.append(ClarifyingQuestion(
            key="users_and_scale.expected_users",
            question="How many users do you expect?",
            reason="Affects architecture decisions like database choice, caching, and load balancing",
            options=["< 1K users", "1K–10K users", "10K–100K users", "100K+ users"],
        ))

    # Deployment model
    if not req.preferences.deployment:
        questions.append(ClarifyingQuestion(
            key="preferences.deployment",
            question="What deployment model do you prefer?",
            reason="Impacts infrastructure cost, scaling behavior, and operational complexity",
            options=["Containers (Docker/K8s)", "Serverless", "VMs", "No preference"],
        ))

    # Budget
    if not req.constraints.budget:
        questions.append(ClarifyingQuestion(
            key="constraints.budget",
            question="What is your budget level?",
            reason="Determines whether to use managed services vs self-hosted, and scaling strategy",
            options=["Low", "Medium", "High"],
        ))

    # Timeline
    if not req.constraints.timeline:
        questions.append(ClarifyingQuestion(
            key="constraints.timeline",
            question="What is your timeline for the first release?",
            reason="Affects build-vs-buy decisions and MVP scope",
            options=["< 1 month", "1–3 months", "3–6 months", "6+ months"],
        ))

    # Team size
    if req.constraints.team_size is None:
        questions.append(ClarifyingQuestion(
            key="constraints.team_size",
            question="How large is your development team?",
            reason="Impacts architecture complexity — smaller teams need simpler systems",
            options=["1–2 developers", "3–5 developers", "6–10 developers", "10+ developers"],
        ))

    # Compliance / security
    if not req.nfrs.security and not req.nfrs.compliance:
        questions.append(ClarifyingQuestion(
            key="nfrs.compliance",
            question="Any compliance or security requirements?",
            reason="Affects data storage, encryption, and audit logging decisions",
            options=["GDPR", "HIPAA", "SOC2", "PCI-DSS", "None"],
        ))

    # Database preference
    if not req.preferences.database:
        questions.append(ClarifyingQuestion(
            key="preferences.database",
            question="Do you have a database preference?",
            reason="Core architectural decision that affects data modeling and querying",
            options=["PostgreSQL", "MongoDB", "MySQL", "DynamoDB", "No preference"],
        ))

    # Return at most 3 at a time to keep the UI clean
    return questions[:3]

