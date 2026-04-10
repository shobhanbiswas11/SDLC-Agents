'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  startWorkflow, sendMessage, getWorkflowStatus, stopWorkflow,
  type WorkflowStatusResponse,
} from '@/lib/api';

// ─── Icons ──────────────────────────────────────────────── //
const SendIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
);
const TerminalIcon = () => (
  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="4 17 10 11 4 5" /><line x1="12" y1="19" x2="20" y2="19" />
  </svg>
);
const CheckIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);
const StopIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
    <rect x="4" y="4" width="16" height="16" rx="2" />
  </svg>
);
const ZapIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
  </svg>
);

// ─── Types ───────────────────────────────────────────────── //
interface OpsMessage { role: 'user' | 'agent'; text: string; ts: number; }
type AgentId = 'reviewer' | 'refactor' | 'ops';

const AGENTS: { id: AgentId; label: string; desc: string; color: string }[] = [
  { id: 'reviewer', label: 'Code Reviewer',    desc: 'Analyzes code quality, patterns, and potential issues.',    color: 'var(--violet)' },
  { id: 'refactor', label: 'Refactor Agent',   desc: 'Suggests and applies safe code refactoring operations.',    color: 'var(--mint)' },
  { id: 'ops',      label: 'Universal Agent',  desc: 'General-purpose agent for files, docs, and repo tasks.',   color: 'var(--sky)' },
];

const PIPELINE_STEPS = [
  { id: 'init',    label: 'Init Session' },
  { id: 'context', label: 'Load Context' },
  { id: 'process', label: 'Process' },
  { id: 'respond', label: 'Respond' },
];

type StepStatus = 'waiting' | 'running' | 'done' | 'error';

function uid() { return Math.random().toString(36).slice(2); }

