// ─── Enums ────────────────────────────────────────────────────────────────────

export type Ecosystem = 'pypi' | 'npm' | 'maven' | 'cargo';
export type Strategy  = 'latest' | 'minimal' | 'stable';
export type SessionStatus =
  | 'created' | 'active' | 'pending_approval'
  | 'approved' | 'rejected' | 'closed';

export type MessageType =
  | 'user_message' | 'agent_message' | 'search_event' | 'solver_event'
  | 'tool_call' | 'tool_result' | 'clarify'
  | 'approval_request' | 'approval_response'
  | 'system' | 'error';

// ─── Core resolver types ──────────────────────────────────────────────────────

export interface ResolvedPackage {
  name: string;
  version: string;
  direct: boolean;
  parents: string[];
  license?: string;
  vulnerabilities: string[];
  deprecated?: boolean;
}

export interface Conflict {
  package: string;
  requested_by: Record<string, string>;
  resolution?: string;
  explanation?: string;
}

export interface SearchResult {
  query: string;
  url: string;
  title: string;
  snippet: string;
  fetched_at: string;
}

export interface ApprovalRequestPayload {
  approval_id: string;
  session_id: string;
  proposed_lockfile: string;
  report_markdown: string;
  conflicts: Conflict[];
  search_citations: SearchResult[];
  stats: {
    resolved: number;
    conflicts: number;
    cves: number;
    license_issues: number;
  };
}

// ─── WebSocket message ────────────────────────────────────────────────────────

export interface WSFrame {
  type: MessageType;
  session_id: string;
  message_id: string;
  timestamp: string;
  payload: Record<string, any>;
  done: boolean;
}

// ─── UI chat message ──────────────────────────────────────────────────────────

export interface ChatEntry {
  id: string;
  type: MessageType;
  timestamp: string;
  // For user / agent messages
  text?: string;
  delta?: string;
  done?: boolean;
  // For solver events
  stage?: string;
  // For search events
  searchResults?: SearchResult[];
  // For approval_request
  approval?: ApprovalRequestPayload;
}

// ─── Session state ────────────────────────────────────────────────────────────

export interface HITLSessionState {
  sessionId: string | null;
  wsUrl: string | null;
  status: SessionStatus;
  ecosystem: Ecosystem;
  manifest: string;
  strategy: Strategy;
  chatTitle: string | null;
  entries: ChatEntry[];
  pendingApproval: ApprovalRequestPayload | null;
  isConnected: boolean;
  isStreaming: boolean;
  finalLockfile: string | null;
  finalReport: string | null;
  error: string | null;
}
