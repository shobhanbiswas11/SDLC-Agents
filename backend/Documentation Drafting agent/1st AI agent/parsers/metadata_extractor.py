# repo_summarizer/metadata_extractor.py
"""
Static metadata extraction for source files.

Extracts structured data (functions, classes, endpoints, schema fields,
env vars, exports, middleware) from each file using AST (Python) and
regex (JS/TS/JSON/.env).  **Zero LLM calls — pure parsing.**

Usage:
    from parsers.metadata_extractor import extract_all_metadata, format_metadata_block
    metadata = extract_all_metadata(file_map)
    prompt_block = format_metadata_block(metadata)
"""

import ast
import re
import json as _json
import pathlib
import posixpath
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional


# ── Skip list ────────────────────────────────────────────────────────────────

_SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".mp4", ".mp3", ".wav", ".ogg",
    ".zip", ".gz", ".tar", ".7z",
    ".pdf", ".docx", ".xlsx",
    ".lock", ".map",
}

_SKIP_FILENAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Pipfile.lock", "poetry.lock", ".DS_Store",
}


def _should_skip(path: str, content: str) -> bool:
    ext = pathlib.Path(path).suffix.lower()
    name = pathlib.Path(path).name.lower()
    if ext in _SKIP_EXTENSIONS or name in _SKIP_FILENAMES:
        return True
    if not content or not content.strip():
        return True
    return False


# ── Empty metadata template ──────────────────────────────────────────────────

def _empty_meta(file_type: str = "unknown") -> Dict[str, Any]:
    return {
        "type": file_type,
        "functions": [],
        "classes": [],
        "exports": [],
        "imports": [],
        "endpoints": [],
        "middleware": [],
        "schema_fields": [],
        "env_vars": [],
        "dependencies": [],
        "scripts": [],
    }


# ══════════════════════════════════════════════════════════════════════════════
# Python — AST-based
# ══════════════════════════════════════════════════════════════════════════════

