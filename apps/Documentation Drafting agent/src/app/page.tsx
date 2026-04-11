'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { streamChat, pushToGitHub, type StreamEvent } from '../lib/api';

/* ═══════════════════════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════════════════════ */

interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  status?: string;
  streaming?: boolean;
  contextFiles?: string[];
  sectionId?: string;
}

interface DocSection {
  id: string;
  label: string;
  icon: string;
  prompt: string;
  desc: string;
}

/* ═══════════════════════════════════════════════════════════════════════════
   Data
   ═══════════════════════════════════════════════════════════════════════════ */

const SECTIONS: DocSection[] = [
  { id: 'readme',        label: 'README',             icon: '📄', desc: 'Full project overview', prompt: 'Generate a comprehensive, well-structured README.md for this GitHub repository. Include project title, badges, overview, features, tech stack, installation, usage examples, configuration, contributing guidelines and license section.' },
  { id: 'install',       label: 'Installation',       icon: '⚙️', desc: 'Setup instructions',     prompt: 'Write a detailed installation and setup guide for this repository. Cover prerequisites, step-by-step installation, environment variables, and verification steps.' },
  { id: 'api',           label: 'API Reference',      icon: '🔌', desc: 'Endpoints & schemas',    prompt: 'Generate complete API reference documentation. Document all endpoints, request/response schemas, authentication, error codes, and curl examples.' },
  { id: 'architecture',  label: 'Architecture',       icon: '🏗️', desc: 'System design',          prompt: 'Write an architecture overview. Explain the high-level design, key components, data flow, design patterns, folder structure, and technology choices.' },
  { id: 'contributing',  label: 'Contributing',       icon: '🤝', desc: 'PR guidelines',          prompt: 'Write a CONTRIBUTING.md covering development workflow, coding standards, PR guidelines, testing requirements, and issue submission process.' },
  { id: 'changelog',     label: 'Changelog',          icon: '📋', desc: 'Version history',        prompt: 'Draft a CHANGELOG.md following the Keep a Changelog format with categorized entries for the latest version based on the codebase.' },
  { id: 'security',      label: 'Security',           icon: '🔒', desc: 'Vuln reporting',         prompt: 'Write a SECURITY.md covering supported versions, how to report vulnerabilities responsibly, and the security response process.' },
  { id: 'faq',           label: 'FAQ',                icon: '❓', desc: 'Common questions',       prompt: 'Generate a comprehensive FAQ document anticipating common questions developers might have about using and contributing to this project.' },
];

const QUICK_PROMPTS = [
  'What does this project do?',
  'List the main dependencies',
  'Explain the folder structure',
  'Generate a README',
];

/* ═══════════════════════════════════════════════════════════════════════════
   Inline SVG Icons
   ═══════════════════════════════════════════════════════════════════════════ */

const SendSVG = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 2L11 13" /><path d="M22 2L15 22 11 13 2 9l20-7z" />
  </svg>
);
const CopySVG = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
  </svg>
);
const DownloadSVG = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
  </svg>
);
const CheckSVG = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);
const GithubSVG = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
  </svg>
);
const PushSVG = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
    <polyline points="17 8 12 3 7 8" />
    <line x1="12" y1="3" x2="12" y2="15" />
  </svg>
);

/* ═══════════════════════════════════════════════════════════════════════════
   Component
   ═══════════════════════════════════════════════════════════════════════════ */

