'use client';

import { Suspense, lazy } from 'react';

const LiveEditor = lazy(
  () => import('@/components/agents/CodingStandardsEnforcer/LiveEditor'),
);
const ChatPanel = lazy(
  () => import('@/components/agents/CodingStandardsEnforcer/ChatPanel'),
);

export default function CodingStandardsEnforcerPage() {
  return (
    <div className="page">
      <div className="card">
        <div className="header-section">
          <h1>AI Coding Standards Enforcer</h1>
          <p className="subtitle">
            Multi-language AI agent for code quality: paste a repo or write code
            with real-time standards enforcement for Python, C++, Java, JS/TS,
            Go &amp; Rust. Chat with the assistant to resolve violations
            interactively.
          </p>
        </div>

        <Suspense
          fallback={
            <div style={{ padding: 40, textAlign: 'center' }}>
              <span className="spinner" /> Loading editor…
            </div>
          }
        >
          <LiveEditor />
        </Suspense>

        <Suspense
          fallback={
            <div style={{ padding: 24, textAlign: 'center' }}>
              <span className="spinner" /> Loading assistant…
            </div>
          }
        >
          <ChatPanel />
        </Suspense>
      </div>
    </div>
  );
}
