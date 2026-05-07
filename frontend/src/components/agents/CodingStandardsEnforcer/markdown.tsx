/**
 * Tiny zero-dep markdown renderer for chat bubbles. Handles the four
 * patterns the orchestrator actually emits:
 *   - **bold**
 *   - `inline code`
 *   - leading "- " bullet lists (each line that starts with `- `)
 *   - blank-line paragraph breaks
 *
 * We intentionally avoid `dangerouslySetInnerHTML` — every rendered span/em
 * is a real React node, so user-supplied text can't inject HTML.
 */
import { Fragment, ReactNode } from 'react';

type InlineToken =
  | { kind: 'text'; text: string }
  | { kind: 'bold'; text: string }
  | { kind: 'code'; text: string };

const INLINE_RE = /(\*\*[^*]+\*\*|`[^`]+`)/g;

function tokenizeInline(line: string): InlineToken[] {
  const out: InlineToken[] = [];
  let lastIndex = 0;
  for (const match of line.matchAll(INLINE_RE)) {
    const start = match.index ?? 0;
    if (start > lastIndex) {
      out.push({ kind: 'text', text: line.slice(lastIndex, start) });
    }
    const m = match[0];
    if (m.startsWith('**')) {
      out.push({ kind: 'bold', text: m.slice(2, -2) });
    } else {
      out.push({ kind: 'code', text: m.slice(1, -1) });
    }
    lastIndex = start + m.length;
  }
  if (lastIndex < line.length) {
    out.push({ kind: 'text', text: line.slice(lastIndex) });
  }
  return out;
}

function renderInline(line: string, keyPrefix: string): ReactNode[] {
  return tokenizeInline(line).map((tok, i) => {
    const k = `${keyPrefix}-${i}`;
    if (tok.kind === 'bold')
      return (
        <strong key={k} className="md-bold">
          {tok.text}
        </strong>
      );
    if (tok.kind === 'code')
      return (
        <code key={k} className="md-code">
          {tok.text}
        </code>
      );
    return <Fragment key={k}>{tok.text}</Fragment>;
  });
}

export function renderMarkdown(text: string): ReactNode {
  if (!text) return null;

  const lines = text.split('\n');
  const out: ReactNode[] = [];
  let buffer: string[] = [];
  let bulletBuffer: string[] = [];

  const flushParagraph = () => {
    if (buffer.length === 0) return;
    const joined = buffer.join('\n');
    out.push(
      <p key={`p-${out.length}`} className="md-p">
        {renderInline(joined, `p-${out.length}`)}
      </p>,
    );
    buffer = [];
  };

  const flushBullets = () => {
    if (bulletBuffer.length === 0) return;
    out.push(
      <ul key={`ul-${out.length}`} className="md-ul">
        {bulletBuffer.map((b, i) => (
          <li key={`li-${i}`}>{renderInline(b, `li-${out.length}-${i}`)}</li>
        ))}
      </ul>,
    );
    bulletBuffer = [];
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    const isBullet = /^- /.test(line);
    const isBlank = line.trim().length === 0;

    if (isBullet) {
      flushParagraph();
      bulletBuffer.push(line.replace(/^- /, ''));
      continue;
    }
    flushBullets();

    if (isBlank) {
      flushParagraph();
      continue;
    }
    buffer.push(line);
  }
  flushBullets();
  flushParagraph();

  return out;
}
