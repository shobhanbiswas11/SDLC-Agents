import React from "react";

export function SeverityBadge({ level, size = "sm" }: { level: string; size?: "sm" | "xs" }) {
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
