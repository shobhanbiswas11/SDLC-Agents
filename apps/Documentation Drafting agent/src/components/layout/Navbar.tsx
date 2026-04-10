'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { healthCheck } from '@/lib/api';

// ── Icons ── //
function IconDoc() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  );
}

function IconChat() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function IconAgent() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
      <path d="M4.93 4.93a10 10 0 0 0 0 14.14" />
    </svg>
  );
}

function IconBuild() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="16 18 22 12 16 6" />
      <polyline points="8 6 2 12 8 18" />
    </svg>
  );
}

function IconGithub() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
    </svg>
  );
}

// ── Tab definitions ── //
export type AppTab = 'chat' | 'agent' | 'build';

interface NavbarProps {
  activeTab: AppTab;
  onTabChange: (tab: AppTab) => void;
}

const TABS: { id: AppTab; label: string; icon: React.ReactNode; desc: string }[] = [
  { id: 'chat',  label: 'RAG Chat',  icon: <IconChat />,  desc: 'Intelligent code-aware Q&A' },
  { id: 'agent', label: 'Ops Agent', icon: <IconAgent />, desc: 'Temporal workflow sessions' },
  { id: 'build', label: 'Doc Builder', icon: <IconBuild />, desc: 'Generate & export documentation' },
];

export default function Navbar({ activeTab, onTabChange }: NavbarProps) {
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;

    const check = async () => {
      const ok = await healthCheck();
      if (mounted) setOnline(ok);
    };

    check();
    const interval = setInterval(check, 15_000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  return (
    <header style={{
      position: 'sticky',
      top: 0,
      zIndex: 50,
      background: 'rgba(8, 8, 18, 0.82)',
      backdropFilter: 'blur(24px)',
      WebkitBackdropFilter: 'blur(24px)',
      borderBottom: '1px solid var(--border)',
    }}>
      <div style={{
        maxWidth: 1300,
        margin: '0 auto',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        height: 64,
        gap: 32,
      }}>

        {/* ── Brand ── */}
        <motion.div
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}
        >
          <div style={{
            width: 38, height: 38,
            borderRadius: 10,
            background: 'linear-gradient(135deg, var(--violet), var(--mint))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 28px rgba(124,108,248,0.4), 0 0 60px rgba(0,229,160,0.15)',
          }}>
            <IconDoc />
          </div>
          <div>
            <div style={{
              fontFamily: 'var(--font-disp)',
              fontSize: 17,
              fontWeight: 800,
              letterSpacing: '-0.4px',
              background: 'linear-gradient(135deg, #fff 0%, var(--violet-l) 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}>
              DocuGenius
            </div>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 9,
              color: 'var(--text3)',
              letterSpacing: '2px',
              textTransform: 'uppercase',
              marginTop: 1,
            }}>
              AI · Documentation Agent
            </div>
          </div>
        </motion.div>

        {/* ── Nav Tabs ── */}
        <nav style={{ display: 'flex', gap: 4, flex: 1 }}>
          {TABS.map((tab, i) => (
            <motion.button
              key={tab.id}
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.07, duration: 0.4 }}
              onClick={() => onTabChange(tab.id)}
              className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
              data-tooltip={tab.desc}
            >
              {tab.icon}
              {tab.label}
            </motion.button>
          ))}
        </nav>

        {/* ── Status & Links ── */}
        <motion.div
          initial={{ opacity: 0, x: 12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3, duration: 0.5 }}
          style={{ display: 'flex', alignItems: 'center', gap: 14, flexShrink: 0 }}
        >
          {/* Connection Status */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 7,
            background: 'var(--surface2)',
            border: '1px solid var(--border)',
            borderRadius: 99,
            padding: '6px 12px',
            fontFamily: 'var(--font-mono)',
            fontSize: 10,
            color: online === null ? 'var(--text3)' : online ? 'var(--mint)' : 'var(--rose)',
            letterSpacing: '1px',
            textTransform: 'uppercase',
          }}>
            <span
              className="status-dot"
              style={{
                background: online === null ? 'var(--text3)' : online ? 'var(--mint)' : 'var(--rose)',
                boxShadow: online ? '0 0 10px var(--mint)' : online === false ? '0 0 10px var(--rose)' : 'none',
              }}
            />
            <AnimatePresence mode="wait">
              <motion.span
                key={String(online)}
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                transition={{ duration: 0.25 }}
              >
                {online === null ? 'Connecting' : online ? 'API Online' : 'API Offline'}
              </motion.span>
            </AnimatePresence>
          </div>

          {/* GitHub link */}
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-ghost"
            style={{ padding: '7px 10px' }}
            aria-label="GitHub"
          >
            <IconGithub />
          </a>
        </motion.div>
      </div>
    </header>
  );
}
