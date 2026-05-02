'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { streamChat, chat, type ChatRequest, type StreamEvent } from '@/lib/api';

// ─── Icons ──────────────────────────────────────────────── //
const SendIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
);
const CopyIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </svg>
);
const GithubIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
  </svg>
);
const FolderIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
  </svg>
);
const FileIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" /><polyline points="13 2 13 9 20 9" />
  </svg>
);
const SparkleIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 3l1.88 5.76a1 1 0 0 0 .95.69H21l-4.94 3.59a1 1 0 0 0-.36 1.12L17.58 20 12 16.41 6.42 20l1.88-5.84a1 1 0 0 0-.36-1.12L3 9.45h6.17a1 1 0 0 0 .95-.69L12 3z" />
  </svg>
);

// ─── Types ────────────────────────────────────────────────── //
interface Message {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  contextFiles?: string[];
  streaming?: boolean;
  status?: string;
  ts: number;
}

type RepoMode = 'github' | 'local';

// ─── Helper ───────────────────────────────────────────────── //
function uid() { return Math.random().toString(36).slice(2); }

const SUGGESTED = [
  'What is the overall architecture of this repo?',
  'How does authentication work?',
  'Explain the main entry point and initialization flow.',
  'What external dependencies are used and why?',
  'Generate a summary of available API endpoints.',
];

