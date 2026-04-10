/**
 * api.ts — Typed client for the DocuGenius backend (FastAPI on port 8001).
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8002";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface StreamEvent {
  type: "status" | "chunk" | "done" | "error";
  message?: string;
  content?: string;
  context_files?: string[];
}

export interface WorkflowStatus {
  status: string;
  last_response: string;
  waiting_for_user: boolean;
  message_count: number;
  error?: string;
}

// ── Stream Chat (primary path — GitHub repo + SSE) ────────────────────────────

export async function streamChat(
  repo: string,
  accessToken: string,
  message: string,
  onEvent: (ev: StreamEvent) => void
): Promise<void> {
  const res = await fetch(`${BASE}/stream-chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo, access_token: accessToken, message }),
  });

  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || `HTTP ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const ev: StreamEvent = JSON.parse(line.slice(6));
          onEvent(ev);
        } catch {
          /* skip malformed */
        }
      }
    }
  }
}

// ── Temporal Workflow Session ─────────────────────────────────────────────────

export async function startWorkflow(
  agentId = "reviewer",
  workspacePath = "."
): Promise<string> {
  const res = await fetch(`${BASE}/api/workflows`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent_id: agentId, workspace_path: workspacePath }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data.workflow_id as string;
}

export async function sendMessage(
  workflowId: string,
  message: string
): Promise<void> {
  const res = await fetch(`${BASE}/api/workflows/${workflowId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}

export async function pollStatus(
  workflowId: string
): Promise<WorkflowStatus> {
  const res = await fetch(`${BASE}/api/workflows/${workflowId}/status`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data.status as WorkflowStatus;
}

export async function stopWorkflow(workflowId: string): Promise<void> {
  await fetch(`${BASE}/api/workflows/${workflowId}`, { method: "DELETE" });
}
