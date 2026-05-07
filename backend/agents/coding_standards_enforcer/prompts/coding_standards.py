"""
Flake8 rule code → coding-standard mapping.

Used to enrich raw flake8 violations with a human-readable standard name
(PEP 8, Pyflakes, McCabe Complexity) and a short description.
"""
from __future__ import annotations


CODING_STANDARDS = {
    # --- PEP 8: Whitespace ---
    "E101": {
        "standard": "PEP 8 — Indentation",
        "description": "Indentation contains mixed spaces and tabs",
    },
    "E111": {
        "standard": "PEP 8 — Indentation",
        "description": "Indentation is not a multiple of four spaces",
    },
    "E112": {
        "standard": "PEP 8 — Indentation",
        "description": "Expected an indented block",
    },
    "E113": {
        "standard": "PEP 8 — Indentation",
        "description": "Unexpectedly indented block",
    },
    "E114": {
        "standard": "PEP 8 — Indentation",
        "description": "Indentation is not a multiple of four (comment)",
    },
    "E115": {
        "standard": "PEP 8 — Indentation",
        "description": "Expected an indented block (comment)",
    },
    "E116": {
        "standard": "PEP 8 — Indentation",
        "description": "Unexpected indentation (comment)",
    },
    "E117": {"standard": "PEP 8 — Indentation", "description": "Over-indented"},
    "E121": {
        "standard": "PEP 8 — Continuation Line",
        "description": "Continuation line under-indented for hanging indent",
    },
    "E122": {
        "standard": "PEP 8 — Continuation Line",
        "description": "Missing indentation or outdented",
    },
    "E123": {
        "standard": "PEP 8 — Continuation Line",
        "description": "Closing bracket does not match indentation",
    },
    "E124": {
        "standard": "PEP 8 — Continuation Line",
        "description": "Closing bracket does not match visual indentation",
    },
    "E125": {
        "standard": "PEP 8 — Continuation Line",
        "description": "Continuation line with same indent as next logical line",
    },
    "E126": {
        "standard": "PEP 8 — Continuation Line",
        "description": "Continuation line over-indented for hanging indent",
    },
    "E127": {
        "standard": "PEP 8 — Continuation Line",
        "description": "Continuation line over-indented for visual indent",
    },
    "E128": {
        "standard": "PEP 8 — Continuation Line",
        "description": "Continuation line under-indented for visual indent",
    },
    "E129": {
        "standard": "PEP 8 — Continuation Line",
        "description": "Visually indented line with same indent as next logical line",
    },
    "E131": {
        "standard": "PEP 8 — Continuation Line",
        "description": "Continuation line unaligned for block comment",
    },
    # --- PEP 8: Whitespace around operators/keywords ---
    "E201": {"standard": "PEP 8 — Whitespace", "description": "Whitespace after '('"},
    "E202": {"standard": "PEP 8 — Whitespace", "description": "Whitespace before ')'"},
    "E203": {
        "standard": "PEP 8 — Whitespace",
        "description": "Whitespace before ':', ';', or ','",
    },
    "E211": {
        "standard": "PEP 8 — Whitespace",
        "description": "Whitespace before '(' or '['",
    },
    "E221": {
        "standard": "PEP 8 — Whitespace",
        "description": "Multiple spaces before operator",
    },
    "E222": {
        "standard": "PEP 8 — Whitespace",
        "description": "Multiple spaces after operator",
    },
    "E223": {"standard": "PEP 8 — Whitespace", "description": "Tab before operator"},
    "E224": {"standard": "PEP 8 — Whitespace", "description": "Tab after operator"},
    "E225": {
        "standard": "PEP 8 — Whitespace",
        "description": "Missing whitespace around operator",
    },
    "E226": {
        "standard": "PEP 8 — Whitespace",
        "description": "Missing whitespace around arithmetic operator",
    },
    "E227": {
        "standard": "PEP 8 — Whitespace",
        "description": "Missing whitespace around bitwise or shift operator",
    },
    "E228": {
        "standard": "PEP 8 — Whitespace",
        "description": "Missing whitespace around modulo operator",
    },
    "E231": {
        "standard": "PEP 8 — Whitespace",
        "description": "Missing whitespace after ','",
    },
    "E241": {
        "standard": "PEP 8 — Whitespace",
        "description": "Multiple spaces after ','",
    },
    "E242": {"standard": "PEP 8 — Whitespace", "description": "Tab after ','"},
    "E251": {
        "standard": "PEP 8 — Whitespace",
        "description": "Unexpected spaces around keyword / parameter default",
    },
    "E252": {
        "standard": "PEP 8 — Whitespace",
        "description": "Missing whitespace around parameter default (PEP 3132)",
    },
    "E261": {
        "standard": "PEP 8 — Whitespace",
        "description": "At least two spaces before inline comment",
    },
    "E262": {
        "standard": "PEP 8 — Whitespace",
        "description": "Inline comment should start with '# '",
    },
    "E265": {
        "standard": "PEP 8 — Whitespace",
        "description": "Block comment should start with '# '",
    },
    "E266": {
        "standard": "PEP 8 — Whitespace",
        "description": "Too many leading '#' for block comment",
    },
    "E271": {
        "standard": "PEP 8 — Whitespace",
        "description": "Multiple spaces after keyword",
    },
    "E272": {
        "standard": "PEP 8 — Whitespace",
        "description": "Multiple spaces before keyword",
    },
    "E273": {
        "standard": "PEP 8 — Whitespace",
        "description": "Whitespace before keyword",
    },
    "E274": {"standard": "PEP 8 — Whitespace", "description": "Tab before keyword"},
    "E275": {
        "standard": "PEP 8 — Whitespace",
        "description": "Missing whitespace after keyword",
    },
    # --- PEP 8: Blank Lines ---
    "E301": {
        "standard": "PEP 8 — Blank Lines",
        "description": "Expected 1 blank line before a nested definition",
    },
    "E302": {
        "standard": "PEP 8 — Blank Lines",
        "description": "Expected 2 blank lines before a function or class definition",
    },
    "E303": {"standard": "PEP 8 — Blank Lines", "description": "Too many blank lines"},
    "E304": {
        "standard": "PEP 8 — Blank Lines",
        "description": "Defs that immediately follow docstrings should not be blank",
    },
    "E305": {
        "standard": "PEP 8 — Blank Lines",
        "description": "Expected 2 blank lines after class or function definition",
    },
    # --- PEP 8: Imports ---
    "E401": {
        "standard": "PEP 8 — Imports",
        "description": "Multiple imports on one line",
    },
    "E402": {
        "standard": "PEP 8 — Imports",
        "description": "Module level import not at top of file",
    },
    # --- PEP 8: Line Length ---
    "E501": {
        "standard": "PEP 8 — Line Length",
        "description": "Line too long (exceeds 79 characters)",
    },
    "E502": {
        "standard": "PEP 8 — Line Length",
        "description": "Backslash is redundant between brackets",
    },
    # --- PEP 8: Statements ---
    "E701": {
        "standard": "PEP 8 — Statement",
        "description": "Multiple statements on one line (colon)",
    },
    "E702": {
        "standard": "PEP 8 — Statement",
        "description": "Multiple statements on one line (semicolon)",
    },
    "E703": {
        "standard": "PEP 8 — Statement",
        "description": "Statement ends with a semicolon",
    },
    "E711": {
        "standard": "PEP 8 — Comparison",
        "description": "Comparison to None (use 'is' or 'is not')",
    },
    "E712": {
        "standard": "PEP 8 — Comparison",
        "description": "Comparison to True/False (use 'if cond:' or 'if not cond:')",
    },
    "E713": {
        "standard": "PEP 8 — Comparison",
        "description": "Test for membership should be 'not in x'",
    },
    "E714": {
        "standard": "PEP 8 — Comparison",
        "description": "Test for object identity should be 'is not'",
    },
    "E721": {
        "standard": "PEP 8 — Comparison",
        "description": "Do not compare types, use isinstance()",
    },
    "E722": {
        "standard": "PEP 8 — Exception",
        "description": "Do not use bare 'except'",
    },
    "E731": {
        "standard": "PEP 8 — Statement",
        "description": "Do not assign a lambda expression, use a def",
    },
    "E741": {"standard": "PEP 8 — Naming", "description": "Ambiguous variable name"},
    "E742": {"standard": "PEP 8 — Naming", "description": "Ambiguous class name"},
    "E743": {"standard": "PEP 8 — Naming", "description": "Ambiguous function name"},
    # --- PEP 8: Runtime ---
    "E901": {
        "standard": "PEP 8 — Syntax",
        "description": "SyntaxError or IndentationError",
    },
    "E902": {
        "standard": "PEP 8 — Syntax",
        "description": "TokenError: EOF in multi-line statement",
    },
    # --- Pyflakes (F) ---
    "F401": {
        "standard": "Pyflakes — Imports",
        "description": "Module imported but unused",
    },
    "F402": {
        "standard": "Pyflakes — Imports",
        "description": "Import module from line N shadowed by loop variable",
    },
    "F403": {
        "standard": "Pyflakes — Imports",
        "description": "Used 'from module import *'",
    },
    "F405": {
        "standard": "Pyflakes — Imports",
        "description": "Name may be undefined from 'import *'",
    },
    "F811": {
        "standard": "Pyflakes — Redefinition",
        "description": "Redefinition of unused name from line N",
    },
    "F821": {"standard": "Pyflakes — Undefined", "description": "Undefined name"},
    "F841": {
        "standard": "Pyflakes — Unused",
        "description": "Local variable is assigned but never used",
    },
    # --- Warnings (W) ---
    "W291": {
        "standard": "PEP 8 — Trailing Whitespace",
        "description": "Trailing whitespace",
    },
    "W292": {
        "standard": "PEP 8 — Trailing Whitespace",
        "description": "No newline at end of file",
    },
    "W293": {
        "standard": "PEP 8 — Trailing Whitespace",
        "description": "Whitespace before a comment",
    },
    "W391": {
        "standard": "PEP 8 — Blank Lines",
        "description": "Blank line at end of file",
    },
    "W503": {
        "standard": "PEP 8 — Line Break",
        "description": "Line break before binary operator",
    },
    "W504": {
        "standard": "PEP 8 — Line Break",
        "description": "Line break after binary operator",
    },
    "W505": {"standard": "PEP 8 — Doc Line Length", "description": "Doc line too long"},
    # --- McCabe Complexity (C) ---
    "C901": {"standard": "McCabe Complexity", "description": "Function is too complex"},
}


