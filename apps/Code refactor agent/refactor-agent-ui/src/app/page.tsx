"use client";

import React, { useState, useRef, useEffect } from "react";
import { useAgentWorkflow } from "../hooks/useAgentWorkflow";
import { SeverityBadge } from "../components/SeverityBadge";
import { LoadingDots } from "../components/LoadingDots";
import { MessageContent } from "../components/MessageContent";
import { Field } from "../components/Field";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8002";

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

export default function Home() {
  const {
    messages,
    isLoading,
    isConnected,
    waitingForUser,
    sessionMeta,
    startSession,
    sendMessage,
    stopSession
  } = useAgentWorkflow();

  const [input, setInput] = useState("");
  const [workspacePath, setWorkspacePath] = useState(".");
  const [sourceType, setSourceType] = useState<"local" | "github">("local");
  const [githubUrl, setGithubUrl] = useState("");
  const [githubBranch, setGithubBranch] = useState("");

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleStartSession = async () => {
    const success = await startSession(workspacePath, sourceType, githubUrl, githubBranch);
    if (success) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const handleSendMessage = () => {
    if (!input.trim()) return;
    sendMessage(input.trim());
    setInput("");
  };

  const quickActions = [
    { label: "Detect smells",  value: "Analyze this file for code smells" },
    { label: "HIGH issues",    value: "Show me all HIGH severity issues" },
    { label: "Best refactor",  value: "Suggest a refactor for the worst smell" },
    { label: "Run tests",      value: "Run the test suite" },
  ];

  const msgCount = messages.filter(m => m.role !== "system").length;

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
                onClick={handleStartSession}
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
                    onKeyDown={e => e.key === "Enter" && !e.shiftKey && handleSendMessage()}
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
                    onClick={handleSendMessage}
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
