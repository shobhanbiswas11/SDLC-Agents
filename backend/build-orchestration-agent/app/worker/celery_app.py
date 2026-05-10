"""
Celery Application Configuration
----------------------------------
Uses Redis as broker and backend. URL from environment variables.
"""

import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "build_agent",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

# Register tasks
celery_app.autodiscover_tasks(["app.worker"])