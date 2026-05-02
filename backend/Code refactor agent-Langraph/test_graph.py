import sys
import asyncio
from graph import graph

state = {
    "history": [{"role": "user", "content": "hello"}],
    "workspace_path": ".",
    "last_response": "",
    "status": "thinking",
    "navigated_file": "",
    "created_files": [],
    "pending_tool_calls": [],
    "context_gathered": False,
    "verification_passed": False,
    "verification_attempts": 0,
}
config = {"configurable": {"thread_id": "test_123"}}

async def test():
    try:
        await graph.ainvoke(state, config=config)
        print('Success!')
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test())