export default function TemporalDashboard() {
  const [selectedAgent, setSelectedAgent] = useState<AgentId>('reviewer');
  const [workspacePath, setWorkspacePath]  = useState('.');
  const [workflowId, setWorkflowId]        = useState<string | null>(null);
  const [messages, setMessages]            = useState<OpsMessage[]>([]);
  const [input, setInput]                  = useState('');
  const [loading, setLoading]              = useState(false);
  const [stepStatuses, setStepStatuses]    = useState<Record<string, StepStatus>>({
    init: 'waiting', context: 'waiting', process: 'waiting', respond: 'waiting',
  });
  const [sessionActive, setSessionActive]  = useState(false);
  const [pollError, setPollError]          = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollRef        = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  /* ── Stop polling on unmount ── */
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  /* ── Step helper ── */
  const setStep = (id: string, status: StepStatus) =>
    setStepStatuses(prev => ({ ...prev, [id]: status }));

  const resetSteps = () =>
    setStepStatuses({ init: 'waiting', context: 'waiting', process: 'waiting', respond: 'waiting' });

  /* ── Start / ensure session ── */
  const ensureSession = useCallback(async (): Promise<string> => {
    if (workflowId) return workflowId;
    setStep('init', 'running');
    const { workflow_id } = await startWorkflow(selectedAgent, workspacePath);
    setWorkflowId(workflow_id);
    setSessionActive(true);
    setStep('init', 'done');
    setStep('context', 'running');
    await new Promise(r => setTimeout(r, 600));
    setStep('context', 'done');
    return workflow_id;
  }, [workflowId, selectedAgent, workspacePath]);

  /* ── Poll for response ── */
  const pollForResponse = useCallback((wfId: string) => {
    setPollError('');
    setStep('process', 'running');

    let attempts = 0;
    const MAX = 60; // 60 × 2s = 2min timeout

    pollRef.current = setInterval(async () => {
      attempts++;
      if (attempts > MAX) {
        clearInterval(pollRef.current!);
        setStep('process', 'error');
        setLoading(false);
        setPollError('Timed out waiting for agent response.');
        return;
      }

      try {
        const data: WorkflowStatusResponse = await getWorkflowStatus(wfId);
        const status = (data.status ?? '').toLowerCase();

        if (data.last_response && (status.includes('waiting') || status.includes('completed') || status === 'idle')) {
          clearInterval(pollRef.current!);
          setStep('process', 'done');
          setStep('respond', 'running');
          await new Promise(r => setTimeout(r, 300));
          setMessages(prev => [...prev, { role: 'agent', text: data.last_response!, ts: Date.now() }]);
          setStep('respond', 'done');
          setLoading(false);
        }
      } catch (err) {
        clearInterval(pollRef.current!);
        setStep('process', 'error');
        setPollError((err as Error).message);
        setLoading(false);
      }
    }, 2000);
  }, []);

  /* ── Submit ── */
  const handleSubmit = useCallback(async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input.trim();
    setInput('');
    setLoading(true);
    resetSteps();
    setMessages(prev => [...prev, { role: 'user', text: userText, ts: Date.now() }]);

    try {
      const wfId = await ensureSession();
      setStep('process', 'running');
      await sendMessage(wfId, userText);
      pollForResponse(wfId);
    } catch (err) {
      setStep('init', 'error');
      setMessages(prev => [...prev, { role: 'agent', text: `❌ ${(err as Error).message}`, ts: Date.now() }]);
      setLoading(false);
    }
  }, [input, loading, ensureSession, pollForResponse]);

  /* ── Terminate ── */
  const terminate = useCallback(async () => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (workflowId) {
      try { await stopWorkflow(workflowId); } catch { /* ignore */ }
    }
    setWorkflowId(null);
    setSessionActive(false);
    resetSteps();
    setLoading(false);
    setPollError('');
  }, [workflowId]);

  const canSubmit = input.trim() && !loading;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 20, alignItems: 'start', height: 'calc(100vh - 130px)', minHeight: 600 }}>

      {/* ── LEFT: Agent Selector ── */}
      <motion.div initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4 }}>
        <div className="glass-card" style={{ marginBottom: 16 }}>
          <div className="chrome-bar">
            <div className="chrome-dot red" /><div className="chrome-dot yellow" /><div className="chrome-dot green" />
            <span className="chrome-title">Agent Selection</span>
          </div>
          <div style={{ padding: 16 }}>
            {AGENTS.map(agent => (
              <motion.button
                key={agent.id}
                whileHover={{ x: 3 }}
                onClick={() => { if (!sessionActive) setSelectedAgent(agent.id); }}
                disabled={sessionActive}
                style={{
                  width: '100%', textAlign: 'left', padding: '12px 14px',
                  borderRadius: 10, marginBottom: 8, cursor: sessionActive ? 'not-allowed' : 'pointer',
                  background: selectedAgent === agent.id ? `linear-gradient(135deg, ${agent.color}18, ${agent.color}08)` : 'rgba(255,255,255,0.02)',
                  border: `1px solid ${selectedAgent === agent.id ? agent.color + '40' : 'var(--border)'}`,
                  transition: 'all 0.2s', opacity: sessionActive && selectedAgent !== agent.id ? 0.4 : 1,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <div style={{ width: 7, height: 7, borderRadius: '50%', background: agent.color,
                    boxShadow: selectedAgent === agent.id ? `0 0 10px ${agent.color}` : 'none' }} />
                  <span style={{ fontSize: 13, fontWeight: 600, color: selectedAgent === agent.id ? '#fff' : 'var(--text2)' }}>
                    {agent.label}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text3)', lineHeight: 1.4, paddingLeft: 15 }}>{agent.desc}</div>
              </motion.button>
            ))}

            <div style={{ marginTop: 16 }}>
              <label className="field-label">Workspace Path</label>
              <input className="field-input" placeholder="." value={workspacePath}
                onChange={e => setWorkspacePath(e.target.value)} disabled={sessionActive} />
            </div>
          </div>
        </div>

        {/* Pipeline Tracker */}
        <div className="glass-card">
          <div className="chrome-bar">
            <div className="chrome-dot red" /><div className="chrome-dot yellow" /><div className="chrome-dot green" />
            <span className="chrome-title">Pipeline</span>
            {sessionActive && (
              <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 10, color: 'var(--mint)', fontFamily: 'var(--font-mono)', letterSpacing: '1px' }}>
                <ZapIcon /> LIVE
              </span>
            )}
          </div>
          <div style={{ padding: '16px 20px' }}>
            {PIPELINE_STEPS.map((step, idx) => {
              const status = stepStatuses[step.id] as StepStatus;
              return (
                <div key={step.id} style={{ display: 'flex', gap: 12, alignItems: 'stretch' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 32 }}>
                    <div className={`step-node ${status}`}>
                      {status === 'done' ? <CheckIcon /> : status === 'running' ? <div className="spinner" style={{ width: 12, height: 12, borderWidth: 1.5 }} /> : idx + 1}
                    </div>
                    {idx < PIPELINE_STEPS.length - 1 && (
                      <div style={{
                        width: 1, flex: 1, minHeight: 16, marginTop: 4,
                        background: status === 'done' ? 'linear-gradient(to bottom, var(--mint), transparent)' : 'var(--border)',
                        transition: 'background 0.4s',
                      }} />
                    )}
                  </div>
                  <div style={{ flex: 1, paddingBottom: idx < PIPELINE_STEPS.length - 1 ? 16 : 0, paddingTop: 5 }}>
                    <div style={{
                      fontSize: 12, fontFamily: 'var(--font-mono)', fontWeight: 500,
                      color: status === 'done' ? 'var(--mint)' : status === 'running' ? '#fff' : status === 'error' ? 'var(--rose)' : 'var(--text3)',
                      transition: 'color 0.3s',
                    }}>
                      {step.label}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Terminate button */}
        <AnimatePresence>
          {sessionActive && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}>
              <button
                onClick={terminate}
                style={{
                  width: '100%', marginTop: 12, padding: '10px',
                  background: 'rgba(255,79,114,0.08)', border: '1px solid rgba(255,79,114,0.25)',
                  borderRadius: 10, color: 'var(--rose)',
                  fontFamily: 'var(--font-mono)', fontSize: 12, cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                  transition: 'all 0.2s',
                }}
                onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,79,114,0.15)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,79,114,0.08)')}
              >
                <StopIcon /> End Session
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* ── RIGHT: Chat Window ── */}
      <motion.div
        initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4, delay: 0.1 }}
        style={{ display: 'flex', flexDirection: 'column', height: '100%' }}
      >
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <div className="chrome-bar" style={{ justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div className="chrome-dot red" /><div className="chrome-dot yellow" /><div className="chrome-dot green" />
              <span className="chrome-title">
                {AGENTS.find(a => a.id === selectedAgent)?.label} · Temporal Session
              </span>
            </div>
            {workflowId && (
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text3)', letterSpacing: '1px' }}>
                ID: {workflowId.slice(0, 16)}…
              </span>
            )}
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '24px 24px 0', display: 'flex', flexDirection: 'column', gap: 20 }}>
            {messages.length === 0 ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.5 }}
                style={{ margin: 'auto', textAlign: 'center', maxWidth: 340 }}
              >
                <div style={{ color: 'var(--border2)', marginBottom: 20 }}><TerminalIcon /></div>
                <div style={{ fontFamily: 'var(--font-disp)', fontSize: 20, fontWeight: 700, color: 'var(--text)', marginBottom: 10 }}>
                  Agent Operations
                </div>
                <div style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.6 }}>
                  Select an agent and send a message to start a Temporal workflow session. The pipeline tracker will update in real-time.
                </div>
              </motion.div>
            ) : (
              messages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
                  style={{ display: 'flex', gap: 12, alignItems: 'flex-start', flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}
                >
                  <div style={{
                    width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
                    background: msg.role === 'user'
                      ? 'linear-gradient(135deg, var(--violet), var(--violet-d))'
                      : `linear-gradient(135deg, ${AGENTS.find(a => a.id === selectedAgent)?.color ?? 'var(--mint)'}30, transparent)`,
                    border: `1px solid ${msg.role === 'user' ? 'rgba(124,108,248,0.4)' : 'rgba(0,229,160,0.3)'}`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 10, fontWeight: 700, color: '#fff', fontFamily: 'var(--font-mono)',
                  }}>
                    {msg.role === 'user' ? 'U' : 'AI'}
                  </div>
                  <div style={{ flex: 1, maxWidth: '88%' }}>
                    {msg.role === 'user' ? (
                      <div className="chat-bubble-user">{msg.text}</div>
                    ) : (
                      <div className="chat-bubble-ai md-render">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                      </div>
                    )}
                  </div>
                </motion.div>
              ))
            )}
            {/* Loading indicator */}
            {loading && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'rgba(0,229,160,0.1)', border: '1px solid rgba(0,229,160,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, color: '#fff', fontFamily: 'var(--font-mono)' }}>AI</div>
                <div className="chat-bubble-ai" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div className="spinner" />
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text2)' }}>Agent processing…</span>
                </div>
              </motion.div>
            )}
            {pollError && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{
                padding: '10px 14px', background: 'rgba(255,79,114,0.08)', border: '1px solid rgba(255,79,114,0.25)',
                borderRadius: 8, fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--rose)',
              }}>
                ⚠ {pollError}
              </motion.div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border)', background: 'rgba(0,0,0,0.2)' }}>
            <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
              <textarea
                className="field-input"
                placeholder={`Ask ${AGENTS.find(a => a.id === selectedAgent)?.label} to perform a task… (Enter to send)`}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }}
                disabled={loading}
                rows={1}
                style={{ resize: 'none', minHeight: 44, maxHeight: 140, paddingTop: 12, paddingBottom: 12, flex: 1 }}
              />
              <motion.button
                type="submit" disabled={!canSubmit}
                whileHover={{ scale: canSubmit ? 1.04 : 1 }} whileTap={{ scale: canSubmit ? 0.95 : 1 }}
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
