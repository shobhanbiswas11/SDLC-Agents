"""
ast_graph_builder.py — Import Graph Builder v2

Architecture (5-step pipeline):
  Step 1: Build file indexes          — scan file_map ONCE, build fast lookup tables
  Step 2: Parse language-specific imports — each parser extracts raw import strings
  Step 3: Normalize edges             — resolve raw imports to actual file paths
  Step 4: Classify internal vs external — separate in-repo deps from third-party
  Step 5: Merge into one graph        — combine all language graphs

Key improvements over v1:
  - Pre-built indexes eliminate repeated file_map scanning
  - Package-aware Python resolution  dotted paths like foo.bar.baz)
  - Cached path lookups via extension and directory indexes
  - Internal vs external dependency separation
  - Single-pass file visiting — each file parsed exactly once
  - Much faster heuristics for Java/Go/Rust via indexed lookups
"""

import ast
import re
import posixpath
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Set, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass, field


# ══════════════════════════════════════════════════════════════════════════════
# Step 1: Build File Indexes
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class FileIndex:
    """
    Pre-built lookup tables for fast path resolution.
    Constructed ONCE from file_map, then shared across all parsers.

    Indexes:
      - by_extension:   {".py": {"src/app.py", "lib/utils.py", ...}}
      - by_stem:        {"app": ["src/app.py", "app.py"], "utils": ["lib/utils.py"]}
      - by_dir:         {"src": {"src/app.py", "src/models.py"}, ...}
      - by_suffix:      {"utils.py": ["src/utils.py", "lib/utils.py"]}
      - all_paths:      frozenset of every path in file_map (O(1) membership check)
      - by_dotted_module: {"foo.bar.baz": ["foo/bar/baz.py", "foo/bar/baz/__init__.py"]}
    """
    by_extension: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    by_stem: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    by_dir: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    by_suffix: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    by_dotted_module: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    all_paths: frozenset = field(default_factory=frozenset)


def build_file_index(file_map: Dict[str, str]) -> FileIndex:
    """
    Scan file_map exactly ONCE and build all lookup tables.
    Every parser uses this index instead of re-scanning file_map.
    """
    idx = FileIndex()
    all_paths = set()

    for path in file_map:
        all_paths.add(path)
        
        # Extension index
        dot_pos = path.rfind(".")
        ext = path[dot_pos:].lower() if dot_pos != -1 else ""
        if ext:
            idx.by_extension[ext].add(path)
        
        # Stem index (filename without extension)
        basename = posixpath.basename(path)
        stem = basename[:basename.rfind(".")] if "." in basename else basename
        idx.by_stem[stem.lower()].append(path)
        
        # Directory index
        dir_path = posixpath.dirname(path)
        if dir_path:
            idx.by_dir[dir_path].add(path)
        
        # Suffix index (for quick endswith lookups)
        # Store multiple levels: "utils.py", "lib/utils.py", "src/lib/utils.py"
        parts = path.split("/")
        for i in range(len(parts)):
            suffix = "/".join(parts[i:])
            idx.by_suffix[suffix].append(path)
        
        # Dotted module index (Python-specific but cheap to precompute)
        if ext == ".py":
            # "src/models/user.py" -> dotted module "src.models.user"
            module_path = path[:-3].replace("/", ".")
            idx.by_dotted_module[module_path].append(path)
            # Also register without top-level dirs for relative resolution
            # e.g., "models.user" from "src/models/user.py"
            parts_no_ext = path[:-3].split("/")
            for start in range(len(parts_no_ext)):
                dotted = ".".join(parts_no_ext[start:])
                if dotted not in idx.by_dotted_module:
                    idx.by_dotted_module[dotted] = []
                if path not in idx.by_dotted_module[dotted]:
                    idx.by_dotted_module[dotted].append(path)

    idx.all_paths = frozenset(all_paths)
    return idx


# ══════════════════════════════════════════════════════════════════════════════
# Step 2: Language-Specific Import Parsers
# Each parser returns RawEdge tuples: (source_path, raw_import_string, import_type)
# ══════════════════════════════════════════════════════════════════════════════

