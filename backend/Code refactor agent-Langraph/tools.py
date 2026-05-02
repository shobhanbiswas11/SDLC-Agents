"""
tools.py — Backward-compatibility shim.

The real implementations are now split across:
  tools/file_tools.py
  tools/analysis_tools.py
  tools/refactor_tools.py
  tools/git_tools.py
  tools/test_tools.py
  tools/interaction_tools.py

Any module that does `from tools import TOOL_HANDLERS` keeps working.
Do not add logic here — edit the relevant tools/*.py files instead.
"""

from tools import TOOL_HANDLERS  # noqa: F401

# Re-export individual handlers for any legacy direct imports
from tools.file_tools import (          # noqa: F401
    handle_read_file,
    handle_write_file,
    handle_list_files,
    handle_navigate_to_file,
)
from tools.analysis_tools import (      # noqa: F401
    handle_analyze_code,
    handle_search_code,
    handle_find_references,
)
from tools.refactor_tools import (      # noqa: F401
    handle_suggest_refactor,
    handle_apply_refactor,
    handle_diff_preview,
    handle_multi_refactor,
    handle_apply_batch_refactor,
    apply_search_replace_blocks,
)
from tools.git_tools import (           # noqa: F401
    handle_git_commit_push,
    handle_github_put_file,
)
from tools.test_tools import (          # noqa: F401
    handle_run_tests,
    handle_terminal_command,
)
from tools.interaction_tools import handle_ask_user  # noqa: F401