'use client';

import {
  Suspense,
  lazy,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import { useAppDispatch, useAppSelector } from '@/hooks';
import {
  analyzeCode,
  fetchBranches as apiFetchBranches,
  loadRepoFiles,
  polishCode,
} from '@/services/api/codingStandardsService';
import { codingStandardsActions } from '@/store/slices/codingStandardsSlice';
import { uiActions } from '@/store/slices/uiSlice';
import type { Language, Violation } from '@/types';

import { Icons } from './icons';
import { LANGUAGES, SAMPLE_CODE } from './sampleCode';
import { TreeNode, buildFileTree } from './FileTree';

const MonacoEditor = lazy(() => import('@monaco-editor/react'));

const getSeverityIcon = (sev: string) => {
  if (sev === 'error') return Icons.circleError;
  if (sev === 'warning') return Icons.circleWarn;
  return Icons.circleInfo;
};

const getSeverityClass = (sev: string) => {
  if (sev === 'error') return 'severity-error';
  if (sev === 'warning') return 'severity-high';
  return 'severity-medium';
};

export default function LiveEditor() {
  const dispatch = useAppDispatch();

  const {
    language,
    code,
    analyzing,
    fixing,
    violations,
    summary,
    autoAnalyze,
    repoUrl,
    repoLoading,
    repoFiles,
    activeRepoFile,
    branches,
    selectedBranch,
    branchesLoading,
  } = useAppSelector((s) => s.codingStandards);

  const { showFileTree, fileSearchQuery, expandedViolations } = useAppSelector(
    (s) => s.ui,
  );

  const [showBranchDropdown, setShowBranchDropdown] = useState(false);
  const branchDropdownRef = useRef<HTMLDivElement | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Seed initial code if empty ────────────────────────────
  useEffect(() => {
    if (!code) {
      dispatch(codingStandardsActions.setCode(SAMPLE_CODE[language]));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Auto-analyze on code/language change (debounced) ──────
  const runAnalysis = useCallback(async () => {
    if (!code.trim()) return;
    dispatch(codingStandardsActions.analyzeStart());
    try {
      const data = await analyzeCode(code, language);
      dispatch(
        codingStandardsActions.analyzeSuccess({
          violations: data.violations || [],
          summary: data.summary || { total_violations: 0 },
        }),
      );
    } catch (e: any) {
      dispatch(
        codingStandardsActions.analyzeFailure(
          e?.message || e?.detail || 'Analysis failed',
        ),
      );
      alert(e?.detail || e?.message || 'Analysis failed');
    }
  }, [code, language, dispatch]);

  useEffect(() => {
    if (!autoAnalyze || !code.trim()) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      runAnalysis();
    }, 1500);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [code, language, autoAnalyze, runAnalysis]);

  // ── Fix All → /polish, applied straight to the editor ─────
  // No separate diff/preview component anymore — the polished
  // code lands directly in the editor and the violations panel
  // updates to show whatever the LLM couldn't fix (usually 0).
  const runFixAll = useCallback(async () => {
    if (!code.trim() || !violations?.length) return;
    dispatch(codingStandardsActions.fixStart());
    try {
      const result = await polishCode(code, language, 5);
      dispatch(codingStandardsActions.setCode(result.fixed_code));
      if (result.remaining_violations && result.remaining_violations.length > 0) {
        dispatch(
          codingStandardsActions.analyzeSuccess({
            violations: result.remaining_violations,
            summary: {
              total_violations: result.remaining_violations.length,
              by_severity: { error: 0, warning: 0, info: 0 },
            },
          }),
        );
      } else {
        dispatch(codingStandardsActions.clearAnalysis());
      }
      dispatch(uiActions.resetExpandedViolations());
      // fixStart flipped `fixing` → true; resolve it.
      dispatch(
        codingStandardsActions.fixSuccess({
          explanation: '',
          fixed_code: result.fixed_code,
          diff: result.diff,
        }),
      );
      // Don't show the diff/preview — applied in place.
      dispatch(codingStandardsActions.setShowDiff(false));
    } catch (e: any) {
      dispatch(
        codingStandardsActions.fixFailure(
          e?.message || e?.detail || 'Fix failed',
        ),
      );
      alert(e?.detail || e?.message || 'Fix failed');
    }
  }, [code, language, violations, dispatch]);

  // ── Copy current editor contents ──────────────────────────
  const [copied, setCopied] = useState(false);
  const copyCode = useCallback(async () => {
    if (!code) return;
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(code);
      } else {
        // Older browser fallback.
        const ta = document.createElement('textarea');
        ta.value = code;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (e) {
      alert('Copy failed.');
    }
  }, [code]);

  const handleLanguageChange = (newLang: Language) => {
    dispatch(codingStandardsActions.setLanguage(newLang));
    if (!repoFiles) {
      dispatch(codingStandardsActions.setCode(SAMPLE_CODE[newLang] || ''));
    }
    // Reset to the empty state, not the "code is clean" state.
    dispatch(codingStandardsActions.clearAnalysis());
    dispatch(uiActions.resetExpandedViolations());
  };

  // ── Fetch branches ────────────────────────────────────────
  const fetchBranches = useCallback(
    async (url: string) => {
      if (!url || (!url.startsWith('http') && !url.startsWith('git@'))) return;
      dispatch(codingStandardsActions.branchesLoadStart());
      try {
        const data = await apiFetchBranches(url);
        dispatch(codingStandardsActions.branchesLoaded(data.branches));
      } catch (e) {
        dispatch(codingStandardsActions.branchesFailed());
      }
    },
    [dispatch],
  );

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        branchDropdownRef.current &&
        !branchDropdownRef.current.contains(e.target as Node)
      ) {
        setShowBranchDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // ── Open a single file in the editor ──────────────────────
  const openRepoFile = useCallback(
    (path: string, filesOverride?: typeof repoFiles) => {
      const files = filesOverride || repoFiles;
      if (!files || !files[path]) return;
      const file = files[path];
      dispatch(
        codingStandardsActions.openFile({
          path,
          content: file.content,
          language: (file.language as Language) || 'python',
        }),
      );
      dispatch(uiActions.resetExpandedViolations());
    },
    [repoFiles, dispatch],
  );

  // ── Repo clone + load ─────────────────────────────────────
  const loadRepo = useCallback(
    async (branchOverride?: string) => {
      if (!repoUrl.trim()) {
        alert('Please enter a repository URL or local path');
        return;
      }
      dispatch(codingStandardsActions.repoLoadStart());
      try {
        const isUrl = repoUrl.startsWith('http') || repoUrl.startsWith('git@');
        const branch = branchOverride || selectedBranch;
        const payload: {
          repo_url?: string;
          local_path?: string;
          branch?: string;
        } = isUrl ? { repo_url: repoUrl } : { local_path: repoUrl };
        if (branch && isUrl) payload.branch = branch;

        const data = await loadRepoFiles(payload);
        if (data.total_files === 0) {
          dispatch(codingStandardsActions.repoLoadFailure('No supported source files found.'));
          alert('No supported source files found in this repository.');
          return;
        }

        dispatch(
          codingStandardsActions.repoLoadSuccess({
            files: data.files,
            repoPath: data.repo_path,
          }),
        );
        dispatch(uiActions.setShowFileTree(true));

        if (branches.length === 0 && isUrl) {
          fetchBranches(repoUrl);
        }

        const firstPath = Object.keys(data.files).sort()[0];
        if (firstPath) openRepoFile(firstPath, data.files);
      } catch (e: any) {
        dispatch(
          codingStandardsActions.repoLoadFailure(
            e?.message || e?.detail || 'Failed to load repo',
          ),
        );
        alert('Failed to load repo: ' + (e?.detail || e?.message));
      }
    },
    [repoUrl, selectedBranch, branches.length, fetchBranches, dispatch, openRepoFile],
  );

  const switchBranch = useCallback(
    (branchName: string) => {
      dispatch(codingStandardsActions.setSelectedBranch(branchName));
      setShowBranchDropdown(false);
      loadRepo(branchName);
    },
    [dispatch, loadRepo],
  );

  const closeRepo = useCallback(() => {
    dispatch(codingStandardsActions.closeRepo());
    dispatch(codingStandardsActions.setCode(SAMPLE_CODE[language] || ''));
    setShowBranchDropdown(false);
  }, [dispatch, language]);

  // ── File tree memoization ─────────────────────────────────
  const fileTree = useMemo(() => {
    if (!repoFiles) return null;
    return buildFileTree(repoFiles);
  }, [repoFiles]);

  const filteredFileList = useMemo(() => {
    if (!repoFiles || !fileSearchQuery.trim()) return null;
    const q = fileSearchQuery.toLowerCase();
    return Object.keys(repoFiles)
      .filter((p) => p.toLowerCase().includes(q))
      .sort();
  }, [repoFiles, fileSearchQuery]);

  const fileCount = repoFiles ? Object.keys(repoFiles).length : 0;

  return (
    <div className="live-editor-container">
      {/* ── Repo URL Bar ───────────────────── */}
      <div className="repo-url-bar">
        <div className="repo-url-input-wrap">
          <span className="repo-url-icon">{Icons.gitBranch}</span>
          <input
            className="repo-url-input"
            placeholder="Paste GitHub URL or local path to load files into editor…"
            value={repoUrl}
            onChange={(e) =>
              dispatch(codingStandardsActions.setRepoUrl(e.target.value))
            }
            onKeyDown={(e) => e.key === 'Enter' && loadRepo()}
          />
          {repoFiles && (
            <button className="repo-close-btn" onClick={closeRepo} title="Close repo">
              {Icons.x}
            </button>
          )}
        </div>

        {(repoFiles || branches.length > 0) && (
          <div className="branch-selector" ref={branchDropdownRef}>
            <button
              className="branch-selector-btn"
              onClick={() => {
                if (branches.length === 0 && !branchesLoading) {
                  fetchBranches(repoUrl);
                }
                setShowBranchDropdown((p) => !p);
              }}
              disabled={branchesLoading}
              title="Select branch"
            >
              {Icons.gitBranch}
              <span className="branch-name">
                {branchesLoading ? 'Loading…' : selectedBranch || 'branch'}
              </span>
              {Icons.chevronDown}
            </button>
            {showBranchDropdown && (
              <div className="branch-dropdown">
                <div className="branch-dropdown-header">Switch branch</div>
                {branchesLoading ? (
                  <div className="branch-dropdown-loading">
                    <span className="spinner" /> Fetching branches…
                  </div>
                ) : branches.length === 0 ? (
                  <div className="branch-dropdown-empty">No branches found</div>
                ) : (
                  <div className="branch-dropdown-list">
                    {branches.map((b) => (
                      <button
                        key={b.name}
                        className={`branch-dropdown-item ${
                          selectedBranch === b.name ? 'active' : ''
                        }`}
                        onClick={() => switchBranch(b.name)}
                      >
                        <span className="branch-item-icon">
                          {selectedBranch === b.name ? Icons.check : Icons.gitBranch}
                        </span>
                        <span className="branch-item-name">{b.name}</span>
                        <span className="branch-item-sha">{b.sha}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <button
          className="repo-load-btn"
          onClick={() => loadRepo()}
          disabled={repoLoading || !repoUrl.trim()}
        >
          {repoLoading && <span className="spinner" />}
          {repoLoading ? 'Cloning…' : 'Load Repo'}
        </button>
      </div>

      {/* ── Toolbar ─────────────────────── */}
      <div className="editor-toolbar">
        <div className="toolbar-left">
          <div className="lang-selector">
            <label>Language</label>
            <select
              value={language}
              onChange={(e) => handleLanguageChange(e.target.value as Language)}
            >
              {LANGUAGES.map((l) => (
                <option key={l.key} value={l.key}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>
          <div className="auto-toggle">
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={autoAnalyze}
                onChange={(e) =>
                  dispatch(codingStandardsActions.setAutoAnalyze(e.target.checked))
                }
              />
              <span className="toggle-slider" />
              Auto-analyze
            </label>
          </div>
          {activeRepoFile && (
            <span className="active-file-badge" title={activeRepoFile}>
              {Icons.fileCode}
              <span>{activeRepoFile.split('/').pop()}</span>
            </span>
          )}
        </div>
        <div className="toolbar-right">
          <button
            className="analyze-btn"
            onClick={runAnalysis}
            disabled={analyzing || !code.trim()}
          >
            {analyzing ? <span className="spinner" /> : Icons.search}
            {analyzing ? 'Analyzing…' : 'Analyze'}
          </button>
          {violations && violations.length > 0 && (
            <button className="fix-all-btn" onClick={runFixAll} disabled={fixing}>
              {fixing ? <span className="spinner" /> : Icons.wrench}
              {fixing ? 'Fixing…' : 'Fix All'}
            </button>
          )}
        </div>
      </div>

      {/* ── Summary Bar ─────────────────── */}
      {summary && (
        <div className="analysis-summary">
          <div className="summary-stats">
            <div
              className={`summary-quality quality-${summary.overall_quality || 'unknown'}`}
            >
              {(summary.overall_quality || 'analyzed').toUpperCase()}
            </div>
            <div className="summary-counts">
              <span className="stat-error">
                {summary.by_severity?.error || 0} errors
              </span>
              <span className="stat-warning">
                {summary.by_severity?.warning || 0} warnings
              </span>
              <span className="stat-info">
                {summary.by_severity?.info || 0} info
              </span>
            </div>
            <span className="summary-total">
              {summary.total_violations || 0} total
            </span>
          </div>
          {summary.top_issues && summary.top_issues.length > 0 && (
            <div className="top-issues">
              {summary.top_issues.map((issue, i) => (
                <span key={i} className="issue-chip">
                  {issue}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Main Layout: [File Tree] | Editor | Violations ── */}
      <div className={`editor-main-layout ${repoFiles ? 'with-tree' : ''}`}>
        {repoFiles && showFileTree && (
          <div className="file-tree-pane">
            <div className="pane-header">
              <span className="pane-title">
                {Icons.folder}
                <span>Files ({fileCount})</span>
              </span>
              <button
                className="tree-collapse-btn"
                onClick={() => dispatch(uiActions.setShowFileTree(false))}
                title="Hide file tree"
              >
                {Icons.x}
              </button>
            </div>
            <div className="tree-search">
              <input
                className="tree-search-input"
                placeholder="Search files…"
                value={fileSearchQuery}
                onChange={(e) =>
                  dispatch(uiActions.setFileSearchQuery(e.target.value))
                }
              />
            </div>
            <div className="tree-scroll">
              {fileSearchQuery.trim() && filteredFileList ? (
                filteredFileList.length === 0 ? (
                  <div className="tree-empty">No files match</div>
                ) : (
                  filteredFileList.map((path) => (
                    <div
                      key={path}
                      className={`tree-file ${activeRepoFile === path ? 'active' : ''}`}
                      style={{ paddingLeft: 12 }}
                      onClick={() => openRepoFile(path)}
                      title={path}
                    >
                      <span className="tree-file-icon">{Icons.fileCode}</span>
                      <span className="tree-file-name">{path}</span>
                    </div>
                  ))
                )
              ) : (
                fileTree &&
                Object.entries(fileTree)
                  .sort(([, a], [, b]) => {
                    const aDir = !(a as any).__file;
                    const bDir = !(b as any).__file;
                    if (aDir !== bDir) return aDir ? -1 : 1;
                    return 0;
                  })
                  .map(([name, node]) => (
                    <TreeNode
                      key={name}
                      name={name}
                      node={node as any}
                      depth={0}
                      onFileClick={openRepoFile}
                      activeFile={activeRepoFile}
                    />
                  ))
              )}
            </div>
          </div>
        )}

        {repoFiles && !showFileTree && (
          <button
            className="tree-show-btn"
            onClick={() => dispatch(uiActions.setShowFileTree(true))}
            title="Show file tree"
          >
            {Icons.sidebar}
          </button>
        )}

        <div className="editor-split">
          <div className="editor-pane">
            <div className="pane-header">
              <span className="pane-title">
                {Icons.code}
                <span>{activeRepoFile ? activeRepoFile : 'Code Editor'}</span>
              </span>
              <div className="pane-header-right">
                <button
                  type="button"
                  className={`copy-code-btn ${copied ? 'copied' : ''}`}
                  onClick={copyCode}
                  disabled={!code}
                  title="Copy code"
                >
                  {copied ? Icons.check : Icons.copy}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
                <span className="char-count">
                  {code.length} chars · {code.split('\n').length} lines
                </span>
              </div>
            </div>
            <div className="monaco-wrapper">
              <Suspense
                fallback={
                  <div className="editor-loading">
                    <span className="spinner" /> Loading editor…
                  </div>
                }
              >
                <MonacoEditor
                  height="100%"
                  language={
                    LANGUAGES.find((l) => l.key === language)?.monacoId ||
                    'plaintext'
                  }
                  value={code}
                  onChange={(val) =>
                    dispatch(codingStandardsActions.setCode(val || ''))
                  }
                  theme="vs-dark"
                  options={{
                    fontSize: 14,
                    fontFamily:
                      "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
                    // Off by default — on a narrow pane the minimap renders
                    // a thin vertical artifact near the top-right edge.
                    minimap: { enabled: false },
                    overviewRulerLanes: 0,
                    overviewRulerBorder: false,
                    hideCursorInOverviewRuler: true,
                    scrollBeyondLastLine: false,
                    lineNumbers: 'on',
                    renderLineHighlight: 'all',
                    bracketPairColorization: { enabled: true },
                    formatOnPaste: true,
                    suggestOnTriggerCharacters: true,
                    wordWrap: 'on',
                    padding: { top: 12 },
                  }}
                />
              </Suspense>
            </div>
          </div>

          <div className="violations-pane">
            <div className="pane-header">
              <span className="pane-title">
                {Icons.alertTriangle}
                <span>
                  {violations ? `${violations.length} Violations` : 'Violations'}
                </span>
              </span>
            </div>
            <div className="violations-scroll">
              {!violations && !analyzing && (
                <div className="empty-state">
                  <div className="empty-icon">{Icons.searchLg}</div>
                  <p>
                    Click <strong>Analyze</strong> or enable{' '}
                    <strong>Auto-analyze</strong> to find violations.
                  </p>
                  <p className="empty-hint">
                    Supports Python, C++, Java, JS/TS, Go, Rust
                  </p>
                </div>
              )}
              {analyzing && (
                <div className="analyzing-state">
                  <span className="spinner large" />
                  <p>AI Agent is analyzing your code…</p>
                </div>
              )}
              {violations?.length === 0 && !analyzing && (
                <div className="clean-state">
                  <div className="clean-icon">{Icons.checkCircle}</div>
                  <p>No violations found — code is clean!</p>
                </div>
              )}
              {violations?.map((v: Violation, i: number) => (
                <div
                  key={i}
                  className={`violation-item ${expandedViolations[i] ? 'expanded' : ''}`}
                >
                  <div
                    className="violation-item-header"
                    onClick={() => dispatch(uiActions.toggleExpandedViolation(i))}
                  >
                    <span className="v-icon">{getSeverityIcon(v.severity)}</span>
                    <span className={`v-badge ${getSeverityClass(v.severity)}`}>
                      {v.rule_code}
                    </span>
                    <span className="v-line">L{v.line}</span>
                    <span className="v-msg">{v.message}</span>
                    <span className="expand-icon">
                      {expandedViolations[i] ? Icons.chevronDown : Icons.chevronRight}
                    </span>
                  </div>
                  {expandedViolations[i] && (
                    <div className="violation-item-body">
                      <div className="v-detail">
                        <span className="v-label">Standard</span>
                        <span className="v-value">{v.rule_standard}</span>
                      </div>
                      <div className="v-detail">
                        <span className="v-label">Explanation</span>
                        <span className="v-value">{v.explanation}</span>
                      </div>
                      {v.original_code && (
                        <div className="v-code-block">
                          <div className="v-code-label">Original</div>
                          <pre>{v.original_code}</pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

    </div>
  );
}