def get_rule_info(rule_code: str) -> dict:
    """Resolve a flake8 rule code to its coding-standard description.

    Falls back to a prefix lookup, and finally a generic descriptor.
    """
    if rule_code in CODING_STANDARDS:
        return CODING_STANDARDS[rule_code]

    prefix_map = {
        "E1": {
            "standard": "PEP 8 — Indentation",
            "description": "Indentation related issue",
        },
        "E2": {
            "standard": "PEP 8 — Whitespace",
            "description": "Whitespace related issue",
        },
        "E3": {
            "standard": "PEP 8 — Blank Lines",
            "description": "Blank line related issue",
        },
        "E4": {"standard": "PEP 8 — Imports", "description": "Import related issue"},
        "E5": {"standard": "PEP 8 — Line Length", "description": "Line length issue"},
        "E7": {
            "standard": "PEP 8 — Statement",
            "description": "Statement related issue",
        },
        "E9": {"standard": "PEP 8 — Syntax", "description": "Syntax error"},
        "F": {"standard": "Pyflakes", "description": "Code analysis issue"},
        "W": {"standard": "PEP 8 — Warning", "description": "Style warning"},
        "C": {"standard": "McCabe Complexity", "description": "Complexity issue"},
    }

    for prefix, info in prefix_map.items():
        if rule_code.startswith(prefix):
            return info

    return {"standard": "Coding Standard", "description": "Unclassified rule"}
