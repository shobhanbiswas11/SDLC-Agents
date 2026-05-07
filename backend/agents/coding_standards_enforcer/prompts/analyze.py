"""
Multi-language analyze prompt — instructs the LLM to identify ALL coding-standard
violations across Python, C++, Java, JS/TS, Go, and Rust.
"""
from __future__ import annotations

from typing import Optional

from langchain_core.prompts import PromptTemplate


# ─────────────────────────────────────────────────────────────
# Standards reference per language — surfaced in /languages
# ─────────────────────────────────────────────────────────────

LANGUAGE_STANDARDS = {
    "python": {
        "name": "Python",
        "standards": [
            "PEP 8 — Style Guide for Python Code",
            "PEP 257 — Docstring Conventions",
            "PEP 20 — The Zen of Python",
            "Pyflakes — Logical error detection",
            "McCabe — Cyclomatic complexity",
        ],
        "categories": [
            "Indentation & Whitespace",
            "Naming Conventions (snake_case functions/variables, PascalCase classes)",
            "Import Organization",
            "Line Length (≤79/120 chars)",
            "Blank Lines between definitions",
            "Unused imports and variables",
            "Bare except clauses",
            "Mutable default arguments",
            "Type hints best practices",
            "Docstring formatting",
        ],
    },
    "cpp": {
        "name": "C++",
        "standards": [
            "C++ Core Guidelines (ISO)",
            "Google C++ Style Guide",
            "MISRA C++ (safety-critical)",
            "CERT C++ Coding Standard",
        ],
        "categories": [
            "Memory Management (RAII, smart pointers vs raw)",
            "Const correctness",
            "Include guards / #pragma once",
            "Naming conventions (CamelCase types, snake_case variables)",
            "Avoid using namespace std in headers",
            "Prefer nullptr over NULL",
            "Rule of Five / Rule of Zero",
            "Avoid C-style casts (use static_cast etc.)",
            "Unused variables and includes",
            "Buffer overflow risks",
            "Initialization of variables",
            "Range-based for loops over index-based",
        ],
    },
    "java": {
        "name": "Java",
        "standards": [
            "Google Java Style Guide",
            "Oracle Java Code Conventions",
            "SonarQube Rules",
            "SpotBugs / FindBugs patterns",
        ],
        "categories": [
            "Naming conventions (camelCase methods, PascalCase classes)",
            "Unused imports",
            "Missing @Override annotations",
            "Raw type usage (generics)",
            "Empty catch blocks",
            "Resource leaks (unclosed streams, connections)",
            "String comparison with == instead of .equals()",
            "Excessive method length / complexity",
            "Missing access modifiers",
            "Javadoc formatting",
            "Magic numbers",
            "Null pointer risks",
        ],
    },
    "javascript": {
        "name": "JavaScript",
        "standards": [
            "ESLint Recommended Rules",
            "Airbnb JavaScript Style Guide",
            "StandardJS",
            "Google JavaScript Style Guide",
        ],
        "categories": [
            "var vs let/const (prefer const)",
            "Strict equality (=== vs ==)",
            "Unused variables and imports",
            "Missing semicolons (style-dependent)",
            "Arrow function usage",
            "Template literals over concatenation",
            "Proper error handling (catch blocks)",
            "Naming conventions (camelCase)",
            "Avoid eval() and with",
            "No console.log in production",
            "Callback hell / promise handling",
            "Module import/export patterns",
        ],
    },
    "typescript": {
        "name": "TypeScript",
        "standards": [
            "typescript-eslint Recommended Rules",
            "Airbnb TypeScript Style Guide",
            "Google TypeScript Style Guide",
        ],
        "categories": [
            "Explicit type annotations vs inference",
            "Avoid 'any' type",
            "Proper interface/type usage",
            "Strict null checks",
            "Unused variables and imports",
            "const assertions and readonly",
            "Proper enum usage",
            "Optional chaining and nullish coalescing",
            "Generic type constraints",
            "Naming conventions (PascalCase types, camelCase variables)",
            "no-non-null-assertion",
            "Proper async/await patterns",
        ],
    },
    "go": {
        "name": "Go",
        "standards": [
            "Effective Go",
            "Go Code Review Comments",
            "Go Proverbs",
            "golint / staticcheck rules",
        ],
        "categories": [
            "Exported names require comments",
            "Error handling (don't ignore errors)",
            "Naming conventions (MixedCaps, no underscores)",
            "Receiver naming (short, consistent)",
            "Unused imports and variables (compile error in Go)",
            "Blank identifier misuse",
            "Package naming",
            "Error wrapping with fmt.Errorf",
            "Context propagation",
            "Goroutine leaks",
            "Defer usage patterns",
            "Interface compliance",
        ],
    },
    "rust": {
        "name": "Rust",
        "standards": [
            "Rust API Guidelines",
            "Clippy lint collection",
            "Rustfmt conventions",
            "Rust Style Guide (RFC 2436)",
        ],
        "categories": [
            "Ownership and borrowing issues",
            "Unnecessary clones",
            "Unused variables (prefix with _)",
            "Missing error handling (unwrap() in production)",
            "Naming conventions (snake_case functions, PascalCase types)",
            "Lifetime annotations",
            "Pattern matching exhaustiveness",
            "Clippy suggestions (needless_return, redundant_clone, etc.)",
            "Unsafe code blocks",
            "Dead code",
            "Proper Result/Option handling",
            "Documentation comments (///)",
        ],
    },
}


