/**
 * Service-layer wrapper around the Coding Standards Enforcer REST API.
 * Routes are mounted at /api/coding_standards_enforcer/* on the backend.
 */
import { apiClient } from './api';
import type {
  AnalyzeResponse,
  FixAllResponse,
  Language,
  LanguagesResponse,
  RepoBranchesResponse,
  RepoFilesResponse,
  Violation,
} from '@/types';

const PREFIX = '/api/coding_standards_enforcer';

export async function fetchLanguages(): Promise<LanguagesResponse> {
  const { data } = await apiClient.get<LanguagesResponse>(`${PREFIX}/languages`);
  return data;
}

export async function analyzeCode(
  code: string,
  language: Language,
): Promise<AnalyzeResponse> {
  const { data } = await apiClient.post<AnalyzeResponse>(
    `${PREFIX}/analyze`,
    { code, language },
  );
  return data;
}

export async function fixAll(
  code: string,
  language: Language,
  violations: Violation[] = [],
): Promise<FixAllResponse> {
  const { data } = await apiClient.post<FixAllResponse>(
    `${PREFIX}/fix`,
    { code, language, violations },
  );
  return data;
}

export interface PolishResponse {
  fixed_code: string;
  diff: string;
  passes_used: number;
  remaining_violations: Violation[];
  history: Array<Record<string, unknown>>;
}

/**
 * Iterative final-fix on the backend.
 *
 * The backend will:
 *   - run autoflake/isort/autopep8/black in-memory (Python only),
 *   - then loop: analyze → LLM fix → re-format,
 *   - until 0 violations remain or progress stalls (max 8 passes).
 *
 * This replaces the client-side iterative loop because the backend has
 * deterministic formatters that produce truly clean Python output.
 */
export async function polishCode(
  code: string,
  language: Language,
  maxPasses = 5,
): Promise<PolishResponse> {
  const { data } = await apiClient.post<PolishResponse>(
    `${PREFIX}/polish`,
    { code, language, max_passes: maxPasses },
    { timeout: 120_000 }, // backend may make several LLM calls
  );
  return data;
}

export async function loadRepoFiles(payload: {
  repo_url?: string;
  local_path?: string;
  branch?: string;
}): Promise<RepoFilesResponse> {
  const { data } = await apiClient.post<RepoFilesResponse>(
    `${PREFIX}/repo-files`,
    payload,
  );
  return data;
}

export async function fetchBranches(
  repoUrl: string,
): Promise<RepoBranchesResponse> {
  const { data } = await apiClient.post<RepoBranchesResponse>(
    `${PREFIX}/repo-branches`,
    { repo_url: repoUrl },
  );
  return data;
}

export async function applyLinters(repoPath: string) {
  const { data } = await apiClient.post(`${PREFIX}/apply-linters`, {
    repo_path: repoPath,
  });
  return data;
}

export function downloadFixedUrl(repoPath: string) {
  return `${apiClient.baseURL()}${PREFIX}/download-fixed?repo_path=${encodeURIComponent(repoPath)}`;
}
