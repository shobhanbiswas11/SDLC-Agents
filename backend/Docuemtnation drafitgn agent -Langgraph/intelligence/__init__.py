"""
intelligence — RAG intelligence layer for the Documentation Drafting Agent.

Modules:
    file_ranker      : Rank files by relevance to a user query
    semantic_ranker  : Gemini-based semantic embedding and reranking
    context_selector : Select and trim the best context for the LLM prompt
    chat_prompt      : Build the final chat prompt with RAG context injected
"""

from .file_ranker import rank_files
from .semantic_ranker import semantic_rerank, get_embeddings
from .context_selector import select_snippets
from .chat_prompt import build_chat_prompt
