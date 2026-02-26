import ast
import re
import posixpath
from collections import defaultdict
from typing import Dict, Set

# ── Python AST-Based Importer ────────────────────────────────────────────────
def build_python_import_graph(file_map: Dict[str, str]) -> Dict[str, Set[str]]:
    """
    Build a graph: file_path -> set(of file_paths it imports)
    Improved to handle both absolute and relative Python imports.
    """
    # Prepare lookup: module name (without .py) -> list of possible full file paths
    module_to_paths = defaultdict(list)
    for path in file_map:
        if path.endswith(".py"):
            name = posixpath.basename(path)[:-3] # Strip off the '.py'
            module_to_paths[name].append(path)

    graph = defaultdict(set)

    for path, content in file_map.items():
        if not path.endswith(".py") or not content:
            continue
            
        try:
            tree = ast.parse(content)
        except Exception:
            # Skip files with syntax errors (e.g., Python 2 code or incomplete files)
            continue
            
        current_dir = posixpath.dirname(path)

        for node in ast.walk(tree):
            # Case 1: Standard Imports (import os, import my_module)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    base_module = alias.name.split(".")[0]
                    graph[path].update(module_to_paths.get(base_module, []))
                    
            # Case 2: From Imports (from my_module import x, from . import y)
            elif isinstance(node, ast.ImportFrom):
                # Handle relative imports (e.g., from ..models import User)
                if node.level is not None and node.level > 0:
                    target_dir = current_dir
                    for _ in range(node.level - 1):
                        target_dir = posixpath.dirname(target_dir)
                    
                    # Target could be the module or the alias if module is None (from . import foo)
                    mod_name = node.module.split(".")[0] if node.module else ""
                    
                    for alias in node.names:
                        target_name = mod_name or alias.name
                        for candidate in module_to_paths.get(target_name, []):
                            # Add basic safety check to ensure relative import belongs to the target tree
                            if candidate.startswith(target_dir):
                                graph[path].add(candidate)
                else:
                    # Handle absolute 'from' imports
                    if node.module:
                        base_module = node.module.split(".")[0]
                        graph[path].update(module_to_paths.get(base_module, []))
    # print(f"Built Python import graph with {len(graph)} nodes.")
    return dict(graph)


# ── JS/TS Import Parser ──────────────────────────────────────────────────────
# Added re.DOTALL to handle multiline destructured imports
_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:.*?\s+from\s+)?['"](?P<mod>[^'"]+)['"])|(?:require\(['"](?P<req>[^'"]+)['"]\))""", 
    re.DOTALL
)

def build_js_import_graph(file_map: Dict[str, str]) -> Dict[str, Set[str]]:
    """
    Builds an import graph for JS/TS. Safely normalizes paths using posixpath 
    and checks if the target file actually exists in the file_map.
    """
    graph = defaultdict(set)
    
    # Valid file extensions for JS/TS ecosystem
    valid_extensions = ["", ".js", ".ts", ".jsx", ".tsx", "/index.js", "/index.ts"]
    
    for path, content in file_map.items():
        if not path.endswith((".js", ".ts", ".jsx", ".tsx")) or not content:
            continue
            
        base_dir = posixpath.dirname(path)
        
        for m in _IMPORT_RE.finditer(content):
            mod = m.group("mod") or m.group("req")
            if not mod:
                continue
                
            # We only track local relative imports, ignoring external node_modules
            if mod.startswith("."):
                # Cleanly resolve "../" or "./" relative to the current file's directory
                normalized_base = posixpath.normpath(posixpath.join(base_dir, mod))
                
                # Check which extension actually matches a file in our repo
                for ext in valid_extensions:
                    candidate = normalized_base + ext
                    # Strip leading slashes to match GitHub's file path formats
                    candidate = candidate.lstrip("/") 
                    
                    if candidate in file_map:
                        graph[path].add(candidate)
                        break # Stop looking once we find the exact match
                        
    return dict(graph)


# ── Combined Graph Builder ───────────────────────────────────────────────────
def build_combined_graph(file_map: Dict[str, str]) -> Dict[str, Set[str]]:
    """Return combined graph (Python + JS/TS heuristics)."""
    combined_graph = defaultdict(set)
    
    py_graph = build_python_import_graph(file_map)
    js_graph = build_js_import_graph(file_map)
    
    for k, v in py_graph.items():
        combined_graph[k].update(v)
        
    for k, v in js_graph.items():
        combined_graph[k].update(v)
        
    return dict(combined_graph)