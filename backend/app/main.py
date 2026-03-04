from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.iac_agent import create_agent
from datetime import datetime, timezone
from typing import List, Optional
import uuid, time, re

app = FastAPI(title="IaC Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = create_agent()
run_history = []

class Message(BaseModel):
    role: str
    content: str

class IaCRequest(BaseModel):
    prompt: str
    conversation_history: Optional[List[Message]] = []

def detect_status(output: str) -> str:
    match = re.search(r'status[:\*\s]+\**\s*(PASS|FAIL)', output, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return 'UNKNOWN'

def has_code_blocks(text: str) -> bool:
    """Check if text already contains markdown code blocks."""
    return "```" in text

def extract_code_blocks(text: str) -> str:
    code_blocks = []
    pattern = r"```([a-zA-Z0-9_-]*)\n([\s\S]*?)```"
    for match in re.finditer(pattern, text):
        language = match.group(1) or 'plaintext'
        code = match.group(2).strip()
        code_blocks.append(f"```{language}\n{code}\n```")
    return "\n\n".join(code_blocks)

def build_context_prompt(prompt: str, conversation_history: List[Message]) -> str:
    if not conversation_history:
        return f"""
        You are an IaC agent. Based on the user's request:
        1. Determine what infrastructure or configuration is needed.
        2. Use generate_iac to generate the appropriate IaC code (Terraform, Kubernetes YAML, Ansible, etc).
        3. Use check_policies to validate the generated code against best practices and security policies.
        4. Return a final answer with: what was generated, policy STATUS (PASS/FAIL), violations, and recommendations.

        User Request: {prompt}
        """

    history_text = ""
    for msg in conversation_history[-6:]:
        role = "User" if msg.role == "user" else "Assistant"
        history_text += f"{role}: {msg.content}\n\n"

    return f"""
        You are an IaC agent with memory of the current conversation.

        Previous conversation:
        {history_text}

        Based on the conversation history above and the new user request:
        1. If the user is asking to modify previously generated IaC, use the context to understand what was generated before and modify it accordingly.
        2. If it's a new request, determine what infrastructure is needed and use generate_iac.
        3. Always use check_policies to validate the generated or modified code.
        4. Return a final answer with: what was generated/modified, policy STATUS (PASS/FAIL), violations, and recommendations.

        New User Request: {prompt}
        """

@app.post("/run-agent")
def run_agent(request: IaCRequest):
    start = time.time()

    result = agent.invoke({
        "input": build_context_prompt(request.prompt, request.conversation_history)
    })

    duration_ms = int((time.time() - start) * 1000)
    output = result.get("output", "")
    steps = [
        {"tool": s[0].tool, "input": s[0].tool_input, "output": s[1]}
        for s in result.get("intermediate_steps", [])
    ]

    # Only append code blocks if output doesn't already contain them
    final_result = output
    if not has_code_blocks(output):
        code_blocks = ""
        for step in steps:
            if step["tool"] == "generate_iac":
                extracted = extract_code_blocks(step["output"])
                if extracted:
                    code_blocks = extracted
                    break
        if code_blocks:
            final_result = f"{output}\n\n{code_blocks}"

    run = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "prompt": request.prompt,
        "result": final_result,
        "steps": steps,
        "total_steps": len(steps),
        "status": detect_status(final_result),
        "duration_ms": duration_ms,
    }
    run_history.insert(0, run)
    return run

@app.post("/fix-agent")
def fix_agent(request: IaCRequest):
    start = time.time()

    result = agent.invoke({
        "input": f"""
        The user wants to fix their IaC based on these violations and recommendations:
        {request.prompt}

        Steps:
        1. Use fix_iac tool with the violations to regenerate a fixed version.
        2. Use check_policies to validate the fixed code.
        3. Return a final answer with the fixed code summary and new policy STATUS (PASS/FAIL).
        """
    })

    duration_ms = int((time.time() - start) * 1000)
    output = result.get("output", "")
    steps = [
        {"tool": s[0].tool, "input": s[0].tool_input, "output": s[1]}
        for s in result.get("intermediate_steps", [])
    ]

    # Only append code blocks if output doesn't already contain them
    final_result = output
    if not has_code_blocks(output):
        code_blocks = ""
        for step in steps:
            if step["tool"] == "fix_iac":
                extracted = extract_code_blocks(step["output"])
                if extracted:
                    code_blocks = extracted
                    break
        if code_blocks:
            final_result = f"{output}\n\n{code_blocks}"

    run = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "prompt": f"[FIX] {request.prompt[:100]}",
        "result": final_result,
        "steps": steps,
        "total_steps": len(steps),
        "status": detect_status(final_result),
        "duration_ms": duration_ms,
    }
    run_history.insert(0, run)
    return run

@app.get("/history")
def get_history():
    return run_history

@app.delete("/history/{run_id}")
def delete_run(run_id: str):
    global run_history
    run_history = [r for r in run_history if r["id"] != run_id]
    return {"message": f"Run {run_id} deleted"}

@app.delete("/history")
def clear_history():
    global run_history
    run_history.clear()
    return {"message": "History cleared"}