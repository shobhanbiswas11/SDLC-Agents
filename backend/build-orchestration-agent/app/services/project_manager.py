"""
Project Manager Service
-----------------------
Handles real-world project ingestion:
  - Clone GitHub repositories
  - Detect project type from files
  - Return appropriate build configuration (Docker image + commands)
  - Cleanup temporary project directories
"""

import os
import shutil
import uuid
import subprocess
from typing import Optional

# ─── Supported project types ───────────────────────────────
PROJECT_TYPES = {
    "nodejs": {
        "markers": ["package.json"],
        "image": "node:18",
        "install_command": "npm install",
        "build_command": "npm run build",
        "label": "Node.js",
    },
    "python": {
        "markers": ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"],
        "image": "python:3.11-slim",
        "install_command": "pip install -r requirements.txt",
        "build_command": "python -m py_compile $(find . -name '*.py' -not -path './venv/*')",
        "label": "Python",
    },
    "go": {
        "markers": ["go.mod"],
        "image": "golang:1.22",
        "install_command": "go mod download",
        "build_command": "go build ./...",
        "label": "Go",
    },
    "java_maven": {
        "markers": ["pom.xml"],
        "image": "maven:3.9-eclipse-temurin-21",
        "install_command": "mvn dependency:resolve",
        "build_command": "mvn compile",
        "label": "Java (Maven)",
    },
    "java_gradle": {
        "markers": ["build.gradle", "build.gradle.kts"],
        "image": "gradle:8.5-jdk21",
        "install_command": "gradle dependencies",
        "build_command": "gradle build",
        "label": "Java (Gradle)",
    },
}

WORKSPACE_ROOT = "/tmp/build_agent_workspaces"


# ─── Clone ──────────────────────────────────────────────────
def clone_repo(github_url: str, branch: str = "main") -> dict:
    """
    Clones a public GitHub repo into a temporary workspace.
    Returns {"project_path": str, "workspace_id": str}.
    """
    workspace_id = uuid.uuid4().hex[:12]
    workspace_path = os.path.join(WORKSPACE_ROOT, workspace_id)
    os.makedirs(workspace_path, exist_ok=True)

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", branch, github_url, workspace_path],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.CalledProcessError as e:
        # Try without --branch flag (some repos use 'master')
        try:
            shutil.rmtree(workspace_path, ignore_errors=True)
            os.makedirs(workspace_path, exist_ok=True)

            subprocess.run(
                ["git", "clone", "--depth", "1", github_url, workspace_path],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.CalledProcessError as e2:
            shutil.rmtree(workspace_path, ignore_errors=True)
            raise ValueError(f"Failed to clone repository: {e2.stderr}")

    return {
        "project_path": workspace_path,
        "workspace_id": workspace_id,
    }


# ─── Detect project type ────────────────────────────────────
def detect_project_type(project_path: str) -> Optional[str]:
    """
    Inspects the project directory to determine the project type.
    Returns the project type key (e.g., 'nodejs', 'python') or None.
    """
    if not os.path.isdir(project_path):
        return None

    files_in_root = set(os.listdir(project_path))

    for ptype, config in PROJECT_TYPES.items():
        for marker in config["markers"]:
            if marker in files_in_root:
                return ptype

    return None


# ─── Build config ────────────────────────────────────────────
def get_build_config(project_type: str) -> dict:
    """
    Returns the build configuration for a given project type.
    """
    config = PROJECT_TYPES.get(project_type)

    if not config:
        raise ValueError(f"Unsupported project type: {project_type}")

    return {
        "project_type": project_type,
        "image": config["image"],
        "install_command": config["install_command"],
        "build_command": config["build_command"],
        "label": config["label"],
    }


# ─── Cleanup ────────────────────────────────────────────────
def cleanup(project_path: str):
    """
    Removes the temporary workspace directory.
    """
    if project_path and project_path.startswith(WORKSPACE_ROOT):
        shutil.rmtree(project_path, ignore_errors=True)
