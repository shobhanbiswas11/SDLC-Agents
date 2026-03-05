import os
import uuid

from fastapi import HTTPException
from app.agent.schemas.spec import Spec
from app.agent.spec_parser import parse_spec_from_text
from app.agent.clarifier import generate_clarification_questions
from app.agent.tools.spec_enricher import apply_rule_based_inference, llm_enrich_spec
from app.agent.tools.spec_validator import detect_missing
from app.agent.tools.spec_merger import merge_answers_into_spec
from app.agent.tools.tree_generator import generate_folder_tree
from app.agent.tools.code_generator import generate_all_code
from app.agent.tools.init_generator import generate_init_instructions
from app.agent.tools.validator import validate_generation
from app.agent.tools.zipper import build_zip
from app.core.config import settings


def generate_project(spec: Spec):
    """Multi-stage project generation pipeline."""
    # Stage 1 — Generate folder tree
    print("[Pipeline] Stage 1: Generating folder tree...")
    tree = generate_folder_tree(spec)

    # Stage 2 — Generate code in batches
    print("[Pipeline] Stage 2: Generating code (batched)...")
    files = generate_all_code(spec, tree)

    # Stage 3 — Generate init instructions
    print("[Pipeline] Stage 3: Generating init instructions...")
    instructions = generate_init_instructions(spec, tree)

    # Stage 4 — Validate completeness
    print("[Pipeline] Stage 4: Validating generation...")
    validate_generation(tree, files)

    # Stage 5 — Build ZIP artifact
    run_id = str(uuid.uuid4())
    artifact_dir = settings.ARTIFACT_DIR
    os.makedirs(artifact_dir, exist_ok=True)
    artifact_path = os.path.join(artifact_dir, f"{run_id}.zip")
    build_zip(files, artifact_path)
    print(f"[Pipeline] Stage 5: ZIP saved to {artifact_path}")

    return {
        "status": "complete",
        "run_id": run_id,
        "tree": tree,
        "files": files,
        "init_instructions": instructions,
    }


def run_generation(text: str = None, spec: Spec = None, answers: dict = None):

    if not text and not spec:
        raise HTTPException(status_code=400, detail="Empty request.")

    # PHASE 1 — Initial Text
    if text:
        spec = parse_spec_from_text(text)
        spec = apply_rule_based_inference(spec)
        spec = llm_enrich_spec(spec)

        missing = detect_missing(spec)

        if missing:
            questions = generate_clarification_questions(missing)

            return {
                "status": "missing",
                "missing_fields": missing,
                "questions": questions,
                "spec": spec.model_dump(),
            }

    # PHASE 2 — Clarification Merge
    if spec and answers:
        spec = merge_answers_into_spec(spec, answers)

    # Continue with whatever spec we have
    return generate_project(spec)

