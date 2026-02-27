import uuid
from fastapi import HTTPException
from app.agent.schemas.spec import Spec
from app.agent.tools.tree import generate_folder_tree
from app.agent.tools.files import generate_file_content
from app.agent.tools.zipper import build_zip
from app.agent.tools.standards import run_standards
from app.core.config import settings
from app.agent.spec_parser import parse_spec_from_text
from app.agent.clarifier import generate_clarification_questions
from app.agent.tools.spec_enricher import apply_rule_based_inference, llm_enrich_spec
from app.agent.tools.spec_validator import detect_missing

def run_generation(text: str = None, spec: Spec = None):

    if not text and not spec:
        raise HTTPException(status_code=400, detail="Empty request.")

    run_id = str(uuid.uuid4())

    if text:
        spec = parse_spec_from_text(text)

    # Step 1: Rule-based inference
    spec = apply_rule_based_inference(spec)

    # Step 2: Optional LLM enrichment
    spec = llm_enrich_spec(spec)

    # Step 3: Detect missing dynamically
    missing = detect_missing(spec)

    if missing:
        questions = generate_clarification_questions(missing)
        return {
            "status": "missing",
            "missing_fields": missing,
            "questions": questions,
            "spec": spec.model_dump(),  # important for frontend continuation
        }



    tree = generate_folder_tree(spec)

    files = {}
    for path in tree:
        files[path] = generate_file_content(path, spec)

    artifact_path = f"{settings.ARTIFACT_DIR}/{run_id}.zip"
    build_zip(files, artifact_path)

    standards = run_standards(artifact_path)

    return {
        "status": "complete",
        "run_id": run_id,
        "artifact_path": artifact_path,
        "standards": standards,
    }