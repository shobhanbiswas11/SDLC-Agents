"""
WebSocket Routes
-----------------
Streams real-time build logs and HITL approval requests to the frontend.
Supports typed messages: log, approval_request, status_update, approval_response.
"""

from fastapi import APIRouter, WebSocket
import redis
import json
import asyncio
import os

router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


@router.websocket("/ws/logs/{task_id}")
async def websocket_logs(websocket: WebSocket, task_id: str):
    print(f"WS CONNECT: {task_id}")

    await websocket.accept()

    pubsub = r.pubsub()
    pubsub.subscribe(f"logs:{task_id}")

    try:
        while True:
            message = pubsub.get_message(ignore_subscribe_messages=True)

            if message:
                data = json.loads(message["data"])

                print(f"WS SEND [{data.get('type', 'unknown')}]: {data.get('message', '')[:80]}")

                # Send structured JSON to frontend
                await websocket.send_text(json.dumps(data))

            await asyncio.sleep(0.1)

    except Exception as e:
        print("WS ERROR:", e)

    finally:
        pubsub.unsubscribe(f"logs:{task_id}")
        try:
            await websocket.close()
        except Exception:
            pass