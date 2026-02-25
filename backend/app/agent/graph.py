import uuid
from app.agent.schemas.spec import Spec
from app.agent.tools.tree import generate_folder_tree
from app.agent.tools.files import generate_file_content
from app.agent.tools.zipper import build_zip
from app.agent.tools.standards import run_standards
from app.core.config import settings
from app.agent.spec_parser import parse_spec_from_text
from app.agent.clarifier import generate_clarification_questions


def detect_missing(spec: Spec) -> list[str]:
    missing = []

    # Infer language from framework
    if spec.framework and not spec.language:
        if spec.framework.lower() == "fastapi":
            spec.language = "python"

    if not spec.project_name:
        missing.append("project_name")
    if not spec.language:
        missing.append("language")
    if not spec.framework:
        missing.append("framework")

    return missing

def run_generation(text: str = None, spec: Spec = None):
    run_id = str(uuid.uuid4())

    if text:
        spec = parse_spec_from_text(text)

    missing = detect_missing(spec)

    if missing:
        questions = generate_clarification_questions(missing)
        return {
            "status": "missing",
            "missing_fields": missing,
            "questions": questions,
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