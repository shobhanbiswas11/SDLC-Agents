"""
api.py — Backward-compatibility shim.

The real implementation lives in app/api.py.
This file exists so that:
  - `uvicorn api:app --port 18200` (Dockerfile / run.bat) still works.
  - `python api.py` still works.

Do not add logic here — edit app/api.py instead.
"""

from app.api import app  # noqa: F401  — re-export for uvicorn

if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=int(os.getenv("PORT", "18200")), reload=True)
