import React, { useState } from "react";

export function DiffViewer({ diff }: { diff: string }) {
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
