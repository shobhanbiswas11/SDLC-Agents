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

export interface SessionStatus {
  status: string;
  last_response: string;
  waiting_for_user: boolean;
  interrupted_question?: string;
  navigated_file?: string;
  created_files?: string[];
  message_count?: number;
  error?: string;
}

// ── Stream Chat (primary path — GitHub repo + SSE) ────────────────────────────

export async function streamChat(
  repo: string,
  accessToken: string,
  message: string,
  onEvent: (ev: StreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${BASE}/stream-chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo, access_token: accessToken, message }),
    signal,
  });

  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || `HTTP ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
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
  } catch (err) {
    // Ignore abort errors — these are intentional cancellations
    if (err instanceof Error && err.name === "AbortError") return;
    throw err;
  } finally {
    reader.releaseLock();
  }
}


// ── LangGraph Session ─────────────────────────────────────────────────────────

export async function startSession(
  agentId = "reviewer",
  workspacePath = "."
): Promise<string> {
  const res = await fetch(`${BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent_id: agentId, workspace_path: workspacePath }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data.session_id as string;
}

export async function sendMessage(
  sessionId: string,
  message: string
): Promise<void> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}

export async function answerQuestion(
  sessionId: string,
  answer: string
): Promise<void> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}

export async function pollStatus(
  sessionId: string
): Promise<SessionStatus> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/status`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json() as SessionStatus;
}

export async function stopSession(sessionId: string): Promise<void> {
  await fetch(`${BASE}/sessions/${sessionId}`, { method: "DELETE" });
}

// ── GitHub Push ───────────────────────────────────────────────────────────────

export interface PushResult {
  success: boolean;
  url?: string;
  error?: string;
}

/**
 * Pushes markdown content to a file in a GitHub repo using the GitHub Contents API.
 * Works directly from the browser — no backend required.
 * @param repo  "owner/repo" string
 * @param token GitHub personal access token with repo scope
 * @param path  File path in the repo, e.g. "README.md" or "docs/api.md"
 * @param content  Markdown string to write
 * @param commitMessage  Git commit message
 */
export async function pushToGitHub(
  repo: string,
  token: string,
  path: string,
  content: string,
  commitMessage: string
): Promise<PushResult> {
  const apiBase = `https://api.github.com/repos/${repo}/contents/${path}`;

  // 1. Try to get the current SHA of the file (needed if updating an existing file)
  let sha: string | undefined;
  try {
    const getRes = await fetch(apiBase, {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
      },
    });
    if (getRes.ok) {
      const data = await getRes.json();
      sha = data.sha as string;
    }
  } catch {
    // File likely doesn't exist yet — that's fine
  }

  // 2. Base64-encode the content (GitHub API requires this)
  const encoded = btoa(unescape(encodeURIComponent(content)));

  // 3. PUT the file
  const body: Record<string, unknown> = {
    message: commitMessage,
    content: encoded,
  };
  if (sha) body.sha = sha; // required when updating an existing file

  try {
    const putRes = await fetch(apiBase, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!putRes.ok) {
      const err = await putRes.json().catch(() => ({ message: putRes.statusText }));
      return { success: false, error: err.message ?? `HTTP ${putRes.status}` };
    }

    const result = await putRes.json();
    const htmlUrl: string =
      result?.content?.html_url ?? `https://github.com/${repo}/blob/main/${path}`;
    return { success: true, url: htmlUrl };
  } catch (e) {
    return { success: false, error: e instanceof Error ? e.message : String(e) };
  }
}
