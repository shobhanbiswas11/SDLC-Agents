"""
RAG Retriever for the Build Agent.

Provides two operations:
  1. retrieve(error_text) — find similar past errors and their successful fixes
  2. store(error_text, fix_metadata) — save a successful error→fix pair

The embedder is the AzureReasoner.embed() method.
"""


class Retriever:
    def __init__(self, vector_store, embedder):
        """
        Args:
            vector_store: VectorStore instance (FAISS-backed)
            embedder: callable(text) -> list[float]  (e.g. AzureReasoner.embed)
        """
        self.vector_store = vector_store
        self.embedder = embedder

    def retrieve(self, error_text: str, k: int = 3) -> list[dict]:
        """
        Retrieve the top-k most similar past fix records for the given error.

        Returns a list of dicts like:
        {
            "error_type": "missing_module",
            "error_message": "Cannot find module 'express'",
            "fix_action": "run_command",
            "fix_command": "npm install express",
            "fix_explanation": "...",
            "project_type": "Node.js",
            "outcome": "success",
            "_distance": 0.123
        }
        """
        try:
            embedding = self.embedder(error_text)
            results = self.vector_store.search(embedding, k=k)
            return results
        except Exception as e:
            print(f"[RAG] Retrieval failed: {e}")
            return []

    def store(self, error_text: str, fix_metadata: dict):
        """
        Store a successful error→fix pair for future retrieval.

        Args:
            error_text: The original error description (used for embedding)
            fix_metadata: Dict with keys like error_type, fix_action,
                          fix_command, fix_explanation, project_type, outcome
        """
        try:
            embedding = self.embedder(error_text)
            self.vector_store.add(embedding, fix_metadata)
            print(f"[RAG] Stored fix (total: {self.vector_store.size})")
        except Exception as e:
            print(f"[RAG] Store failed: {e}")

    @property
    def has_data(self) -> bool:
        return self.vector_store.size > 0