// ─── Component ────────────────────────────────────────────── //
export default function RAGChat() {
  const [mode, setMode] = useState<RepoMode>('github');
  const [repo, setRepo]       = useState('');
  const [token, setToken]     = useState('');
  const [localPath, setLocal] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput]     = useState('');
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [useStream, setUseStream] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<(() => void) | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const canSubmit = input.trim() && !loading && (
    mode === 'local' ? localPath.trim() : repo.trim()
  );

  const buildRequest = useCallback((): ChatRequest => ({
    ...(mode === 'github' ? { repo, access_token: token } : { local_path: localPath }),
    message: input.trim(),
  }), [mode, repo, token, localPath, input]);

  const handleSubmit = useCallback(async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!canSubmit) return;

    const userMsg: Message = { id: uid(), role: 'user', text: input.trim(), ts: Date.now() };
    const asstId = uid();
    const asstMsg: Message = { id: asstId, role: 'assistant', text: '', streaming: true, ts: Date.now() };

    setMessages(prev => [...prev, userMsg, asstMsg]);
    setInput('');
    setLoading(true);

    const req = buildRequest();

    if (useStream) {
      abortRef.current = streamChat(
        req,
        (evt: StreamEvent) => {
          if (evt.type === 'status') {
            setMessages(prev => prev.map(m => m.id === asstId ? { ...m, status: evt.content } : m));
          } else if (evt.type === 'chunk' && evt.content) {
            setMessages(prev => prev.map(m =>
              m.id === asstId ? { ...m, text: m.text + evt.content } : m
            ));
          } else if (evt.type === 'context_files') {
            setMessages(prev => prev.map(m =>
              m.id === asstId ? { ...m, contextFiles: evt.files } : m
            ));
          } else if (evt.type === 'done') {
            setMessages(prev => prev.map(m => m.id === asstId ? { ...m, streaming: false, status: undefined } : m));
            setLoading(false);
          } else if (evt.type === 'error') {
            setMessages(prev => prev.map(m =>
              m.id === asstId ? { ...m, text: `❌ Error: ${evt.content}`, streaming: false, status: undefined } : m
            ));
            setLoading(false);
          }
        },
        (err) => {
          setMessages(prev => prev.map(m =>
            m.id === asstId ? { ...m, text: `❌ ${err.message}`, streaming: false } : m
          ));
          setLoading(false);
        }
      );
    } else {
      try {
        const res = await chat(req);
        setMessages(prev => prev.map(m =>
          m.id === asstId ? { ...m, text: res.answer, contextFiles: res.context_files, streaming: false } : m
        ));
      } catch (err) {
        setMessages(prev => prev.map(m =>
          m.id === asstId ? { ...m, text: `❌ ${(err as Error).message}`, streaming: false } : m
        ));
      } finally {
        setLoading(false);
      }
    }
  }, [canSubmit, input, buildRequest, useStream]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); }
  };

  const copyMessage = async (id: string, text: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const clearChat = () => {
    abortRef.current?.();
    setMessages([]);
    setLoading(false);
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 20, alignItems: 'start', height: 'calc(100vh - 130px)', minHeight: 600 }}>

      {/* ── LEFT: Config Panel ── */}
      <motion.div initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4 }}>
        <div className="glass-card" style={{ overflow: 'visible' }}>
          <div className="chrome-bar">
            <div className="chrome-dot red" /><div className="chrome-dot yellow" /><div className="chrome-dot green" />
            <span className="chrome-title">RAG Configuration</span>
          </div>
          <div style={{ padding: 20 }}>

            {/* Mode toggle */}
            <div style={{ display: 'flex', background: 'rgba(0,0,0,0.3)', borderRadius: 10, padding: 4, gap: 4, marginBottom: 20 }}>
              {(['github', 'local'] as RepoMode[]).map(m => (
                <button key={m} onClick={() => setMode(m)} style={{
                  flex: 1, padding: '8px 12px', borderRadius: 7,
                  background: mode === m ? 'linear-gradient(135deg, rgba(124,108,248,0.25), rgba(0,229,160,0.1))' : 'transparent',
                  border: mode === m ? '1px solid rgba(124,108,248,0.3)' : '1px solid transparent',
                  color: mode === m ? '#fff' : 'var(--text3)',
                  fontFamily: 'var(--font-mono)', fontSize: 11, cursor: 'pointer',
                  transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                  textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 600,
                }}>
                  {m === 'github' ? <><GithubIcon /> GitHub</> : <><FolderIcon /> Local</>}
                </button>
              ))}
            </div>

            {/* Repo inputs */}
            <AnimatePresence mode="wait">
              {mode === 'github' ? (
                <motion.div key="gh" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.18 }}>
                  <div style={{ marginBottom: 14 }}>
                    <label className="field-label">Repository</label>
                    <input className="field-input" placeholder="owner/repository" value={repo} onChange={e => setRepo(e.target.value)} disabled={loading} />
                  </div>
                  <div style={{ marginBottom: 20 }}>
                    <label className="field-label">Access Token</label>
                    <input className="field-input" type="password" placeholder="ghp_xxxxxxxxxx" value={token} onChange={e => setToken(e.target.value)} disabled={loading} />
                  </div>
                </motion.div>
              ) : (
                <motion.div key="local" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.18 }}>
                  <div style={{ marginBottom: 20 }}>
                    <label className="field-label">Directory Path</label>
                    <input className="field-input" placeholder="/path/to/project" value={localPath} onChange={e => setLocal(e.target.value)} disabled={loading} />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Streaming toggle */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '10px 14px',
              background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border)',
              borderRadius: 10, marginBottom: 20, cursor: 'pointer',
            }} onClick={() => setUseStream(s => !s)}>
              <div>
                <div style={{ fontSize: 13, color: 'var(--text)', fontWeight: 500 }}>Streaming Mode</div>
                <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 2 }}>Real-time SSE response chunks</div>
              </div>
              <div style={{
                width: 38, height: 21, borderRadius: 99,
                background: useStream ? 'linear-gradient(135deg, rgba(124,108,248,0.4), rgba(0,229,160,0.3))' : 'rgba(255,255,255,0.06)',
                border: useStream ? '1px solid rgba(124,108,248,0.5)' : '1px solid var(--border2)',
                position: 'relative', transition: 'all 0.25s',
              }}>
                <div style={{
                  position: 'absolute', top: '50%', transform: `translateY(-50%) translateX(${useStream ? 17 : 3}px)`,
                  width: 13, height: 13, borderRadius: '50%',
                  background: useStream ? 'var(--violet)' : 'var(--text3)',
                  boxShadow: useStream ? '0 0 10px rgba(124,108,248,0.6)' : 'none',
                  transition: 'all 0.25s',
                }} />
              </div>
            </div>

            {/* Suggested prompts */}
            <div>
              <label className="field-label" style={{ marginBottom: 10 }}>Suggested Queries</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {SUGGESTED.map((s, i) => (
                  <motion.button
                    key={i}
                    whileHover={{ scale: 1.01, x: 3 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => setInput(s)}
                    disabled={loading}
                    style={{
                      textAlign: 'left', padding: '8px 12px',
                      background: 'rgba(124,108,248,0.04)', border: '1px solid var(--border)',
                      borderRadius: 8, color: 'var(--text2)',
                      fontFamily: 'var(--font-mono)', fontSize: 11, cursor: 'pointer',
                      lineHeight: 1.4, transition: 'all 0.2s',
                    }}
                    onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.borderColor = 'rgba(124,108,248,0.35)'; (e.currentTarget as HTMLButtonElement).style.color = 'var(--text)'; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border)'; (e.currentTarget as HTMLButtonElement).style.color = 'var(--text2)'; }}
                  >
                    {s}
                  </motion.button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* ── RIGHT: Chat Window ── */}
      <motion.div
        initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4, delay: 0.1 }}
        style={{ display: 'flex', flexDirection: 'column', height: '100%' }}
      >
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          {/* Header */}
          <div className="chrome-bar" style={{ justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div className="chrome-dot red" /><div className="chrome-dot yellow" /><div className="chrome-dot green" />
              <span className="chrome-title">RAG Chat · {mode === 'github' ? repo || 'No repo' : localPath || 'No path'}</span>
            </div>
            {messages.length > 0 && (
              <button onClick={clearChat} className="btn-ghost" style={{ padding: '4px 10px', fontSize: 10 }}>Clear</button>
            )}
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '24px 24px 0', display: 'flex', flexDirection: 'column', gap: 20 }}>
            {messages.length === 0 ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.5 }}
                style={{ margin: 'auto', textAlign: 'center', maxWidth: 340 }}
              >
                <div style={{
                  width: 60, height: 60, borderRadius: 18, margin: '0 auto 20px',
                  background: 'linear-gradient(135deg, rgba(124,108,248,0.2), rgba(0,229,160,0.1))',
                  border: '1px solid rgba(124,108,248,0.3)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  boxShadow: 'var(--glow-violet)',
                }}>
                  <SparkleIcon />
                </div>
                <div style={{ fontFamily: 'var(--font-disp)', fontSize: 20, fontWeight: 700, color: 'var(--text)', marginBottom: 10 }}>
                  RAG-Powered Chat
                </div>
                <div style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.6 }}>
                  Configure a repository on the left and ask anything — architecture, APIs, logic flows, and more.
                </div>
              </motion.div>
            ) : (
              messages.map((msg, i) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: i === messages.length - 1 ? 0 : 0 }}
                  style={{ display: 'flex', flexDirection: msg.role === 'user' ? 'row-reverse' : 'row', gap: 12, alignItems: 'flex-start' }}
                >
                  {/* Avatar */}
                  <div style={{
                    width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
                    background: msg.role === 'user'
                      ? 'linear-gradient(135deg, var(--violet), var(--violet-d))'
                      : 'linear-gradient(135deg, rgba(0,229,160,0.25), rgba(56,189,248,0.15))',
                    border: '1px solid',
                    borderColor: msg.role === 'user' ? 'rgba(124,108,248,0.4)' : 'rgba(0,229,160,0.3)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 11, fontWeight: 700, color: '#fff', fontFamily: 'var(--font-mono)',
                    boxShadow: msg.role === 'user' ? 'var(--glow-violet)' : 'var(--glow-mint)',
                  }}>
                    {msg.role === 'user' ? 'U' : 'AI'}
                  </div>

                  {/* Bubble */}
                  <div style={{ flex: 1, maxWidth: '88%' }}>
                    {msg.role === 'user' ? (
                      <div className="chat-bubble-user">{msg.text}</div>
                    ) : (
                      <div>
                        {/* Status badge */}
                        {msg.streaming && msg.status && (
                          <motion.div
                            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                            style={{
                              display: 'inline-flex', alignItems: 'center', gap: 7,
                              marginBottom: 10, padding: '4px 10px',
                              background: 'rgba(56,189,248,0.08)', border: '1px solid rgba(56,189,248,0.2)',
                              borderRadius: 99, fontFamily: 'var(--font-mono)', fontSize: 10,
                              color: 'var(--sky)', letterSpacing: '1px',
                            }}
                          >
                            <div className="spinner" style={{ width: 10, height: 10, borderWidth: 1.5 }} />
                            {msg.status}
                          </motion.div>
                        )}
                        <div className={`chat-bubble-ai md-render ${msg.streaming && !msg.text ? 'loading' : ''}`}>
                          {msg.text ? (
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                          ) : msg.streaming ? (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text3)' }}>
                              <div className="spinner" />
                              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>Thinking...</span>
                            </div>
                          ) : null}
                          {msg.streaming && msg.text && <span className="blink-cursor" />}
                        </div>
                        {/* Context files */}
                        {msg.contextFiles && msg.contextFiles.length > 0 && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                            style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}
                          >
                            <span style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--font-mono)', width: '100%', letterSpacing: '1px', textTransform: 'uppercase' }}>
                              Context Files
                            </span>
                            {msg.contextFiles.map((f, idx) => (
                              <span key={idx} style={{
                                display: 'inline-flex', alignItems: 'center', gap: 5,
                                padding: '3px 9px', background: 'rgba(0,229,160,0.06)',
                                border: '1px solid rgba(0,229,160,0.15)', borderRadius: 6,
                                fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--mint-d)',
                              }}>
                                <FileIcon />{f.split('/').pop()}
                              </span>
                            ))}
                          </motion.div>
                        )}
                        {/* Copy button */}
                        {!msg.streaming && msg.text && (
                          <button
                            onClick={() => copyMessage(msg.id, msg.text)}
                            className="btn-ghost"
                            style={{ marginTop: 8, padding: '4px 10px', fontSize: 10 }}
                          >
                            <CopyIcon />
                            {copiedId === msg.id ? 'Copied!' : 'Copy'}
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border)', background: 'rgba(0,0,0,0.2)' }}>
            <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
              <textarea
                ref={textareaRef}
                className="field-input"
                placeholder="Ask anything about the codebase... (Shift+Enter for newline)"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading}
                rows={1}
                style={{
                  resize: 'none', minHeight: 44, maxHeight: 140,
                  paddingTop: 12, paddingBottom: 12, flex: 1,
                }}
              />
              <motion.button
                type="submit"
                disabled={!canSubmit}
                whileHover={{ scale: canSubmit ? 1.04 : 1 }}
                whileTap={{ scale: canSubmit ? 0.95 : 1 }}
                className="btn-primary"
                style={{ height: 44, padding: '0 18px', flexShrink: 0, borderRadius: 10 }}
              >
                {loading ? <div className="spinner" /> : <SendIcon />}
              </motion.button>
            </form>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
