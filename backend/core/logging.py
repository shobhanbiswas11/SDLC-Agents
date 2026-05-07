"""Logging configuration — call configure_logging() once at startup."""
from __future__ import annotations

import logging
import os


def configure_logging(level: str | None = None) -> None:
    level = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