def _build_language_context(language: str) -> str:
    lang = LANGUAGE_STANDARDS.get(language.lower())
    if not lang:
        return "Analyze the code for general coding standard violations."

    standards_str = "\n".join(f"  - {s}" for s in lang["standards"])
    categories_str = "\n".join(f"  - {c}" for c in lang["categories"])

    return f"""Language: {lang['name']}

Applicable Standards:
{standards_str}

Violation Categories to Check:
{categories_str}"""


def get_language_context(language: str) -> str:
    return _build_language_context(language)


def get_supported_languages() -> list:
    return list(LANGUAGE_STANDARDS.keys())


def get_language_info(language: str) -> Optional[dict]:
    return LANGUAGE_STANDARDS.get(language.lower())


# ─────────────────────────────────────────────────────────────
# Prompt template
# ─────────────────────────────────────────────────────────────

analyze_prompt = PromptTemplate(
    input_variables=["language", "language_context", "code"],
    template="""You are an expert code review agent specializing in coding standards enforcement across multiple programming languages. You must analyze the provided code and identify ALL coding standard violations.

{language_context}

Code to Analyze:
```{language}
{code}
```

Instructions:
- Identify EVERY coding standard violation in the code above.
- For each violation, provide the exact line number, a rule code, the standard it violates, and a clear explanation.
- Also provide a FIXED version of that specific line or block.
- Be thorough — check for style, naming, best practices, potential bugs, and anti-patterns.
- If the code is clean, return an empty violations array.

You MUST respond in EXACTLY this JSON format (no markdown fencing, no extra text):
{{
  "violations": [
    {{
      "line": <line_number>,
      "column": 1,
      "rule_code": "<short_code>",
      "rule_standard": "<standard_name>",
      "rule_description": "<brief_description>",
      "message": "<detailed_violation_message>",
      "severity": "<error|warning|info>",
      "original_code": "<the_violating_line_or_block>",
      "suggested_code": "<the_fixed_version>",
      "explanation": "<why_this_is_a_violation_and_what_was_changed>"
    }}
  ],
  "summary": {{
    "total_violations": <count>,
    "by_severity": {{"error": <n>, "warning": <n>, "info": <n>}},
    "overall_quality": "<excellent|good|fair|poor>",
    "top_issues": ["<brief_issue_1>", "<brief_issue_2>"]
  }}
}}
""",
)
