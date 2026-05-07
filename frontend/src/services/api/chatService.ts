/**
 * HITL chat client — REST session creation + WebSocket lifecycle.
 *
 * The browser keeps one WebSocket alive per session. Reconnects on transient
 * drops up to MAX_RECONNECT_ATTEMPTS times with exponential backoff. The
 * orchestrator replays the persisted history on reconnect, so the UI stays
 * consistent.
 */
import { apiClient } from './api';
import type { AppDispatch } from '@/store';
import { chatActions } from '@/store/slices/chatSlice';
import type {
  CreateSessionResponse,
  Language,
  WSFrame,
} from '@/types';

const PREFIX = '/api/coding_standards_enforcer';
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_BASE = API.replace(/^http/, 'ws');

let _ws: WebSocket | null = null;
let _reconnectAttempts = 0;
let _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let _intentionalClose = false;
let _currentSessionId: string | null = null;
let _currentDispatch: AppDispatch | null = null;
const MAX_RECONNECT_ATTEMPTS = 5;

function _clearReconnectTimer() {
  if (_reconnectTimer !== null) {
    clearTimeout(_reconnectTimer);
    _reconnectTimer = null;
  }
}

function _scheduleReconnect() {
  if (_intentionalClose || !_currentSessionId || !_currentDispatch) return;
  if (_reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    _currentDispatch(chatActions.setError('Connection lost. Please refresh.'));
    return;
  }
  const delay = Math.min(1000 * Math.pow(2, _reconnectAttempts), 30_000);
  _reconnectAttempts++;
  _reconnectTimer = setTimeout(() => {
    if (_currentSessionId && _currentDispatch) {
      connectWS(_currentDispatch, _currentSessionId);
    }
  }, delay);
}

// ── REST ────────────────────────────────────────────────────

export async function createChatSession(
  dispatch: AppDispatch,
  code: string,
  language: Language,
  title?: string,
): Promise<string> {
  try {
    const { data } = await apiClient.post<CreateSessionResponse>(
      `${PREFIX}/session`,
      { code, language, title },
    );
    const wsUrl =
      data.websocket_url ||
      `${WS_BASE}${PREFIX}/chat/${data.session_id}`;
    dispatch(
      chatActions.sessionCreated({
        sessionId: data.session_id,
        wsUrl,
        language,
        code,
        title: title ?? null,
      }),
    );
    return data.session_id;
  } catch (e: any) {
    const msg = e?.detail || e?.message || 'Failed to create session';
    dispatch(chatActions.setError(msg));
    throw e;
  }
}

export async function deleteChatSession(sessionId: string) {
  await apiClient.delete(`${PREFIX}/session/${sessionId}`);
}

// ── WebSocket ──────────────────────────────────────────────

export function connectWS(dispatch: AppDispatch, sessionId: string) {
  _intentionalClose = false;
  _currentSessionId = sessionId;
  _currentDispatch = dispatch;

  if (_ws && _ws.readyState !== WebSocket.CLOSED) {
    try {
      _ws.close();
    } catch {
      /* ignore */
    }
  }

  const url = `${WS_BASE}${PREFIX}/chat/${sessionId}`;
  const ws = new WebSocket(url);
  _ws = ws;

  ws.onopen = () => {
    _reconnectAttempts = 0;
    _clearReconnectTimer();
    dispatch(chatActions.setConnected(true));
  };

  ws.onmessage = (event: MessageEvent) => {
    try {
      const frame = JSON.parse(event.data) as WSFrame;
      dispatch(chatActions.frameReceived(frame));
    } catch {
      /* ignore malformed frames */
    }
  };

  ws.onclose = () => {
    dispatch(chatActions.setConnected(false));
    if (!_intentionalClose) _scheduleReconnect();
  };

  ws.onerror = () => {
    /* the close handler will run shortly after — handle reconnect there */
  };
}

export function disconnectWS() {
  _intentionalClose = true;
  _clearReconnectTimer();
  if (_ws) {
    try {
      _ws.close();
    } catch {
      /* ignore */
    }
    _ws = null;
  }
  _currentSessionId = null;
  _currentDispatch = null;
}

export function sendMessage(text: string) {
  if (!_ws || _ws.readyState !== WebSocket.OPEN || !_currentSessionId) return;
  _ws.send(
    JSON.stringify({
      type: 'user_message',
      session_id: _currentSessionId,
      payload: { text },
    }),
  );
  if (_currentDispatch) {
    _currentDispatch(chatActions.userMessageSent({ text }));
  }
}

export function sendApproval(
  approvalId: string,
  decision: 'APPROVE' | 'REJECT',
  comment?: string,
) {
  if (!_ws || _ws.readyState !== WebSocket.OPEN || !_currentSessionId) return;
  _ws.send(
    JSON.stringify({
      type: 'approval_response',
      session_id: _currentSessionId,
      payload: { approval_id: approvalId, decision, comment },
    }),
  );
  if (_currentDispatch) _currentDispatch(chatActions.approvalDecided());
}
