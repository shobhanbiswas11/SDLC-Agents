"""
semantic_safety.py — Policy loading and semantic guard checks for refactoring.

Keeps behavior-sensitive checks out of tools.py so tool handlers stay focused.
"""

import fnmatch
import re
from pathlib import Path

import yaml

_policy_cache: dict[str, dict] = {}


def _default_refactor_policy() -> dict:
    return {
        "semantic_guard": {
            "enabled": False,
            "protect_storage_keys": True,
            "protect_env_keys": True,
            "protect_routes": True,
            "protect_imports": True,
            "protect_export_names": True,
            "protect_response_keys": True,
            "protect_status_codes": True,
            "protected_file_globs": [],
            "protected_string_literals": [],
            "protected_regex_patterns": [],
        }
    }


def _deep_merge_dict(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_refactor_policy(workspace_path: str) -> dict:
    """
    Load optional repository policy from workspace.
    Supported locations (first found wins):
      - <workspace>/refactor-policy.yaml
      - <workspace>/.refactor-policy.yaml
      - <workspace>/config/refactor-policy.yaml
    """
    workspace_abs = str(Path(workspace_path).resolve())
    cached = _policy_cache.get(workspace_abs)
    if cached is not None:
        return cached

    default_policy = _default_refactor_policy()
    candidates = [
        Path(workspace_abs) / "refactor-policy.yaml",
        Path(workspace_abs) / ".refactor-policy.yaml",
        Path(workspace_abs) / "config" / "refactor-policy.yaml",
    ]

    loaded: dict = {}
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            try:
                file_data = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
                if isinstance(file_data, dict):
                    loaded = file_data
            except Exception:
                loaded = {}
            break

    policy = _deep_merge_dict(default_policy, loaded)
    _policy_cache[workspace_abs] = policy
    return policy


def is_path_protected_by_policy(path: Path, workspace_path: str, policy: dict) -> bool:
    guard = (policy or {}).get("semantic_guard", {})
    patterns = guard.get("protected_file_globs", [])
    if not isinstance(patterns, list) or not patterns:
        return False

    try:
        rel_path = str(path.resolve().relative_to(Path(workspace_path).resolve())).replace("\\", "/")
    except Exception:
        rel_path = str(path).replace("\\", "/")

    return any(fnmatch.fnmatch(rel_path, pattern) for pattern in patterns if isinstance(pattern, str) and pattern.strip())


def _extract_storage_keys(code: str) -> set[str]:
    pattern = re.compile(
        r"(?:localStorage|sessionStorage)\.(?:getItem|setItem|removeItem)\(\s*(['\"`])(.+?)\1\s*\)",
        re.DOTALL,
    )
    return {match.group(2) for match in pattern.finditer(code)}


def _extract_env_var_keys(code: str) -> set[str]:
    js_pattern = re.compile(r"process\.env\.([A-Z0-9_]+)")
    py_pattern = re.compile(r"os\.getenv\(\s*(['\"])([A-Z0-9_]+)\1")

    keys = {match.group(1) for match in js_pattern.finditer(code)}
    keys.update(match.group(2) for match in py_pattern.finditer(code))
    return keys


def _parse_js_ast(code: str):
    try:
        import esprima  # type: ignore
        return esprima.parseModule(code, {"tolerant": True, "jsx": True})
    except Exception:
        return None


def _js_node_type(node) -> str:
    if node is None:
        return ""
    if isinstance(node, dict):
        return str(node.get("type", ""))
    return str(getattr(node, "type", ""))


def _js_node_get(node, key: str, default=None):
    if node is None:
        return default
    if isinstance(node, dict):
        return node.get(key, default)
    return getattr(node, key, default)


def _walk_js_ast(node):
    if node is None:
        return
    if isinstance(node, (str, int, float, bool)):
        return

    if isinstance(node, list):
        for item in node:
            yield from _walk_js_ast(item)
        return

    yield node

    if isinstance(node, dict):
        for value in node.values():
            yield from _walk_js_ast(value)
        return

    for value in getattr(node, "__dict__", {}).values():
        yield from _walk_js_ast(value)


def _js_literal_string(node) -> str | None:
    node_type = _js_node_type(node)
    if node_type == "Literal":
        value = _js_node_get(node, "value")
        return value if isinstance(value, str) else None
    return None


def _js_member_chain(node) -> str | None:
    node_type = _js_node_type(node)

    if node_type == "Identifier":
        return _js_node_get(node, "name")

    if node_type == "ThisExpression":
        return "this"

    if node_type == "MemberExpression":
        obj = _js_member_chain(_js_node_get(node, "object"))
        prop_node = _js_node_get(node, "property")
        computed = bool(_js_node_get(node, "computed", False))

        if computed:
            prop = _js_literal_string(prop_node) or _js_member_chain(prop_node)
        else:
            prop = _js_node_get(prop_node, "name") if _js_node_type(prop_node) == "Identifier" else _js_member_chain(prop_node)

        if obj and prop:
            return f"{obj}.{prop}"

    return None


def _js_object_keys(node) -> set[str]:
    keys: set[str] = set()
    if _js_node_type(node) != "ObjectExpression":
        return keys

    for prop in _js_node_get(node, "properties", []) or []:
        if _js_node_type(prop) != "Property":
            continue
        key_node = _js_node_get(prop, "key")
        key_type = _js_node_type(key_node)
        if key_type == "Identifier":
            name = _js_node_get(key_node, "name")
            if isinstance(name, str):
                keys.add(name)
        elif key_type == "Literal":
            value = _js_node_get(key_node, "value")
            if isinstance(value, str):
                keys.add(value)
    return keys


def _extract_route_literals(code: str) -> set[str]:
    routes: set[str] = set()

    ast_root = _parse_js_ast(code)
    if ast_root is not None:
        for node in _walk_js_ast(ast_root):
            n_type = _js_node_type(node)

            if n_type == "CallExpression":
                callee_chain = _js_member_chain(_js_node_get(node, "callee")) or ""
                args = _js_node_get(node, "arguments", []) or []
                if args:
                    first_arg = args[0]
                    first_str = _js_literal_string(first_arg)
                    if isinstance(first_str, str) and first_str.startswith("/"):
                        if any(callee_chain.endswith(suffix) for suffix in (
                            ".push", ".replace", ".navigate", ".get", ".post", ".put", ".patch", ".delete"
                        )):
                            routes.add(first_str)

            if n_type == "JSXAttribute":
                name_node = _js_node_get(node, "name")
                attr_name = _js_node_get(name_node, "name")
                if attr_name in {"href", "to"}:
                    value_node = _js_node_get(node, "value")
                    value_type = _js_node_type(value_node)
                    if value_type == "Literal":
                        literal_value = _js_node_get(value_node, "value")
                        if isinstance(literal_value, str) and literal_value.startswith("/"):
                            routes.add(literal_value)

        if routes:
            return routes

    patterns = [
        re.compile(r"\bhref\s*=\s*(['\"])(/[^'\"\s]*)\1"),
        re.compile(r"\bto\s*=\s*(['\"])(/[^'\"\s]*)\1"),
        re.compile(r"(?:push|replace|navigate|get|post|put|patch|delete)\(\s*(['\"])(/[^'\"\s]*)\1\s*\)"),
    ]
    for pattern in patterns:
        routes.update(match.group(2) for match in pattern.finditer(code))
    return routes


def _extract_import_lines(code: str, file_suffix: str) -> set[str]:
    suffix = file_suffix.lower()
    lines = code.splitlines()

    if suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        return {
            line.strip()
            for line in lines
            if line.strip().startswith("import ") or line.strip().startswith("const ") and "require(" in line
        }

    if suffix == ".py":
        return {
            line.strip()
            for line in lines
            if line.strip().startswith("import ") or line.strip().startswith("from ")
        }

    return set()


def _extract_export_names(code: str, file_suffix: str) -> set[str]:
    suffix = file_suffix.lower()
    names: set[str] = set()

    if suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        ast_root = _parse_js_ast(code)
        if ast_root is not None:
            body = _js_node_get(ast_root, "body", []) or []
            for node in body:
                n_type = _js_node_type(node)
                if n_type == "ExportDefaultDeclaration":
                    names.add("__default_export__")
                elif n_type == "ExportNamedDeclaration":
                    declaration = _js_node_get(node, "declaration")
                    d_type = _js_node_type(declaration)
                    if d_type in {"FunctionDeclaration", "ClassDeclaration"}:
                        id_node = _js_node_get(declaration, "id")
                        name = _js_node_get(id_node, "name")
                        if isinstance(name, str):
                            names.add(name)
                    elif d_type == "VariableDeclaration":
                        for decl in _js_node_get(declaration, "declarations", []) or []:
                            id_node = _js_node_get(decl, "id")
                            name = _js_node_get(id_node, "name")
                            if isinstance(name, str):
                                names.add(name)

                    for spec in _js_node_get(node, "specifiers", []) or []:
                        exported = _js_node_get(spec, "exported")
                        exported_name = _js_node_get(exported, "name")
                        if isinstance(exported_name, str):
                            names.add(exported_name)

            if names:
                return names

        for match in re.finditer(r"export\s*\{([^}]+)\}", code):
            raw_items = match.group(1).split(",")
            for item in raw_items:
                token = item.strip()
                if not token:
                    continue
                if " as " in token:
                    token = token.split(" as ", 1)[1].strip()
                names.add(token)
        for match in re.finditer(r"export\s+(?:const|let|var|function|class)\s+([A-Za-z_$][A-Za-z0-9_$]*)", code):
            names.add(match.group(1))
        if re.search(r"export\s+default\b", code):
            names.add("__default_export__")

    if suffix == ".py":
        for match in re.finditer(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", code, flags=re.MULTILINE):
            names.add(match.group(1))
        for match in re.finditer(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*[:\(]", code, flags=re.MULTILINE):
            names.add(match.group(1))

    return names


def _extract_response_status_codes(code: str) -> set[str]:
    status_codes: set[str] = set()

    ast_root = _parse_js_ast(code)
    if ast_root is not None:
        for node in _walk_js_ast(ast_root):
            if _js_node_type(node) != "CallExpression":
                continue
            callee_chain = _js_member_chain(_js_node_get(node, "callee")) or ""
            if not callee_chain.endswith(".status"):
                continue
            args = _js_node_get(node, "arguments", []) or []
            if not args:
                continue
            first = args[0]
            if _js_node_type(first) == "Literal":
                value = _js_node_get(first, "value")
                if isinstance(value, (int, float)):
                    status_codes.add(str(int(value)))
        if status_codes:
            return status_codes

    status_codes.update(match.group(1) for match in re.finditer(r"res\.status\(\s*(\d{3})\s*\)", code))
    return status_codes


def _extract_response_object_keys(code: str) -> set[str]:
    keys: set[str] = set()

    ast_root = _parse_js_ast(code)
    if ast_root is not None:
        for node in _walk_js_ast(ast_root):
            if _js_node_type(node) != "CallExpression":
                continue

            callee = _js_node_get(node, "callee")
            callee_chain = _js_member_chain(callee) or ""
            if not (callee_chain.endswith(".send") or callee_chain.endswith(".json")):
                continue

            args = _js_node_get(node, "arguments", []) or []
            if not args:
                continue
            keys.update(_js_object_keys(args[0]))

        if keys:
            return keys

    call_patterns = [
        re.compile(r"res\.(?:send|json)\(\s*\{([\s\S]*?)\}\s*\)", re.MULTILINE),
        re.compile(r"res\.status\(\s*\d{3}\s*\)\.(?:send|json)\(\s*\{([\s\S]*?)\}\s*\)", re.MULTILINE),
    ]
    key_patterns = [
        re.compile(r"['\"]([A-Za-z0-9_\-]+)['\"]\s*:\s*"),
        re.compile(r"\b([A-Za-z_$][A-Za-z0-9_$]*)\s*:\s*"),
    ]

    for call_pattern in call_patterns:
        for match in call_pattern.finditer(code):
            body = match.group(1)
            for key_pattern in key_patterns:
                for key_match in key_pattern.finditer(body):
                    keys.add(key_match.group(1))
    return keys


def validate_semantic_safety(original: str, candidate: str, file_suffix: str, policy: dict | None = None) -> dict:
    """
    Guardrail checks that reject refactors likely to alter runtime behavior.
    These checks intentionally prioritize safety over aggressive refactoring.
    """
    guard = (policy or _default_refactor_policy()).get("semantic_guard", {})
    if not guard.get("enabled", True):
        return {"ok": True, "violations": []}

    violations: list[str] = []

    if guard.get("protect_storage_keys", True):
        old_storage = _extract_storage_keys(original)
        new_storage = _extract_storage_keys(candidate)
        removed_storage = sorted(old_storage - new_storage)
        added_storage = sorted(new_storage - old_storage)
        if removed_storage or added_storage:
            violations.append(
                "storage keys changed"
                + (f"; removed={removed_storage}" if removed_storage else "")
                + (f"; added={added_storage}" if added_storage else "")
            )

    if guard.get("protect_env_keys", True):
        old_env = _extract_env_var_keys(original)
        new_env = _extract_env_var_keys(candidate)
        removed_env = sorted(old_env - new_env)
        added_env = sorted(new_env - old_env)
        if removed_env or added_env:
            violations.append(
                "environment variable keys changed"
                + (f"; removed={removed_env}" if removed_env else "")
                + (f"; added={added_env}" if added_env else "")
            )

    if guard.get("protect_routes", True):
        old_routes = _extract_route_literals(original)
        new_routes = _extract_route_literals(candidate)
        removed_routes = sorted(old_routes - new_routes)
        added_routes = sorted(new_routes - old_routes)
        if removed_routes or added_routes:
            violations.append(
                "route literals changed"
                + (f"; removed={removed_routes}" if removed_routes else "")
                + (f"; added={added_routes}" if added_routes else "")
            )

    if guard.get("protect_imports", True):
        old_imports = _extract_import_lines(original, file_suffix)
        new_imports = _extract_import_lines(candidate, file_suffix)
        removed_imports = sorted(old_imports - new_imports)
        if removed_imports:
            violations.append(f"imports removed={removed_imports[:8]}")

    if guard.get("protect_export_names", True):
        old_exports = _extract_export_names(original, file_suffix)
        new_exports = _extract_export_names(candidate, file_suffix)
        removed_exports = sorted(old_exports - new_exports)
        added_exports = sorted(new_exports - old_exports)
        if removed_exports or added_exports:
            violations.append(
                "export names changed"
                + (f"; removed={removed_exports}" if removed_exports else "")
                + (f"; added={added_exports}" if added_exports else "")
            )

    if guard.get("protect_status_codes", True):
        old_status_codes = _extract_response_status_codes(original)
        new_status_codes = _extract_response_status_codes(candidate)
        removed_status_codes = sorted(old_status_codes - new_status_codes)
        added_status_codes = sorted(new_status_codes - old_status_codes)
        if removed_status_codes or added_status_codes:
            violations.append(
                "response status codes changed"
                + (f"; removed={removed_status_codes}" if removed_status_codes else "")
                + (f"; added={added_status_codes}" if added_status_codes else "")
            )

    if guard.get("protect_response_keys", True):
        old_response_keys = _extract_response_object_keys(original)
        new_response_keys = _extract_response_object_keys(candidate)
        removed_response_keys = sorted(old_response_keys - new_response_keys)
        added_response_keys = sorted(new_response_keys - old_response_keys)
        if removed_response_keys or added_response_keys:
            violations.append(
                "response object keys changed"
                + (f"; removed={removed_response_keys[:20]}" if removed_response_keys else "")
                + (f"; added={added_response_keys[:20]}" if added_response_keys else "")
            )

    literals = guard.get("protected_string_literals", [])
    if isinstance(literals, list):
        removed_literals = [lit for lit in literals if isinstance(lit, str) and lit and lit in original and lit not in candidate]
        if removed_literals:
            violations.append(f"protected literals removed={removed_literals[:12]}")

    patterns = guard.get("protected_regex_patterns", [])
    if isinstance(patterns, list):
        pattern_violations = []
        for raw_pattern in patterns:
            if not isinstance(raw_pattern, str) or not raw_pattern.strip():
                continue
            try:
                compiled = re.compile(raw_pattern)
            except re.error:
                continue
            old_count = len(compiled.findall(original))
            new_count = len(compiled.findall(candidate))
            if old_count != new_count:
                pattern_violations.append(f"{raw_pattern} ({old_count}->{new_count})")
        if pattern_violations:
            violations.append(f"protected regex changed={pattern_violations[:8]}")

    return {
        "ok": len(violations) == 0,
        "violations": violations,
    }
