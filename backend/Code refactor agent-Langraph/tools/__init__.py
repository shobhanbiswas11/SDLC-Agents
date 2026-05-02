"""tools — Tool handler implementations for the Code Refactoring Agent.

Each sub-module groups semantically related handlers. This package assembles
the unified ``TOOL_HANDLERS`` dispatch table consumed by ``agent/nodes/tool_node.py``.
"""

from tools.file_tools import (
    handle_read_file,
    handle_write_file,
    handle_list_files,
    handle_navigate_to_file,
)
from tools.analysis_tools import (
    handle_analyze_code,
    handle_search_code,
    handle_find_references,
)
from tools.refactor_tools import (
    handle_suggest_refactor,
    handle_apply_refactor,
    handle_apply_batch_refactor,
    handle_diff_preview,
    handle_multi_refactor,
)
from tools.git_tools import (
    handle_git_commit_push,
    handle_github_put_file,
)
from tools.test_tools import (
    handle_run_tests,
    handle_terminal_command,
)
from tools.interaction_tools import handle_ask_user

# ── Dispatch table — keys must match 'name:' in config/tools/*.yaml ───────────
TOOL_HANDLERS: dict = {
    "analyze_code":       handle_analyze_code,
    "suggest_refactor":   handle_suggest_refactor,
    "apply_refactor":     handle_apply_refactor,
    "apply_batch_refactor": handle_apply_batch_refactor,
    "diff_preview":       handle_diff_preview,
    "run_tests":          handle_run_tests,
    "read_file":          handle_read_file,
    "write_file":         handle_write_file,
    "navigate_to_file":   handle_navigate_to_file,
    "list_files":         handle_list_files,
    "ask_user":           handle_ask_user,
    "search_code":        handle_search_code,
    "find_references":    handle_find_references,
    "multi_refactor":     handle_multi_refactor,
    "terminal_command":   handle_terminal_command,
    "git_commit_push":    handle_git_commit_push,
    "github_put_file":    handle_github_put_file,
}

__all__ = ["TOOL_HANDLERS"]
