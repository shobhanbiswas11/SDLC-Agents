import React from "react";

export function Field({ label, children }: { label: string; children: React.ReactNode }) {
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
