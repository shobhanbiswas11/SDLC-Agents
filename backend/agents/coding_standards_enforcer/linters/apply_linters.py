"""
Apply Python formatters/linters in-place: autoflake → isort → autopep8 → black.

Each tool is called via subprocess; missing tools are silently skipped so a
partial install doesn't break the pipeline.
"""
from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


def _try_run(cmd: List[str]) -> bool:
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return True
    except FileNotFoundError:
        return False
    except Exception as e:
        logger.warning("Linter %s failed: %s", cmd[0], e)
        return False


def run_python_formatters(repo_path: str) -> List[str]:
    """Run the standard Python formatter chain. Returns list of tools that ran."""
    tools_run: List[str] = []

    if _try_run(
        [
            "autoflake",
            "--in-place",
            "--recursive",
            "--remove-all-unused-imports",
            "--remove-unused-variables",
            "--ignore-init-module-imports",
            repo_path,
        ]
    ):
        tools_run.append("autoflake")

    if _try_run(["isort", "--profile", "black", repo_path]):
        tools_run.append("isort")

    if _try_run(["autopep8", "--in-place", "--recursive", "--aggressive", repo_path]):
        tools_run.append("autopep8")

    if _try_run(["black", "--quiet", repo_path]):
        tools_run.append("black")

    return tools_run


def format_python_in_memory(code: str) -> Tuple[str, List[str]]:
    """
    Apply autoflake → isort → autopep8 → black to a string of Python source
    and return the formatted text plus the list of tools that actually ran.

    Errors are swallowed per-tool — if a formatter is missing or fails on a
    snippet, we keep going with the partial result.
    """
    if not code.strip():
        return code, []

    tools: List[str] = []
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "snippet.py"
        path.write_text(code)

        # autoflake — drop unused imports/vars
        try:
            subprocess.run(
                [
                    "autoflake",
                    "--in-place",
                    "--remove-all-unused-imports",
                    "--remove-unused-variables",
                    "--ignore-init-module-imports",
                    str(path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            tools.append("autoflake")
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning("autoflake failed in-memory: %s", e)

        # isort
        try:
            subprocess.run(
                ["isort", "--profile", "black", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            tools.append("isort")
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning("isort failed in-memory: %s", e)

        # autopep8
        try:
            subprocess.run(
                ["autopep8", "--in-place", "--aggressive", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            tools.append("autopep8")
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning("autopep8 failed in-memory: %s", e)

        # black — wins over autopep8 on style
        try:
            subprocess.run(
                ["black", "--quiet", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            tools.append("black")
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning("black failed in-memory: %s", e)

        try:
            return path.read_text(), tools
        except Exception:
            return code, tools
