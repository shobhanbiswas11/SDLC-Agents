"""
Log Streamer Utility
---------------------
Publishes structured messages to Redis for WebSocket streaming.
Supports typed messages: log, approval_request, status_update.
"""

import redis
import json
import os
from app.services.log_service import save_log

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def publish_log(task_id: str, message: str, step: str = "info"):
    """Publish a log message to the WebSocket channel."""
    payload = {
        "type": "log",
        "task_id": task_id,
        "message": message,
        "step": step,
    }

    # Real-time stream
    r.publish(f"logs:{task_id}", json.dumps(payload))

    # Persist to DB
    save_log(task_id, message)


def publish_approval_request(task_id: str, fix_details: dict):
    """Publish an approval request to the WebSocket channel."""
    payload = {
        "type": "approval_request",
        "task_id": task_id,
        "fix_details": fix_details,
    }

    r.publish(f"logs:{task_id}", json.dumps(payload))


def publish_status(task_id: str, status: str, message: str = ""):
    """Publish a status update to the WebSocket channel."""
    payload = {
        "type": "status_update",
        "task_id": task_id,
        "status": status,
        "message": message,
    }

    r.publish(f"logs:{task_id}", json.dumps(payload))