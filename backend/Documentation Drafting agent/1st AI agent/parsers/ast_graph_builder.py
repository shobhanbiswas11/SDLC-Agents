import ast
import re
import posixpath
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Set, List, Tuple

# ── Python AST-Based Importer ────────────────────────────────────────────────
def build_python_import_graph(file_map: Dict[str, str], max_workers: int = 6) -> Dict[str, Set[str]]:
    """
    Build a graph: file_path -> set(of file_paths it imports)
    Improved to handle both absolute and relative Python imports.
    Parsing runs in parallel using ThreadPoolExecutor.
    """
    # Prepare lookup: module name (without .py) -> list of possible full file paths
    module_to_paths: Dict[str, List[str]] = defaultdict(list)
    for path in file_map:
        if path.endswith(".py"):
            name = posixpath.basename(path)[:-3]  # Strip off the '.py'
            module_to_paths[name].append(path)

    py_files = [(path, content) for path, content in file_map.items()
                if path.endswith(".py") and content]

    # Parse one file and return its import edges
    def _parse_file(item: Tuple[str, str]):
        path, content = item
        edges: Set[str] = set()
        try:
            tree = ast.parse(content)
        except Exception:
            return path, edges

        current_dir = posixpath.dirname(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    base_module = alias.name.split(".")[0]
                    edges.update(module_to_paths.get(base_module, []))

            elif isinstance(node, ast.ImportFrom):
                if node.level is not None and node.level > 0:
                    target_dir = current_dir
                    for _ in range(node.level - 1):
                        target_dir = posixpath.dirname(target_dir)
                    mod_name = node.module.split(".")[0] if node.module else ""
                    for alias in node.names:
                        target_name = mod_name or alias.name
                        for candidate in module_to_paths.get(target_name, []):
                            if candidate.startswith(target_dir):
                                edges.add(candidate)
                else:
                    if node.module:
                        base_module = node.module.split(".")[0]
                        edges.update(module_to_paths.get(base_module, []))
        return path, edges

    graph: Dict[str, Set[str]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_parse_file, item) for item in py_files]
        for future in as_completed(futures):
            path, edges = future.result()
            if edges:
                graph[path] = edges

    return graph


