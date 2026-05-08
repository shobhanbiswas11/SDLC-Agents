"""
FastAPI application entry point — GENAICOE Dependency Resolver Agent.
"""
from __future__ import annotations
import logging
import os
import pathlib

# ── Load .env BEFORE any other import reads os.getenv() ──────────────────────
try:
    from dotenv import load_dotenv
    _env_file = pathlib.Path(__file__).parent / ".env"
    if _env_file.exists():
        load_dotenv(_env_file, override=False)
        logging.getLogger(__name__).debug("Loaded .env from %s", _env_file)
except ImportError:
    pass  # rely on shell environment

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agents.dependency_resolver import agent_router
from agents.dependency_resolver.initialization import initialize, shutdown

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GENAICOE — Dependency Resolver Agent",
    description=(
        "Resolves package dependency conflicts deterministically, audits for CVEs, "
        "and provides a real-time Human-in-the-Loop chat interface."
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
    logger.info("Starting GENAICOE Dependency Resolver…")
    await initialize(app.state)
    logger.info("Startup complete")


@app.on_event("shutdown")
async def on_shutdown():
    await shutdown(app.state)


app.include_router(agent_router, prefix="/api")


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "GENAICOE Dependency Resolver",
        "version": "0.2.0",
        "status":  "running",
        "docs":    "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, ws_max_size=65536)
