'use client';
import React, {
  useEffect, useRef, useState, useCallback, useMemo,
} from 'react';
import { useAppDispatch, useAppSelector } from '@/hooks';
import {
  setManifest, reset, userMessageSent, approvalDecided,
  sessionCreated, setChatTitle,
} from '@/store/slices/dependencyResolverSlice';
import {
  createSession, connectWS, disconnectWS, sendMessage, sendApproval, deleteSession,
} from '@/services/dependencyResolverService';
import type {
  Ecosystem, Strategy, ChatEntry, ApprovalRequestPayload,
} from '@/types/dependencyResolver';

// ── Theme ───────────────────────────────────────────────────────────────────
// Brand cyan #009eda + white. Tailwind arbitrary colours used inline below.

const ECOSYSTEM_LABEL: Record<Ecosystem, string> = {
  pypi:  'Python (PyPI)',
  npm:   'Node.js (npm)',
  maven: 'Java (Maven)',
  cargo: 'Rust (Cargo)',
};

const STRATEGY_LABEL: Record<Strategy, string> = {
  stable:  'Stable',
  latest:  'Latest',
  minimal: 'Minimal',
};

const STAGES = [
  'parsing', 'parsing_done', 'fetching', 'fetching_done',
  'solving', 'solving_done', 'auditing', 'auditing_done', 'explaining',
];

const SESSIONS_KEY = 'dep-resolver:sessions';

// ── Ecosystem detection from pasted text ────────────────────────────────────

function detectEcosystem(text: string): Ecosystem | null {
  const t = text.trim();
  if (/<project[\s>]|<dependency>|<groupId>/i.test(t)) return 'maven';
  try {
    if (t.startsWith('{')) {
      const obj = JSON.parse(t);
      if (obj && (obj.dependencies || obj.devDependencies)) return 'npm';
    }
  } catch { /* fallthrough */ }
  if (/^\s*\[dependencies\]/m.test(t) || /^\s*\[package\]/m.test(t)) return 'cargo';
  if (/^[A-Za-z0-9_\-.]+\s*[><=~!]=?\s*\S+/m.test(t)) return 'pypi';
  return null;
}

// ── Local session history (sidebar) ─────────────────────────────────────────

interface StoredSession {
  id: string;
  title: string;
  ecosystem: Ecosystem;
  createdAt: string;
}

function loadStoredSessions(): StoredSession[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(SESSIONS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveStoredSessions(sessions: StoredSession[]) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions.slice(0, 30)));
  } catch { /* quota or disabled storage — ignore */ }
}

function deriveLocalTitle(manifest: string, ecosystem: Ecosystem): string {
  const lines = manifest.split('\n').map(l => l.trim()).filter(Boolean);
  if (ecosystem === 'npm') {
    try {
      const obj = JSON.parse(manifest);
      const pkgs = Object.keys(obj.dependencies ?? obj.devDependencies ?? {});
      if (pkgs.length) return pkgs.slice(0, 3).join(', ');
    } catch { /* fall through */ }
  }
  if (ecosystem === 'cargo') {
    const deps = lines.filter(l => l.includes('=') && !l.startsWith('['));
    if (deps.length) {
      return deps.slice(0, 3).map(l => l.split('=')[0].trim()).join(', ');
    }
  }
  if (ecosystem === 'pypi') {
    return lines.slice(0, 3).map(l => l.split(/[><=~!]/)[0].trim()).filter(Boolean).join(', ');
  }
  return lines.slice(0, 1).join('').slice(0, 40) || 'New conversation';
}

// ── Chat thread components ──────────────────────────────────────────────────

const STAGE_LABEL: Record<string, string> = {
  parsing: 'Parsing manifest',
  parsing_done: 'Parsed manifest',
  fetching: 'Fetching package metadata',
  fetching_done: 'Fetched package metadata',
  solving: 'Running version solver',
  solving_done: 'Resolved versions',
  auditing: 'Auditing for vulnerabilities',
  auditing_done: 'Audit complete',
  explaining: 'Generating explanation',
};

