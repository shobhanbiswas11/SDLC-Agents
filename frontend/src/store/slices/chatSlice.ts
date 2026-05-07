import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type {
  ApprovalPayload,
  ChatEntry,
  ChatSessionState,
  Language,
  SessionStatus,
  WSFrame,
} from '@/types';

const initialState: ChatSessionState = {
  sessionId: null,
  wsUrl: null,
  status: 'created',
  language: 'python',
  code: '',
  title: null,
  entries: [],
  pendingApproval: null,
  isConnected: false,
  isStreaming: false,
  error: null,
};

const slice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    sessionCreated(
      state,
      {
        payload,
      }: PayloadAction<{
        sessionId: string;
        wsUrl: string;
        language: Language;
        code: string;
        title?: string | null;
      }>,
    ) {
      state.sessionId = payload.sessionId;
      state.wsUrl = payload.wsUrl;
      state.language = payload.language;
      state.code = payload.code;
      state.title = payload.title ?? null;
      state.status = 'created';
      state.entries = [];
      state.pendingApproval = null;
      state.error = null;
    },

    setConnected(state, { payload }: PayloadAction<boolean>) {
      state.isConnected = payload;
      if (payload && state.status === 'created') state.status = 'active';
    },

    setStatus(state, { payload }: PayloadAction<SessionStatus>) {
      state.status = payload;
    },

    setError(state, { payload }: PayloadAction<string | null>) {
      state.error = payload;
    },

    setCode(state, { payload }: PayloadAction<string>) {
      state.code = payload;
    },

    /** Local-only echo — used when the client sends a user message. */
    userMessageSent(state, { payload }: PayloadAction<{ text: string }>) {
      state.entries.push({
        id: crypto.randomUUID(),
        type: 'user_message',
        timestamp: new Date().toISOString(),
        text: payload.text,
        done: true,
      });
    },

    /** Single dispatcher for every inbound WS frame. */
    frameReceived(state, { payload: frame }: PayloadAction<WSFrame>) {
      const { type, payload, message_id, timestamp, done } = frame;

      switch (type) {
        case 'analyze_event':
        case 'polish_event': {
          const entry: ChatEntry = {
            id: message_id,
            type,
            timestamp,
            stage: payload.stage,
            text: payload.text,
            violations: payload.violations,
            done: true,
          };
          state.entries.push(entry);
          break;
        }

        case 'agent_message': {
          if (payload.delta !== undefined) {
            const last = state.entries[state.entries.length - 1];
            if (last && last.type === 'agent_message' && !last.done) {
              last.text = (last.text || '') + payload.delta;
              last.done = done;
            } else {
              state.entries.push({
                id: message_id,
                type,
                timestamp,
                text: payload.delta,
                done,
              });
            }
            state.isStreaming = !done;
          } else if (payload.text !== undefined) {
            state.entries.push({
              id: message_id,
              type,
              timestamp,
              text: payload.text,
              done: true,
            });
            state.isStreaming = false;
          }
          break;
        }

        case 'approval_request': {
          const approval = payload as ApprovalPayload;
          state.pendingApproval = approval;
          state.status = 'pending_approval';
          state.entries.push({
            id: message_id,
            type,
            timestamp,
            approval,
            done: true,
          });
          break;
        }

        case 'system': {
          if (payload.kind === 'fix_applied' && typeof payload.code === 'string') {
            state.code = payload.code;
            state.pendingApproval = null;
            state.status = 'active';
          }
          state.entries.push({
            id: message_id,
            type,
            timestamp,
            text: payload.text,
            done: true,
          });
          break;
        }

        case 'error': {
          state.entries.push({
            id: message_id,
            type,
            timestamp,
            text: payload.text,
            done: true,
          });
          state.error = payload.text;
          break;
        }

        case 'user_message': {
          state.entries.push({
            id: message_id,
            type,
            timestamp,
            text: payload.text,
            done: true,
          });
          break;
        }

        default:
          break;
      }
    },

    approvalDecided(state) {
      state.pendingApproval = null;
      state.status = 'active';
    },

    reset() {
      return initialState;
    },
  },
});

export const chatActions = slice.actions;
export default slice.reducer;
