/**
 * Domain types for the Coding Standards Enforcer agent.
 * These mirror the backend's Pydantic schemas.
 */

export type Language =
  | 'python'
  | 'cpp'
  | 'java'
  | 'javascript'
  | 'typescript'
  | 'go'
  | 'rust';

export type Severity = 'error' | 'warning' | 'info';

export interface Violation {
  line: number;
  column: number;
  rule_code: string;
  rule_standard: string;
  rule_description: string;
  message: string;
  severity: Severity;
  original_code: string;
  suggested_code: string;
  explanation: string;
  diff: string;
}

export interface AnalysisSummary {
  total_violations: number;
  by_severity?: Record<Severity, number>;
  overall_quality?: 'excellent' | 'good' | 'fair' | 'poor';
  top_issues?: string[];
  error?: string;
}

export interface AnalyzeResponse {
  language: Language;
  violations: Violation[];
  summary: AnalysisSummary;
}

export interface FixAllResponse {
  explanation: string;
  fixed_code: string;
  diff: string;
}

export interface FileEntry {
  content: string;
  language: string;
  size_bytes: number;
}

export interface RepoFilesResponse {
  repo_path: string;
  total_files: number;
  files: Record<string, FileEntry>;
}

export interface Branch {
  name: string;
  sha: string;
}

export interface RepoBranchesResponse {
  branches: Branch[];
  total: number;
}

export interface LanguageInfo {
  key: Language;
  name: string;
  standards: string[];
  categories: string[];
}

export interface LanguagesResponse {
  languages: LanguageInfo[];
}
