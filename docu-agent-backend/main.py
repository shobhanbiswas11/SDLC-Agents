# main.py
import os
import base64
import hashlib
import hmac
import requests
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")

# Import the process function from your pipeline
from process_automated_readme import process_automated_readme
from memory.preferences import load_preferences, save_preferences

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="DocuGenius API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PushReadmeRequest(BaseModel):
    repo: str
    access_token: str
    branch: str = "main"
    commit_message: str = "Update README via DocuGenius"
    local_readme_path: Optional[str] = None


@app.post("/push-readme")
async def push_readme(body: PushReadmeRequest):
    """
    Dynamically generates and pushes a README file to the given GitHub repository.
    """
    token = body.access_token or os.environ.get("YOUR_GITHUB_ACCESS_TOKEN", "")
    if not token:
        raise HTTPException(status_code=400, detail="GitHub access token required")

    try:
        owner, repo_name = body.repo.split("/", 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="repo should be in the format 'owner/repo'")

    try:
        # Generate and push README dynamically
        await process_automated_readme(
            repo_name=body.repo,
            token=token,
            include_all_files=False,
        )
        return {
            "status": "success",
            "message": f"README generated and pushed for {body.repo}",
            "file_url": f"https://github.com/{owner}/{repo_name}/blob/{body.branch}/README.md",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating README: {str(e)}")

        return {
            "status": "success",
            "message": f"README {action} on {body.repo}",
            "file_url": f"https://github.com/{owner}/{repo_name}/blob/{body.branch}/README.md",
        }
    else:
        raise HTTPException(status_code=500, detail=f"GitHub PUT error: {put_resp.status_code} {put_resp.text}")


@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    GitHub webhook endpoint. When a push to main occurs, this triggers
    process_automated_readme in the background (returns quickly to GitHub).
    Validates the X-Hub-Signature-256 header if GITHUB_WEBHOOK_SECRET is set.
    """
    raw_body = await request.body()

    # --- Signature Validation ---
    if GITHUB_WEBHOOK_SECRET:
        sig_header = request.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(
            GITHUB_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig_header, expected):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        import json as _json
        payload = _json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Avoid re-triggering from our own commit message
    commits = payload.get("commits", [])
    if commits and any("Update README via DocuGenius" in c.get("message", "") for c in commits):
        return {"status": "ignored", "reason": "Self-triggered commit"}

    repo_name = payload.get("repository", {}).get("full_name")
    branch_ref = payload.get("ref", "")

    # Only trigger for pushes to the main branch
    if not repo_name or "refs/heads/main" not in branch_ref:
        return {"status": "ignored", "reason": "Not the main branch or missing repository name"}

    token = os.environ.get("YOUR_GITHUB_ACCESS_TOKEN")
    if not token:
        return {"status": "error", "reason": "Missing token in environment"}

    # --- Extract changed files from push payload ---
    changed_files = set()
    for commit in commits:
        changed_files.update(commit.get("added", []))
        changed_files.update(commit.get("modified", []))
        changed_files.update(commit.get("removed", []))

    print(f"[webhook] {len(changed_files)} files changed: {changed_files}")

    # --- Add Preference Check ---
    prefs = load_preferences(repo_name)
    if not prefs.get("auto_generate_on_push", True):
        print(f"[webhook] Skipped: auto_generate_on_push is disabled for {repo_name}")
        return {"status": "ignored", "reason": "auto_generate_on_push is disabled by user preferences"}

    # Kick off background task with changed_files for diff-aware processing
    background_tasks.add_task(
        process_automated_readme,
        repo_name=repo_name,
        token=token,
        include_all_files=False,
        changed_files=changed_files if changed_files else None,
    )

    return {
        "status": "success",
        "message": "Webhook received! Generating docs in background.",
        "changed_files": len(changed_files),
    }


# ── User Preferences Endpoints ────────────────────────────────────────────────

class PreferencesRequest(BaseModel):
    include_sections: list = []
    exclude_sections: list = []
    tone: str = "professional"
    extra_instructions: str = ""
    custom_badges: list = []
    auto_generate_on_push: bool = True


@app.post("/preferences/{owner}/{repo}")
async def set_preferences(owner: str, repo: str, body: PreferencesRequest):
    """Save per-repo preferences for README generation."""
    repo_name = f"{owner}/{repo}"
    path = save_preferences(repo_name, body.model_dump())
    return {
        "status": "success",
        "message": f"Preferences saved for {repo_name}",
        "file": path,
        "preferences": load_preferences(repo_name),
    }


@app.get("/preferences/{owner}/{repo}")
async def get_preferences(owner: str, repo: str):
    """Get current preferences for a repo."""
    repo_name = f"{owner}/{repo}"
    prefs = load_preferences(repo_name)
    return {"repo": repo_name, "preferences": prefs}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)