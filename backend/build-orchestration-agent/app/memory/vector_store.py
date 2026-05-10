"""
FAISS-backed vector store with disk persistence.

Stores embeddings of past build-error → fix pairs so the agent
can retrieve similar past fixes when reasoning about new errors.
"""

import os
import json
import faiss
import numpy as np

# Default storage directory
STORE_DIR = os.getenv("RAG_STORE_DIR", "/tmp/build_agent_rag")


class VectorStore:
    def __init__(self, dim: int = 1536, store_dir: str | None = None):
        self.dim = dim
        self.store_dir = store_dir or STORE_DIR
        self.index_path = os.path.join(self.store_dir, "faiss.index")
        self.meta_path = os.path.join(self.store_dir, "metadata.json")

        os.makedirs(self.store_dir, exist_ok=True)

        # Try loading persisted state; fall back to empty
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            self.index = faiss.read_index(self.index_path)
            with open(self.meta_path, "r") as f:
                self.data: list[dict] = json.load(f)
        else:
            self.index = faiss.IndexFlatL2(dim)
            self.data = []

    # ── Write ────────────────────────────────────────────
    def add(self, embedding: list[float], metadata: dict):
        """Add a single embedding + metadata pair and persist."""
        vec = np.array([embedding], dtype="float32")
        self.index.add(vec)
        self.data.append(metadata)
        self._persist()

    # ── Read ─────────────────────────────────────────────
    def search(self, embedding: list[float], k: int = 3) -> list[dict]:
        """Return top-k most similar metadata entries."""
        if len(self.data) == 0:
            return []

        k = min(k, len(self.data))
        vec = np.array([embedding], dtype="float32")
        distances, indices = self.index.search(vec, k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.data):
                entry = dict(self.data[idx])
                entry["_distance"] = float(dist)
                results.append(entry)
        return results

    # ── Persistence ──────────────────────────────────────
    def _persist(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "w") as f:
            json.dump(self.data, f)

    @property
    def size(self) -> int:
        return len(self.data)