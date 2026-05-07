/**
 * Types for the HITL chat layer — mirror backend Pydantic models.
 */
import type { Language, Violation } from './codingStandards';

export type SessionStatus =
  | 'created'
  | 'active'
  | 'pending_approval'
  | 'closed';

export type MessageType =
  | 'user_message'
  | 'agent_message'
  | 'analyze_event'
  | 'polish_event'
  | 'approval_request'
  | 'approval_response'
  | 'system'
  | 'error';

export interface ApprovalPayload {
  approval_id: string;
  session_id: string;
  proposed_code: string;
  diff: string;
  summary: string;
  remaining_violations: Violation[];
}

export interface ChatEntry {
  id: string;
  type: MessageType;
  timestamp: string;
  text?: string;
  stage?: string;
  violations?: Violation[];
  approval?: ApprovalPayload;
  done: boolean;
}

export interface WSFrame {
  type: MessageType;
  session_id: string;
  message_id: string;
  timestamp: string;
  payload: Record<string, any>;
  done: boolean;
}

export interface ChatSessionState {
  sessionId: string | null;
  wsUrl: string | null;
  status: SessionStatus;
  language: Language;
  code: string;
  title: string | null;
  entries: ChatEntry[];
  pendingApproval: ApprovalPayload | null;
  isConnected: boolean;
  isStreaming: boolean;
  error: string | null;
}

export interface CreateSessionResponse {
  session_id: string;
  websocket_url: string;
  status: SessionStatus;
  created_at: string;
}
