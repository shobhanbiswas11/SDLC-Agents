/**
 * Dependency Resolver API + WebSocket service.
 * Communicates with the HITL backend at /api/dependency_resolver/...
 */
import { apiClient } from '@/services/api';
import type { AppDispatch } from '@/store';
import type { Ecosystem, Strategy, WSFrame } from '@/types/dependencyResolver';
import {
  sessionCreated, setConnected, frameReceived, setError, setStatus,
} from '@/store/slices/dependencyResolverSlice';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_BASE = API.replace(/^http/, 'ws');

async function ensureBackendHealth(dispatch: AppDispatch) {
  try {
    await apiClient.get('/health');
    return true;
  } catch (error: any) {
    const message = error.response?.data?.detail
      || error.message
      || 'Unable to reach backend';
    dispatch(setError(`Backend unavailable: ${message}`));
    return false;
  }
}

let _ws: WebSocket | null = null;

// ── Reconnection state ──────────────────────────────────────────────────────
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
    _currentDispatch(setError('Connection lost. Please refresh the page.'));
    return;
  }

  const delay = Math.min(1000 * Math.pow(2, _reconnectAttempts), 30000);
  _reconnectAttempts++;

  _reconnectTimer = setTimeout(() => {
    if (_currentSessionId && _currentDispatch) {
      connectWS(_currentDispatch, _currentSessionId);
    }
  }, delay);
}

// ── REST API ──────────────────────────────────────────────────────────────────

/**
 * Create a new resolution session
 */
export async function createSession(
  dispatch: AppDispatch,
  ecosystem: Ecosystem,
  manifest: string,
  strategy: Strategy,
): Promise<string> {
  try {
    if (!await ensureBackendHealth(dispatch)) {
      throw new Error('Backend health check failed');
    }

    const { data } = await apiClient.post('/api/dependency_resolver/session', {
      ecosystem,
      manifest,
      strategy,
    });

    const wsUrl = data.websocket_url
      || `${WS_BASE}/api/dependency_resolver/chat/${data.session_id}`;

    dispatch(sessionCreated({
      sessionId: data.session_id,
      wsUrl,
    }));

    return data.session_id;
  } catch (error: any) {
    const message = error.response?.data?.detail || error.message || 'Failed to create session';
    dispatch(setError(message));
    throw error;
  }
}

/**
 * Get current session state
 */
export async function getSession(sessionId: string) {
  const { data } = await apiClient.get(`/api/dependency_resolver/session/${sessionId}`);
  return data;
}

/**
 * Delete a session on the backend (best-effort).
 */
export async function deleteSession(sessionId: string): Promise<void> {
  try {
    await apiClient.delete(`/api/dependency_resolver/session/${sessionId}`);
  } catch (error) {
    // Backend may have already evicted it; not fatal.
    console.warn('deleteSession failed:', error);
  }
}

// ── WebSocket Chat ───────────────────────────────────────────────────────────

/**
 * Connect to WebSocket chat for a session.
 * Supports automatic reconnection with exponential backoff.
 */
export function connectWS(dispatch: AppDispatch, sessionId: string): WebSocket {
  // Store for reconnection
  _currentDispatch = dispatch;
  _currentSessionId = sessionId;
  _intentionalClose = false;
  _clearReconnectTimer();

  // Close any existing connection
  if (_ws) {
    _intentionalClose = true;
    _ws.close();
    _intentionalClose = false;
    _ws = null;
  }

  const url = `${WS_BASE}/api/dependency_resolver/chat/${sessionId}`;
  const ws = new WebSocket(url);
  _ws = ws;

  ws.onopen = () => {
    _reconnectAttempts = 0;
    dispatch(setConnected(true));
    dispatch(setStatus('active'));
  };

  ws.onclose = () => {
    dispatch(setConnected(false));
    _ws = null;
    if (!_intentionalClose) {
      _scheduleReconnect();
    }
  };

  ws.onerror = (_ev) => {
    dispatch(setConnected(false));
  };

  ws.onmessage = (ev) => {
    try {
      const frame: WSFrame = JSON.parse(ev.data);
      dispatch(frameReceived(frame));
    } catch (error) {
      console.warn('Malformed WebSocket frame:', error);
    }
  };

  return ws;
}

/**
 * Send a user message via WebSocket
 */
export function sendMessage(sessionId: string, text: string): void {
  if (!_ws || _ws.readyState !== WebSocket.OPEN) {
    console.warn('WebSocket not connected');
    return;
  }

  if (text.length > 50000) {
    _currentDispatch?.(setError('Message too large (max 50KB).'));
    return;
  }

  _ws.send(JSON.stringify({
    type: 'user_message',
    session_id: sessionId,
    payload: { text },
  }));
}

/**
 * Send an approval decision via WebSocket (with REST fallback)
 */
export function sendApproval(
  sessionId: string,
  decision: 'APPROVE' | 'REJECT',
  comment?: string,
): void {
  if (!_ws || _ws.readyState !== WebSocket.OPEN) {
    // REST fallback
    apiClient.post(`/api/dependency_resolver/session/${sessionId}/approve`, {
      session_id: sessionId,
      decision,
      comment,
    }).catch(console.error);
    return;
  }

  _ws.send(JSON.stringify({
    type: 'approval_response',
    session_id: sessionId,
    payload: { decision, comment },
  }));
}

/**
 * Disconnect WebSocket (intentional close, no reconnect)
 */
export function disconnectWS(): void {
  _intentionalClose = true;
  _clearReconnectTimer();
  if (_ws) {
    _ws.close();
    _ws = null;
  }
  _currentSessionId = null;
  _currentDispatch = null;
}

/**
 * Check if WebSocket is connected
 */
export function isWSConnected(): boolean {
  return _ws !== null && _ws.readyState === WebSocket.OPEN;
}
