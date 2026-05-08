/**
 * Agent types and interfaces for the Agent Garden frontend
 */

export interface Agent {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: AgentCategory;
  endpoint: string;
  version: string;
  status: 'active' | 'inactive' | 'beta';
  tags: string[];
}

export type AgentCategory =
  | 'text_processing'
  | 'data_analysis'
  | 'content_generation'
  | 'code_generation'
  | 'image_processing'
  | 'translation'
  | 'summarization'
  | 'classification'
  | 'extraction'
  | 'other';

export interface AgentRequest {
  [key: string]: any;
}

export interface AgentResponse {
  status: 'success' | 'error' | 'pending';
  data?: any;
  error?: string;
  message?: string;
  timestamp?: string;
}

export interface ExecutionState {
  isLoading: boolean;
  error: string | null;
  result: any;
  timestamp?: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'user';
  createdAt: string;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  hasMore: boolean;
}
