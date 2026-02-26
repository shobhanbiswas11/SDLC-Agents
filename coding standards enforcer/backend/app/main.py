from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.services.repo_service import clone_repository
from app.services.scan_service import run_flake8, extract_snippet
from app.services.ai_service import generate_fix
from app.services.diff_service import generate_diff
from app.services.apply_service import apply_fix
from app.services.git_service import (
    create_branch_only,
    commit_changes,
    push_branch,
    create_pull_request
)

app = FastAPI()


# ===============================
# Request Models
# ===============================

class ScanRequest(BaseModel):
    repo_url: str


class ApplyFixRequest(BaseModel):
    repo_path: str
    repo_url: str
    file_path: str
    original_code: str
    suggested_code: str


# ===============================
# Health Check
# ===============================

@app.get("/")
def health():
    return {"status": "Backend running"}


# ===============================
# Scan Endpoint
# ===============================

@app.post("/scan")
def scan_repo(request: ScanRequest):
    try:
        repo_path = clone_repository(request.repo_url)
        violations = run_flake8(repo_path)

        if not violations:
            return {"message": "No violations found 🎉"}

        first_violation = violations[0]

        snippet = extract_snippet(
            first_violation["file_path"],
            first_violation["line_number"]
        )

        ai_result = generate_fix(
            snippet,
            first_violation["message"]
        )

        diff = generate_diff(snippet, ai_result["fixed_code"])

        return {
            "file": first_violation["file_path"],
            "line": first_violation["line_number"],
            "violation": first_violation["message"],
            "original_code": snippet,
            "explanation": ai_result["explanation"],
            "suggested_code": ai_result["fixed_code"],
            "diff": diff
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===============================
# Full Automation Apply Fix
# ===============================

@app.post("/apply-fix")
def apply_fix_endpoint(request: ApplyFixRequest):
    try:
        # 1️⃣ Create new branch first
        branch_name = create_branch_only(request.repo_path)

        # 2️⃣ Apply file modification
        apply_fix(
            file_path=request.file_path,
            original_code=request.original_code,
            suggested_code=request.suggested_code
        )

        # 3️⃣ Commit changes
        commit_changes(
            repo_path=request.repo_path,
            file_path=request.file_path
        )

        # 4️⃣ Push branch
        push_branch(request.repo_path, branch_name)

        # 5️⃣ Create PR
        pr_url = create_pull_request(
            request.repo_url,
            branch_name
        )

        return {
            "message": "Full automation successful 🚀",
            "branch": branch_name,
            "pull_request": pr_url
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))