# ── JS/TS Import Parser ──────────────────────────────────────────────────────
# Added re.DOTALL to handle multiline destructured imports
_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:.*?\s+from\s+)?['"](?P<mod>[^'"]+)['"])|(?:require\(['"](?P<req>[^'"]+)['"]\))""", 
    re.DOTALL
)

def build_js_import_graph(file_map: Dict[str, str], max_workers: int = 6) -> Dict[str, Set[str]]:
    """
    Builds an import graph for JS/TS. Safely normalizes paths using posixpath
    and checks if the target file actually exists in the file_map.
    Scanning runs in parallel using ThreadPoolExecutor.
    """
    valid_extensions = ["", ".js", ".ts", ".jsx", ".tsx", "/index.js", "/index.ts"]
    js_files = [(path, content) for path, content in file_map.items()
                if path.endswith((".js", ".ts", ".jsx", ".tsx")) and content]

    def _scan_file(item: Tuple[str, str]):
        path, content = item
        edges: Set[str] = set()
        base_dir = posixpath.dirname(path)
        for m in _IMPORT_RE.finditer(content):
            mod = m.group("mod") or m.group("req")
            if not mod or not mod.startswith("."):
                continue
            normalized_base = posixpath.normpath(posixpath.join(base_dir, mod))
            for ext in valid_extensions:
                candidate = (normalized_base + ext).lstrip("/")
                if candidate in file_map:
                    edges.add(candidate)
                    break
        return path, edges

    graph: Dict[str, Set[str]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_scan_file, item) for item in js_files]
        for future in as_completed(futures):
            path, edges = future.result()
            if edges:
                graph[path] = edges

    return graph


# ── Generic Heuristic Import Parser (Java, C++, Go, Rust) ────────────────────

def build_heuristic_import_graph(file_map: Dict[str, str], max_workers: int = 6) -> Dict[str, Set[str]]:
    """
    Builds an import graph for other common languages using regex heuristics.
    Supports Java, Kotlin, C/C++, Go, and Rust.
    """
    java_re = re.compile(r"^\s*import\s+(?:static\s+)?([\w\.]+)\s*;?", re.MULTILINE)
    cpp_re = re.compile(r'^\s*#include\s+"([^"]+)"', re.MULTILINE)
    go_single_re = re.compile(r'^\s*import\s+"([^"]+)"', re.MULTILINE)
    go_multi_re = re.compile(r'import\s+\((.*?)\)', re.DOTALL)
    rust_re = re.compile(r'^\s*use\s+([a-zA-Z0-9_:]+)', re.MULTILINE)

    def _scan_file(item: Tuple[str, str]):
        path, content = item
        edges: Set[str] = set()
        base_dir = posixpath.dirname(path)
        
        try:
            if path.endswith((".java", ".kt")):
                for m in java_re.finditer(content):
                    imported_class = m.group(1)
                    relative_path = imported_class.replace(".", "/")
                    for ext in [".java", ".kt"]:
                        for known_path in file_map:
                            if known_path.endswith(f"{relative_path}{ext}"):
                                edges.add(known_path)
                                
            elif path.endswith((".c", ".cpp", ".h", ".hpp")):
                for m in cpp_re.finditer(content):
                    inc_path = m.group(1)
                    normalized = posixpath.normpath(posixpath.join(base_dir, inc_path))
                    if normalized in file_map:
                        edges.add(normalized)
                        
            elif path.endswith(".go"):
                for m in go_single_re.finditer(content):
                    pkg = m.group(1)
                    for known_path in file_map:
                        if posixpath.dirname(known_path).endswith(pkg) and known_path.endswith(".go"):
                            edges.add(known_path)
                for m in go_multi_re.finditer(content):
                    inner = m.group(1)
                    for inc_re in re.finditer(r'"([^"]+)"', inner):
                        pkg = inc_re.group(1)
                        for known_path in file_map:
                            if posixpath.dirname(known_path).endswith(pkg) and known_path.endswith(".go"):
                                edges.add(known_path)
                                
            elif path.endswith(".rs"):
                for m in rust_re.finditer(content):
                    module_path = m.group(1).replace("::", "/")
                    if module_path.startswith("crate/"):
                        module_path = module_path[6:]
                    elif module_path.startswith("super/"):
                        module_path = module_path[6:]
                    for known_path in file_map:
                        if known_path.endswith(f"{module_path}.rs") or known_path.endswith(f"{module_path}/mod.rs"):
                            edges.add(known_path)
        except Exception:
            pass # Ignore parsing errors
                        
        return path, edges

    target_files = [(p, c) for p, c in file_map.items()
                    if p.endswith((".java", ".kt", ".c", ".cpp", ".h", ".hpp", ".go", ".rs")) and c]

    graph: Dict[str, Set[str]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_scan_file, item) for item in target_files]
        for future in as_completed(futures):
            path, edges = future.result()
            if edges:
                graph[path] = edges

    return graph


# ── Combined Graph Builder ───────────────────────────────────────────────────
def build_combined_graph(file_map: Dict[str, str]) -> Dict[str, Set[str]]:
    """Return combined graph (Python + JS/TS + Heuristic fallback)."""
    combined_graph = defaultdict(set)
    
    py_graph = build_python_import_graph(file_map)
    js_graph = build_js_import_graph(file_map)
    heuristic_graph = build_heuristic_import_graph(file_map)
    
    for k, v in py_graph.items():
        combined_graph[k].update(v)
        
    for k, v in js_graph.items():
        combined_graph[k].update(v)
        
    for k, v in heuristic_graph.items():
        combined_graph[k].update(v)
        
    return dict(combined_graph)