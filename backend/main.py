"""
FastAPI application entry point — Coding Standards Enforcer Agent.
"""
from __future__ import annotations

import logging
import pathlib

# ── Load .env BEFORE any other import reads os.getenv() ──────────────────────
try:
    from dotenv import load_dotenv

    _env_file = pathlib.Path(__file__).parent / ".env"
    if _env_file.exists():
        load_dotenv(_env_file, override=False)
        logging.getLogger(__name__).debug("Loaded .env from %s", _env_file)
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agents.coding_standards_enforcer import agent_router as coding_standards_router
from agents.coding_standards_enforcer.initialization import (
    initialize as init_coding_standards,
    shutdown as shutdown_coding_standards,
)
from core.logging import configure_logging
from core_router import core_router

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GENAICOE — Coding Standards Enforcer Agent",
    description=(
        "Multi-language AI agent that detects coding-standard violations and "
        "produces AI-generated fixes for Python, C++, Java, JS/TS, Go, and Rust."
    ),
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    logger.info("Starting Coding Standards Enforcer…")
    await init_coding_standards(app.state)
    logger.info("Startup complete")


@app.on_event("shutdown")
async def on_shutdown():
    await shutdown_coding_standards(app.state)


# Mount the cross-cutting core router (currently just /, /health) and the
# agent router under /api.
app.include_router(core_router)
app.include_router(coding_standards_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