class RawEdge(NamedTuple):
    source: str          # file that contains the import
    raw_import: str      # the raw import string (e.g., "flask", "../utils", "java.util.List")
    import_type: str     # "absolute" | "relative" | "path_relative"
    language: str        # "python" | "js" | "java" | "go" | "rust" | "cpp"
    level: int = 0       # Python relative import level (0 = absolute)
    source_dir: str = "" # directory of the source file


def _parse_python_imports(path: str, content: str) -> List[RawEdge]:
    """Extract raw import strings from a Python file using AST (100% accurate)."""
    edges = []
    try:
        tree = ast.parse(content)
    except Exception:
        return edges

    source_dir = posixpath.dirname(path)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                edges.append(RawEdge(
                    source=path,
                    raw_import=alias.name,
                    import_type="absolute",
                    language="python",
                    level=0,
                    source_dir=source_dir,
                ))

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            level = node.level if node.level is not None else 0

            if level > 0:
                # Relative import: from .foo import bar, from ..utils import helper
                # We also need the imported names for cases like "from . import foo"
                if module:
                    edges.append(RawEdge(
                        source=path,
                        raw_import=module,
                        import_type="relative",
                        language="python",
                        level=level,
                        source_dir=source_dir,
                    ))
                else:
                    # from . import foo, bar — each name could be a module
                    for alias in node.names:
                        edges.append(RawEdge(
                            source=path,
                            raw_import=alias.name,
                            import_type="relative",
                            language="python",
                            level=level,
                            source_dir=source_dir,
                        ))
            else:
                # Absolute import: from flask import Flask
                if module:
                    edges.append(RawEdge(
                        source=path,
                        raw_import=module,
                        import_type="absolute",
                        language="python",
                        level=0,
                        source_dir=source_dir,
                    ))

    return edges


