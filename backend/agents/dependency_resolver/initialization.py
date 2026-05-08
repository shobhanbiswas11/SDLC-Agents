"""
Startup initialisation for the Dependency Resolver agent.
Warms caches, pre-fetches OSV feed snapshot, and validates search provider.
"""
from __future__ import annotations
import logging
import os

logger = logging.getLogger(__name__)


async def initialize(app_state) -> None:
    logger.info("Initialising Dependency Resolver agent…")

    # Ensure state directories exist
    for d in ["state", "state/hitl", "logs"]:
        os.makedirs(d, exist_ok=True)

    # Warm registry caches (fire-and-forget ping)
    try:
        from agents.dependency_resolver.registry.pypi import PyPIRegistry
        from agents.dependency_resolver.registry.npm import NPMRegistry
        app_state.pypi_registry = PyPIRegistry()
        app_state.npm_registry  = NPMRegistry()
        logger.info("Registry clients initialised")
    except Exception as exc:
        logger.warning(f"Registry init warning: {exc}")

    # Validate search provider
    search_provider = os.getenv("SEARCH_PROVIDER", "none")
    app_state.search_available = search_provider != "none"
    logger.info(f"Search provider: {search_provider}")

    # Validate LLM — reinitialise in case the singleton was built before .env loaded
    try:
        from dotenv import load_dotenv
        import pathlib
        _env = pathlib.Path(__file__).resolve().parents[2] / ".env"
        if _env.exists():
            load_dotenv(_env, override=False)
    except ImportError:
        pass

    try:
        from core.llm import get_llm_service
        svc = get_llm_service()
        svc.reinitialise()          # no-op if already configured; retries if first build failed
        app_state.llm_available = svc.available()
        logger.info(f"LLM available: {app_state.llm_available}")
    except Exception as exc:
        logger.warning(f"LLM init error: {exc}")
        app_state.llm_available = False

    logger.info("Dependency Resolver agent initialised ✓")


async def shutdown(app_state) -> None:
    logger.info("Dependency Resolver agent shutting down…")
