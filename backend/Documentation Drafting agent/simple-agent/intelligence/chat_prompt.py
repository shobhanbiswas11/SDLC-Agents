# repo_summarizer/chat_prompt.py
"""
Chat Prompt Builder

Constructs the prompt for the Codebase Chatbot feature, injecting the
file structure, metadata, and top semantically ranked files.
"""

def build_chat_prompt(
    structure: str,
    metadata_block: str,
    code_snippets: str,
    user_message: str,
) -> str:
    """
    Builds the final prompt string to send to the LLM for chatbot Q&A.
    """
    return f"""
You are an expert AI software engineer assisting a user with their codebase.
Your goal is to answer the user's question accurately, concisely, and completely.

⚠️ CRITICAL INSTRUCTIONS:
1. Base your answer ONLY on the provided context below (Project Structure, Metadata, and Key Source Files).
2. If the context does not contain enough information to answer the question fully, say so clearly. Do not hallucinate code.
3. If providing code examples, ensure they match the style and conventions seen in the context.
4. When you mention specific logic or endpoints, reference the filename where it is defined.
5. Provide your output entirely in standard Markdown.

====== PROJECT STRUCTURE ======
{structure}
===============================

====== AVAILABLE FUNCTIONS & ENDPOINTS (API Metadata) ======
{metadata_block}
============================================================

====== RELEVANT SOURCE CODE (From Semantic Search) ======
{code_snippets}
=========================================================

USER'S QUESTION:
{user_message}

Answer exactly what the user is asking, directly and professionally.
"""
