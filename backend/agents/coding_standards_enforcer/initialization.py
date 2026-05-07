"""
Startup hooks for the Coding Standards Enforcer agent.

Currently: warm the LLM service so the first user request doesn't pay the
authentication latency.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


async def initialize(app_state) -> None:
    logger.info("Initialising Coding Standards Enforcer agent…")

    # Ensure state/log directories exist (used for future audit history).
    for d in ["state", "logs"]:
        os.makedirs(d, exist_ok=True)

    try:
        from core.services.llm_service import get_llm_service

        svc = get_llm_service()
        svc.reinitialise()
        app_state.llm_available = svc.available()
        logger.info("LLM available: %s", app_state.llm_available)
    except Exception as exc:
        logger.warning("LLM init error: %s", exc)
        app_state.llm_available = False

    logger.info("Coding Standards Enforcer agent initialised ✓")


async def shutdown(app_state) -> None:
    logger.info("Coding Standards Enforcer agent shutting down…")