# Safer regex — no DOTALL, no catastrophic backtracking
_JS_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:[^;"']+\s+from\s+)?['"](?P<mod>[^'"]+)['"])|(?:require\(['"](?P<req>[^'"]+)['"]\))"""
)


def _parse_js_imports(path: str, content: str) -> List[RawEdge]:
    """Extract raw import strings from a JS/TS file using regex."""
    edges = []
    source_dir = posixpath.dirname(path)

    for m in _JS_IMPORT_RE.finditer(content):
        mod = m.group("mod") or m.group("req")
        if not mod:
            continue

        if mod.startswith("."):
            import_type = "path_relative"
        else:
            import_type = "absolute"

        edges.append(RawEdge(
            source=path,
            raw_import=mod,
            import_type=import_type,
            language="js",
            source_dir=source_dir,
        ))

    return edges


# Pre-compiled regexes for heuristic languages
_JAVA_IMPORT_RE = re.compile(r"^\s*import\s+(?:static\s+)?([\w\.]+)\s*;?", re.MULTILINE)
_CPP_INCLUDE_RE = re.compile(r'^\s*#include\s+"([^"]+)"', re.MULTILINE)
_GO_SINGLE_RE = re.compile(r'^\s*import\s+"([^"]+)"', re.MULTILINE)
_GO_MULTI_RE = re.compile(r'import\s+\((.*?)\)', re.DOTALL)
_GO_PKG_RE = re.compile(r'"([^"]+)"')
_RUST_USE_RE = re.compile(r'^\s*use\s+([a-zA-Z0-9_:]+)', re.MULTILINE)


def _parse_heuristic_imports(path: str, content: str) -> List[RawEdge]:
    """Extract raw import strings from Java, C/C++, Go, and Rust files."""
    edges = []
    source_dir = posixpath.dirname(path)

    if path.endswith((".java", ".kt")):
        for m in _JAVA_IMPORT_RE.finditer(content):
            edges.append(RawEdge(
                source=path, raw_import=m.group(1),
                import_type="absolute", language="java",
                source_dir=source_dir,
            ))

    elif path.endswith((".c", ".cpp", ".h", ".hpp")):
        for m in _CPP_INCLUDE_RE.finditer(content):
            edges.append(RawEdge(
                source=path, raw_import=m.group(1),
                import_type="path_relative", language="cpp",
                source_dir=source_dir,
            ))

    elif path.endswith(".go"):
        for m in _GO_SINGLE_RE.finditer(content):
            edges.append(RawEdge(
                source=path, raw_import=m.group(1),
                import_type="absolute", language="go",
                source_dir=source_dir,
            ))
        for m in _GO_MULTI_RE.finditer(content):
            for pkg_match in _GO_PKG_RE.finditer(m.group(1)):
                edges.append(RawEdge(
                    source=path, raw_import=pkg_match.group(1),
                    import_type="absolute", language="go",
                    source_dir=source_dir,
                ))

    elif path.endswith(".rs"):
        for m in _RUST_USE_RE.finditer(content):
            edges.append(RawEdge(
                source=path, raw_import=m.group(1),
                import_type="absolute", language="rust",
                source_dir=source_dir,
            ))

    return edges


# ══════════════════════════════════════════════════════════════════════════════
# Step 2 (orchestrator): Single-pass file visitor
# ══════════════════════════════════════════════════════════════════════════════

# Map file extensions to their parser function
_PARSER_MAP = {
    ".py": _parse_python_imports,
    ".js": _parse_js_imports,
    ".ts": _parse_js_imports,
    ".jsx": _parse_js_imports,
    ".tsx": _parse_js_imports,
    ".mjs": _parse_js_imports,
    ".cjs": _parse_js_imports,
    ".java": _parse_heuristic_imports,
    ".kt": _parse_heuristic_imports,
    ".c": _parse_heuristic_imports,
    ".cpp": _parse_heuristic_imports,
    ".h": _parse_heuristic_imports,
    ".hpp": _parse_heuristic_imports,
    ".go": _parse_heuristic_imports,
    ".rs": _parse_heuristic_imports,
}


def _parse_single_file(item: Tuple[str, str]) -> List[RawEdge]:
    """Visit one file, pick the right parser, return raw edges."""
    path, content = item
    if not content:
        return []
    ext_pos = path.rfind(".")
    ext = path[ext_pos:].lower() if ext_pos != -1 else ""
    parser = _PARSER_MAP.get(ext)
    if parser is None:
        return []
    try:
        return parser(path, content)
    except Exception:
        return []


def extract_all_raw_edges(
    file_map: Dict[str, str],
    max_workers: int = 8,
) -> List[RawEdge]:
    """
    Single-pass: visit every parseable file exactly once, extract raw edges.
    Each file is visited by ONE parser (determined by extension).
    """
    parseable = [
        (path, content)
        for path, content in file_map.items()
        if content and any(path.endswith(ext) for ext in _PARSER_MAP)
    ]

    all_edges: List[RawEdge] = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_parse_single_file, item) for item in parseable]
        for future in as_completed(futures):
            edges = future.result()
            if edges:
                all_edges.extend(edges)

    return all_edges


# ══════════════════════════════════════════════════════════════════════════════
# Step 3: Normalize Edges — resolve raw import strings to actual file paths
# ══════════════════════════════════════════════════════════════════════════════

