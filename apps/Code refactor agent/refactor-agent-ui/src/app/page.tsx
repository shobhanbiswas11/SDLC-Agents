"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import axios from "axios";

// ─────────────────────────────────────────────
// CONFIG
// ─────────────────────────────────────────────
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8002";
const POLL_INTERVAL = 3000;

// ─────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────
interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
}

// ─────────────────────────────────────────────
// GLOBAL STYLES (injected once)
// ─────────────────────────────────────────────
const GLOBAL_STYLE = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Fira+Code:wght@300;400;500;600&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:        #07090f;
    --surface:   #0d1117;
    --surface2:  #111827;
    --border:    rgba(255,255,255,0.06);
    --border2:   rgba(255,255,255,0.11);
    --accent:    #22d3ee;
    --accent2:   #06b6d4;
    --accent-dim: rgba(34,211,238,0.10);
    --accent-glow: rgba(34,211,238,0.22);
    --text:      #e2e8f0;
    --text-muted:#64748b;
    --text-dim:  #94a3b8;
    --red:       #fb7185;
    --amber:     #fbbf24;
    --blue:      #60a5fa;
    --green:     #4ade80;
    --green2:    #22c55e;
    --mono:      'Fira Code', monospace;
    --sans:      'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  }

  body { background: var(--bg); color: var(--text); font-family: var(--sans); }

  ::-webkit-scrollbar { width: 5px; height: 5px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 4px; }
  ::-webkit-scrollbar-thumb:hover { background: rgba(34,211,238,0.25); }

  @keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @keyframes blink {
    0%,100% { opacity: 1; } 50% { opacity: 0; }
  }
  @keyframes pulse-dot {
    0%,100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.35); opacity: 0.55; }
  }
  @keyframes spin-arc {
    to { transform: rotate(360deg); }
  }
  @keyframes glow-pulse {
    0%,100% { box-shadow: 0 0 10px rgba(34,211,238,0.18); }
    50%      { box-shadow: 0 0 24px rgba(34,211,238,0.4); }
  }

  .msg-enter {
    animation: fadeSlideIn 0.2s ease forwards;
  }

  .btn-primary {
    position: relative;
    overflow: hidden;
    transition: transform 0.12s ease, box-shadow 0.2s ease;
  }
  .btn-primary:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 0 24px rgba(34,211,238,0.3) !important;
  }
  .btn-primary:active:not(:disabled) {
    transform: translateY(0);
  }
  .btn-primary::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0.08), transparent);
    opacity: 0;
    transition: opacity 0.2s;
  }
  .btn-primary:hover::after { opacity: 1; }

  .input-field {
    transition: border-color 0.2s, box-shadow 0.2s;
  }
  .input-field:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px var(--accent-glow) !important;
    outline: none;
  }

  .tab-btn {
    transition: all 0.15s ease;
    cursor: pointer;
  }
  .tab-btn:hover { color: var(--accent) !important; }

  .quick-chip {
    transition: all 0.15s ease;
    cursor: pointer;
  }
  .quick-chip:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    background: var(--accent-dim) !important;
  }

  .sidebar-stat {
    border-left: 2px solid var(--border2);
    padding-left: 10px;
    margin-bottom: 14px;
    transition: border-color 0.2s;
  }
  .sidebar-stat:hover { border-color: var(--accent); }
