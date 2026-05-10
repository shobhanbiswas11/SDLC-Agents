"""
Chat-style intent parser for the Build Agent.

Takes a natural language message from the user and extracts:
  - intent: "build", "status", "help", "general"
  - github_url (if present)
  - project_path (if present)
  - branch (if mentioned)

Uses regex first (fast), falls back to LLM if ambiguous.
"""

import re
from typing import Optional
from pydantic import BaseModel


class ChatIntent(BaseModel):
    intent: str  # "build", "status", "help", "general"
    github_url: Optional[str] = None
    project_path: Optional[str] = None
    branch: str = "main"
    reply: str = ""  # conversational reply to show immediately


# ── Regex patterns ────────────────────────────────────────
GITHUB_URL_RE = re.compile(
    r"https?://(?:www\.)?github\.com/[\w.\-]+/[\w.\-]+(?:/(?:tree|blob)/[\w.\-/]*)?"
)
LOCAL_PATH_RE = re.compile(r"(?:^|[\s])(/[\w.\-/]+)")
BRANCH_RE = re.compile(r"\bbranch[:\s]+(\S+)", re.IGNORECASE)


def parse_chat_message(message: str) -> ChatIntent:
    """Parse a natural language message into a structured intent."""
    text = message.strip()
    lower = text.lower()

    # ── Help ──────────────────────────────────────────
    if lower in ("help", "hi", "hello", "hey", "?"):
        return ChatIntent(
            intent="help",
            reply=(
                "Hi! I'm your Build Agent. Here's what I can do:\n\n"
                "- **Build from GitHub:** Just paste a GitHub URL, e.g. `https://github.com/user/repo`\n"
                "- **Build from local path:** Give me a path, e.g. `/Users/you/projects/my-app`\n"
                "- **Check status:** Ask `what's the status?` or `how's the build going?`\n\n"
                "I support Node.js, Python, Go, and Java projects. Just tell me what you need!"
            ),
        )

    # ── Status check ──────────────────────────────────
    status_keywords = ["status", "how's", "going", "progress", "what happened", "last build"]
    if any(kw in lower for kw in status_keywords):
        return ChatIntent(
            intent="status",
            reply="Let me check on the latest build status for you...",
        )

    # ── Build intent: extract GitHub URL ──────────────
    github_match = GITHUB_URL_RE.search(text)
    if github_match:
        url = github_match.group(0)
        # Clean URL: remove /tree/branch suffix if present, extract branch
        branch = "main"
        tree_match = re.search(r"/tree/([\w.\-/]+)", url)
        if tree_match:
            branch = tree_match.group(1).split("/")[0]
            url = url[:url.index("/tree/")]

        # Check for explicit branch mention
        branch_match = BRANCH_RE.search(text)
        if branch_match:
            branch = branch_match.group(1)

        return ChatIntent(
            intent="build",
            github_url=url,
            branch=branch,
            reply=f"Got it! I'll clone **{url}** (branch: `{branch}`) and run the build. Let me get started...",
        )

    # ── Build intent: extract local path ──────────────
    path_match = LOCAL_PATH_RE.search(text)
    if path_match:
        path = path_match.group(1)
        return ChatIntent(
            intent="build",
            project_path=path,
            reply=f"I'll build the project at `{path}`. Starting now...",
        )

    # ── Build intent: keywords without URL ────────────
    build_keywords = ["build", "fix", "run", "compile", "deploy", "test"]
    if any(kw in lower for kw in build_keywords):
        return ChatIntent(
            intent="general",
            reply=(
                "I'd love to help! Could you give me a GitHub URL or a local project path?\n\n"
                "For example:\n"
                "- `https://github.com/your-name/your-repo`\n"
                "- `/path/to/your/project`"
            ),
        )

    # ── Fallback: treat as general chat ───────────────
    return ChatIntent(
        intent="general",
        reply=(
            "I'm your Build Agent — I can run builds, diagnose failures, and suggest fixes.\n\n"
            "Just paste a GitHub URL or a local path, and I'll take it from there!"
        ),
    )