def _resolve_python_import(edge: RawEdge, idx: FileIndex) -> Optional[str]:
    """Resolve a Python import to a file path using the pre-built index."""
    raw = edge.raw_import

    if edge.import_type == "relative":
        # Walk up directories based on the level
        target_dir = edge.source_dir
        for _ in range(edge.level - 1):
            target_dir = posixpath.dirname(target_dir)

        # Try: target_dir/module.py or target_dir/module/__init__.py
        parts = raw.split(".")
        relative_path = posixpath.join(target_dir, *parts)

        # Check module.py
        candidate = relative_path + ".py"
        if candidate in idx.all_paths:
            return candidate

        # Check module/__init__.py (package)
        candidate = posixpath.join(relative_path, "__init__.py")
        if candidate in idx.all_paths:
            return candidate

        # Fallback: just the first part as a stem
        first_part = parts[0].lower()
        for path in idx.by_stem.get(first_part, []):
            if path.endswith(".py") and path.startswith(target_dir):
                return path

        return None

    else:
        # Absolute import
        # Try full dotted module resolution first: "foo.bar.baz" -> "foo/bar/baz.py"
        candidates = idx.by_dotted_module.get(raw, [])
        if candidates:
            return candidates[0]

        # Try the full path: "foo.bar" -> "foo/bar.py" or "foo/bar/__init__.py"
        parts = raw.split(".")
        slash_path = "/".join(parts)

        candidate = slash_path + ".py"
        if candidate in idx.all_paths:
            return candidate

        candidate = posixpath.join(slash_path, "__init__.py")
        if candidate in idx.all_paths:
            return candidate

        # Fallback: match just the top-level module name as a stem
        first_part = parts[0].lower()
        matches = idx.by_stem.get(first_part, [])
        py_matches = [p for p in matches if p.endswith(".py")]
        if py_matches:
            return py_matches[0]

        return None


_JS_EXTENSIONS = ["", ".js", ".ts", ".jsx", ".tsx", "/index.js", "/index.ts", "/index.jsx", "/index.tsx"]


def _resolve_js_import(edge: RawEdge, idx: FileIndex) -> Optional[str]:
    """Resolve a JS/TS relative import to a file path."""
    if edge.import_type != "path_relative":
        return None  # external package — skip

    normalized = posixpath.normpath(posixpath.join(edge.source_dir, edge.raw_import))

    for ext in _JS_EXTENSIONS:
        candidate = (normalized + ext).lstrip("/")
        if candidate in idx.all_paths:
            return candidate

    return None


def _resolve_java_import(edge: RawEdge, idx: FileIndex) -> Optional[str]:
    """Resolve a Java/Kotlin import using suffix matching against the index."""
    # "com.example.models.User" -> "com/example/models/User"
    relative_path = edge.raw_import.replace(".", "/")

    for ext in (".java", ".kt"):
        suffix = relative_path + ext
        matches = idx.by_suffix.get(suffix, [])
        if matches:
            return matches[0]

    return None


def _resolve_cpp_import(edge: RawEdge, idx: FileIndex) -> Optional[str]:
    """Resolve a C/C++ #include with a relative path."""
    normalized = posixpath.normpath(posixpath.join(edge.source_dir, edge.raw_import))
    if normalized in idx.all_paths:
        return normalized
    return None


def _resolve_go_import(edge: RawEdge, idx: FileIndex) -> Optional[str]:
    """Resolve a Go import by matching directory suffixes."""
    pkg = edge.raw_import
    # Check if any directory ends with this package path
    for dir_path, files in idx.by_dir.items():
        if dir_path.endswith(pkg):
            go_files = [f for f in files if f.endswith(".go")]
            if go_files:
                return go_files[0]
    return None


def _resolve_rust_import(edge: RawEdge, idx: FileIndex) -> Optional[str]:
    """Resolve a Rust use statement."""
    module_path = edge.raw_import.replace("::", "/")

    # Strip crate:: or super:: prefix
    if module_path.startswith("crate/"):
        module_path = module_path[6:]
    elif module_path.startswith("super/"):
        module_path = module_path[6:]

    # Try module.rs
    suffix = module_path + ".rs"
    matches = idx.by_suffix.get(suffix, [])
    if matches:
        return matches[0]

    # Try module/mod.rs
    suffix = module_path + "/mod.rs"
    matches = idx.by_suffix.get(suffix, [])
    if matches:
        return matches[0]

    return None


# Dispatcher: language -> resolver
_RESOLVERS = {
    "python": _resolve_python_import,
    "js": _resolve_js_import,
    "java": _resolve_java_import,
    "cpp": _resolve_cpp_import,
    "go": _resolve_go_import,
    "rust": _resolve_rust_import,
}