`;

// ─────────────────────────────────────────────
// SEVERITY BADGE
// ─────────────────────────────────────────────
function SeverityBadge({ level, size = "sm" }: { level: string; size?: "sm" | "xs" }) {
  const cfg: Record<string, { color: string; glow: string; label: string }> = {
    HIGH:   { color: "#fb7185", glow: "rgba(251,113,133,0.25)", label: "HIGH" },
    MEDIUM: { color: "#fbbf24", glow: "rgba(251,191,36,0.25)",  label: "MED"  },
    LOW:    { color: "#60a5fa", glow: "rgba(96,165,250,0.25)",  label: "LOW"  },
  };
  const c = cfg[level] || cfg.LOW;
  const isXs = size === "xs";
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      gap: isXs ? 4 : 5,
      padding: isXs ? "3px 8px" : "4px 11px",
      borderRadius: 4,
      fontSize: isXs ? 11 : 12,
      fontWeight: 600,
      letterSpacing: 1,
      fontFamily: "var(--mono)",
      color: c.color,
      background: `${c.color}14`,
      border: `1px solid ${c.color}33`,
      boxShadow: `0 0 6px ${c.glow}`,
    }}>
      <span style={{ width: isXs ? 4 : 5, height: isXs ? 4 : 5, borderRadius: "50%", background: c.color, flexShrink: 0 }} />
      {c.label}
    </span>
  );
}

// ─────────────────────────────────────────────
// DIFF VIEWER
// ─────────────────────────────────────────────
function DiffViewer({ diff }: { diff: string }) {
  const [copied, setCopied] = useState(false);
  const lines = diff.split("\n");

  const copy = () => {
    navigator.clipboard.writeText(diff).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div style={{
      background: "#060a0f",
      border: "1px solid var(--border2)",
      borderRadius: 8,
      overflow: "hidden",
      margin: "10px 0",
      boxShadow: "0 6px 28px rgba(0,0,0,0.45)",
    }}>
      {/* Header */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "7px 12px",
        borderBottom: "1px solid var(--border)",
        background: "rgba(34,211,238,0.03)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ width: 2, height: 12, background: "var(--accent)", borderRadius: 1, display: "block" }} />
          <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: 1.2, color: "var(--accent)", fontFamily: "var(--mono)" }}>
            DIFF
          </span>
          <span style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--sans)" }}>
            {lines.filter(l => l.startsWith("+") && !l.startsWith("+++")).length} additions,{" "}
            {lines.filter(l => l.startsWith("-") && !l.startsWith("---")).length} deletions
          </span>
        </div>
        <button onClick={copy} style={{
          background: "none",
          border: "1px solid var(--border2)",
          color: copied ? "var(--green)" : "var(--text-muted)",
          borderRadius: 4,
          padding: "2px 8px",
          fontSize: 11,
          cursor: "pointer",
          fontFamily: "var(--mono)",
          transition: "all 0.2s",
        }}>
          {copied ? "✓ copied" : "copy"}
        </button>
      </div>
      {/* Lines */}
      <pre style={{ margin: 0, padding: "10px 0", fontSize: 13, lineHeight: 1.65, overflowX: "auto", fontFamily: "var(--mono)" }}>
        {lines.map((line, i) => {
          let color = "var(--text-dim)";
          let bg = "transparent";
          let lineNumColor = "var(--text-muted)";
          if (line.startsWith("+") && !line.startsWith("+++")) {
            color = "#4ade80"; bg = "rgba(74,222,128,0.06)"; lineNumColor = "#4ade8055";
          } else if (line.startsWith("-") && !line.startsWith("---")) {
            color = "#fb7185"; bg = "rgba(251,113,133,0.06)"; lineNumColor = "#fb718555";
          } else if (line.startsWith("@@")) {
            color = "var(--accent)"; bg = "rgba(34,211,238,0.04)";
          } else if (line.startsWith("---") || line.startsWith("+++")) {
            color = "var(--text-dim)"; bg = "rgba(255,255,255,0.02)";
          }
          return (
            <div key={i} style={{ display: "flex", backgroundColor: bg }}>
              <span style={{
                minWidth: 36,
                textAlign: "right",
                padding: "0 10px 0 4px",
                color: lineNumColor,
                fontSize: 11,
                userSelect: "none",
                borderRight: "1px solid var(--border)",
                flexShrink: 0,
              }}>
                {i + 1}
              </span>
              <span style={{ color, padding: "0 12px", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                {line || " "}
              </span>
            </div>
          );
        })}
      </pre>
    </div>
  );
}

// ─────────────────────────────────────────────
// MESSAGE CONTENT RENDERER
// ─────────────────────────────────────────────
function MessageContent({ content }: { content: string }) {
  const normalized = content
    .replace(/^\s*```(?:diff)?\s*/i, "")
    .replace(/\s*```\s*$/i, "")
    .replace(/\u00a0/g, " ");

  const hasUnifiedDiff = normalized.includes("--- a/") && normalized.includes("+++ b/");
  const fencedDiffRegex = /```diff\s*([\s\S]*?)```/gi;

  if (fencedDiffRegex.test(content)) {
    const chunks: Array<{ type: "text" | "diff"; value: string }> = [];
    let lastIndex = 0;
    fencedDiffRegex.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = fencedDiffRegex.exec(content)) !== null) {
      const before = content.slice(lastIndex, match.index).trim();
      if (before) chunks.push({ type: "text", value: before });
      chunks.push({ type: "diff", value: match[1].trim() });
      lastIndex = fencedDiffRegex.lastIndex;
    }
    const tail = content.slice(lastIndex).trim();
    if (tail) chunks.push({ type: "text", value: tail });
    return (
      <div>
        {chunks.map((chunk, i) =>
          chunk.type === "diff"
            ? <DiffViewer key={i} diff={chunk.value} />
            : <div key={i} style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{chunk.value}</div>
        )}
      </div>
    );
  }

  if (hasUnifiedDiff) return <DiffViewer diff={normalized} />;

  // Generic fenced code blocks (```lang ... ```)
  const codeFenceRegex = /```([a-zA-Z0-9_-]+)?\n([\s\S]*?)```/g;
  if (codeFenceRegex.test(content)) {
    codeFenceRegex.lastIndex = 0;
    const blocks: Array<{ type: "text" | "code"; value: string; lang?: string }> = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = codeFenceRegex.exec(content)) !== null) {
      const before = content.slice(lastIndex, match.index).trim();
      if (before) blocks.push({ type: "text", value: before });
      blocks.push({ type: "code", lang: match[1] || "text", value: match[2].trimEnd() });
      lastIndex = codeFenceRegex.lastIndex;
    }

    const tail = content.slice(lastIndex).trim();
    if (tail) blocks.push({ type: "text", value: tail });

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {blocks.map((block, idx) => {
          if (block.type === "code") {
            return (
              <div
                key={idx}
                style={{
                  border: "1px solid var(--border2)",
                  borderRadius: 8,
                  background: "#05070d",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    padding: "6px 10px",
                    fontSize: 11,
                    color: "var(--text-muted)",
                    borderBottom: "1px solid var(--border)",
                    background: "rgba(255,255,255,0.02)",
                    fontFamily: "var(--mono)",
                  }}
                >
                  {block.lang}
                </div>
                <pre
                  style={{
                    margin: 0,
                    padding: "10px 12px",
                    overflowX: "auto",
                    fontSize: 13,
                    lineHeight: 1.65,
                    fontFamily: "var(--mono)",
                    color: "#dbe3ef",
                    whiteSpace: "pre",
                  }}
                >
                  {block.value}
                </pre>
              </div>
            );
          }

          return <FormattedTextBlock key={idx} text={block.value} />;
        })}
      </div>
    );
  }

  const severityRegex = /\b(HIGH|MEDIUM|LOW)\b/g;
  if (severityRegex.test(normalized)) {
    const segments = normalized.split(/\b(HIGH|MEDIUM|LOW)\b/);
    return (
      <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", lineHeight: 1.7 }}>
        {segments.map((seg, i) =>
          ["HIGH", "MEDIUM", "LOW"].includes(seg)
            ? <SeverityBadge key={i} level={seg} />
            : <span key={i}>{seg}</span>
        )}
      </div>
    );
  }

  return <FormattedTextBlock text={normalized} />;
}

function FormattedTextBlock({ text }: { text: string }) {
  const lines = text.split("\n");
  const rendered: React.ReactNode[] = [];

  lines.forEach((rawLine, index) => {
    const line = rawLine.trimEnd();

    if (!line.trim()) {
      rendered.push(<div key={`sp-${index}`} style={{ height: 6 }} />);
      return;
    }

    if (/^---+$/.test(line.trim())) {
      rendered.push(
        <div
          key={`hr-${index}`}
          style={{
            borderTop: "1px solid var(--border2)",
            margin: "6px 0 4px",
          }}
        />
      );
      return;
    }

    if (line.startsWith("### ")) {
      rendered.push(
        <div
          key={`h3-${index}`}
          style={{
            fontSize: 14,
            fontWeight: 700,
            color: "var(--text)",
            margin: "2px 0",
          }}
        >
          {line.replace(/^###\s+/, "")}
        </div>
      );
      return;
    }

    if (line.startsWith("## ")) {
      rendered.push(
        <div
          key={`h2-${index}`}
          style={{
            fontSize: 16,
            fontWeight: 800,
            color: "var(--text)",
            margin: "3px 0",
          }}
        >
          {line.replace(/^##\s+/, "")}
        </div>
      );
      return;
    }

    if (line.startsWith("# ")) {
      rendered.push(
        <div
          key={`h1-${index}`}
          style={{
            fontSize: 18,
            fontWeight: 800,
            color: "var(--text)",
            margin: "4px 0",
          }}
        >
          {line.replace(/^#\s+/, "")}
        </div>
      );
      return;
    }

    const bullet = line.match(/^[-*]\s+(.*)$/);
    if (bullet) {
      rendered.push(
        <div key={`b-${index}`} style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
          <span style={{ color: "var(--text-muted)", marginTop: 2 }}>•</span>
          <span style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{bullet[1]}</span>
        </div>
      );
      return;
    }

    rendered.push(
      <div key={`p-${index}`} style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
        {line}
      </div>
    );
  });

  return <div style={{ lineHeight: 1.72 }}>{rendered}</div>;
}

// ─────────────────────────────────────────────
// LOADING DOTS
// ─────────────────────────────────────────────
function LoadingDots() {
  return (
    <span style={{ display: "inline-flex", gap: 4, alignItems: "center" }}>
      {[0, 1, 2].map(i => (
        <span key={i} style={{
          width: 5, height: 5, borderRadius: "50%",
          background: "var(--accent)",
          display: "block",
          animation: `pulse-dot 1.2s ${i * 0.2}s ease-in-out infinite`,
        }} />
      ))}
    </span>
  );
}

// ─────────────────────────────────────────────
// FORM FIELD
// ─────────────────────────────────────────────
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{
        display: "block",
        fontSize: 20,
        fontWeight: 500,
        letterSpacing: 0.4,
        color: "var(--text-muted)",
        marginBottom: 6,
        fontFamily: "var(--sans)",
      }}>
        {label}
      </label>
      {children}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px 14px",
  borderRadius: 6,
  border: "1px solid var(--border2)",
  background: "rgba(0,0,0,0.35)",
  color: "var(--text)",
  fontSize: 15,
  fontFamily: "var(--mono)",
  outline: "none",
  boxSizing: "border-box",
};

// ─────────────────────────────────────────────
// MAIN PAGE
// ─────────────────────────────────────────────
export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [waitingForUser, setWaitingForUser] = useState(false);
  const [workspacePath, setWorkspacePath] = useState(".");
  const [sourceType, setSourceType] = useState<"local" | "github">("local");
  const [githubUrl, setGithubUrl] = useState("");
  const [githubBranch, setGithubBranch] = useState("");
  const [sessionMeta, setSessionMeta] = useState<{ id: string; source: string; workspace: string } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const style = document.createElement("style");
    style.textContent = GLOBAL_STYLE;
    document.head.appendChild(style);
    return () => { document.head.removeChild(style); };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => () => { if (pollRef.current) clearTimeout(pollRef.current); }, []);

  // ── Start Session ─────────────────────────────────────────────────
  const startSession = useCallback(async () => {
    try {
      const res = await axios.post(`${API_BASE}/api/workflows`, {
        agent_id: "refactoring-agent",
        workspace_path: workspacePath,
        source_type: sourceType,
        github_url: sourceType === "github" ? githubUrl.trim() : null,
        github_branch: sourceType === "github" && githubBranch.trim() ? githubBranch.trim() : null,
      });
      const wfId = res.data.workflow_id;
      const resolvedWorkspace = res.data.workspace_path || workspacePath;
      const sourceLabel = (res.data.source_type || sourceType) === "github" ? "GitHub" : "Local";
      setWorkflowId(wfId);
      setIsConnected(true);
      setSessionMeta({ id: wfId, source: sourceLabel, workspace: resolvedWorkspace });
      setMessages([{
        role: "system",
        content: `Session initialized · ${wfId.slice(0, 16)}…\n\nReady to analyze. Send me a file path and I'll detect code smells, generate diffs, and apply refactors with your approval.`,
        timestamp: new Date(),
      }]);
      setTimeout(() => inputRef.current?.focus(), 100);
    } catch (err: any) {
      setMessages([{
        role: "system",
        content: `Connection failed: ${err.message}\n\nEnsure the backend API URL is reachable and Temporal is configured on the server.`,
        timestamp: new Date(),
      }]);
    }
  }, [workspacePath, sourceType, githubUrl, githubBranch]);

  // ── Poll ──────────────────────────────────────────────────────────
  const startPolling = useCallback((wfId: string) => {
    if (pollRef.current) clearTimeout(pollRef.current);
    let pollCount = 0;
    let currentInterval = POLL_INTERVAL;

    const poll = async () => {
      pollCount++;
      if (pollCount > 60) {
        setIsLoading(false);
        setMessages(prev => [...prev, {
          role: "system",
          content: "Request timed out. Try a smaller file or more specific query.",
          timestamp: new Date(),
        }]);
        return;
      }
      try {
        const res = await axios.get(`${API_BASE}/api/workflows/${wfId}/status`, { timeout: 10000 });
        const data = res.data.status;
        currentInterval = POLL_INTERVAL;

        if (data.waiting_for_user) {
          setWaitingForUser(true);
          setIsLoading(false);
          if (data.last_response) {
            setMessages(prev => {
              if (prev[prev.length - 1]?.content === data.last_response) return prev;
              return [...prev, { role: "assistant", content: data.last_response, timestamp: new Date() }];
            });
          }
          return;
        }

        if (data.status === "idle" && data.last_response) {
          setMessages(prev => {
            if (prev[prev.length - 1]?.content === data.last_response) return prev;
            return [...prev, { role: "assistant", content: data.last_response, timestamp: new Date() }];
          });
          setIsLoading(false);
          setWaitingForUser(false);
          return;
        }

        pollRef.current = setTimeout(poll, currentInterval);
      } catch {
        currentInterval = Math.min(currentInterval * 1.5, 8000);
        pollRef.current = setTimeout(poll, currentInterval);
      }
    };
    pollRef.current = setTimeout(poll, currentInterval);
  }, []);

  // ── Send ──────────────────────────────────────────────────────────
  const sendMessage = useCallback(async () => {
    if (!input.trim() || !workflowId) return;
    const userMsg = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMsg, timestamp: new Date() }]);
    setIsLoading(true);
    setWaitingForUser(false);
    try {
      await axios.post(`${API_BASE}/api/workflows/${workflowId}/messages`, { message: userMsg });
      startPolling(workflowId);
    } catch (err: any) {
      setMessages(prev => [...prev, { role: "system", content: `Send error: ${err.message}`, timestamp: new Date() }]);
      setIsLoading(false);
    }
  }, [input, workflowId, startPolling]);

  // ── Stop ──────────────────────────────────────────────────────────
  const stopSession = useCallback(async () => {
    if (!workflowId) return;
    try { await axios.delete(`${API_BASE}/api/workflows/${workflowId}`); } catch {}
    if (pollRef.current) clearTimeout(pollRef.current);
    setWorkflowId(null); setIsConnected(false);
    setIsLoading(false); setWaitingForUser(false);
    setMessages([]); setSessionMeta(null);
  }, [workflowId]);

  const quickActions = [
    { label: "Detect smells",  value: "Analyze this file for code smells" },
    { label: "HIGH issues",    value: "Show me all HIGH severity issues" },
    { label: "Best refactor",  value: "Suggest a refactor for the worst smell" },
    { label: "Run tests",      value: "Run the test suite" },
  ];

  const msgCount = messages.filter(m => m.role !== "system").length;

  // ─────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "var(--bg)", overflow: "hidden" }}>

      {/* ── Header ───────────────────────────────────── */}
      <header style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 24px",
        height: 60,
        background: "var(--surface)",
        borderBottom: "1px solid var(--border)",
        flexShrink: 0,
        position: "relative",
        zIndex: 10,
      }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
          <div style={{
            width: 30, height: 30,
            background: "var(--accent-dim)",
            border: "1px solid var(--accent)",
            borderRadius: 7,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 15,
            boxShadow: "0 0 14px var(--accent-glow)",
          }}>⚙</div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, fontFamily: "var(--sans)", color: "var(--text)", letterSpacing: -0.2 }}>
              Refactor<span style={{ color: "var(--accent)", fontWeight: 800 }}>Agent</span>
            </div>
            <div style={{ fontSize: 12, color: "var(--text-muted)", fontFamily: "var(--sans)", letterSpacing: 0.2, fontWeight: 400 }}>
              code smell detection &amp; safe refactoring
            </div>
          </div>
        </div>

        {/* Center — breadcrumb or status */}
        {sessionMeta && (
          <div style={{
            position: "absolute", left: "50%", transform: "translateX(-50%)",
            display: "flex", alignItems: "center", gap: 6,
            fontSize: 12, color: "var(--text-muted)", fontFamily: "var(--mono)",
          }}>
            <span style={{ color: "var(--accent)", opacity: 0.7 }}>{sessionMeta.source}</span>
            <span style={{ opacity: 0.3 }}>/</span>
            <span style={{ maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {sessionMeta.workspace}
            </span>
          </div>
        )}

        {/* Right */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{
              width: 6, height: 6, borderRadius: "50%",
              background: isConnected ? "var(--green)" : "var(--red)",
              display: "block",
              animation: isConnected ? "glow-pulse 2s infinite" : "none",
            }} />
            <span style={{ fontSize: 12, color: isConnected ? "var(--green)" : "var(--red)", fontFamily: "var(--sans)", fontWeight: 500 }}>
              {isConnected ? "Connected" : "Offline"}
            </span>
          </div>
          {isConnected && (
            <button onClick={stopSession} className="tab-btn" style={{
              padding: "5px 12px",
              borderRadius: 5,
              border: "1px solid rgba(251,113,133,0.25)",
              background: "rgba(251,113,133,0.06)",
              color: "var(--red)",
              cursor: "pointer",
              fontSize: 12,
              fontFamily: "var(--sans)",
              fontWeight: 500,
              letterSpacing: 0.2,
            }}>
              End Session
            </button>
          )}
        </div>
      </header>

      {/* ── Body ─────────────────────────────────────── */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

        {!isConnected ? (
          /* ════════════════════════════════════════════
             CONNECTION SCREEN
          ════════════════════════════════════════════ */
          <div style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 24,
            background: "var(--bg)",
            position: "relative",
            overflow: "hidden",
          }}>
            {/* Background grid */}
            <div style={{
              position: "absolute", inset: 0, opacity: 0.03,
              backgroundImage: `
                linear-gradient(var(--accent) 1px, transparent 1px),
                linear-gradient(90deg, var(--accent) 1px, transparent 1px)
              `,
              backgroundSize: "44px 44px",
              pointerEvents: "none",
            }} />

            {/* Card */}
            <div style={{
              background: "var(--surface)",
              border: "1px solid var(--border2)",
              borderRadius: 14,
              padding: "40px 34px",
              width: "100%",
              maxWidth: 460,
              position: "relative",
              boxShadow: "0 32px 80px rgba(0,0,0,0.55), 0 0 0 1px rgba(34,211,238,0.03)",
              animation: "fadeSlideIn 0.35s ease",
            }}>
              {/* Top accent line */}
              <div style={{
                position: "absolute", top: 0, left: 34, right: 34, height: 1,
                background: "linear-gradient(90deg, transparent, var(--accent), transparent)",
              }} />

              {/* Icon + title */}
              <div style={{ textAlign: "center", marginBottom: 30 }}>
                <div style={{
                  width: 52, height: 52,
                  margin: "0 auto 16px",
                  background: "var(--accent-dim)",
                  border: "1px solid var(--accent)",
                  borderRadius: 12,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 22,
                  boxShadow: "0 0 28px var(--accent-glow)",
                }}>⚙</div>
                <h2 style={{
                  fontFamily: "var(--sans)",
                  fontSize: 28,
                  fontWeight: 800,
                  color: "var(--text)",
                  marginBottom: 8,
                  letterSpacing: -0.5,
                }}>
                  New Session
                </h2>
                <p style={{ fontSize: 15, color: "var(--text-muted)", lineHeight: 1.6, fontFamily: "var(--sans)", fontWeight: 400 }}>
                  Point to a codebase. Detect smells. Apply safe refactors.
                </p>
              </div>

              {/* Source type tabs */}
              <div style={{
                display: "flex",
                gap: 0,
                background: "rgba(0,0,0,0.25)",
                borderRadius: 7,
                border: "1px solid var(--border)",
                padding: 3,
                marginBottom: 22,
              }}>
                {(["local", "github"] as const).map(type => (
                  <button
                    key={type}
                    onClick={() => setSourceType(type)}
                    className="tab-btn"
                    style={{
                      flex: 1,
                      padding: "8px 0",
                      borderRadius: 5,
                      border: "none",
                      background: sourceType === type ? "var(--accent-dim)" : "transparent",
                      color: sourceType === type ? "var(--accent)" : "var(--text-muted)",
                      fontSize: 13,
                      fontWeight: sourceType === type ? 600 : 400,
                      fontFamily: "var(--sans)",
                      cursor: "pointer",
                      outline: sourceType === type ? "1px solid rgba(34,211,238,0.2)" : "none",
                      transition: "all 0.15s",
                    }}
                  >
                    {type === "local" ? "📂 Local" : "🐙 GitHub"}
                  </button>
                ))}
              </div>

              {/* Fields */}
              {sourceType === "local" ? (
                <Field label="Workspace Path">
                  <input
                    type="text" value={workspacePath}
                    onChange={e => setWorkspacePath(e.target.value)}
                    placeholder="/path/to/your/project"
                    className="input-field"
                    style={inputStyle}
                  />
                </Field>
              ) : (
                <>
                  <Field label="Repository URL">
                    <input
                      type="text" value={githubUrl}
                      onChange={e => setGithubUrl(e.target.value)}
                      placeholder="https://github.com/owner/repo.git"
                      className="input-field"
                      style={inputStyle}
                    />
                  </Field>
                  <Field label="Branch (optional)">
                    <input
                      type="text" value={githubBranch}
                      onChange={e => setGithubBranch(e.target.value)}
                      placeholder="main"
                      className="input-field"
                      style={inputStyle}
                    />
                  </Field>
                </>
              )}

              {/* Start button */}
              <button
                onClick={startSession}
                disabled={sourceType === "github" && !githubUrl.trim()}
                className="btn-primary"
                style={{
                  width: "100%",
                  marginTop: 10,
                  padding: "13px 0",
                  borderRadius: 7,
                  border: "1px solid var(--accent)",
                  background: "var(--accent-dim)",
                  color: "var(--accent)",
                  fontSize: 15,
                  fontWeight: 600,
                  fontFamily: "var(--sans)",
                  letterSpacing: 0.6,
                  cursor: sourceType === "github" && !githubUrl.trim() ? "not-allowed" : "pointer",
                  opacity: sourceType === "github" && !githubUrl.trim() ? 0.4 : 1,
                  boxShadow: "0 0 20px var(--accent-glow)",
                }}
              >
                Initialize Session →
              </button>

              {/* Prerequisites note */}
              <div style={{
                marginTop: 18,
                padding: "8px 12px",
                borderRadius: 5,
                background: "rgba(0,0,0,0.2)",
                border: "1px solid var(--border)",
                fontSize: 12,
                color: "var(--text-muted)",
                fontFamily: "var(--sans)",
                letterSpacing: 0.1,
                lineHeight: 1.7,
              }}>
                <span style={{ color: "var(--amber)", fontWeight: 600 }}>Prereqs</span>
                {" · "}API: {API_BASE}
              </div>
            </div>
          </div>

        ) : (
          /* ════════════════════════════════════════════
             CHAT INTERFACE
          ════════════════════════════════════════════ */
          <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

            {/* ── Sidebar ──────────────────────────────── */}
            <aside style={{
              width: 224,
              flexShrink: 0,
              background: "var(--surface)",
              borderRight: "1px solid var(--border)",
              display: "flex",
              flexDirection: "column",
              padding: "20px 16px",
              overflowY: "auto",
            }}>
              {/* Session info */}
              <div style={{ marginBottom: 24 }}>
                <div style={{
                  fontSize: 10,
                  letterSpacing: 1.2,
                  color: "var(--text-muted)",
                  fontWeight: 600,
                  fontFamily: "var(--sans)",
                  marginBottom: 12,
                  textTransform: "uppercase",
                }}>
                  Session
                </div>
                <div className="sidebar-stat">
                  <div style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--sans)", letterSpacing: 0.3, marginBottom: 2 }}>ID</div>
                  <div style={{ fontSize: 12, color: "var(--text-dim)", fontFamily: "var(--mono)", wordBreak: "break-all" }}>
                    {sessionMeta?.id.slice(0, 20)}…
                  </div>
                </div>
                <div className="sidebar-stat">
                  <div style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--sans)", letterSpacing: 0.3, marginBottom: 2 }}>Source</div>
                  <div style={{ fontSize: 12, color: "var(--accent)", fontFamily: "var(--mono)" }}>{sessionMeta?.source}</div>
                </div>
                <div className="sidebar-stat">
                  <div style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--sans)", letterSpacing: 0.3, marginBottom: 2 }}>Workspace</div>
                  <div style={{ fontSize: 12, color: "var(--text-dim)", fontFamily: "var(--mono)", wordBreak: "break-all", lineHeight: 1.5 }}>
                    {sessionMeta?.workspace}
                  </div>
                </div>
                <div className="sidebar-stat">
                  <div style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--sans)", letterSpacing: 0.3, marginBottom: 2 }}>Messages</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "var(--text)", fontFamily: "var(--sans)" }}>
                    {msgCount}
                  </div>
                </div>
              </div>

              {/* Severity legend */}
              <div style={{ marginBottom: 24 }}>
                <div style={{
                  fontSize: 12, letterSpacing: 1.2, color: "var(--text-muted)",
                  fontWeight: 600, fontFamily: "var(--sans)", marginBottom: 12, textTransform: "uppercase",
                }}>
                  Severity
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {["HIGH", "MEDIUM", "LOW"].map(level => (
                    <div key={level} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <SeverityBadge level={level} size="xs" />
                      <span style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--sans)" }}>
                        {level === "HIGH" ? "critical fix" : level === "MEDIUM" ? "should fix" : "nice to fix"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Quick actions */}
              <div>
                <div style={{
                  fontSize: 12, letterSpacing: 1.2, color: "var(--text-muted)",
                  fontWeight: 600, fontFamily: "var(--sans)", marginBottom: 10, textTransform: "uppercase",
                }}>
                  Quick Actions
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                  {quickActions.map(({ label, value }, i) => (
                    <button
                      key={i}
                      className="quick-chip"
                      onClick={() => { setInput(value); inputRef.current?.focus(); }}
                      style={{
                        padding: "7px 10px",
                        borderRadius: 5,
                        border: "1px solid var(--border2)",
                        background: "rgba(255,255,255,0.02)",
                        color: "var(--text-muted)",
                        fontSize: 12,
                        fontFamily: "var(--sans)",
                        fontWeight: 500,
                        textAlign: "left",
                      }}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <div style={{ flex: 1 }} />

              {/* Status pill */}
              <div style={{
                padding: "8px 10px",
                borderRadius: 5,
                background: isLoading
                  ? "rgba(34,211,238,0.05)"
                  : waitingForUser
                  ? "rgba(251,191,36,0.05)"
                  : "rgba(74,222,128,0.05)",
                border: `1px solid ${isLoading ? "rgba(34,211,238,0.18)" : waitingForUser ? "rgba(251,191,36,0.18)" : "rgba(74,222,128,0.18)"}`,
                fontSize: 12,
                color: isLoading ? "var(--accent)" : waitingForUser ? "var(--amber)" : "var(--green)",
                fontFamily: "var(--sans)",
                fontWeight: 500,
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}>
                <span style={{
                  width: 5, height: 5, borderRadius: "50%",
                  background: isLoading ? "var(--accent)" : waitingForUser ? "var(--amber)" : "var(--green)",
                  animation: isLoading ? "pulse-dot 1s infinite" : "none",
                  flexShrink: 0,
                }} />
                {isLoading ? "Analyzing…" : waitingForUser ? "Awaiting reply" : "Idle"}
              </div>
            </aside>

            {/* ── Chat Panel ───────────────────────────── */}
            <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", background: "var(--bg)" }}>

              {/* Messages */}
              <div style={{
                flex: 1,
                overflowY: "auto",
                padding: "24px 28px",
                display: "flex",
                flexDirection: "column",
                gap: 4,
              }}>
                {messages.map((msg, i) => (
                  <div
                    key={i}
                    className="msg-enter"
                    style={{
                      display: "flex",
                      justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                      marginBottom: 8,
                    }}
                  >
                    {/* Avatar for non-user */}
                    {msg.role !== "user" && (
                      <div style={{
                        width: 28, height: 28,
                        flexShrink: 0,
                        borderRadius: 6,
                        background: msg.role === "assistant" ? "var(--accent-dim)" : "rgba(255,255,255,0.03)",
                        border: `1px solid ${msg.role === "assistant" ? "rgba(34,211,238,0.25)" : "var(--border)"}`,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 13,
                        marginRight: 10,
                        marginTop: 2,
                        alignSelf: "flex-start",
                      }}>
                        {msg.role === "assistant" ? "⚙" : "⚡"}
                      </div>
                    )}

                    <div style={{ maxWidth: "76%", minWidth: 0 }}>
                      {/* Role label */}
                      {msg.role !== "user" && (
                        <div style={{
                          fontSize: 11,
                          fontWeight: 600,
                          letterSpacing: 0.2,
                          color: msg.role === "assistant" ? "var(--accent)" : "var(--text-muted)",
                          marginBottom: 4,
                          fontFamily: "var(--sans)",
                        }}>
                          {msg.role === "assistant" ? "Refactor Agent" : "System"}
                        </div>
                      )}

                      {/* Bubble */}
                      <div style={{
                        padding: "12px 16px",
                        borderRadius: msg.role === "user" ? "12px 3px 12px 12px" : "3px 12px 12px 12px",
                        background: msg.role === "user"
                          ? "rgba(34,211,238,0.07)"
                          : msg.role === "assistant"
                          ? "var(--surface2)"
                          : "rgba(255,255,255,0.025)",
                        border: msg.role === "user"
                          ? "1px solid rgba(34,211,238,0.18)"
                          : msg.role === "assistant"
                          ? "1px solid var(--border2)"
                          : "1px solid var(--border)",
                        color: msg.role === "user" ? "var(--accent)" : "var(--text)",
                        fontSize: 15,
                        lineHeight: 1.7,
                        fontFamily: "var(--sans)",
                        fontWeight: 400,
                        boxShadow: msg.role === "user"
                          ? "0 4px 18px rgba(34,211,238,0.05)"
                          : "0 2px 10px rgba(0,0,0,0.18)",
                      }}>
                        <MessageContent content={msg.content} />
                      </div>

                      {/* Timestamp */}
                      <div style={{
                        fontSize: 11, color: "var(--text-muted)",
                        marginTop: 4,
                        textAlign: msg.role === "user" ? "right" : "left",
                        fontFamily: "var(--mono)",
                        letterSpacing: 0.2,
                      }}>
                        {msg.timestamp.toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                ))}

                {/* Loading bubble */}
                {isLoading && (
                  <div className="msg-enter" style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                    <div style={{
                      width: 28, height: 28, borderRadius: 6,
                      background: "var(--accent-dim)",
                      border: "1px solid rgba(34,211,238,0.25)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 15,
                    }}>⚙</div>
                    <div style={{
                      padding: "12px 16px",
                      borderRadius: "3px 12px 12px 12px",
                      background: "var(--surface2)",
                      border: "1px solid var(--border2)",
                      display: "flex", alignItems: "center", gap: 10,
                    }}>
                      <LoadingDots />
                      <span style={{ fontSize: 14, color: "var(--text-muted)", fontFamily: "var(--sans)", fontWeight: 500 }}>
                        Analyzing
                      </span>
                    </div>
                  </div>
                )}

                {/* Waiting for user banner */}
                {waitingForUser && !isLoading && (
                  <div className="msg-enter" style={{
                    margin: "4px 0 8px 38px",
                    padding: "9px 14px",
                    borderRadius: 5,
                    background: "rgba(251,191,36,0.05)",
                    border: "1px solid rgba(251,191,36,0.18)",
                    borderLeft: "3px solid var(--amber)",
                    color: "var(--amber)",
                    fontSize: 13,
                    fontFamily: "var(--sans)",
                    fontWeight: 500,
                    display: "flex", alignItems: "center", gap: 8,
                  }}>
                    <span style={{ animation: "blink 1.2s infinite" }}>▋</span>
                    Waiting for your approval — type yes / no below
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* ── Input Bar ──────────────────────────── */}
              <div style={{
                padding: "14px 28px 18px",
                borderTop: "1px solid var(--border)",
                background: "var(--surface)",
                flexShrink: 0,
              }}>
                <div style={{
                  display: "flex",
                  gap: 10,
                  background: "var(--surface2)",
                  border: `1px solid ${waitingForUser ? "rgba(251,191,36,0.3)" : "var(--border2)"}`,
                  borderRadius: 9,
                  padding: "4px 4px 4px 16px",
                  transition: "border-color 0.2s",
                  boxShadow: "0 4px 16px rgba(0,0,0,0.22)",
                }}>
                  <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && !e.shiftKey && sendMessage()}
                    placeholder={
                      waitingForUser
                        ? "yes / no / your answer…"
                        : "e.g.  analyze src/utils.py for code smells"
                    }
                    disabled={isLoading}
                    style={{
                      flex: 1,
                      background: "transparent",
                      border: "none",
                      outline: "none",
                      color: "var(--text)",
                      fontSize: 15,
                      fontFamily: "var(--sans)",
                      fontWeight: 400,
                      padding: "10px 0",
                    }}
                  />
                  <button
                    onClick={sendMessage}
                    disabled={isLoading || !input.trim()}
                    className="btn-primary"
                    style={{
                      padding: "10px 20px",
                      borderRadius: 6,
                      border: "none",
                      background: isLoading || !input.trim()
                        ? "rgba(255,255,255,0.03)"
                        : "var(--accent-dim)",
                      color: isLoading || !input.trim() ? "var(--text-muted)" : "var(--accent)",
                      fontSize: 14,
                      fontWeight: 600,
                      fontFamily: "var(--sans)",
                      letterSpacing: 0.3,
                      cursor: isLoading || !input.trim() ? "not-allowed" : "pointer",
                      outline: isLoading || !input.trim() ? "none" : "1px solid rgba(34,211,238,0.18)",
                      transition: "all 0.15s",
                      boxShadow: isLoading || !input.trim() ? "none" : "0 0 14px var(--accent-glow)",
                    }}
                  >
                    {waitingForUser ? "Reply" : "Send"} ↵
                  </button>
                </div>

                {/* Bottom hints */}
                <div style={{
                  marginTop: 8,
                  display: "flex",
                  gap: 6,
                  flexWrap: "wrap",
                }}>
                  {quickActions.map(({ label, value }, i) => (
                    <button
                      key={i}
                      className="quick-chip"
                      onClick={() => { setInput(value); inputRef.current?.focus(); }}
                      style={{
                        padding: "3px 9px",
                        borderRadius: 4,
                        border: "1px solid var(--border)",
                        background: "transparent",
                        color: "var(--text-muted)",
                        fontSize: 12,
                        fontFamily: "var(--sans)",
                        fontWeight: 500,
                        letterSpacing: 0.1,
                      }}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
