'use client';

import {
  KeyboardEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import { useAppDispatch, useAppSelector } from '@/hooks';
import {
  connectWS,
  createChatSession,
  deleteChatSession,
  disconnectWS,
  sendApproval,
  sendMessage,
} from '@/services/api/chatService';
import { chatActions } from '@/store/slices/chatSlice';
import { codingStandardsActions } from '@/store/slices/codingStandardsSlice';
import type { ChatEntry } from '@/types';

import { Icons } from './icons';
import { renderMarkdown } from './markdown';

/**
 * The HITL chat panel — renders alongside the editor.
 *
 * Lifecycle:
 *   • "Start chat" creates a session over REST, then opens a WebSocket.
 *   • Messages stream in via the redux chat slice.
 *   • Approval frames render with APPROVE / REJECT buttons.
 *   • On approve, the orchestrator pushes a `system { kind: 'fix_applied' }`
 *     frame and the slice copies the polished code back into the editor.
 */
export default function ChatPanel() {
  const dispatch = useAppDispatch();
  const editorCode = useAppSelector((s) => s.codingStandards.code);
  const editorLanguage = useAppSelector((s) => s.codingStandards.language);

  const {
    sessionId,
    entries,
    pendingApproval,
    isConnected,
    status,
    error,
    code: chatCode,
  } = useAppSelector((s) => s.chat);

  const [draft, setDraft] = useState('');
  const [starting, setStarting] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // ── Auto-scroll to bottom on new entry ────────────────────
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [entries.length, pendingApproval]);

  // ── Sync polished code back into the main editor ──────────
  useEffect(() => {
    if (chatCode && chatCode !== editorCode) {
      dispatch(codingStandardsActions.setCode(chatCode));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatCode]);

  // ── Tear down on unmount ──────────────────────────────────
  useEffect(() => {
    return () => {
      disconnectWS();
    };
  }, []);

  const startChat = useCallback(async () => {
    if (!editorCode.trim()) {
      alert('Write or load some code first.');
      return;
    }
    setStarting(true);
    try {
      const sid = await createChatSession(
        dispatch,
        editorCode,
        editorLanguage,
      );
      connectWS(dispatch, sid);
    } catch (e: any) {
      alert('Could not start chat: ' + (e?.detail || e?.message));
    } finally {
      setStarting(false);
    }
  }, [editorCode, editorLanguage, dispatch]);

  const endChat = useCallback(async () => {
    if (sessionId) {
      try {
        await deleteChatSession(sessionId);
      } catch {
        /* ignore */
      }
    }
    disconnectWS();
    dispatch(chatActions.reset());
  }, [sessionId, dispatch]);

  const submitDraft = useCallback(() => {
    const text = draft.trim();
    if (!text) return;
    sendMessage(text);
    setDraft('');
  }, [draft]);

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submitDraft();
    }
  };

  const approve = useCallback(() => {
    if (!pendingApproval) return;
    sendApproval(pendingApproval.approval_id, 'APPROVE');
  }, [pendingApproval]);

  const reject = useCallback(() => {
    if (!pendingApproval) return;
    sendApproval(pendingApproval.approval_id, 'REJECT');
  }, [pendingApproval]);

  const visibleEntries = useMemo(
    () => entries.filter((e) => e.type !== 'approval_request'),
    [entries],
  );

  return (
    <div className="chat-panel">
      <div className="pane-header">
        <span className="pane-title">
          {Icons.chat ?? Icons.code}
          <span>Assistant</span>
        </span>
        <div className="chat-header-right">
          <span
            className={`chat-status ${
              isConnected ? 'connected' : 'disconnected'
            }`}
          >
            {isConnected ? '● live' : status === 'pending_approval' ? '◐ awaiting approval' : '○ offline'}
          </span>
          {sessionId ? (
            <button
              className="chat-end-btn"
              onClick={endChat}
              title="End chat"
            >
              {Icons.x}
              <span>End</span>
            </button>
          ) : (
            <button
              className="chat-start-btn"
              onClick={startChat}
              disabled={starting || !editorCode.trim()}
            >
              {starting ? <span className="spinner" /> : Icons.wrench}
              <span>{starting ? 'Starting…' : 'Start chat'}</span>
            </button>
          )}
        </div>
      </div>

      {error && <div className="chat-error">{error}</div>}

      <div className="chat-scroll" ref={scrollRef}>
        {!sessionId && (
          <div className="chat-empty">
            <p>
              Start a chat to discuss the violations in your code, ask the
              assistant to explain a specific issue, or say <code>fix all</code>{' '}
              to have it polish the code and ask for your approval before
              applying.
            </p>
          </div>
        )}

        {sessionId &&
          visibleEntries.map((entry) => (
            <ChatEntryView key={entry.id} entry={entry} />
          ))}

        {pendingApproval && (
          <div className="approval-card">
            <div className="approval-card-header">
              <span className="approval-tag">REVIEW NEEDED</span>
              <span className="approval-summary">
                {pendingApproval.summary || 'Apply polished fix?'}
              </span>
            </div>
            {pendingApproval.diff && (
              <details className="approval-diff">
                <summary>Show diff</summary>
                <pre>{pendingApproval.diff}</pre>
              </details>
            )}
            {pendingApproval.remaining_violations.length > 0 && (
              <div className="approval-remaining">
                {pendingApproval.remaining_violations.length} violation(s) the
                LLM couldn't resolve.
              </div>
            )}
            <div className="approval-actions">
              <button className="approval-approve" onClick={approve}>
                {Icons.check} Approve
              </button>
              <button className="approval-reject" onClick={reject}>
                {Icons.x} Reject
              </button>
            </div>
          </div>
        )}
      </div>

      {sessionId && (
        <div className="chat-input-wrap">
          <textarea
            className="chat-input"
            placeholder={
              isConnected
                ? 'Ask about a violation, or type "fix all"…'
                : 'Reconnecting…'
            }
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={!isConnected}
            rows={2}
          />
          <button
            className="chat-send-btn"
            onClick={submitDraft}
            disabled={!isConnected || !draft.trim()}
          >
            {Icons.search}
            <span>Send</span>
          </button>
        </div>
      )}
    </div>
  );
}

function ChatEntryView({ entry }: { entry: ChatEntry }) {
  const isUser = entry.type === 'user_message';
  const isAssistant = entry.type === 'agent_message';
  const isPipeline =
    entry.type === 'analyze_event' || entry.type === 'polish_event';
  const isError = entry.type === 'error';

  if (isPipeline) {
    return (
      <div className="chat-pipeline">
        <span className="chat-pipeline-stage">{entry.stage}</span>
        <span className="chat-pipeline-text">{entry.text}</span>
      </div>
    );
  }

  return (
    <div
      className={`chat-bubble ${
        isUser
          ? 'from-user'
          : isAssistant
          ? 'from-assistant'
          : isError
          ? 'from-error'
          : 'from-system'
      }`}
    >
      {!isUser && (
        <div className="chat-author">
          {isAssistant ? 'Assistant' : isError ? 'Error' : 'System'}
        </div>
      )}
      <div className="chat-text">
        {isAssistant ? renderMarkdown(entry.text || '') : entry.text}
      </div>
    </div>
  );
}
