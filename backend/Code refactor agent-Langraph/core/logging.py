"""
core/logging.py — Centralised logging configuration for the Code Refactor Agent.

Usage:
    from core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("Something happened")
"""

import logging
import os
import sys
from pathlib import Path


def _configure_root_logger() -> None:
    """Set up root logger once at import time."""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    log_file = os.getenv("LOG_FILE", "")
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(level=level, format=fmt, datefmt=date_fmt, handlers=handlers, force=True)


_configure_root_logger()


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)
