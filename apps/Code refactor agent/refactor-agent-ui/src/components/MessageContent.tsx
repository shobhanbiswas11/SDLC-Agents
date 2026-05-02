import React from "react";
import { DiffViewer } from "./DiffViewer";
import { SeverityBadge } from "./SeverityBadge";
import { FormattedTextBlock } from "./FormattedTextBlock";

export function MessageContent({ content }: { content: string }) {
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