def _extract_python(path: str, content: str) -> Dict[str, Any]:
    meta = _empty_meta("python")
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return meta

    for node in ast.walk(tree):
        # ── Functions ─────────────────────────────────────────────────
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
            # Check for route decorators (Flask / FastAPI)
            for dec in node.decorator_list:
                dec_str = _decorator_string(dec)
                if dec_str:
                    route_info = _parse_python_route_decorator(dec_str)
                    if route_info:
                        meta["endpoints"].append(route_info)
            meta["functions"].append(name)

        # ── Classes ───────────────────────────────────────────────────
        elif isinstance(node, ast.ClassDef):
            meta["classes"].append(node.name)

        # ── Imports ───────────────────────────────────────────────────
        elif isinstance(node, ast.Import):
            for alias in node.names:
                meta["imports"].append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                meta["imports"].append(node.module.split(".")[0])

    # Deduplicate
    meta["imports"] = sorted(set(meta["imports"]))
    meta["functions"] = list(dict.fromkeys(meta["functions"]))
    meta["classes"] = list(dict.fromkeys(meta["classes"]))

    # ── Exports (module-level __all__) ────────────────────────────────
    all_match = re.search(r'__all__\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if all_match:
        meta["exports"] = re.findall(r'["\'](\w+)["\']', all_match.group(1))

    return meta


def _decorator_string(dec) -> Optional[str]:
    """Try to reconstruct a decorator as a readable string."""
    try:
        if isinstance(dec, ast.Call):
            if isinstance(dec.func, ast.Attribute):
                return f"{dec.func.value.id}.{dec.func.attr}" if hasattr(dec.func.value, 'id') else None
            elif isinstance(dec.func, ast.Name):
                return dec.func.id
        elif isinstance(dec, ast.Attribute):
            return f"{dec.value.id}.{dec.attr}" if hasattr(dec.value, 'id') else None
        elif isinstance(dec, ast.Name):
            return dec.id
    except Exception:
        pass
    return None


def _parse_python_route_decorator(dec_str: str) -> Optional[Dict[str, str]]:
    """Detect Flask/FastAPI-style route decorators like app.get, router.post."""
    methods = {"get", "post", "put", "delete", "patch"}
    parts = dec_str.lower().split(".")
    if len(parts) == 2 and parts[1] in methods:
        return {"method": parts[1].upper(), "decorator": dec_str}
    if dec_str.lower() in ("route", "api_route"):
        return {"method": "ROUTE", "decorator": dec_str}
    return None


# ══════════════════════════════════════════════════════════════════════════════
# JavaScript / TypeScript / JSX / TSX — Regex-based
# ══════════════════════════════════════════════════════════════════════════════

# Express routes: router.get("/path", ...) or app.post("/path", ...)
_JS_ROUTE_RE = re.compile(
    r'(?:router|app|Router)\s*\.\s*(get|post|put|delete|patch|use)\s*\(\s*["\']([^"\']*)["\']',
    re.IGNORECASE,
)

# Functions: function name(...) or const name = (...) => or const name = function
_JS_FUNC_RE = re.compile(
    r'(?:function\s+(\w+)\s*\()|'                           # function foo(
    r'(?:(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[\w]+)\s*=>)|'  # const foo = (...) =>
    r'(?:(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function)',   # const foo = function
)

# Exports: module.exports = { ... } or export { ... } or export default
_JS_EXPORTS_OBJECT_RE = re.compile(r'module\.exports\s*=\s*\{([^}]+)\}')
_JS_EXPORT_NAMED_RE = re.compile(r'export\s+(?:const|let|var|function|class|async\s+function)\s+(\w+)')
_JS_EXPORT_DEFAULT_RE = re.compile(r'export\s+default\s+(?:function\s+)?(\w+)')

# Middleware: app.use(name) or router.use(name)
_JS_MIDDLEWARE_RE = re.compile(
    r'(?:app|router|Router)\s*\.\s*use\s*\(\s*(\w+)',
)

# Mongoose schema: field: { type: String } or field: String
_MONGOOSE_FIELD_RE = re.compile(
    r'(\w+)\s*:\s*(?:\{\s*type\s*:\s*(Schema\.Types\.\w+|\w+)|'  # field: { type: String }
    r'(String|Number|Boolean|Date|ObjectId|Buffer|Mixed|Map|Schema\.Types\.\w+))',  # field: String
)

# React component: function ComponentName or const ComponentName = 
_REACT_COMPONENT_RE = re.compile(
    r'(?:function\s+([A-Z]\w+)\s*\()|'
    r'(?:(?:const|let)\s+([A-Z]\w+)\s*=\s*(?:\([^)]*\)|[\w]+)\s*=>)'
)

# Import: import X from 'Y' or require('Y')
_JS_IMPORT_RE = re.compile(
    r'(?:import\s+.*?\s+from\s+["\']([^"\']+)["\'])|(?:require\s*\(\s*["\']([^"\']+)["\'])',
    re.DOTALL,
)


def _extract_javascript(path: str, content: str) -> Dict[str, Any]:
    meta = _empty_meta("javascript")

    # ── Endpoints ─────────────────────────────────────────────────────
    for m in _JS_ROUTE_RE.finditer(content):
        method = m.group(1).upper()
        route = m.group(2)
        meta["endpoints"].append({"method": method, "path": route})

    # ── Functions ─────────────────────────────────────────────────────
    for m in _JS_FUNC_RE.finditer(content):
        name = m.group(1) or m.group(2) or m.group(3)
        if name:
            meta["functions"].append(name)

    # ── React components (PascalCase functions returning JSX) ─────────
    for m in _REACT_COMPONENT_RE.finditer(content):
        comp = m.group(1) or m.group(2)
        if comp and comp not in meta["functions"]:
            meta["functions"].append(comp)

    # ── Exports ───────────────────────────────────────────────────────
    obj_match = _JS_EXPORTS_OBJECT_RE.search(content)
    if obj_match:
        exports = re.findall(r'(\w+)', obj_match.group(1))
        meta["exports"].extend(exports)
    for m in _JS_EXPORT_NAMED_RE.finditer(content):
        meta["exports"].append(m.group(1))
    default_m = _JS_EXPORT_DEFAULT_RE.search(content)
    if default_m:
        meta["exports"].append(default_m.group(1))

    # ── Middleware ─────────────────────────────────────────────────────
    for m in _JS_MIDDLEWARE_RE.finditer(content):
        mw = m.group(1)
        if mw not in ("function", "async", "require"):
            meta["middleware"].append(mw)

    # Also detect inline middleware in route definitions
    for line in content.splitlines():
        inline_mw = re.findall(
            r'(?:router|app)\.\w+\([^,]+,\s*(\w+)(?:\s*,|\s*\))',
            line,
        )
        for mw in inline_mw:
            if mw not in meta["middleware"] and mw[0].islower():
                meta["middleware"].append(mw)

    # ── Schema fields (Mongoose) ──────────────────────────────────────
    for m in _MONGOOSE_FIELD_RE.finditer(content):
        field_name = m.group(1)
        field_type = m.group(2) or m.group(3)
        if field_name not in ("type", "ref", "default", "required", "unique", "enum"):
            meta["schema_fields"].append(f"{field_name}({field_type})")

    # ── Imports ───────────────────────────────────────────────────────
    for m in _JS_IMPORT_RE.finditer(content):
        mod = m.group(1) or m.group(2)
        if mod:
            # Simplify: just keep the package/module name
            mod_name = mod.split("/")[0].lstrip("@.")
            if mod_name and mod_name not in ("", "."):
                meta["imports"].append(mod_name)

    # Deduplicate
    meta["functions"] = list(dict.fromkeys(meta["functions"]))
    meta["exports"] = list(dict.fromkeys(meta["exports"]))
    meta["middleware"] = list(dict.fromkeys(meta["middleware"]))
    meta["schema_fields"] = list(dict.fromkeys(meta["schema_fields"]))
    meta["imports"] = sorted(set(meta["imports"]))

    return meta


# ══════════════════════════════════════════════════════════════════════════════
# .env / .env.example
# ══════════════════════════════════════════════════════════════════════════════

_ENV_VAR_RE = re.compile(r'^([A-Z][A-Z0-9_]+)\s*=', re.MULTILINE)


def _extract_env(path: str, content: str) -> Dict[str, Any]:
    meta = _empty_meta("env")
    meta["env_vars"] = _ENV_VAR_RE.findall(content)
    return meta


# ══════════════════════════════════════════════════════════════════════════════
# package.json
# ══════════════════════════════════════════════════════════════════════════════

def _extract_package_json(path: str, content: str) -> Dict[str, Any]:
    meta = _empty_meta("package.json")
    try:
        data = _json.loads(content)
    except Exception:
        return meta

    # dependencies + devDependencies
    for dep_key in ("dependencies", "devDependencies"):
        deps = data.get(dep_key, {})
        if isinstance(deps, dict):
            meta["dependencies"].extend(sorted(deps.keys()))

    # scripts
    scripts = data.get("scripts", {})
    if isinstance(scripts, dict):
        meta["scripts"] = [f"{k}: {v}" for k, v in scripts.items()]

    return meta


# ══════════════════════════════════════════════════════════════════════════════
# Generic JSON config (e.g. tsconfig.json, .eslintrc.json)
# ══════════════════════════════════════════════════════════════════════════════

def _extract_json_config(path: str, content: str) -> Dict[str, Any]:
    meta = _empty_meta("json_config")
    try:
        data = _json.loads(content)
        if isinstance(data, dict):
            meta["exports"] = list(data.keys())[:15]  # just top-level keys
    except Exception:
        pass
    return meta


# ══════════════════════════════════════════════════════════════════════════════
# Markdown — extract headings
# ══════════════════════════════════════════════════════════════════════════════

def _extract_markdown(path: str, content: str) -> Dict[str, Any]:
    meta = _empty_meta("markdown")
    headings = re.findall(r'^#{1,3}\s+(.+)', content, re.MULTILINE)
    meta["exports"] = headings[:10]  # store first 10 headings as "exports" for visibility
    return meta


# ══════════════════════════════════════════════════════════════════════════════
# requirements.txt / Pipfile
# ══════════════════════════════════════════════════════════════════════════════

def _extract_requirements(path: str, content: str) -> Dict[str, Any]:
    meta = _empty_meta("requirements")
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            pkg = re.split(r'[>=<!\[\];]', line)[0].strip()
            if pkg:
                meta["dependencies"].append(pkg)
    return meta


# ══════════════════════════════════════════════════════════════════════════════
# Java — Regex-based
# ══════════════════════════════════════════════════════════════════════════════

# Spring/JAX-RS route annotations
_JAVA_ROUTE_RE = re.compile(
    r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)\s*(?:\([^)]*value\s*=\s*["\']([^"\']*)["\']|\(["\']([^"\']*)["\']|\()?',
    re.IGNORECASE,
)
# Public methods
_JAVA_METHOD_RE = re.compile(
    r'(?:public|protected|private|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)\s*(?:throws[^{]*)?\{',
)
# Classes and interfaces
_JAVA_CLASS_RE = re.compile(
    r'(?:public|protected|private)?\s*(?:abstract|final)?\s*(?:class|interface|enum)\s+(\w+)',
)
# Import statements
_JAVA_IMPORT_RE = re.compile(r'^import\s+(?:static\s+)?([\w.]+);', re.MULTILINE)


def _extract_java(path: str, content: str) -> Dict[str, Any]:
    meta = _empty_meta("java")

    for m in _JAVA_ROUTE_RE.finditer(content):
        method_map = {
            "GetMapping": "GET", "PostMapping": "POST", "PutMapping": "PUT",
            "DeleteMapping": "DELETE", "PatchMapping": "PATCH", "RequestMapping": "ROUTE",
        }
        http_method = method_map.get(m.group(1), "ROUTE")
        route_path = m.group(2) or m.group(3) or "/"
        meta["endpoints"].append({"method": http_method, "path": route_path})

    for m in _JAVA_METHOD_RE.finditer(content):
        name = m.group(1)
        if name not in ("if", "for", "while", "switch", "catch", "class"):
            meta["functions"].append(name)

    for m in _JAVA_CLASS_RE.finditer(content):
        meta["classes"].append(m.group(1))

    for m in _JAVA_IMPORT_RE.finditer(content):
        pkg = m.group(1).split(".")[0]
        if pkg:
            meta["imports"].append(pkg)

    meta["functions"] = list(dict.fromkeys(meta["functions"]))
    meta["classes"]   = list(dict.fromkeys(meta["classes"]))
    meta["imports"]   = sorted(set(meta["imports"]))
    return meta


# ══════════════════════════════════════════════════════════════════════════════
# Go — Regex-based
# ══════════════════════════════════════════════════════════════════════════════

_GO_FUNC_RE   = re.compile(r'^func\s+(?:\(\w+\s+[\*]?\w+\)\s+)?(\w+)\s*\(', re.MULTILINE)
_GO_STRUCT_RE = re.compile(r'^type\s+(\w+)\s+struct', re.MULTILINE)
_GO_ROUTE_RE  = re.compile(
    r'(?:mux|router|r|http)\s*\.(?:Handle(?:Func)?|GET|POST|PUT|DELETE|PATCH)\s*\(\s*["\']([^"\']*)["\']',
    re.IGNORECASE,
)
_GO_IMPORT_RE = re.compile(r'"([\w./]+)"')


def _extract_go(path: str, content: str) -> Dict[str, Any]:
    meta = _empty_meta("go")

    for m in _GO_FUNC_RE.finditer(content):
        name = m.group(1)
        if name not in ("init", "main") or True:  # include all
            meta["functions"].append(name)

    for m in _GO_STRUCT_RE.finditer(content):
        meta["classes"].append(m.group(1))

    for m in _GO_ROUTE_RE.finditer(content):
        meta["endpoints"].append({"method": "ROUTE", "path": m.group(1)})

    # Only capture stdlib / external imports (short names)
    for m in _GO_IMPORT_RE.finditer(content):
        pkg = m.group(1).split("/")[-1]  # last segment, e.g. "net/http" -> "http"
        if pkg and len(pkg) < 30:
            meta["imports"].append(pkg)

    meta["functions"] = list(dict.fromkeys(meta["functions"]))
    meta["classes"]   = list(dict.fromkeys(meta["classes"]))
    meta["imports"]   = sorted(set(meta["imports"]))
    return meta


# ══════════════════════════════════════════════════════════════════════════════
# Rust — Regex-based
# ══════════════════════════════════════════════════════════════════════════════

_RUST_FN_RE     = re.compile(r'^(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*[(<]', re.MULTILINE)
_RUST_STRUCT_RE = re.compile(r'^(?:pub\s+)?struct\s+(\w+)', re.MULTILINE)
_RUST_ENUM_RE   = re.compile(r'^(?:pub\s+)?enum\s+(\w+)', re.MULTILINE)
_RUST_IMPL_RE   = re.compile(r'^impl(?:<[^>]*>)?\s+(?:[\w:]+\s+for\s+)?(\w+)', re.MULTILINE)
_RUST_USE_RE    = re.compile(r'^use\s+([\w:]+)', re.MULTILINE)
# Actix-web / Axum route macros
_RUST_ROUTE_RE  = re.compile(r'#\[(?:get|post|put|delete|patch)\(["\']([^"\']+)["\']\)\]', re.IGNORECASE)


def _extract_rust(path: str, content: str) -> Dict[str, Any]:
    meta = _empty_meta("rust")

    for m in _RUST_FN_RE.finditer(content):
        meta["functions"].append(m.group(1))

    for m in _RUST_STRUCT_RE.finditer(content):
        meta["classes"].append(m.group(1))

    for m in _RUST_ENUM_RE.finditer(content):
        meta["classes"].append(m.group(1))

    for m in _RUST_IMPL_RE.finditer(content):
        # impl blocks show what types are implemented
        meta["exports"].append(m.group(1))

    for m in _RUST_ROUTE_RE.finditer(content):
        # detect HTTP method from macro name
        line_start = content.rfind("#[", 0, m.start())
        method_m = re.search(r'#\[(\w+)\(', content[m.start()-20:m.start()+5])
        http_method = method_m.group(1).upper() if method_m else "ROUTE"
        meta["endpoints"].append({"method": http_method, "path": m.group(1)})

    for m in _RUST_USE_RE.finditer(content):
        crate = m.group(1).split("::")[0]
        if crate:
            meta["imports"].append(crate)

    meta["functions"] = list(dict.fromkeys(meta["functions"]))
    meta["classes"]   = list(dict.fromkeys(meta["classes"]))
    meta["exports"]   = list(dict.fromkeys(meta["exports"]))
    meta["imports"]   = sorted(set(meta["imports"]))
    return meta


# ══════════════════════════════════════════════════════════════════════════════
# C# — Regex-based
# ══════════════════════════════════════════════════════════════════════════════

_CS_CLASS_RE  = re.compile(r'(?:public|internal|private|protected)?\s*(?:abstract|sealed)?\s*class\s+(\w+)')
_CS_METHOD_RE = re.compile(
    r'(?:public|private|protected|internal|static|override|virtual|async|\s)+[\w<>\[\]?]+\s+(\w+)\s*\([^)]*\)'
)
_CS_ROUTE_RE  = re.compile(
    r'\[(?:Http(?:Get|Post|Put|Delete|Patch)|Route)(?:\(["\']([^"\']*)["\']\))?\]',
    re.IGNORECASE,
)
_CS_USING_RE  = re.compile(r'^using\s+(?:static\s+)?([\w.]+);', re.MULTILINE)


def _extract_csharp(path: str, content: str) -> Dict[str, Any]:
    meta = _empty_meta("csharp")

    for m in _CS_CLASS_RE.finditer(content):
        meta["classes"].append(m.group(1))

    for m in _CS_METHOD_RE.finditer(content):
        name = m.group(1)
        if name not in ("if", "for", "while", "switch", "catch", "new", "return", "class"):
            meta["functions"].append(name)

    for m in _CS_ROUTE_RE.finditer(content):
        route_path = m.group(1) or "/"
        method_m = re.search(r'Http(Get|Post|Put|Delete|Patch)', m.group(0), re.IGNORECASE)
        http_method = method_m.group(1).upper() if method_m else "ROUTE"
        meta["endpoints"].append({"method": http_method, "path": route_path})

    for m in _CS_USING_RE.finditer(content):
        ns = m.group(1).split(".")[0]
        if ns:
            meta["imports"].append(ns)

    meta["functions"] = list(dict.fromkeys(meta["functions"]))
    meta["classes"]   = list(dict.fromkeys(meta["classes"]))
    meta["imports"]   = sorted(set(meta["imports"]))
    return meta


# ══════════════════════════════════════════════════════════════════════════════
# Router — determine which extractor to use
# ══════════════════════════════════════════════════════════════════════════════

def _extract_one(path: str, content: str) -> Dict[str, Any]:
    """Pick the right extractor based on file extension / name."""
    name = pathlib.Path(path).name.lower()
    ext = pathlib.Path(path).suffix.lower()

    # .env files
    if name.startswith(".env") or name == "env" or name.endswith(".env"):
        return _extract_env(path, content)

    # package.json
    if name == "package.json":
        return _extract_package_json(path, content)

    # Python
    if ext == ".py":
        return _extract_python(path, content)

    # JavaScript / TypeScript
    if ext in (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"):
        return _extract_javascript(path, content)

    # Markdown
    if ext == ".md":
        return _extract_markdown(path, content)

    # requirements.txt
    if name in ("requirements.txt", "requirements-dev.txt"):
        return _extract_requirements(path, content)

    # Java
    if ext == ".java":
        return _extract_java(path, content)

    # Go
    if ext == ".go":
        return _extract_go(path, content)

    # Rust
    if ext == ".rs":
        return _extract_rust(path, content)

    # C#
    if ext == ".cs":
        return _extract_csharp(path, content)

    # Generic JSON configs
    if ext == ".json":
        return _extract_json_config(path, content)

    # Unknown — return empty
    return _empty_meta("other")


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

def extract_all_metadata(
    file_map: Dict[str, str],
    verbose: bool = True,
    max_workers: int = 8,
) -> Dict[str, Dict[str, Any]]:
    """
    Extract structured metadata from every file in file_map.

    Returns {path: metadata_dict} for each non-skipped file.
    No LLM calls — pure static parsing. Runs in parallel using
    ThreadPoolExecutor for faster processing of large repos.
    """
    # Pre-filter to skip binary/empty files
    to_process = [
        (path, content)
        for path, content in file_map.items()
        if not _should_skip(path, content)
    ]
    skipped = len(file_map) - len(to_process)

    results: Dict[str, Dict[str, Any]] = {}

    def _extract_item(item):
        path, content = item
        return path, _extract_one(path, content)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_extract_item, item): item[0] for item in to_process}
        for future in as_completed(futures):
            path, meta = future.result()
            results[path] = meta

    if verbose:
        print(f"[metadata_extractor] {len(results)} files extracted, {skipped} skipped (parallel, {max_workers} workers).")
    return results


def _format_single(path: str, meta: Dict[str, Any]) -> str:
    """Format one file's metadata as a compact text line."""
    parts = [path + ":"]

    if meta.get("endpoints"):
        eps = ", ".join(
            f"{e['method']} {e.get('path', e.get('decorator', ''))}"
            for e in meta["endpoints"]
        )
        parts.append(f"  endpoints: [{eps}]")

    if meta.get("functions"):
        parts.append(f"  functions: [{', '.join(meta['functions'][:15])}]")

    if meta.get("classes"):
        parts.append(f"  classes: [{', '.join(meta['classes'][:10])}]")

    if meta.get("exports"):
        parts.append(f"  exports: [{', '.join(str(e) for e in meta['exports'][:10])}]")

    if meta.get("schema_fields"):
        parts.append(f"  schema: [{', '.join(meta['schema_fields'][:15])}]")

    if meta.get("env_vars"):
        parts.append(f"  env_vars: [{', '.join(meta['env_vars'][:20])}]")

    if meta.get("middleware"):
        parts.append(f"  middleware: [{', '.join(meta['middleware'][:10])}]")

    if meta.get("dependencies"):
        parts.append(f"  dependencies: [{', '.join(meta['dependencies'][:20])}]")

    if meta.get("scripts"):
        parts.append(f"  scripts: [{', '.join(meta['scripts'][:10])}]")

    if meta.get("imports"):
        parts.append(f"  imports: [{', '.join(meta['imports'][:15])}]")

    return "\n".join(parts)


def format_metadata_block(all_metadata: Dict[str, Dict[str, Any]]) -> str:
    """
    Format all file metadata into a compact text block for the LLM prompt.

    Returns a string like:
        routes/pdf.js:
          endpoints: [POST /api/pdf/upload, DELETE /api/pdf/:id]
          functions: [uploadPdf, deletePdf]
          imports: [PdfController, express]
        models/User.js:
          schema: [email(String), password(String)]
        .env.example:
          env_vars: [PORT, MONGO_URI, JWT_SECRET]
    """
    blocks = []
    for path in sorted(all_metadata.keys()):
        meta = all_metadata[path]
        # Only include files that have SOME useful metadata
        has_data = any(
            meta.get(k) for k in
            ("functions", "classes", "exports", "endpoints",
             "schema_fields", "env_vars", "middleware",
             "dependencies", "scripts")
        )
        if has_data:
            blocks.append(_format_single(path, meta))
    return "\n\n".join(blocks)
