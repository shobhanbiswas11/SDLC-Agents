import { useState, useEffect, useRef } from "react";
import Markdown from "react-markdown";
import ApprovalModal from "./components/ApprovalModal";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

/* ── Message Types ────────────────────────────────────────── */
const MSG = {
  AGENT: "agent",
  USER: "user",
  PIPELINE: "pipeline",
  ERROR_CARD: "error_card",
  FIX_CARD: "fix_card",
  SYSTEM: "system",
};

/* ── Agent Avatar ─────────────────────────────────────────── */
function AgentAvatar() {
  return (
    <div className="avatar agent-avatar">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 2L2 7l10 5 10-5-10-5z" />
        <path d="M2 17l10 5 10-5" />
        <path d="M2 12l10 5 10-5" />
      </svg>
    </div>
  );
}

/* ── Chat Bubble ──────────────────────────────────────────── */
function ChatMessage({ msg }) {
  if (msg.type === MSG.USER) {
    return (
      <div className="chat-row user-row">
        <div className="bubble user-bubble">
          <div className="bubble-header">
            <span className="bubble-sender">You</span>
          </div>
          <div className="bubble-body">{msg.text}</div>
          {msg.meta && <div className="bubble-meta">{msg.meta}</div>}
        </div>
        <div className="avatar user-avatar">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
          </svg>
        </div>
      </div>
    );
  }

  if (msg.type === MSG.PIPELINE) {
    return (
      <div className="chat-row agent-row">
        <AgentAvatar />
        <div className="bubble pipeline-bubble">
          <div className="pipeline-indicator">
            <span className={`pipeline-dot ${msg.active ? "dot-active" : msg.done ? "dot-done" : ""}`}></span>
            <span className="pipeline-label">{msg.text}</span>
          </div>
        </div>
      </div>
    );
  }

  if (msg.type === MSG.ERROR_CARD) {
    return (
      <div className="chat-row agent-row">
        <AgentAvatar />
        <div className="bubble card-bubble error-card">
          <div className="card-header error-header">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z"/>
            </svg>
            <span>Build Error Detected</span>
          </div>
          <div className="card-body">
            <div className="card-field">
              <span className="field-label">Type</span>
              <span className="field-value error-value">{msg.errorType}</span>
            </div>
            <div className="card-field">
              <span className="field-label">Confidence</span>
              <span className="field-value">{Math.round((msg.confidence || 0) * 100)}%</span>
            </div>
            {msg.target && (
              <div className="card-field">
                <span className="field-label">Target</span>
                <span className="field-value mono">{msg.target}</span>
              </div>
            )}
            <div className="card-field full">
              <span className="field-label">Message</span>
              <span className="field-value mono">{msg.message}</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (msg.type === MSG.FIX_CARD) {
    return (
      <div className="chat-row agent-row">
        <AgentAvatar />
        <div className="bubble card-bubble fix-card">
          <div className="card-header fix-header">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M11.251.068a.5.5 0 0 1 .227.58L9.677 6.5H13a.5.5 0 0 1 .364.843l-8 8.5a.5.5 0 0 1-.842-.49L6.323 9.5H3a.5.5 0 0 1-.364-.843l8-8.5a.5.5 0 0 1 .615-.089z"/>
            </svg>
            <span>Proposed Fix</span>
            <span className={`risk-tag risk-${msg.risk}`}>{(msg.risk || "unknown").toUpperCase()}</span>
          </div>
          <div className="card-body">
            {msg.explanation && <p className="fix-explanation">{msg.explanation}</p>}
            <div className="command-preview">
              <code>{msg.command}</code>
            </div>
            <div className="card-field">
              <span className="field-label">Confidence</span>
              <span className="field-value">{Math.round((msg.confidence || 0) * 100)}%</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (msg.type === MSG.SYSTEM) {
    return (
      <div className="chat-row system-row">
        <div className="system-msg"><Markdown>{msg.text}</Markdown></div>
      </div>
    );
  }

  // Default: agent message
  return (
    <div className="chat-row agent-row">
      <AgentAvatar />
      <div className={`bubble agent-bubble ${msg.step === "error" ? "bubble-error" : ""} ${msg.step === "success" ? "bubble-success" : ""}`}>
        <div className="bubble-body"><Markdown>{msg.text}</Markdown></div>
      </div>
    </div>
  );
}

/* ── Main App ─────────────────────────────────────────────── */
function App() {
  const [messages, setMessages] = useState([]);
  const [status, setStatus] = useState("idle");
  const [taskId, setTaskId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [pendingApproval, setPendingApproval] = useState(null);

  // Chat input
  const [input, setInput] = useState("");

  // History drawer
  const [showHistory, setShowHistory] = useState(false);
  const [builds, setBuilds] = useState([]);

  const wsRef = useRef(null);
  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    fetchBuilds();
  }, []);

  const addMessage = (msg) => {
    setMessages((prev) => [...prev, { ...msg, id: Date.now() + Math.random() }]);
  };

  /* ── Submit (chat-style) ──────────────────────────────── */
  const handleSubmit = async (e) => {
    e.preventDefault();
    const msg = input.trim();
    if (!msg || loading) return;

    // Show user message
    addMessage({ type: MSG.USER, text: msg });
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg }),
      });

      const data = await res.json();

      if (!res.ok) {
        let errorMsg = "Something went wrong";
        if (data.detail) {
          if (typeof data.detail === "string") errorMsg = data.detail;
          else if (Array.isArray(data.detail))
            errorMsg = data.detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
          else errorMsg = JSON.stringify(data.detail);
        }
        addMessage({ type: MSG.AGENT, text: errorMsg, step: "error" });
        setLoading(false);
        return;
      }

      // Show the agent's reply
      addMessage({ type: MSG.AGENT, text: data.reply });

      // If a build was triggered, connect WebSocket and poll
      if (data.task_id) {
        setTaskId(data.task_id);
        setStatus("running");
        setPendingApproval(null);
        connectWebSocket(data.task_id);
        pollStatus(data.task_id);
        fetchBuilds();
      } else {
        setLoading(false);
      }
    } catch (err) {
      addMessage({ type: MSG.AGENT, text: `Connection error: ${err.message}`, step: "error" });
      setLoading(false);
    }
  };

  /* ── Handle Enter key ─────────────────────────────────── */
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  /* ── WebSocket ────────────────────────────────────────── */
  const connectWebSocket = (tid) => {
    if (wsRef.current) wsRef.current.close();

    const wsUrl = API_BASE.replace(/^http/, "ws");
    const ws = new WebSocket(`${wsUrl}/ws/logs/${tid}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        const msgType = parsed.type || "log";

        switch (msgType) {
          case "log":
            handleLogMessage(parsed);
            break;
          case "approval_request":
            setPendingApproval(parsed);
            addMessage({
              type: MSG.AGENT,
              text: "I need your approval before applying this fix. Please review the details.",
              step: "approval",
            });
            break;
          case "status_update":
            handleStatusUpdate(parsed);
            break;
          case "approval_response":
            setPendingApproval(null);
            addMessage({
              type: MSG.SYSTEM,
              text: `Decision: ${parsed.decision}`,
            });
            break;
          default:
            addMessage({ type: MSG.AGENT, text: event.data });
        }
      } catch {
        addMessage({ type: MSG.AGENT, text: event.data });
      }
    };

    ws.onclose = () => console.log("WebSocket closed");
  };

  const handleLogMessage = (parsed) => {
    const step = parsed.step || "info";
    const message = parsed.message || "";

    // Convert analysis results into rich cards
    if (step === "analysis" && message.startsWith("Error Type:")) {
      return; // Skip raw — we'll show the card from status_update
    }

    if (step === "reasoning" && message.startsWith("Suggested Fix:")) {
      return; // Skip raw — we'll show the card
    }

    // Skip duplicate iteration headers
    if (message.startsWith("Iteration ")) {
      addMessage({ type: MSG.SYSTEM, text: message });
      return;
    }

    addMessage({ type: MSG.AGENT, text: message, step });
  };

  const handleStatusUpdate = (parsed) => {
    const s = parsed.status;
    const msg = parsed.message || "";

    const pipelineSteps = {
      building: "Building project...",
      analyzing: "Analyzing build logs...",
      reasoning: "Reasoning about the fix...",
      awaiting_approval: "Waiting for your approval...",
      applying_fix: "Applying the approved fix...",
      rebuilding: "Re-running the build...",
      success: "Build completed successfully!",
      failed: msg || "Build failed.",
      timeout: "Approval timed out.",
      rejected: "Fix was rejected.",
    };

    const text = pipelineSteps[s] || msg || s;
    const isDone = ["success"].includes(s);
    const isError = ["failed", "timeout", "rejected"].includes(s);
    const isActive = !isDone && !isError;

    addMessage({
      type: MSG.PIPELINE,
      text,
      active: isActive,
      done: isDone,
    });

    if (isDone) setStatus("success");
    if (isError) setStatus("failed");
  };

  /* ── Poll ─────────────────────────────────────────────── */
  const pollStatus = (tid) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/status/${tid}`);
        const data = await res.json();

        if (data.status === "SUCCESS" || data.status === "FAILURE") {
          clearInterval(interval);
          setLoading(false);
          setStatus(data.status === "SUCCESS" ? "success" : "failed");
          fetchBuilds();
        }
      } catch (err) {
        console.error("Poll error:", err);
      }
    }, 2000);
  };

  /* ── History ──────────────────────────────────────────── */
  const fetchBuilds = async () => {
    try {
      const res = await fetch(`${API_BASE}/builds`);
      const data = await res.json();
      setBuilds(Array.isArray(data) ? data : []);
    } catch { /* ignore */ }
  };

  const loadBuildLogs = async (build) => {
    try {
      const res = await fetch(`${API_BASE}/logs/${build.id}`);
      const data = await res.json();

      setMessages([]);
      setStatus("idle");

      addMessage({
        type: MSG.SYSTEM,
        text: `Viewing build ${build.id.substring(0, 8)}... (${build.status})`,
      });

      data.forEach((l) => {
        addMessage({ type: MSG.AGENT, text: l.message });
      });

      setShowHistory(false);
    } catch { /* ignore */ }
  };

  const handleApprovalClose = () => setPendingApproval(null);

  const canSubmit = input.trim().length > 0;

  /* ── Render ────────────────────────────────────────────── */
  return (
    <div className="app-shell">
      {/* HITL Modal Overlay */}
      {pendingApproval && (
        <ApprovalModal approval={pendingApproval} taskId={taskId} onClose={handleApprovalClose} />
      )}

      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <div className="logo">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <div>
            <h1 className="header-title">Build Agent</h1>
            <p className="header-subtitle">AI-powered build orchestration assistant</p>
          </div>
        </div>
        <div className="header-right">
          <div className={`status-pill status-${status}`}>
            <span className="status-dot"></span>
            {status === "idle" ? "Ready" : status === "running" ? "Running" : status === "success" ? "Success" : "Failed"}
          </div>
          <button className="history-btn" onClick={() => setShowHistory(!showHistory)}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            History
          </button>
        </div>
      </header>

      <div className="main-area">
        {/* History Drawer */}
        {showHistory && (
          <aside className="history-drawer">
            <div className="drawer-header">
              <h2>Build History</h2>
              <button className="drawer-close" onClick={() => setShowHistory(false)}>×</button>
            </div>
            <div className="drawer-body">
              {builds.length === 0 && <p className="empty-msg">No builds yet</p>}
              {builds.map((b) => (
                <button key={b.id} className="history-item" onClick={() => loadBuildLogs(b)}>
                  <span className={`hi-status hi-${(b.status || "").toLowerCase()}`}>{b.status}</span>
                  <span className="hi-type">{b.project_type || "Unknown"}</span>
                  <span className="hi-id">{b.id?.substring(0, 10)}...</span>
                  {b.github_url && <span className="hi-url">{b.github_url.replace("https://github.com/", "")}</span>}
                  {b.created_at && <span className="hi-time">{new Date(b.created_at).toLocaleString()}</span>}
                </button>
              ))}
            </div>
          </aside>
        )}

        {/* Chat Area */}
        <div className="chat-area">
          {/* Welcome state */}
          {messages.length === 0 && (
            <div className="welcome">
              <div className="welcome-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" />
                  <path d="M2 17l10 5 10-5" />
                  <path d="M2 12l10 5 10-5" />
                </svg>
              </div>
              <h2 className="welcome-title">Build Agent</h2>
              <p className="welcome-desc">
                Tell me what you'd like to build. Paste a GitHub URL, give me a local path,
                or just ask a question — I'll take it from there.
              </p>
              <div className="welcome-features">
                <div className="feature">
                  <span className="feature-icon">🔍</span>
                  <span>Auto-detect project type</span>
                </div>
                <div className="feature">
                  <span className="feature-icon">🧠</span>
                  <span>AI-powered error diagnosis</span>
                </div>
                <div className="feature">
                  <span className="feature-icon">👤</span>
                  <span>Human-in-the-loop approval</span>
                </div>
              </div>
            </div>
          )}

          {/* Messages */}
          <div className="messages-container">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} msg={msg} />
            ))}
            <div ref={chatEndRef} />
          </div>
        </div>
      </div>

      {/* Input Bar */}
      <footer className="input-bar">
        <form onSubmit={handleSubmit} className="input-form">
          <textarea
            ref={inputRef}
            className="chat-input"
            placeholder="Ask me anything... e.g. 'Fix my build at https://github.com/user/repo'"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            style={{ resize: "none", overflow: "hidden", minHeight: "24px", maxHeight: "120px" }}
            onInput={(e) => { e.target.style.height = "auto"; e.target.style.height = e.target.scrollHeight + "px"; }}
          />
          <button type="submit" disabled={loading || !canSubmit} className="send-btn">
            {loading ? (
              <span className="spinner"></span>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            )}
          </button>
        </form>
      </footer>
    </div>
  );
}

export default App;