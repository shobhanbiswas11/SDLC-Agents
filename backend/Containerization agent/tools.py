"""
tools.py — All tool handler functions for the Docker AI Agent.
Pure business logic — no UI, no console output (except podman_build streaming).
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import socket
import subprocess
import time
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

console = Console()

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", "venv", ".venv",
    "dist", "build", ".next", "target", ".gradle", ".mypy_cache",
}
CONTAINER_RUNTIME = os.getenv("CONTAINER_RUNTIME", "docker")


def _rt() -> str:
    return CONTAINER_RUNTIME


def _resolve(file_path: str, workspace: str) -> Path | None:
    """Find a file by exact path or by bare filename search within workspace."""
    ws     = Path(workspace)
    direct = Path(file_path) if Path(file_path).is_absolute() else ws / file_path
    if direct.exists():
        return direct
    bare = Path(file_path).name
    for match in ws.rglob(bare):
        if match.is_file():
            return match
    return None


def _strip_fences(text: str) -> str:
    text = re.sub(r"^```[a-zA-Z]*\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n```$",          "", text, flags=re.MULTILINE)
    return text.strip("` \n")


# ---------------------------------------------------------------------------
# Internal LLM helper (single-turn)
# ---------------------------------------------------------------------------

async def _llm(system: str, user: str, max_tokens: int = 4096) -> str:
    from agent import get_client
    client     = get_client()
    deployment = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    try:
        resp = await client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            temperature=0.2,
            max_completion_tokens=max_tokens,
            timeout=90,
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:
        return f"[LLM Error: {exc}]"


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def handle_read_file(file_path: str, workspace_path: str = ".", **_) -> dict:
    path = _resolve(file_path, workspace_path)
    if path is None:
        return {"status": "error", "error": f"File not found: '{file_path}'"}
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        return {"status": "success", "file_path": str(path), "content": content}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


async def handle_write_file(file_path: str, content: str, workspace_path: str = ".", **_) -> dict:
    path = Path(file_path) if Path(file_path).is_absolute() else Path(workspace_path) / file_path
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        created = not path.exists()
        path.write_text(content, encoding="utf-8")
        verb = "Created" if created else "Updated"
        return {"status": "success", "file_path": str(path), "message": f"{verb}: {path.name}"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


async def handle_list_files(directory: str = ".", workspace_path: str = ".", **_) -> dict:
    ws   = Path(workspace_path)
    base = ws / directory if directory != "." else ws
    if not base.exists():
        return {"status": "error", "error": f"Directory not found: {base}"}
    files: list[str] = []
    for f in sorted(base.rglob("*")):
        if any(part in SKIP_DIRS for part in f.parts):
            continue
        if f.is_file():
            try:
                files.append(str(f.relative_to(ws)))
            except ValueError:
                files.append(str(f))
        if len(files) >= 400:
            break
    return {"status": "success", "files": files, "count": len(files)}


async def handle_ask_user(question: str, **_) -> dict:
    # Handled inline by the agent loop; this stub is a safety fallback.
    return {"status": "ask_user", "question": question}


async def handle_analyze_project(
    file_listing: str,
    key_files_content: str = "",
    workspace_path: str = ".",
    **_,
) -> dict:
    system = (
        "You are a DevOps expert. Analyze the project file listing and key file contents. "
        "Return ONLY a valid JSON object with exactly these keys:\n"
        '{"language","framework","port","entry_point","dependency_file",'
        '"needs_db","needs_redis","build_cmd","start_cmd","notes"}'
    )
    user   = f"File listing:\n{file_listing}\n\nKey files content:\n{key_files_content or '(not provided)'}"
    raw    = await _llm(system, user, max_tokens=1024)
    try:
        analysis = json.loads(_strip_fences(raw))
        return {"status": "success", "analysis": analysis, "raw": raw}
    except Exception:
        return {"status": "success", "analysis": {}, "raw": raw, "warning": "Could not parse JSON"}


async def handle_generate_dockerfile(analysis: str, workspace_path: str = ".", **_) -> dict:
    system = (
        "You are a Docker expert. Generate a Dockerfile and .dockerignore.\n"
        "Return exactly two sections separated by '---DOCKERIGNORE---':\n"
        "[Dockerfile content]\n---DOCKERIGNORE---\n[.dockerignore content]\n"
        "Use Alpine base images. Use multi-stage builds if suitable."
    )
    raw = await _llm(system, f"Project analysis:\n{analysis}", max_tokens=2048)
    if "---DOCKERIGNORE---" in raw:
        df_content, di_content = [p.strip() for p in raw.split("---DOCKERIGNORE---", 1)]
    else:
        df_content = raw.strip()
        di_content = "node_modules\n.git\n__pycache__\n*.pyc\nvenv\n.env\n"
    ws = Path(workspace_path)
    (ws / "Dockerfile").write_text(_strip_fences(df_content), encoding="utf-8")
    (ws / ".dockerignore").write_text(di_content, encoding="utf-8")
    return {"status": "success", "message": "Dockerfile and .dockerignore written to workspace."}


async def handle_generate_compose(analysis: str, workspace_path: str = ".", **_) -> dict:
    system = (
        "You are a Docker Compose expert. Generate a production-ready docker-compose.yml. "
        "Return ONLY raw valid YAML — no markdown fences, no explanation."
    )
    raw     = _strip_fences(await _llm(system, f"Project analysis:\n{analysis}", max_tokens=1024))
    dest    = Path(workspace_path) / "docker-compose.yml"
    dest.write_text(raw, encoding="utf-8")
    return {"status": "success", "message": "docker-compose.yml written to workspace."}


async def handle_podman_build(image_name: str, workspace_path: str = ".", **_) -> dict:
    cmd = [_rt(), "build", "-t", image_name, "."]
    ws  = Path(workspace_path).resolve()

    console.print(f"\n[bold blue]🔨  Building:[/] [cyan]{image_name}[/]  [dim]({' '.join(cmd)})[/]\n")

    log_lines: list[str] = []
    t0 = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=str(ws),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        async for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").rstrip()
            log_lines.append(line)
            ll = line.lower()
            if "error" in ll or "failed" in ll:
                console.print(f"  [red]{line}[/]")
            elif line.startswith("Step") or "--->" in line or "FROM " in line.upper():
                console.print(f"  [cyan]{line}[/]")
            else:
                console.print(f"  [dim]{line}[/]")
        await proc.wait()
    except Exception as exc:
        return {"status": "error", "error": f"Build subprocess error: {exc}"}

    elapsed  = time.monotonic() - t0
    full_log = "\n".join(log_lines)

    if proc.returncode == 0:
        console.print(f"\n  [bold green]✅  Build succeeded in {elapsed:.1f}s[/]\n")
        return {
            "status":     "success",
            "image_name": image_name,
            "exit_code":  0,
            "log":        full_log[-5000:],
            "message":    f"Successfully built {image_name} in {elapsed:.1f}s",
        }
    else:
        console.print(f"\n  [bold red]❌  Build FAILED (exit {proc.returncode})[/]\n")
        return {
            "status":     "error",
            "image_name": image_name,
            "exit_code":  proc.returncode,
            "log":        full_log[-5000:],
            "error":      "Build failed — see log for details.",
        }


async def handle_podman_run(
    image_name: str,
    ports: str = "",
    detach: bool = True,
    workspace_path: str = ".",
    **_,
) -> dict:
    cmd = [_rt(), "run"]
    if detach:
        cmd.append("-d")
    if ports:
        cmd += ["-p", ports]
    container_name = re.sub(r"[:/]", "-", image_name)
    cmd += ["--name", container_name, image_name]
    try:
        res = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True, timeout=30)
        if res.returncode == 0:
            return {"status": "success", "container_id": res.stdout.strip()[:12], "name": container_name, "message": "Container started."}
        return {"status": "error", "error": (res.stderr or res.stdout).strip()[-1000:]}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


async def handle_podman_logs(container_id: str, tail: str = "100", workspace_path: str = ".", **_) -> dict:
    try:
        res = await asyncio.to_thread(
            subprocess.run,
            [_rt(), "logs", "--tail", str(tail), container_id],
            capture_output=True, text=True, timeout=30,
        )
        logs = ((res.stdout or "") + (res.stderr or "")).strip()
        return {"status": "success", "logs": logs[-4000:]}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


async def handle_podman_stop(container_id: str, workspace_path: str = ".", **_) -> dict:
    try:
        await asyncio.to_thread(subprocess.run, [_rt(), "stop", container_id], capture_output=True, timeout=15)
        await asyncio.to_thread(subprocess.run, [_rt(), "rm",   container_id], capture_output=True, timeout=15)
        return {"status": "success", "message": f"Container '{container_id}' stopped and removed."}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


async def handle_repair_file(file_path: str, error_log: str, workspace_path: str = ".", **_) -> dict:
    path = _resolve(file_path, workspace_path)
    if not path:
        return {"status": "error", "error": f"File not found: {file_path}"}
    original = path.read_text(encoding="utf-8", errors="replace")
    system   = (
        "You are a DevOps engineer. Fix the file below based on the error log. "
        "Return ONLY the corrected file content — no explanations, no markdown fences."
    )
    user     = f"=== File: {path.name} ===\n{original}\n\n=== Error log ===\n{error_log[-3000:]}"
    fixed    = _strip_fences(await _llm(system, user, max_tokens=4096))
    if not fixed.strip():
        return {"status": "error", "error": "LLM returned empty fix."}
    path.write_text(fixed, encoding="utf-8")
    return {"status": "success", "message": f"Repaired {path.name}"}


async def handle_repair_build(
    file_path: str,
    error_log: str,
    image_name: str,
    workspace_path: str = ".",
    **_,
) -> dict:
    """Atomic: repair a file, then immediately retry podman_build."""
    repair = await handle_repair_file(file_path, error_log, workspace_path)
    if repair["status"] != "success":
        return repair
    build = await handle_podman_build(image_name, workspace_path)
    return {
        **build,
        "repair_message": repair["message"],
    }


async def handle_optimize_image(current_image_name: str = "", workspace_path: str = ".", **_) -> dict:
    df_path = Path(workspace_path) / "Dockerfile"
    if not df_path.exists():
        return {"status": "error", "error": "Dockerfile not found in workspace."}
    original  = df_path.read_text(encoding="utf-8")
    system    = (
        "You are a Docker optimization expert. Rewrite the Dockerfile to use multi-stage builds "
        "and Alpine base images to minimise final image size. "
        "Return ONLY the optimised Dockerfile content — no fences, no explanation."
    )
    optimized = _strip_fences(await _llm(system, f"Current Dockerfile:\n{original}", max_tokens=2048))
    df_path.write_text(optimized, encoding="utf-8")
    return {"status": "success", "message": "Dockerfile optimised (multi-stage + Alpine)."}


async def handle_health_check(port: int, timeout: int = 30, workspace_path: str = ".", **_) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("localhost", int(port)), timeout=1):
                return {"status": "success", "message": f"App is responding on port {port}."}
        except OSError:
            await asyncio.sleep(2)
    return {"status": "error", "error": f"Timed out after {timeout}s waiting for port {port}."}


async def handle_terminal_command(
    command: str,
    explanation: str = "",
    workspace_path: str = ".",
    **_,
) -> dict:
    ws = Path(workspace_path).resolve()
    if explanation:
        console.print(f"  [dim]$ {command}  # {explanation}[/]")
    try:
        t0     = time.monotonic()
        result = await asyncio.to_thread(
            subprocess.run, command, shell=True, cwd=str(ws),
            capture_output=True, text=True, timeout=120,
        )
        elapsed = int((time.monotonic() - t0) * 1000)
        return {
            "status":      "success",
            "command":     command,
            "return_code": result.returncode,
            "stdout":      (result.stdout or "").strip()[-4000:],
            "stderr":      (result.stderr or "").strip()[-2000:],
            "elapsed_ms":  elapsed,
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# Handler dispatch map
# ---------------------------------------------------------------------------

TOOL_HANDLERS: dict[str, object] = {
    "read_file":          handle_read_file,
    "write_file":         handle_write_file,
    "list_files":         handle_list_files,
    "ask_user":           handle_ask_user,
    "analyze_project":    handle_analyze_project,
    "generate_dockerfile": handle_generate_dockerfile,
    "generate_compose":   handle_generate_compose,
    "podman_build":       handle_podman_build,
    "podman_run":         handle_podman_run,
    "podman_logs":        handle_podman_logs,
    "podman_stop":        handle_podman_stop,
    "repair_file":        handle_repair_file,
    "repair_build":       handle_repair_build,
    "optimize_image":     handle_optimize_image,
    "health_check":       handle_health_check,
    "terminal_command":   handle_terminal_command,
}
