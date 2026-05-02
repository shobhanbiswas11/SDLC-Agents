'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { chat, type ChatRequest } from '@/lib/api';

// ── Icons ── //
const DownloadIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7 10 12 15 17 10" />
    <line x1="12" y1="15" x2="12" y2="3" />
  </svg>
);

const CopyIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="13" height="13" rx="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </svg>
);

const GithubIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12C24 5.37 18.63 0 12 0z" />
  </svg>
);

const FolderIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
  </svg>
);

const BuildIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="12 2 2 7 12 12 22 7 12 2" />
    <polyline points="2 17 12 22 22 17" />
    <polyline points="2 12 12 17 22 12" />
  </svg>
);

const PREVIEW_TABS = ['preview', 'code'] as const;
type PreviewMode = (typeof PREVIEW_TABS)[number];

const TOOLS = [
  { id: 'generate_readme', label: 'Generate README' },
  { id: 'generate_api_docs', label: 'Generate API Docs' },
  { id: 'document_databases', label: 'Document Databases' },
  { id: 'summarize_codebase', label: 'Summarize Codebase' },
  { id: 'describe_architecture', label: 'Architecture Guide' },
] as const;

type ToolId = (typeof TOOLS)[number]['id'];

export default function DocumentBuilder() {
  // Config state
  const [repoMode, setRepoMode] = useState<'github' | 'local'>('local');
  const [repo, setRepo] = useState('');
  const [token, setToken] = useState('');
  const [localPath, setLocalPath] = useState('.');
  const [tool, setTool] = useState<ToolId>('generate_readme');
  const [audience, setAudience] = useState('Developers');
  const [custom, setCustom] = useState('');

  // Generation state
  const [loading, setLoading] = useState(false);
  const [output, setOutput] = useState('');
  const [error, setError] = useState('');
  const [previewTab, setPreviewTab] = useState<PreviewMode>('preview');

  // Copy status
  const [copied, setCopied] = useState(false);

  const sourceValue = repoMode === 'github' ? repo.trim() : localPath.trim();
  const canGenerate = !loading && sourceValue.length > 0;

  const handleGenerate = async () => {
    if (!canGenerate) return;

    setLoading(true);
    setError('');
    setOutput('');
    setCopied(false);

    try {
      const promptParts = [
        `Execute the tool: ${tool}.`,
        `Target audience is ${audience}.`,
        custom.trim() ? `Custom instructions: ${custom.trim()}.` : '',
        'Return ONLY the valid Markdown for the document, nothing else.',
      ].filter(Boolean);

      const prompt = promptParts.join(' ');

      const req: ChatRequest = {
        ...(repoMode === 'github'
          ? { repo, access_token: token }
          : { local_path: localPath }),
        message: prompt,
      };

      const res = await chat(req);
      setOutput(res.answer ?? '');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!output) return;
    try {
      await navigator.clipboard.writeText(output);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError('Copy failed. Your browser may be blocking clipboard access.');
    }
  };

  const handleDownload = () => {
    if (!output) return;

    const blob = new Blob([output], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = tool === 'generate_readme' ? 'README.md' : 'DOCUMENTATION.md';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    URL.revokeObjectURL(url);
  };

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(300px, 350px) 1fr',
        gap: 20,
        alignItems: 'start',
        height: 'calc(100vh - 130px)',
        minHeight: 600,
      }}
    >
      {/* LEFT: Settings */}
      <motion.div initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }}>
        <div className="glass-card" style={{ marginBottom: 16 }}>
          <div className="chrome-bar">
            <div className="chrome-dot red" />
            <div className="chrome-dot yellow" />
            <div className="chrome-dot green" />
            <span className="chrome-title">Source Configuration</span>
          </div>

          <div style={{ padding: '20px 24px' }}>
            <div
              style={{
                display: 'flex',
                background: 'rgba(0,0,0,0.3)',
                borderRadius: 10,
                padding: 4,
                gap: 4,
                marginBottom: 20,
              }}
            >
              {(['github', 'local'] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setRepoMode(mode)}
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    borderRadius: 7,
                    background:
                      repoMode === mode
                        ? 'linear-gradient(135deg, rgba(124,108,248,0.25), rgba(0,229,160,0.1))'
                        : 'transparent',
                    border: repoMode === mode ? '1px solid rgba(124,108,248,0.3)' : '1px solid transparent',
                    color: repoMode === mode ? '#fff' : 'var(--text3)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 11,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 6,
                    textTransform: 'uppercase',
                    letterSpacing: '1px',
                    fontWeight: 600,
                  }}
                >
                  {mode === 'github' ? (
                    <>
                      <GithubIcon /> GitHub
                    </>
                  ) : (
                    <>
                      <FolderIcon /> Local
                    </>
                  )}
                </button>
              ))}
            </div>

            <AnimatePresence mode="wait">
              {repoMode === 'github' ? (
                <motion.div key="gh" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}>
                  <div style={{ marginBottom: 14 }}>
                    <label className="field-label">Repository</label>
                    <input
                      className="field-input"
                      placeholder="user/repo"
                      value={repo}
                      onChange={(e) => setRepo(e.target.value)}
                      disabled={loading}
                    />
                  </div>

                  <div style={{ marginBottom: 14 }}>
                    <label className="field-label">Access Token</label>
                    <input
                      className="field-input"
                      type="password"
                      placeholder="ghp_xxxxxxxxxx"
                      value={token}
                      onChange={(e) => setToken(e.target.value)}
                      disabled={loading}
                    />
                  </div>
                </motion.div>
              ) : (
                <motion.div key="local" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}>
                  <div style={{ marginBottom: 14 }}>
                    <label className="field-label">Workspace Path</label>
                    <input
                      className="field-input"
                      placeholder="/path/to/project"
                      value={localPath}
                      onChange={(e) => setLocalPath(e.target.value)}
                      disabled={loading}
                    />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        <div className="glass-card">
          <div className="chrome-bar">
            <div className="chrome-dot red" />
            <div className="chrome-dot yellow" />
            <div className="chrome-dot green" />
            <span className="chrome-title">Generator Settings</span>
          </div>

          <div style={{ padding: '20px 24px' }}>
            <div style={{ marginBottom: 16 }}>
              <label className="field-label">Document Type</label>
              <div style={{ position: 'relative' }}>
                <select
                  className="field-input"
                  style={{ appearance: 'none' }}
                  value={tool}
                  onChange={(e) => setTool(e.target.value as ToolId)}
                  disabled={loading}
                >
                  {TOOLS.map((t) => (
                    <option key={t.id} value={t.id} style={{ background: '#0d0d20' }}>
                      {t.label}
                    </option>
                  ))}
                </select>
                <div
                  style={{
                    position: 'absolute',
                    right: 14,
                    top: 12,
                    pointerEvents: 'none',
                    color: 'var(--text3)',
                    fontSize: 10,
                  }}
                >
                  ▼
                </div>
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label className="field-label">Target Audience</label>
              <div style={{ position: 'relative' }}>
                <select
                  className="field-input"
                  style={{ appearance: 'none' }}
                  value={audience}
                  onChange={(e) => setAudience(e.target.value)}
                  disabled={loading}
                >
                  <option style={{ background: '#0d0d20' }} value="General User">
                    General User
                  </option>
                  <option style={{ background: '#0d0d20' }} value="Developers">
                    Developers
                  </option>
                  <option style={{ background: '#0d0d20' }} value="System Architects">
                    System Architects
                  </option>
                </select>
                <div
                  style={{
                    position: 'absolute',
                    right: 14,
                    top: 12,
                    pointerEvents: 'none',
                    color: 'var(--text3)',
                    fontSize: 10,
                  }}
                >
                  ▼
                </div>
              </div>
            </div>

            <div style={{ marginBottom: 24 }}>
              <label className="field-label">Custom Instructions</label>
              <textarea
                className="field-input"
                placeholder="e.g. Focus on the core API logic..."
                value={custom}
                onChange={(e) => setCustom(e.target.value)}
                disabled={loading}
                rows={3}
                style={{ resize: 'vertical' }}
              />
            </div>

            <button
              type="button"
              onClick={handleGenerate}
              disabled={!canGenerate}
              className="btn-primary"
              style={{ width: '100%', height: 48, borderRadius: 12 }}
            >
              {loading ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div className="spinner" /> Generating...
                </div>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <BuildIcon /> Generate Document
                </div>
              )}
            </button>
          </div>
        </div>
      </motion.div>

      {/* RIGHT: Preview */}
      <motion.div
        initial={{ opacity: 0, x: 16 }}
        animate={{ opacity: 1, x: 0 }}
        style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
      >
        <div className="glass-card" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          {/* Header */}
          <div className="chrome-bar" style={{ padding: '10px 18px' }}>
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 6 }}>
              {PREVIEW_TABS.map((tab) => (
                <button
                  key={tab}
                  type="button"
                  className={`btn-ghost ${previewTab === tab ? 'active' : ''}`}
                  onClick={() => setPreviewTab(tab)}
                  style={{
                    background: previewTab === tab ? 'rgba(0,0,0,0.4)' : 'transparent',
                    border: previewTab === tab ? '1px solid var(--border)' : '1px solid transparent',
                    color: previewTab === tab ? '#fff' : 'var(--text3)',
                    textTransform: 'uppercase',
                    letterSpacing: '1px',
                  }}
                >
                  {tab}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', gap: 6 }}>
              <button
                type="button"
                className="btn-ghost"
                onClick={handleCopy}
                disabled={!output}
                style={{ width: 80, justifyContent: 'center' }}
              >
                <CopyIcon /> {copied ? 'Copied' : 'Copy'}
              </button>

              <button type="button" className="btn-ghost" onClick={handleDownload} disabled={!output}>
                <DownloadIcon /> Download
              </button>
            </div>
          </div>

          {/* Body */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '32px 40px',
              background: previewTab === 'code' ? 'rgba(0,0,0,0.3)' : 'transparent',
            }}
          >
            {error ? (
              <div
                style={{
                  color: 'var(--rose)',
                  background: 'rgba(255,79,114,0.1)',
                  padding: 16,
                  borderRadius: 8,
                  fontFamily: 'var(--font-mono)',
                  fontSize: 13,
                }}
              >
                ❌ {error}
              </div>
            ) : !output && !loading ? (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  opacity: 0.4,
                }}
              >
                <BuildIcon />
                <div style={{ marginTop: 16, fontFamily: 'var(--font-mono)', fontSize: 13, letterSpacing: '1px' }}>
                  Ready to generate markdown
                </div>
              </div>
            ) : loading ? (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  color: 'var(--sky)',
                }}
              >
                <div
                  className="spinner"
                  style={{
                    width: 32,
                    height: 32,
                    borderWidth: 3,
                    borderColor: 'rgba(56,189,248,0.2)',
                    borderTopColor: 'var(--sky)',
                  }}
                />
                <div
                  style={{
                    marginTop: 24,
                    fontFamily: 'var(--font-mono)',
                    fontSize: 13,
                    letterSpacing: '2px',
                    textTransform: 'uppercase',
                  }}
                >
                  Analyzing Repository...
                </div>
              </div>
            ) : previewTab === 'preview' ? (
              <div className="md-render" style={{ maxWidth: 840, margin: '0 auto' }}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{output}</ReactMarkdown>
              </div>
            ) : (
              <pre
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 13,
                  color: 'var(--text2)',
                  lineHeight: 1.6,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  margin: 0,
                  maxWidth: 840,
                  marginLeft: 'auto',
                  marginRight: 'auto',
                }}
              >
                {output}
              </pre>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
}