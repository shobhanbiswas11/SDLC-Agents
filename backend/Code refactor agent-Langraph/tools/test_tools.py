"""
tools/test_tools.py — Testing and terminal execution tool handlers.

Handlers:
  handle_run_tests        — run a test suite or fall back to a syntax check
  handle_terminal_command — execute an arbitrary shell command in the workspace
"""

from __future__ import annotations

import asyncio
import os
import shlex
import shutil
import subprocess
from pathlib import Path

from core.logging import get_logger

logger = get_logger(__name__)

_TEST_TIMEOUT = 120  # seconds
_DEFAULT_COMMAND_ALLOWLIST = {
    "python",
    "python3",
    "pytest",
    "node",
    "npm",
    "npx",
    "yarn",
    "pnpm",
    "git",
}


def _split_command(command: str) -> list[str]:
    """Split a command string without invoking a shell."""
    return shlex.split(command, posix=os.name != "nt")


def _allowed_executable(argv: list[str]) -> bool:
    """Return True if the executable is allowlisted."""
    if not argv:
        return False
    configured = os.getenv("TERMINAL_COMMAND_ALLOWLIST", "")
    allowed = {
        item.strip().lower()
        for item in configured.split(",")
        if item.strip()
    } or _DEFAULT_COMMAND_ALLOWLIST
    executable = Path(argv[0]).name.lower()
    if executable.endswith(".exe"):
        executable = executable[:-4]
    return executable in allowed


async def handle_run_tests(
    test_command: str = "pytest",
    test_path: str = "",
    source_file: str = "",
    workspace_path: str = ".",
    **_,
) -> dict:
    """
    Run tests for a refactored file.

    Strategy (in order):
    1. If *test_path* is provided, run ``{test_command} {test_path}``.
    2. Else if *source_file* is provided, search for a conventional test file
       (``test_{stem}.py`` in ``tests/``, next to the source, or in ``sample_code/``).
    3. If no test file found, fall back to a syntax check (``python -m py_compile``
       for ``.py``; ``node --check`` for ``.js``).
    4. If no syntax checker is configured, return a descriptive warning.
    """
    workspace = Path(workspace_path)
    resolved_source: Path | None = None

    if source_file:
        src = Path(source_file)
        resolved_source = src if src.is_absolute() else workspace / src

    # Auto-discover test file
    if not test_path and resolved_source is not None:
        stem = resolved_source.stem
        candidates = [
            workspace / "tests" / f"test_{stem}.py",
            resolved_source.parent / f"test_{stem}.py",
            workspace / "sample_code" / f"test_{stem}.py",
        ]
        for candidate in candidates:
            if candidate.exists():
                test_path = (
                    str(candidate.relative_to(workspace))
                    if candidate.is_absolute()
                    else str(candidate)
                )
                break

    # Syntax-check fallback
    if not test_path and resolved_source is not None:
        suffix = resolved_source.suffix.lower()
        syntax_cmd: list[str] | None = None
        checker_name = ""

        if suffix == ".py":
            syntax_cmd = ["python", "-m", "py_compile", str(resolved_source)]
            checker_name = "python -m py_compile"
        elif suffix in {".js", ".mjs", ".cjs"}:
            node_path = shutil.which("node")
            if node_path:
                syntax_cmd = [node_path, "--check", str(resolved_source)]
                checker_name = "node --check"

        if syntax_cmd is None:
            return {
                "status": "success",
                "passed": False,
                "return_code": 0,
                "stdout": "",
                "stderr": "",
                "test_path": "",
                "source_file": str(resolved_source),
                "used_syntax_check": False,
                "message": (
                    f"⚠️ No dedicated tests found and no syntax checker is configured "
                    f"for '{suffix or 'unknown'}' files in this environment."
                ),
            }

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                syntax_cmd,
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=_TEST_TIMEOUT,
            )
            passed = result.returncode == 0
            stderr_tail = (result.stderr or "").strip()[-300:]
            return {
                "status": "success",
                "passed": passed,
                "return_code": result.returncode,
                "stdout": (result.stdout or "")[-3000:],
                "stderr": (result.stderr or "")[-1000:],
                "test_path": "",
                "source_file": str(resolved_source),
                "used_syntax_check": True,
                "message": (
                    f"⚠️ No dedicated tests found. Fallback syntax check ({checker_name}) passed."
                    if passed
                    else (
                        f"❌ No dedicated tests found and fallback syntax check ({checker_name}) failed."
                        + (f" Error: {stderr_tail}" if stderr_tail else "")
                    )
                ),
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Syntax check timed out after 120 seconds."}
        except Exception as exc:
            return {"status": "error", "error": f"Failed to run syntax check: {str(exc)}"}

    # Run the actual test command
    try:
        cmd = _split_command(test_command)
    except ValueError as exc:
        return {"status": "error", "error": f"Invalid test command: {exc}"}
    if test_path:
        cmd.append(test_path)
    if not _allowed_executable(cmd):
        return {
            "status": "error",
            "error": f"Test command executable is not allowlisted: {cmd[0] if cmd else ''}",
        }
    logger.info("run_tests: %s", " ".join(cmd))
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=_TEST_TIMEOUT,
        )
        passed = result.returncode == 0
        return {
            "status": "success",
            "passed": passed,
            "return_code": result.returncode,
            "stdout": (result.stdout or "")[-3000:],
            "stderr": (result.stderr or "")[-1000:],
            "test_path": test_path,
            "source_file": str(resolved_source) if resolved_source else "",
            "used_syntax_check": False,
            "message": "✅ All tests passed!" if passed else "❌ Some tests failed.",
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "Test command timed out after 120 seconds."}
    except Exception as exc:
        return {"status": "error", "error": f"Failed to run tests: {str(exc)}"}


async def handle_terminal_command(
    command: str,
    explanation: str = "",
    workspace_path: str = ".",
    **_,
) -> dict:
    """Execute an allowlisted command in the workspace directory."""
    import time as _time

    if os.getenv("ALLOW_TERMINAL_COMMANDS", "").lower() not in {"1", "true", "yes"}:
        return {
            "status": "error",
            "error": (
                "terminal_command is disabled. Set ALLOW_TERMINAL_COMMANDS=true "
                "and TERMINAL_COMMAND_ALLOWLIST to enable selected commands."
            ),
        }

    workspace = Path(workspace_path).resolve()
    try:
        cmd = _split_command(command)
    except ValueError as exc:
        return {"status": "error", "error": f"Invalid command: {exc}"}
    if not _allowed_executable(cmd):
        return {
            "status": "error",
            "error": f"Command executable is not allowlisted: {cmd[0] if cmd else ''}",
        }

    logger.info("terminal_command: %s", " ".join(cmd))

    try:
        t0 = _time.monotonic()
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=_TEST_TIMEOUT,
        )
        elapsed = int((_time.monotonic() - t0) * 1000)
        return {
            "status": "success",
            "command": " ".join(cmd),
            "explanation": explanation,
            "return_code": result.returncode,
            "stdout": (result.stdout or "").strip()[-5000:],
            "stderr": (result.stderr or "").strip()[-2000:],
            "elapsed_ms": elapsed,
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "Command timed out after 120 seconds."}
    except Exception as exc:
        return {"status": "error", "error": f"Failed to execute command: {str(exc)}"}
