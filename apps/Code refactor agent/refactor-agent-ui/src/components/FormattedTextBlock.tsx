import React from "react";

export function FormattedTextBlock({ text }: { text: string }) {
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