export default function Home() {
  /* ── State ── */
  const [repo, setRepo]             = useState('');
  const [token, setToken]           = useState('');
  const [connected, setConnected]   = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [repoName, setRepoName]     = useState('');

  const [messages, setMessages]     = useState<Message[]>([]);
  const [input, setInput]           = useState('');
  const [streaming, setStreaming]    = useState(false);
  const [activeSection, setActive]  = useState<string | null>(null);

  const [previewMd, setPreviewMd]   = useState('');
  const [previewTab, setPreviewTab] = useState<'preview' | 'raw'>('preview');
  const [copied, setCopied]         = useState(false);

  // ── Push to GitHub modal state ──
  const [showPushModal, setShowPushModal] = useState(false);
  const [pushPath, setPushPath]           = useState('README.md');
  const [pushMsg, setPushMsg]             = useState('docs: update documentation via DocuGenius');
  const [pushing, setPushing]             = useState(false);
  const [pushResult, setPushResult]       = useState<{ ok: boolean; url?: string; err?: string } | null>(null);

  const endRef    = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLTextAreaElement>(null);
  const abortRef  = useRef<AbortController | null>(null);

  /* ── Auto-scroll ── */
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  /* ── Connect ── */
  const handleConnect = useCallback(async () => {
    if (!repo.trim() || !token.trim()) return;
    setConnecting(true);
    try {
      let name = repo.trim();
      const m = name.match(/github\.com\/([^/\s]+\/[^/\s]+)/);
      if (m) name = m[1].replace(/\.git$/, '');
      setRepoName(name);
      setConnected(true);
      setMessages([{
        id: 'welcome',
        role: 'agent',
        content: `**Connected to \`${name}\`** 🎉\n\nYour repository is linked. Choose a documentation section from the sidebar, or ask me anything about the codebase below.`,
      }]);
    } finally { setConnecting(false); }
  }, [repo, token]);

  const handleDisconnect = () => {
    setConnected(false); setRepo(''); setToken(''); setRepoName('');
    setMessages([]); setPreviewMd(''); setActive(null);
  };

  /* ── Send (SSE) ── */
  const send = useCallback(async (text: string, secId?: string) => {
    if (!text.trim() || streaming || !connected) return;

    const uid = `u-${Date.now()}`;
    const aid = `a-${Date.now()}`;

    setMessages(p => [
      ...p,
      { id: uid, role: 'user', content: text, sectionId: secId },
      { id: aid, role: 'agent', content: '', streaming: true, status: 'Initializing…' },
    ]);
    setInput('');
    setStreaming(true);

    // Cancel any previous in-flight stream before starting a new one.
    // This prevents React StrictMode double-invocation from accumulating chunks twice.
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    let accum = '';

    try {
      await streamChat(repoName, token, text, (ev: StreamEvent) => {
        setMessages(prev => prev.map(m => {
          if (m.id !== aid) return m;
          switch (ev.type) {
            case 'status':
              return { ...m, status: ev.message ?? '' };
            case 'chunk':
              accum += ev.content ?? '';
              return { ...m, content: accum, status: undefined };
            case 'done':
              return { ...m, streaming: false, status: undefined, contextFiles: ev.context_files };
            case 'error':
              return { ...m, streaming: false, status: undefined, content: `⚠️ **Error:** ${ev.message}` };
            default: return m;
          }
        }));

        if (secId && (ev.type === 'chunk' || ev.type === 'done')) {
          setPreviewMd(accum);
          setActive(secId);
        }
      }, controller.signal);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      // Don't show an error if the request was intentionally aborted
      if (msg === 'The user aborted a request.' || msg === 'AbortError') {
        setMessages(p => p.filter(m => m.id !== aid && m.id !== uid));
        return;
      }
      setMessages(p => p.map(m =>
        m.id === aid ? { ...m, streaming: false, status: undefined, content: `⚠️ **Error:** ${msg}` } : m
      ));
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
      setStreaming(false);
    }
  }, [streaming, connected, repoName, token]);

  const handleSend    = () => { if (input.trim()) send(input.trim()); };
  const handleKey     = (e: React.KeyboardEvent) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } };
  const handleSection = (s: DocSection) => { if (!streaming && connected) { setActive(s.id); send(s.prompt, s.id); } };

  /* ── Copy / Download ── */
  const handleCopy = async () => {
    if (!previewMd) return;
    await navigator.clipboard.writeText(previewMd);
    setCopied(true); setTimeout(() => setCopied(false), 2000);
  };
  const handleDownload = () => {
    if (!previewMd) return;
    const blob = new Blob([previewMd], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url;
    a.download = activeSection ? `${activeSection}.md` : 'documentation.md';
    a.click(); URL.revokeObjectURL(url);
  };

  /* ── Push to GitHub ── */
  const openPushModal = () => {
    // Pre-fill a sensible file path based on the active section
    const sectionPathMap: Record<string, string> = {
      readme: 'README.md',
      install: 'docs/INSTALLATION.md',
      api: 'docs/API.md',
      architecture: 'docs/ARCHITECTURE.md',
      contributing: 'CONTRIBUTING.md',
      changelog: 'CHANGELOG.md',
      security: 'SECURITY.md',
      faq: 'docs/FAQ.md',
    };
    if (activeSection && sectionPathMap[activeSection]) {
      setPushPath(sectionPathMap[activeSection]);
    }
    setPushResult(null);
    setShowPushModal(true);
  };
  const handlePush = async () => {
    if (!pushPath.trim() || !previewMd || !repoName || !token) return;
    setPushing(true);
    setPushResult(null);
    const result = await pushToGitHub(repoName, token, pushPath.trim(), previewMd, pushMsg.trim() || 'docs: update via DocuGenius');
    setPushResult(result.success ? { ok: true, url: result.url } : { ok: false, err: result.error });
    setPushing(false);
  };

  /* ═══════════════════════════════════════════════════════════════════════
     Render
     ═══════════════════════════════════════════════════════════════════════ */
  return (
    <>
      {/* ── Mesh Background ── */}
      <div className="mesh-bg" aria-hidden="true">
        <div className="mesh-orb mesh-orb--indigo" />
        <div className="mesh-orb mesh-orb--emerald" />
        <div className="mesh-orb mesh-orb--cyan" />
      </div>

      <div className="shell">

        {/* ════════════════════════════════════════════════════════════════
            LEFT SIDEBAR
            ════════════════════════════════════════════════════════════════ */}
        <aside className="sidebar">
          {/* Brand */}
          <div className="brand">
            <div className="brand-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
            </div>
            <div className="brand-text">
              <div className="brand-name">DocuGenius</div>
              <div className="brand-sub">AI Documentation Agent</div>
            </div>
          </div>

          {/* Connected repo */}
          {connected && (
            <div className="repo-pill">
              <div className="repo-pill-dot" />
              <div className="repo-pill-name">{repoName}</div>
            </div>
          )}

          {/* Section nav */}
          <div className="sidebar-label">Documentation</div>
          <div className="sections">
            {SECTIONS.map(s => (
              <button
                key={s.id}
                id={`sec-${s.id}`}
                className={`sec-btn${activeSection === s.id ? ' active' : ''}`}
                onClick={() => handleSection(s)}
                disabled={streaming || !connected}
                title={s.desc}
              >
                <span className="sec-icon">{s.icon}</span>
                <span>{s.label}</span>
              </button>
            ))}
          </div>

          {/* Quick prompts */}
          {connected && (
            <div className="quick-zone">
              <div className="quick-label">Quick asks</div>
              {QUICK_PROMPTS.map(q => (
                <button
                  key={q}
                  className="quick-btn"
                  onClick={() => { setInput(q); inputRef.current?.focus(); }}
                  disabled={streaming}
                >
                  {q}
                </button>
              ))}
            </div>
          )}
        </aside>

        {/* ════════════════════════════════════════════════════════════════
            CENTER — CHAT
            ════════════════════════════════════════════════════════════════ */}
        <main className="center">

          {/* Top bar */}
          <div className="topbar">
            {!connected ? (
              <>
                <div className="topbar-label">Connect a GitHub Repository</div>
                <div className="topbar-row">
                  <input
                    id="repo-input"
                    className="topbar-input"
                    placeholder="owner/repo  or  https://github.com/owner/repo"
                    value={repo}
                    onChange={e => setRepo(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleConnect()}
                    disabled={connecting}
                    style={{ flex: 2 }}
                  />
                  <input
                    id="token-input"
                    className="topbar-input"
                    type="password"
                    placeholder="Personal access token"
                    value={token}
                    onChange={e => setToken(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleConnect()}
                    disabled={connecting}
                    style={{ flex: 1.2 }}
                  />
                  <button
                    id="btn-connect"
                    className="btn-connect"
                    onClick={handleConnect}
                    disabled={connecting || !repo.trim() || !token.trim()}
                  >
                    {connecting ? <span className="spinner" /> : <GithubSVG />}
                    {connecting ? 'Connecting…' : 'Connect'}
                  </button>
                </div>
              </>
            ) : (
              <div className="topbar-connected">
                <div className="topbar-conn-info">
                  <div className="topbar-conn-dot" />
                  <GithubSVG />
                  <span>{repoName}</span>
                </div>
                <button className="btn-disconnect" onClick={handleDisconnect} id="btn-disconnect">
                  Disconnect
                </button>
              </div>
            )}
          </div>

          {/* Chat area */}
          {messages.length === 0 ? (
            <div className="welcome">
              <div className="welcome-glow">📄</div>
              <h2>Documentation Drafting Agent</h2>
              <p>
                Connect a GitHub repository above and I&#39;ll analyze its codebase. Then pick a
                documentation section from the sidebar or ask me anything in plain English.
              </p>
              <div className="welcome-arrow">↑ Enter repo URL + token to begin</div>
            </div>
          ) : (
            <div className="messages" id="messages">
              {messages.map(msg => (
                <div key={msg.id} className={`msg ${msg.role === 'user' ? 'msg--user' : ''}`}>
                  <div className={`msg-ava ${msg.role === 'agent' ? 'msg-ava--agent' : 'msg-ava--user'}`}>
                    {msg.role === 'agent' ? '🤖' : '👤'}
                  </div>
                  <div className="msg-body">
                    <div className={`msg-content ${msg.role === 'agent' ? 'msg-content--agent' : 'msg-content--user'}`}>
                      {/* Status pill */}
                      {msg.streaming && msg.status && !msg.content && (
                        <div className="status-pill"><div className="spinner" />{msg.status}</div>
                      )}
                      {/* Typing dots */}
                      {msg.streaming && !msg.status && !msg.content && (
                        <div className="typing"><span /><span /><span /></div>
                      )}
                      {/* Content */}
                      {msg.content && (
                        <>
                          {msg.streaming && msg.status && (
                            <div className="status-pill" style={{ marginBottom: 12 }}><div className="spinner" />{msg.status}</div>
                          )}
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                        </>
                      )}
                      {/* Context files */}
                      {msg.contextFiles && msg.contextFiles.length > 0 && (
                        <div className="ctx-files">
                          {msg.contextFiles.map(f => <span key={f} className="ctx-tag">{f}</span>)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={endRef} />
            </div>
          )}

          {/* Composer */}
          <div className="composer">
            <div className="composer-wrap">
              <textarea
                id="composer-input"
                ref={inputRef}
                className="composer-input"
                placeholder={!connected ? 'Connect a repository first…' : streaming ? 'Agent is responding…' : 'Ask about the codebase or request docs…'}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                disabled={!connected || streaming}
                rows={1}
              />
            </div>
            <button
              id="btn-send"
              className="btn-send"
              onClick={handleSend}
              disabled={!connected || streaming || !input.trim()}
              title="Send (Enter)"
            >
              {streaming ? <span className="spinner" style={{ width: 16, height: 16 }} /> : <SendSVG />}
            </button>
          </div>
        </main>

        {/* ════════════════════════════════════════════════════════════════
            RIGHT — PREVIEW
            ════════════════════════════════════════════════════════════════ */}
        <aside className="preview">
          <div className="preview-head">
            <span className="preview-title">
              {activeSection ? SECTIONS.find(s => s.id === activeSection)?.label ?? 'Preview' : 'Doc Preview'}
            </span>
          </div>

          <div className="preview-toolbar">
            <button id="tab-preview" className={`tab-btn${previewTab === 'preview' ? ' active' : ''}`} onClick={() => setPreviewTab('preview')}>Preview</button>
            <button id="tab-raw"     className={`tab-btn${previewTab === 'raw'     ? ' active' : ''}`} onClick={() => setPreviewTab('raw')}>Raw MD</button>
            <div className="toolbar-actions">
              <button id="btn-copy" className={`icon-btn${copied ? ' copied' : ''}`} onClick={handleCopy} disabled={!previewMd} title={copied ? 'Copied!' : 'Copy markdown'}>
                {copied ? <CheckSVG /> : <CopySVG />}
              </button>
              <button id="btn-download" className="icon-btn" onClick={handleDownload} disabled={!previewMd} title="Download .md">
                <DownloadSVG />
              </button>
              <button id="btn-push-github" className="icon-btn icon-btn--push" onClick={openPushModal} disabled={!previewMd || !connected} title="Push to GitHub">
                <PushSVG />
              </button>
            </div>
          </div>

          {previewMd ? (
            previewTab === 'preview' ? (
              <div className="preview-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{previewMd}</ReactMarkdown>
              </div>
            ) : (
              <pre className="raw-view">{previewMd}</pre>
            )
          ) : (
            <div className="preview-empty">
              <div className="preview-empty-icon">📝</div>
              <div className="preview-empty-text">
                Generated docs will appear here. Pick a section from the sidebar to draft it.
              </div>
            </div>
          )}
        </aside>
      </div>

      {/* ════════════════════════════════════════════════════════════════
          PUSH TO GITHUB MODAL
          ════════════════════════════════════════════════════════════════ */}
      {showPushModal && (
        <div className="modal-overlay" onClick={() => { if (!pushing) setShowPushModal(false); }}>
          <div className="modal" onClick={e => e.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="modal-title">
            <div className="modal-header">
              <h3 id="modal-title"><GithubSVG /> Push to GitHub</h3>
              <button className="modal-close" onClick={() => setShowPushModal(false)} disabled={pushing} aria-label="Close">✕</button>
            </div>

            <div className="modal-body">
              <label className="modal-label" htmlFor="push-path">File path in repo</label>
              <input
                id="push-path"
                className="modal-input"
                value={pushPath}
                onChange={e => setPushPath(e.target.value)}
                placeholder="README.md"
                disabled={pushing}
              />

              <label className="modal-label" htmlFor="push-commit">Commit message</label>
              <input
                id="push-commit"
                className="modal-input"
                value={pushMsg}
                onChange={e => setPushMsg(e.target.value)}
                placeholder="docs: update documentation via DocuGenius"
                disabled={pushing}
              />

              {pushResult && (
                pushResult.ok ? (
                  <div className="push-success">
                    ✅ Pushed successfully!{' '}
                    {pushResult.url && <a href={pushResult.url} target="_blank" rel="noopener noreferrer">View on GitHub ↗</a>}
                  </div>
                ) : (
                  <div className="push-error">⚠️ {pushResult.err}</div>
                )
              )}
            </div>

            <div className="modal-footer">
              <button className="btn-cancel" onClick={() => setShowPushModal(false)} disabled={pushing}>Cancel</button>
              <button
                id="btn-confirm-push"
                className="btn-confirm-push"
                onClick={handlePush}
                disabled={pushing || !pushPath.trim()}
              >
                {pushing ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Pushing…</> : <><PushSVG /> Push to GitHub</>}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}