def normalize_edges(
    raw_edges: List[RawEdge],
    idx: FileIndex,
) -> List[Tuple[str, str, str]]:
    """
    Resolve every raw edge to (source_path, target_path, raw_import).
    Returns only edges where the target was found in the file index.
    Unresolvable edges are silently dropped.
    """
    resolved = []
    for edge in raw_edges:
        resolver = _RESOLVERS.get(edge.language)
        if resolver is None:
            continue
        target = resolver(edge, idx)
        if target and target != edge.source:  # no self-edges
            resolved.append((edge.source, target, edge.raw_import))
    return resolved


# ══════════════════════════════════════════════════════════════════════════════
# Step 4: Classify Internal vs External
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ClassifiedGraph:
    """
    The final classified graph output.

    internal: {source_path: {target_path, ...}}  — edges between files in the repo
    external: {source_path: {package_name, ...}}  — imports of third-party packages
    """
    internal: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    external: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))


def classify_edges(
    resolved_edges: List[Tuple[str, str, str]],
    raw_edges: List[RawEdge],
    idx: FileIndex,
) -> ClassifiedGraph:
    """
    Split edges into internal (within the repo) and external (third-party).
    Internal = edges that resolved to a file in the repo.
    External = raw imports that did NOT resolve (likely pip/npm packages).
    """
    graph = ClassifiedGraph()

    # All resolved edges are internal by definition
    for source, target, _ in resolved_edges:
        graph.internal[source].add(target)

    # Collect resolved raw_imports so we know which ones were internal
    resolved_imports = set()
    for source, _, raw_import in resolved_edges:
        resolved_imports.add((source, raw_import))

    # Any raw edge that was NOT resolved is external
    for edge in raw_edges:
        if (edge.source, edge.raw_import) not in resolved_imports:
            # For external deps, just keep the top-level package name
            if edge.language == "python":
                pkg = edge.raw_import.split(".")[0]
            elif edge.language == "js":
                # @scope/package -> @scope/package, lodash -> lodash
                parts = edge.raw_import.split("/")
                if edge.raw_import.startswith("@") and len(parts) >= 2:
                    pkg = "/".join(parts[:2])
                else:
                    pkg = parts[0]
            elif edge.language == "java":
                pkg = edge.raw_import.split(".")[0]
            elif edge.language == "go":
                pkg = edge.raw_import
            elif edge.language == "rust":
                pkg = edge.raw_import.split("::")[0]
            else:
                pkg = edge.raw_import

            if pkg and not pkg.startswith("."):
                graph.external[edge.source].add(pkg)

    return graph


# ══════════════════════════════════════════════════════════════════════════════
# Step 5: Merge Into One Graph — Public API
# ══════════════════════════════════════════════════════════════════════════════

def build_combined_graph(
    file_map: Dict[str, str],
    max_workers: int = 8,
) -> Dict[str, Set[str]]:
    """
    Public API — drop-in replacement for the v1 function.

    Returns the internal import graph: {source_path: set(target_paths)}
    Same signature and return type as v1, fully backwards compatible.

    Pipeline:
      1. Build file indexes (once)
      2. Parse all imports (single pass, parallel)
      3. Normalize edges (resolve to file paths)
      4. Classify internal vs external
      5. Return internal graph
    """
    # Step 1: Build indexes
    idx = build_file_index(file_map)

    # Step 2: Parse all imports (single pass)
    raw_edges = extract_all_raw_edges(file_map, max_workers=max_workers)

    # Step 3: Normalize edges
    resolved = normalize_edges(raw_edges, idx)

    # Step 4: Classify
    classified = classify_edges(resolved, raw_edges, idx)

    # Step 5: Return internal graph (same format as v1)
    return dict(classified.internal)


def build_full_graph(
    file_map: Dict[str, str],
    max_workers: int = 8,
) -> ClassifiedGraph:
    """
    Extended API — returns the full ClassifiedGraph with both
    internal and external dependency information.

    Useful for:
      - Dependency auditing
      - Checking for unused imports
      - Generating dependency reports
      - Understanding third-party coupling
    """
    idx = build_file_index(file_map)
    raw_edges = extract_all_raw_edges(file_map, max_workers=max_workers)
    resolved = normalize_edges(raw_edges, idx)
    return classify_edges(resolved, raw_edges, idx)