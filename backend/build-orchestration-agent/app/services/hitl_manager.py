"""
Human-in-the-Loop Manager
--------------------------
Coordinates approval flow between the Celery worker and the user.

Flow:
  1. Worker calls `request_approval(task_id, fix_details)`.
  2. Fix details are published to the WebSocket channel AND stored in Redis.
  3. Worker polls Redis waiting for user response.
  4. User responds via API → `submit_response(task_id, decision)`.
  5. Worker picks up the response and proceeds.
"""

import redis
import json
import time
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# Default timeout: 5 minutes
DEFAULT_TIMEOUT = 300


# ─── Request Approval ────────────────────────────────────────
def request_approval(task_id: str, fix_details: dict, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """
    Stores an approval request in Redis and publishes it to the WS channel.
    Then polls Redis until the user responds or timeout is reached.

    Returns:
        {"decision": "approve|reject|modify|timeout", "modified_command": "..." or None}
    """
    request_key = f"hitl:{task_id}:request"
    response_key = f"hitl:{task_id}:response"

    # Clear any stale data
    r.delete(request_key, response_key)

    # Store the request
    request_payload = {
        "task_id": task_id,
        "fix_details": fix_details,
        "status": "pending",
        "timestamp": time.time(),
    }
    r.set(request_key, json.dumps(request_payload), ex=timeout + 60)

    # Publish to WebSocket channel (the WS handler will forward this)
    ws_payload = {
        "type": "approval_request",
        "task_id": task_id,
        "fix_details": fix_details,
    }
    r.publish(f"logs:{task_id}", json.dumps(ws_payload))

    # Poll for response
    start = time.time()
    while time.time() - start < timeout:
        response = r.get(response_key)

        if response:
            r.delete(request_key, response_key)
            return json.loads(response)

        time.sleep(1)

    # Timeout → auto-reject
    r.delete(request_key, response_key)
    return {"decision": "timeout", "modified_command": None}


# ─── Submit Response (called by API) ─────────────────────────
def submit_response(task_id: str, decision: str, modified_command: str = None):
    """
    Stores the user's decision in Redis so the polling worker picks it up.
    """
    response_key = f"hitl:{task_id}:response"

    response_payload = {
        "decision": decision,
        "modified_command": modified_command,
        "timestamp": time.time(),
    }

    r.set(response_key, json.dumps(response_payload), ex=600)

    # Also publish a confirmation to the WS channel
    r.publish(f"logs:{task_id}", json.dumps({
        "type": "approval_response",
        "task_id": task_id,
        "decision": decision,
    }))


# ─── Get Pending Approval ────────────────────────────────────
def get_pending_approval(task_id: str) -> dict:
    """
    Returns the current pending approval request for a task, or None.
    """
    request_key = f"hitl:{task_id}:request"
    data = r.get(request_key)

    if data:
        return json.loads(data)

    return None
