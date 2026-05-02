# repo_summarizer/semantic_ranker.py
"""
Semantic File Ranker

An opt-in second-pass re-ranker that uses Azure OpenAI embeddings to score
candidate files by semantic relevance to a "what are the most important source
files in this project?" query.

Only activated when USE_SEMANTIC_RANKING=true in .env.
Falls back gracefully to heuristic ranking if embeddings fail.

Usage:
    from intelligence.semantic_ranker import semantic_rerank
    ranked = semantic_rerank(heuristic_top40, file_map, client, model)
"""

import math
import os
import hashlib
from typing import Dict, List, Tuple, Optional

try:
    from google import genai as _genai_sdk
    from google.genai import types as _genai_types
except ImportError:
    _genai_sdk = None
    _genai_types = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    dot   = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _build_file_text(path: str, content: str, max_lines: int = 50) -> str:
    """Create a short textual representation of a file for embedding."""
    lines = (content or "").splitlines()[:max_lines]
    snippet = "\n".join(lines)
    return f"File: {path}\n{snippet}"


def get_embeddings(
    texts: List[str],
    model: str = "models/gemini-embedding-2",
    batch_size: int = 16,
) -> List[Optional[List[float]]]:
    """
    Embed a list of text strings using the new google.genai SDK.
    Falls back to None slots if embedding fails.
    """
    results: List[Optional[List[float]]] = [None] * len(texts)

    if _genai_sdk is None:
        print("[semantic_ranker] google-genai SDK not installed.")
        return results

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[semantic_ranker] GEMINI_API_KEY is not set.")
        return results

    client = _genai_sdk.Client(api_key=api_key)

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        try:
            response = client.models.embed_content(
                model=model,
                contents=batch,
            )
            for i, emb_obj in enumerate(response.embeddings):
                results[start + i] = emb_obj.values
        except Exception as e:
            print(f"[semantic_ranker] Embedding batch {start // batch_size} failed: {e}")

    return results


# ── Main re-ranker ────────────────────────────────────────────────────────────

def semantic_rerank(
    candidates: List[Tuple[str, float]],
    file_map: Dict[str, str],
    model: str = "models/gemini-embedding-2",
    query: str = "most important source files that define the core logic, API routes, and data models of this project",
    top_k: int = 20,
    cached_embeddings: Optional[Dict[str, List[float]]] = None,
) -> List[Tuple[str, float]]:
    """
    Re-rank a list of (path, heuristic_score) pairs using semantic embeddings.

    Process:
    1. Embed each candidate file (filename + first 50 lines).
    2. Embed the query string.
    3. Score each file by cosine similarity to the query.
    4. Blend: final_score = 0.6 * semantic_sim + 0.4 * normalised_heuristic
       (lower heuristic = more important, we invert for blending)
    5. Return top_k by blended score descending.

    Falls back to original order if embeddings fail entirely.

    Args:
        candidates: List of (path, heuristic_score) from rank_files().
        file_map:   {path: content} dict.
        model:      Embedding model deployment name (e.g., models/text-embedding-004).
        query:      Natural language description of what we're looking for.
        top_k:      Number of results to return.

    Returns:
        List of (path, blended_score) sorted descending (higher = more relevant).
    """
    if not candidates:
        return candidates

    print(f"[semantic_ranker] Re-ranking {len(candidates)} candidates with embeddings...")

    if cached_embeddings is None:
        cached_embeddings = {}

    # ── Build text representations and check cache ────────────────────────────
    query_emb = None
    file_embs: List[Optional[List[float]]] = [None] * len(candidates)
    
    texts_to_embed = [query]
    text_indices = [("query", 0)]

    for i, (path, _) in enumerate(candidates):
        text = _build_file_text(path, file_map.get(path, ""))
        text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        
        if text_hash in cached_embeddings:
            file_embs[i] = cached_embeddings[text_hash]
        else:
            texts_to_embed.append(text)
            text_indices.append(("file", i, text_hash))

    # ── Fetch missing embeddings ──────────────────────────────────────────────
    print(f"[semantic_ranker] Fetching {len(texts_to_embed)} new embeddings ({len(texts_to_embed)-1} files, 1 query)...")
    new_embeddings = get_embeddings(texts_to_embed, model=model)

    for idx_info, emb in zip(text_indices, new_embeddings):
        if idx_info[0] == "query":
            query_emb = emb
        else:
            _, i, text_hash = idx_info
            file_embs[i] = emb
            if emb is not None:
                cached_embeddings[text_hash] = emb

    if query_emb is None:
        print("[semantic_ranker] Query embedding failed — falling back to heuristic order.")
        return candidates[:top_k]

    # ── Compute similarity scores ─────────────────────────────────────────────
    sim_scores: List[Tuple[str, float, float]] = []  # (path, sim, heuristic)
    for (path, h_score), emb in zip(candidates, file_embs):
        if emb is not None:
            sim = _cosine_similarity(query_emb, emb)
        else:
            sim = 0.0  # treat failed embeddings as least relevant
        sim_scores.append((path, sim, h_score))

    if not sim_scores:
        return candidates[:top_k]

    # ── Normalise heuristic scores (lower original = higher importance) ────────
    max_h = max(h for _, _, h in sim_scores) or 1.0
    min_h = min(h for _, _, h in sim_scores)
    h_range = max_h - min_h or 1.0

    blended: List[Tuple[str, float]] = []
    for path, sim, h_score in sim_scores:
        # Invert & normalise heuristic so 1.0 = best
        norm_h = 1.0 - ((h_score - min_h) / h_range)
        # Blend: 60% semantic, 40% heuristic
        score = 0.6 * sim + 0.4 * norm_h
        blended.append((path, score))

    # Sort descending (higher blended score = more relevant)
    blended.sort(key=lambda x: x[1], reverse=True)

    print(f"[semantic_ranker] Top-3 after re-ranking: {[p for p, _ in blended[:3]]}")

    return blended[:top_k]