function PipelineCard({ events }: { events: ChatEntry[] }) {
  if (!events.length) return null;
  const last = events[events.length - 1]?.stage ?? '';
  const idx = STAGES.indexOf(last);
  const pct = idx < 0 ? 0 : Math.round(((idx + 1) / STAGES.length) * 100);
  const seenStages = new Set<string>();

  // Collapse duplicate stage events; keep the most recent message for each.
  const stageOrder: { stage: string; text: string; done: boolean }[] = [];
  for (const e of events) {
    if (!e.stage) continue;
    const key = e.stage.replace(/_done$/, '');
    const isDone = e.stage.endsWith('_done');
    const existing = stageOrder.find(s => s.stage === key);
    if (existing) {
      existing.text = e.text || existing.text;
      if (isDone) existing.done = true;
    } else {
      stageOrder.push({ stage: key, text: e.text || STAGE_LABEL[e.stage] || e.stage, done: isDone });
    }
    seenStages.add(key);
  }

  const isComplete = pct >= 100;

  return (
    <div className="my-2 rounded-lg border border-[#009eda]/30 bg-white shadow-sm">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#009eda]/15 bg-[#009eda]/5">
        <span className="text-[11px] font-semibold text-[#007aab] tracking-wide uppercase">
          Resolution pipeline
        </span>
        <span className="text-[11px] font-mono text-[#007aab]">{pct}%</span>
      </div>
      <div className="px-4 py-3">
        <div className="w-full h-1 bg-[#009eda]/15 rounded-full overflow-hidden mb-3">
          <div
            className="h-1 bg-[#009eda] rounded-full transition-all duration-700"
            style={{ width: `${pct}%` }}
          />
        </div>
        <ul className="space-y-1.5">
          {stageOrder.map(s => (
            <li key={s.stage} className="flex items-center gap-2 text-[12px]">
              <span className={`inline-block w-1.5 h-1.5 rounded-full
                ${s.done ? 'bg-[#009eda]' :
                  isComplete ? 'bg-gray-300' : 'bg-[#009eda]/60 animate-pulse'}`} />
              <span className={s.done ? 'text-gray-700' : 'text-gray-500'}>{s.text}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function InlineApproval({
  approval, disabled, onDecide,
}: {
  approval: ApprovalRequestPayload;
  disabled: boolean;
  onDecide: (d: 'APPROVE' | 'REJECT', comment?: string) => void;
}) {
  const [comment, setComment] = useState('');
  const [showLockfile, setShowLockfile] = useState(false);
  const { stats } = approval;

  const summary = `I have prepared a proposed lockfile: ${stats.resolved} package${stats.resolved === 1 ? '' : 's'} resolved, ${stats.conflicts} conflict${stats.conflicts === 1 ? '' : 's'}, ${stats.cves} known vulnerabilit${stats.cves === 1 ? 'y' : 'ies'}. Would you like to approve it?`;

  return (
    <div className="space-y-3">
      <p className="text-sm leading-relaxed text-gray-800">{summary}</p>

      <button
        onClick={() => setShowLockfile(v => !v)}
        className="text-xs text-[#007aab] hover:text-[#005a80] underline"
      >
        {showLockfile ? 'Hide lockfile' : 'Show proposed lockfile'}
      </button>
      {showLockfile && (
        <pre className="text-[11px] font-mono bg-[#009eda]/5 border border-[#009eda]/20 rounded-lg
          p-3 max-h-48 overflow-y-auto whitespace-pre-wrap break-all text-gray-700">
          {approval.proposed_lockfile}
        </pre>
      )}

      <input
        value={comment}
        onChange={e => setComment(e.target.value)}
        placeholder="Optional note (reason for rejection, follow-up, etc.)"
        disabled={disabled}
        className="w-full text-xs border border-gray-200 rounded-lg px-3 py-2
          focus:outline-none focus:ring-1 focus:ring-[#009eda] focus:border-[#009eda]
          disabled:opacity-50"
      />

      <div className="flex gap-2">
        <button
          onClick={() => onDecide('APPROVE', comment || undefined)}
          disabled={disabled}
          className="px-4 py-1.5 rounded-md bg-[#009eda] hover:bg-[#0085bb] text-white
            text-xs font-medium transition disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Approve
        </button>
        <button
          onClick={() => onDecide('REJECT', comment || undefined)}
          disabled={disabled}
          className="px-4 py-1.5 rounded-md border border-gray-300 hover:bg-gray-50 text-gray-700
            text-xs font-medium transition disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Reject
        </button>
      </div>
    </div>
  );
}

function Bubble({ entry, sessionId }: { entry: ChatEntry; sessionId: string }) {
  const dispatch = useAppDispatch();
  const { status, pendingApproval } = useAppSelector(s => s.dependencyResolver);

  const handleDecide = useCallback((decision: 'APPROVE' | 'REJECT', comment?: string) => {
    if (!pendingApproval) return;
    sendApproval(sessionId, decision, comment);
    dispatch(approvalDecided(decision));
  }, [sessionId, pendingApproval, dispatch]);

  // Solver events handled inline by the parent (see PipelineCard).
  if (entry.type === 'solver_event') return null;

  if (entry.type === 'system') {
    return (
      <div className="text-[12px] text-gray-500 py-1 italic">{entry.text}</div>
    );
  }

  if (entry.type === 'error') {
    return (
      <div className="text-xs text-red-700 bg-red-50 border border-red-100 rounded-md px-3 py-2">
        {entry.text}
      </div>
    );
  }

  if (entry.type === 'tool_call' || entry.type === 'tool_result' || entry.type === 'search_event' || entry.type === 'clarify') {
    return (
      <div className="text-[12px] text-gray-500 py-0.5">{entry.text}</div>
    );
  }

  const isUser = entry.type === 'user_message';
  const isApproval = entry.type === 'approval_request' && entry.approval;

  if (isUser) {
    return (
      <div className="flex justify-end py-2">
        <div className="max-w-[78%] rounded-2xl rounded-tr-sm bg-[#009eda] text-white
          px-4 py-2.5 text-sm leading-relaxed shadow-sm">
          <span style={{ whiteSpace: 'pre-wrap' }}>{entry.text}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start py-2">
      <div className="w-7 h-7 rounded-full bg-[#009eda] text-white flex items-center
        justify-center text-[10px] font-semibold shrink-0 mr-3 mt-0.5">DR</div>
      <div className="max-w-[78%] rounded-2xl rounded-tl-sm bg-white border border-[#009eda]/25
        text-gray-800 px-4 py-3 text-sm leading-relaxed shadow-sm">
        {isApproval ? (
          <InlineApproval
            approval={entry.approval!}
            disabled={status === 'approved' || status === 'rejected'}
            onDecide={handleDecide}
          />
        ) : (
          <>
            <span style={{ whiteSpace: 'pre-wrap' }}>{entry.text}</span>
            {!entry.done && entry.type === 'agent_message' && (
              <span className="inline-block w-1.5 h-4 bg-[#009eda]/60 animate-pulse ml-1 rounded-sm align-middle" />
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ── Sidebar ─────────────────────────────────────────────────────────────────

function Sidebar({
  sessions, activeId, activeTitle, onSelect, onNew, onDelete,
}: {
  sessions: StoredSession[];
  activeId: string | null;
  activeTitle: string | null;
  onSelect: (s: StoredSession) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}) {
  const [confirmId, setConfirmId] = useState<string | null>(null);

  return (
    <aside className="w-64 shrink-0 bg-white border-r border-[#009eda]/15 flex flex-col h-screen">
      <div className="p-3 border-b border-[#009eda]/15">
        <h2 className="text-sm font-semibold text-gray-900 mb-2">Dependency Resolver</h2>
        <button
          onClick={onNew}
          className="w-full text-left text-sm text-white bg-[#009eda] hover:bg-[#0085bb]
            rounded-md px-3 py-2 transition font-medium"
        >
          + New conversation
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {sessions.length === 0 && (
          <p className="text-xs text-gray-400 px-2 py-3">No previous conversations.</p>
        )}
        {sessions.map(s => {
          const isActive = s.id === activeId;
          const displayTitle = isActive && activeTitle ? activeTitle : s.title;
          const isConfirming = confirmId === s.id;

          return (
            <div
              key={s.id}
              className={`group rounded-md transition relative
                ${isActive
                  ? 'bg-[#009eda]/10 border border-[#009eda]/40'
                  : 'border border-transparent hover:bg-[#009eda]/5 hover:border-[#009eda]/20'}`}
            >
              <button
                onClick={() => onSelect(s)}
                className="w-full text-left px-3 py-2 pr-8"
              >
                <p className={`text-sm font-medium truncate
                  ${isActive ? 'text-[#005a80]' : 'text-gray-800'}`}>
                  {displayTitle}
                </p>
                <p className="text-[11px] text-gray-500 mt-0.5">
                  {ECOSYSTEM_LABEL[s.ecosystem]} · {new Date(s.createdAt).toLocaleDateString()}
                </p>
              </button>

              {!isConfirming ? (
                <button
                  onClick={(e) => { e.stopPropagation(); setConfirmId(s.id); }}
                  title="Delete conversation"
                  className="absolute top-2 right-2 opacity-0 group-hover:opacity-100
                    text-gray-400 hover:text-red-600 transition w-5 h-5
                    flex items-center justify-center text-xs"
                >
                  ×
                </button>
              ) : (
                <div className="absolute top-1.5 right-1.5 flex gap-1">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(s.id);
                      setConfirmId(null);
                    }}
                    className="text-[10px] font-medium text-white bg-red-500 hover:bg-red-600
                      rounded px-1.5 py-0.5 transition"
                  >
                    Delete
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setConfirmId(null); }}
                    className="text-[10px] font-medium text-gray-600 bg-white border border-gray-300
                      hover:bg-gray-50 rounded px-1.5 py-0.5 transition"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="p-3 border-t border-[#009eda]/15 text-[11px] text-gray-400 leading-relaxed">
        Resolves package conflicts, audits CVEs, and asks for your approval before delivering a lockfile.
      </div>
    </aside>
  );
}

// ── Welcome message ─────────────────────────────────────────────────────────

const WELCOME: ChatEntry = {
  id: 'welcome',
  type: 'agent_message',
  timestamp: new Date().toISOString(),
  text:
    "Hello. I am a dependency resolver agent.\n\n" +
    "I can resolve version conflicts across PyPI, npm, Maven, and Cargo, audit packages for known vulnerabilities, and produce a lockfile for you to review.\n\n" +
    "When you are ready, paste a manifest (requirements.txt, package.json, pom.xml, or Cargo.toml) and I will get started. You can also ask me general questions about how the resolver works.",
  done: true,
};

// ── Main page ───────────────────────────────────────────────────────────────

export default function DependencyResolverPage() {
  const dispatch = useAppDispatch();
  const {
    sessionId, status, entries, isConnected, isStreaming,
    finalLockfile, ecosystem, error: storeError, chatTitle,
  } = useAppSelector(s => s.dependencyResolver);

  const [input, setInput]       = useState('');
  const [strategy, setStrategy] = useState<Strategy>('stable');
  const [storedSessions, setStoredSessions] = useState<StoredSession[]>([]);
  const [resolving, setResolving] = useState(false);
  const bottomRef               = useRef<HTMLDivElement>(null);
  const textareaRef             = useRef<HTMLTextAreaElement>(null);

  // Load stored session list on mount
  useEffect(() => {
    setStoredSessions(loadStoredSessions());
    return () => { disconnectWS(); };
  }, []);

  // Auto-scroll on new entries
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries]);

  // Sync LLM-generated title back into local sidebar history
  useEffect(() => {
    if (!sessionId || !chatTitle) return;
    setStoredSessions(prev => {
      const updated = prev.map(s =>
        s.id === sessionId ? { ...s, title: chatTitle } : s,
      );
      saveStoredSessions(updated);
      return updated;
    });
  }, [chatTitle, sessionId]);

  // ── Start a new session from a pasted manifest ──────────────────────────
  const startSession = useCallback(async (
    text: string, eco: Ecosystem, strat: Strategy,
  ) => {
    setResolving(true);
    try {
      dispatch(setManifest({ manifest: text, ecosystem: eco, strategy: strat }));
      const sid = await createSession(dispatch, eco, text, strat);
      // Local placeholder title (LLM will replace via system frame)
      const localTitle = deriveLocalTitle(text, eco);
      dispatch(setChatTitle(localTitle));
      connectWS(dispatch, sid);

      const next: StoredSession = {
        id: sid,
        title: localTitle,
        ecosystem: eco,
        createdAt: new Date().toISOString(),
      };
      const updated = [next, ...loadStoredSessions().filter(s => s.id !== sid)];
      saveStoredSessions(updated);
      setStoredSessions(updated);
    } catch {
      /* error already dispatched */
    } finally {
      setResolving(false);
    }
  }, [dispatch]);

  const handleSubmit = useCallback(async () => {
    const text = input.trim();
    if (!text || isStreaming || resolving) return;

    if (!sessionId) {
      const eco = detectEcosystem(text);
      if (eco) {
        setInput('');
        await startSession(text, eco, strategy);
      } else {
        // Local guidance reply (no session yet, so no backend round-trip)
        dispatch(userMessageSent({ text }));
        dispatch({
          type: 'dependencyResolver/frameReceived',
          payload: {
            type: 'agent_message',
            session_id: 'local',
            payload: {
              text:
                "I can answer questions, but to resolve dependencies I need a manifest. " +
                "Paste the contents of a requirements.txt, package.json, pom.xml, or Cargo.toml " +
                "and I will start the resolution pipeline.",
            },
            message_id: crypto.randomUUID(),
            timestamp: new Date().toISOString(),
            done: true,
          },
        });
        setInput('');
      }
      return;
    }

    if (!isConnected) return;
    dispatch(userMessageSent({ text }));
    sendMessage(sessionId, text);
    setInput('');
    textareaRef.current?.focus();
  }, [input, sessionId, isStreaming, isConnected, resolving, strategy, dispatch, startSession]);

  const handleSelectSession = useCallback((s: StoredSession) => {
    if (s.id === sessionId) return;
    disconnectWS();
    dispatch(reset());
    dispatch(sessionCreated({
      sessionId: s.id,
      wsUrl: `${(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/^http/, 'ws')}/api/dependency_resolver/chat/${s.id}`,
      title: s.title,
    }));
    connectWS(dispatch, s.id);
  }, [sessionId, dispatch]);

  const handleNewSession = useCallback(() => {
    disconnectWS();
    dispatch(reset());
    setInput('');
  }, [dispatch]);

  const handleDeleteSession = useCallback((id: string) => {
    deleteSession(id);
    const updated = loadStoredSessions().filter(s => s.id !== id);
    saveStoredSessions(updated);
    setStoredSessions(updated);
    if (id === sessionId) {
      disconnectWS();
      dispatch(reset());
    }
  }, [sessionId, dispatch]);

  const handleRerun = useCallback(() => {
    if (!isConnected || !sessionId) return;
    dispatch(userMessageSent({ text: '/run' }));
    sendMessage(sessionId, '/run');
  }, [isConnected, sessionId, dispatch]);

  const handleDownload = useCallback(() => {
    if (!finalLockfile) return;
    const name = ecosystem === 'npm'   ? 'package-lock.json'
               : ecosystem === 'cargo' ? 'Cargo.lock'
               : ecosystem === 'maven' ? 'pom.resolved.xml'
               :                         'requirements.lock.txt';
    const blob = new Blob([finalLockfile], { type: 'text/plain' });
    const url  = URL.createObjectURL(blob);
    const a    = Object.assign(document.createElement('a'), { href: url, download: name });
    a.click();
    URL.revokeObjectURL(url);
  }, [finalLockfile, ecosystem]);

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const detectedEco = useMemo(
    () => (input.length > 12 ? detectEcosystem(input) : null),
    [input],
  );

  // ── Build the inline thread ─────────────────────────────────────────────
  // Walk entries and keep them in original order, but collapse contiguous
  // solver_event runs into a single PipelineCard rendered inline.
  type ThreadItem =
    | { kind: 'entry'; entry: ChatEntry }
    | { kind: 'pipeline'; events: ChatEntry[]; key: string };

  const threadItems = useMemo<ThreadItem[]>(() => {
    const items: ThreadItem[] = [];
    let solverBuf: ChatEntry[] = [];
    let solverKey = '';
    const flush = () => {
      if (solverBuf.length) {
        items.push({ kind: 'pipeline', events: solverBuf, key: `pipe-${solverKey}` });
        solverBuf = [];
        solverKey = '';
      }
    };
    for (const e of entries) {
      if (e.type === 'solver_event') {
        if (!solverKey) solverKey = e.id;
        solverBuf.push(e);
      } else {
        flush();
        items.push({ kind: 'entry', entry: e });
      }
    }
    flush();
    return items;
  }, [entries]);

  const showWelcome = !sessionId && entries.length === 0;

  const statusBadge: { label: string; cls: string } | null =
    !sessionId ? null :
    status === 'created'          ? { label: 'Starting',          cls: 'bg-gray-100 text-gray-600' }
  : status === 'active'           ? { label: 'Resolving',         cls: 'bg-[#009eda]/10 text-[#007aab]' }
  : status === 'pending_approval' ? { label: 'Awaiting approval', cls: 'bg-amber-50 text-amber-700' }
  : status === 'approved'         ? { label: 'Approved',          cls: 'bg-green-50 text-green-700' }
  : status === 'rejected'         ? { label: 'Rejected',          cls: 'bg-red-50 text-red-700' }
  :                                  { label: 'Closed',            cls: 'bg-gray-100 text-gray-500' };

  const headerTitle =
    sessionId ? (chatTitle || ECOSYSTEM_LABEL[ecosystem]) : 'New conversation';

  return (
    <div className="flex h-screen bg-white">
      <Sidebar
        sessions={storedSessions}
        activeId={sessionId}
        activeTitle={chatTitle}
        onSelect={handleSelectSession}
        onNew={handleNewSession}
        onDelete={handleDeleteSession}
      />

      <main className="flex-1 flex flex-col min-w-0">

        {/* Top bar */}
        <header className="border-b border-[#009eda]/15 px-6 py-3 flex items-center justify-between shrink-0">
          <div className="min-w-0">
            <h1 className="text-sm font-semibold text-gray-900 truncate">{headerTitle}</h1>
            {sessionId && (
              <p className="text-[11px] text-gray-400 mt-0.5">
                {ECOSYSTEM_LABEL[ecosystem]} · {sessionId.slice(0, 8)}
              </p>
            )}
          </div>
          <div className="flex items-center gap-3 shrink-0">
            {sessionId && (
              <span className={`flex items-center gap-1.5 text-[11px] font-medium
                ${isConnected ? 'text-[#007aab]' : 'text-gray-400'}`}>
                <span className={`w-1.5 h-1.5 rounded-full
                  ${isConnected ? 'bg-[#009eda]' : 'bg-gray-300'}`} />
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            )}
            {statusBadge && (
              <span className={`text-[11px] font-medium px-2 py-0.5 rounded ${statusBadge.cls}`}>
                {statusBadge.label}
              </span>
            )}
            {finalLockfile && (
              <button
                onClick={handleDownload}
                className="text-[11px] font-medium px-3 py-1 rounded-md bg-[#009eda] text-white
                  hover:bg-[#0085bb] transition"
              >
                Download lockfile
              </button>
            )}
            {sessionId && (
              <button
                onClick={handleRerun}
                disabled={!isConnected || isStreaming}
                className="text-[11px] font-medium px-3 py-1 rounded-md border border-[#009eda]/40
                  text-[#007aab] hover:bg-[#009eda]/5 transition
                  disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Re-run resolver
              </button>
            )}
          </div>
        </header>

        {/* Chat thread (pipeline rendered inline) */}
        <div className="flex-1 overflow-y-auto min-h-0">
          <div className="max-w-3xl mx-auto px-6 py-6 space-y-1">
            {showWelcome && (
              <Bubble entry={WELCOME} sessionId={sessionId ?? ''} />
            )}
            {threadItems.map(item => (
              item.kind === 'pipeline'
                ? <PipelineCard key={item.key} events={item.events} />
                : <Bubble key={item.entry.id} entry={item.entry} sessionId={sessionId ?? ''} />
            ))}
            {storeError && (
              <div className="text-xs text-red-700 bg-red-50 border border-red-100
                rounded-md px-3 py-2 my-2">
                {storeError}
              </div>
            )}
            {finalLockfile && status === 'approved' && (
              <div className="bg-[#009eda]/5 border border-[#009eda]/30 rounded-lg p-4 mt-4 space-y-2">
                <p className="text-sm font-medium text-[#005a80]">Lockfile finalised</p>
                <pre className="text-[11px] font-mono bg-white border border-[#009eda]/20 rounded
                  p-3 max-h-44 overflow-y-auto whitespace-pre-wrap text-gray-700">
                  {finalLockfile}
                </pre>
                <button
                  onClick={handleDownload}
                  className="text-xs text-[#007aab] hover:text-[#005a80] underline"
                >
                  Download
                </button>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input area */}
        <div className="border-t border-[#009eda]/15 px-6 py-4 shrink-0">
          <div className="max-w-3xl mx-auto">
            <div className="border border-gray-300 rounded-xl bg-white focus-within:ring-1
              focus-within:ring-[#009eda] focus-within:border-[#009eda] transition">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                disabled={resolving || isStreaming || (sessionId !== null && !isConnected)}
                placeholder={
                  resolving        ? 'Starting resolver…' :
                  isStreaming      ? 'Agent responding…' :
                  sessionId && !isConnected ? 'Reconnecting…' :
                  !sessionId       ? 'Paste a manifest to start, or ask a question…' :
                  status === 'pending_approval'
                    ? 'Reply, ask a follow-up, or approve above.'
                    : 'Send a message, type "/run" to re-resolve, or paste a new manifest.'
                }
                rows={2}
                className="w-full resize-none text-sm px-4 py-3 bg-transparent
                  focus:outline-none placeholder-gray-400 disabled:text-gray-400"
              />
              <div className="flex items-center justify-between px-3 py-2 border-t border-gray-100">
                <div className="flex items-center gap-3 text-[11px] text-gray-500">
                  {!sessionId && (
                    <>
                      <label className="flex items-center gap-1.5">
                        <span>Strategy</span>
                        <select
                          value={strategy}
                          onChange={e => setStrategy(e.target.value as Strategy)}
                          className="text-[11px] border border-gray-200 rounded px-1.5 py-0.5
                            bg-white focus:outline-none focus:border-[#009eda]"
                        >
                          {(Object.keys(STRATEGY_LABEL) as Strategy[]).map(s => (
                            <option key={s} value={s}>{STRATEGY_LABEL[s]}</option>
                          ))}
                        </select>
                      </label>
                      {detectedEco && (
                        <span className="text-[#007aab]">
                          Detected: {ECOSYSTEM_LABEL[detectedEco]}
                        </span>
                      )}
                    </>
                  )}
                </div>
                <button
                  onClick={handleSubmit}
                  disabled={!input.trim() || resolving || isStreaming
                    || (sessionId !== null && !isConnected)}
                  className="px-4 py-1.5 rounded-md bg-[#009eda] hover:bg-[#0085bb] text-white
                    text-xs font-medium transition
                    disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Send
                </button>
              </div>
            </div>
            <p className="text-[11px] text-gray-400 mt-2 text-center">
              Guardrails active. No lockfile is delivered without your explicit approval.
            </p>
          </div>
        </div>

      </main>
    </div>
  );
}
