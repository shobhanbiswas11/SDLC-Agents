import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type {
  HITLSessionState, ChatEntry, ApprovalRequestPayload,
  SessionStatus, Ecosystem, Strategy, WSFrame, MessageType,
} from '@/types/dependencyResolver';

const initial: HITLSessionState = {
  sessionId:       null,
  wsUrl:           null,
  status:          'created',
  ecosystem:       'pypi',
  manifest:        '',
  strategy:        'stable',
  chatTitle:       null,
  entries:         [],
  pendingApproval: null,
  isConnected:     false,
  isStreaming:     false,
  finalLockfile:   null,
  finalReport:     null,
  error:           null,
};

const slice = createSlice({
  name: 'dependencyResolver',
  initialState: initial,
  reducers: {
    // ── Session setup ────────────────────────────────────────────────────────
    setManifest(state, { payload }: PayloadAction<{ manifest: string; ecosystem: Ecosystem; strategy: Strategy }>) {
      state.manifest  = payload.manifest;
      state.ecosystem = payload.ecosystem;
      state.strategy  = payload.strategy;
    },
    sessionCreated(state, { payload }: PayloadAction<{ sessionId: string; wsUrl: string; title?: string | null }>) {
      state.sessionId = payload.sessionId;
      state.wsUrl     = payload.wsUrl;
      state.status    = 'created';
      state.entries   = [];
      state.chatTitle = payload.title ?? null;
      state.pendingApproval = null;
      state.finalLockfile   = null;
      state.finalReport     = null;
      state.error           = null;
    },
    setChatTitle(state, { payload }: PayloadAction<string>) {
      state.chatTitle = payload;
    },
    setConnected(state, { payload }: PayloadAction<boolean>) {
      state.isConnected = payload;
      if (payload) state.status = 'active';
    },
    setStatus(state, { payload }: PayloadAction<SessionStatus>) {
      state.status = payload;
    },

    // ── Incoming WS frames ───────────────────────────────────────────────────
    frameReceived(state, { payload: frame }: PayloadAction<WSFrame>) {
      const { type, payload, message_id, timestamp, done } = frame;

      switch (type as MessageType) {
        case 'solver_event': {
          const entry: ChatEntry = {
            id: message_id, type, timestamp,
            stage: payload.stage,
            text:  payload.text,
            done:  true,
          };
          state.entries.push(entry);
          break;
        }

        case 'agent_message': {
          if (payload.delta !== undefined) {
            // Streaming fragment — append to last agent_message or create new
            const last = state.entries[state.entries.length - 1];
            if (last && last.type === 'agent_message' && !last.done) {
              last.text  = (last.text || '') + payload.delta;
              last.done  = done;
            } else {
              state.entries.push({
                id: message_id, type, timestamp,
                text: payload.delta,
                done,
              });
            }
            state.isStreaming = !done;
          } else if (payload.text) {
            state.entries.push({ id: message_id, type, timestamp, text: payload.text, done: true });
            state.isStreaming = false;
          }
          break;
        }

        case 'search_event': {
          const entry: ChatEntry = {
            id: message_id, type, timestamp,
            text:          payload.text,
            searchResults: payload.results,
            done:          true,
          };
          state.entries.push(entry);
          break;
        }

        case 'tool_call': {
          state.entries.push({
            id: message_id,
            type,
            timestamp,
            text: `${payload.tool} ${JSON.stringify(payload.args)}`,
            done: true,
          });
          break;
        }

        case 'tool_result': {
          state.entries.push({
            id: message_id,
            type,
            timestamp,
            text: payload.ok ? 'Tool executed successfully' : `Tool error: ${payload.error}`,
            done: true,
          });
          break;
        }

        case 'clarify': {
          state.entries.push({
            id: message_id,
            type,
            timestamp,
            text: payload.text || 'Please clarify your request',
            done: true,
          });
          break;
        }

        case 'approval_request': {
          const approval = payload as ApprovalRequestPayload;
          state.pendingApproval = approval;
          state.status = 'pending_approval';
          state.entries.push({
            id: message_id, type, timestamp, approval, done: true,
          });
          break;
        }

        case 'system': {
          // Title frame: capture but don't render as a chat bubble.
          if (payload.kind === 'title' && typeof payload.title === 'string') {
            state.chatTitle = payload.title;
            break;
          }
          state.entries.push({ id: message_id, type, timestamp, text: payload.text, done: true });
          if (payload.lockfile)       state.finalLockfile = payload.lockfile;
          if (payload.report_markdown) state.finalReport  = payload.report_markdown;
          break;
        }

        case 'error': {
          state.entries.push({ id: message_id, type, timestamp, text: payload.text, done: true });
          state.error = payload.text;
          break;
        }

        case 'user_message': {
          state.entries.push({ id: message_id, type, timestamp, text: payload.text, done: true });
          break;
        }
      }
    },

    // ── Local user message echo ──────────────────────────────────────────────
    userMessageSent(state, { payload }: PayloadAction<{ text: string }>) {
      state.entries.push({
        id:        crypto.randomUUID(),
        type:      'user_message',
        timestamp: new Date().toISOString(),
        text:      payload.text,
        done:      true,
      });
    },

    // ── Approval ─────────────────────────────────────────────────────────────
    approvalDecided(state, { payload }: PayloadAction<'APPROVE' | 'REJECT'>) {
      state.pendingApproval = null;
      state.status = payload === 'APPROVE' ? 'approved' : 'rejected';
    },

    // ── Misc ─────────────────────────────────────────────────────────────────
    reset: () => initial,
    setError(state, { payload }: PayloadAction<string | null>) {
      state.error = payload;
    },
  },
});

export const {
  setManifest,
  sessionCreated,
  setConnected,
  setStatus,
  setChatTitle,
  frameReceived,
  userMessageSent,
  approvalDecided,
  reset,
  setError,
} = slice.actions;

export default slice.reducer;
