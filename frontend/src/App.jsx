import { useState, useRef, useEffect, useMemo, useCallback, lazy, Suspense } from "react";
import "./App.css";

// Lazy-load the heavy diff viewer — only loaded when a card is expanded
const ReactDiffViewer = lazy(() => import("react-diff-viewer-continued"));

const PAGE_SIZE_OPTIONS = [25, 50, 100, 200];
const DEFAULT_PAGE_SIZE = 50;

function App() {
  const [repoUrl, setRepoUrl] = useState("");
  const [localPath, setLocalPath] = useState("");
  const [sourceType, setSourceType] = useState("github");
  const [scanResult, setScanResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState([]);
  const [linterLoading, setLinterLoading] = useState(false);
  const [linterResult, setLinterResult] = useState(null);
  const [expandedCards, setExpandedCards] = useState({});
  const [activeStandard, setActiveStandard] = useState(null);
  const [correctedFiles, setCorrectedFiles] = useState(null);
  const [correctedLoading, setCorrectedLoading] = useState(false);
  const [expandedFiles, setExpandedFiles] = useState({});
  const [copiedKey, setCopiedKey] = useState(null);

  // ── Pagination & Search state ──────────────────────
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [showFilesOverview, setShowFilesOverview] = useState(false);

  // Linter remaining violations pagination
  const [linterPage, setLinterPage] = useState(1);
  const LINTER_PAGE_SIZE = 100;

  const logEndRef = useRef(null);

  // ── Debounce search ────────────────────────────────
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setCurrentPage(1); // reset to page 1 on search
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Auto-scroll logs
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const addLog = useCallback((msg) => {
    const ts = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, { time: ts, message: msg }]);
  }, []);

  const toggleCard = useCallback((globalIndex) => {
    setExpandedCards((prev) => ({ ...prev, [globalIndex]: !prev[globalIndex] }));
  }, []);

  // ── Memoized filtering ────────────────────────────
  const filteredViolations = useMemo(() => {
    if (!scanResult?.violations) return [];

    let result = scanResult.violations;

    // Filter by standard
    if (activeStandard) {
      result = result.filter(
        (v) => (v.rule_standard || "Other") === activeStandard
      );
    }

    // Filter by search query
    if (debouncedSearch) {
      const q = debouncedSearch.toLowerCase();
      result = result.filter(
        (v) =>
          (v.file_relative || v.file || "").toLowerCase().includes(q) ||
          (v.rule_code || "").toLowerCase().includes(q) ||
          (v.violation || v.message || "").toLowerCase().includes(q) ||
          (v.rule_standard || "").toLowerCase().includes(q) ||
          (v.rule_description || "").toLowerCase().includes(q)
      );
    }

    return result;
  }, [scanResult, activeStandard, debouncedSearch]);

  // ── Memoized groupings ────────────────────────────
  const standardGroups = useMemo(() => {
    if (!scanResult?.violations) return {};
    const groups = {};
    scanResult.violations.forEach((v) => {
      const key = v.rule_standard || "Other";
      if (!groups[key]) groups[key] = 0;
      groups[key]++;
    });
    return groups;
  }, [scanResult]);

  const fileGroups = useMemo(() => {
    const groups = {};
    filteredViolations.forEach((v) => {
      const key = v.file_relative || v.file;
      if (!groups[key]) groups[key] = 0;
      groups[key]++;
    });
    return groups;
  }, [filteredViolations]);

  // ── Pagination ────────────────────────────────────
  const totalPages = Math.max(1, Math.ceil(filteredViolations.length / pageSize));

  const paginatedViolations = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredViolations.slice(start, start + pageSize);
  }, [filteredViolations, currentPage, pageSize]);

  // Global index for a paginated item
  const getGlobalIndex = useCallback(
    (localIdx) => (currentPage - 1) * pageSize + localIdx,
    [currentPage, pageSize]
  );

  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(1);
    setExpandedCards({});
  }, [activeStandard]);

  const expandAllOnPage = useCallback(() => {
    const map = {};
    paginatedViolations.forEach((_, i) => {
      map[getGlobalIndex(i)] = true;
    });
    setExpandedCards(map);
  }, [paginatedViolations, getGlobalIndex]);

  const collapseAll = useCallback(() => setExpandedCards({}), []);

  // ── Page navigation helpers ───────────────────────
  const goToPage = useCallback(
    (page) => {
      const clamped = Math.max(1, Math.min(page, totalPages));
      setCurrentPage(clamped);
      setExpandedCards({});
      // Scroll to results
      document.querySelector(".result-section")?.scrollIntoView({ behavior: "smooth", block: "start" });
    },
    [totalPages]
  );

  const renderPagination = () => {
    if (totalPages <= 1) return null;

    // Build a smart page range
    const pages = [];
    const delta = 2;
    const left = Math.max(2, currentPage - delta);
    const right = Math.min(totalPages - 1, currentPage + delta);

    pages.push(1);
    if (left > 2) pages.push("...");
    for (let i = left; i <= right; i++) pages.push(i);
    if (right < totalPages - 1) pages.push("...");
    if (totalPages > 1) pages.push(totalPages);

    return (
      <div className="pagination">
        <button
          className="page-btn"
          disabled={currentPage === 1}
          onClick={() => goToPage(currentPage - 1)}
        >
          ‹ Prev
        </button>

        <div className="page-numbers">
          {pages.map((p, i) =>
            p === "..." ? (
              <span key={`ellipsis-${i}`} className="page-ellipsis">
                …
              </span>
            ) : (
              <button
                key={p}
                className={`page-num ${p === currentPage ? "active" : ""}`}
                onClick={() => goToPage(p)}
              >
                {p}
              </button>
            )
          )}
        </div>

        <button
          className="page-btn"
          disabled={currentPage === totalPages}
          onClick={() => goToPage(currentPage + 1)}
        >
          Next ›
        </button>

        <div className="page-size-selector">
          <label>Per page:</label>
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setCurrentPage(1);
              setExpandedCards({});
            }}
          >
            {PAGE_SIZE_OPTIONS.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>

        <span className="page-info">
          {((currentPage - 1) * pageSize + 1).toLocaleString()}–
          {Math.min(currentPage * pageSize, filteredViolations.length).toLocaleString()}{" "}
          of {filteredViolations.length.toLocaleString()}
        </span>
      </div>
    );
  };

  // ── Streaming scan ────────────────────────────────
  const scanRepo = async () => {
    if (sourceType === "github" && !repoUrl)
      return alert("Please enter a repository URL");
    if (sourceType === "local" && !localPath)
      return alert("Please enter a local directory path");

    setLoading(true);
    setScanResult(null);
    setLinterResult(null);
    setCorrectedFiles(null);
    setExpandedCards({});
    setActiveStandard(null);
    setSearchQuery("");
    setDebouncedSearch("");
    setCurrentPage(1);
    setLogs([]);

    addLog("Starting scan...");

    const payload =
      sourceType === "github"
        ? { repo_url: repoUrl }
        : { local_path: localPath };

    try {
      const res = await fetch("http://127.0.0.1:8000/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const event = JSON.parse(line);
            if (event.type === "log") {
              addLog(event.message);
            } else if (event.type === "result") {
              setScanResult(event.data);
              addLog("Scan complete!");
            } else if (event.type === "error") {
              addLog("Error: " + event.message);
              alert(event.message);
            }
          } catch {
            // ignore malformed lines
          }
        }
      }
    } catch (e) {
      addLog("Fatal error: " + e.message);
      alert("Scan failed: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  // ── Apply linters ─────────────────────────────────
  const applyLinters = async () => {
    if (linterLoading || !scanResult?.repo_path) return;

    setLinterLoading(true);
    setCorrectedFiles(null);
    setLinterPage(1);

    try {
      const res = await fetch("http://127.0.0.1:8000/apply-linters", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_path: scanResult.repo_path }),
      });

      const data = await res.json();

      if (!res.ok) {
        alert(data.detail);
        return;
      }

      setLinterResult(data);

      // Auto-fetch corrected files
      try {
        const params = new URLSearchParams({ repo_path: scanResult.repo_path });
        const corrRes = await fetch(
          `http://127.0.0.1:8000/corrected-files?${params}`
        );
        const corrData = await corrRes.json();
        if (corrRes.ok && corrData.files) {
          setCorrectedFiles(corrData.files);
          // Don't auto-expand all files if there are many
          if (Object.keys(corrData.files).length <= 20) {
            const allExpanded = {};
            Object.keys(corrData.files).forEach((f) => (allExpanded[f] = true));
            setExpandedFiles(allExpanded);
          }
        }
      } catch {
        // silent
      }
    } finally {
      setLinterLoading(false);
    }
  };

  // ── Fetch corrected file contents ─────────────────
  const fetchCorrectedFiles = async () => {
    if (!scanResult?.repo_path) return;
    setCorrectedLoading(true);

    try {
      const params = new URLSearchParams({ repo_path: scanResult.repo_path });
      const res = await fetch(
        `http://127.0.0.1:8000/corrected-files?${params}`
      );
      const data = await res.json();

      if (!res.ok) {
        alert(data.detail || "Failed to fetch files");
        return;
      }

      setCorrectedFiles(data.files);
      if (Object.keys(data.files).length <= 20) {
        const allExpanded = {};
        Object.keys(data.files).forEach((f) => (allExpanded[f] = true));
        setExpandedFiles(allExpanded);
      }
    } catch (e) {
      alert("Failed to load corrected files: " + e.message);
    } finally {
      setCorrectedLoading(false);
    }
  };

  // ── Download zip ──────────────────────────────────
  const downloadFixed = async () => {
    if (!scanResult?.repo_path) return;

    try {
      const params = new URLSearchParams({ repo_path: scanResult.repo_path });
      const res = await fetch(`http://127.0.0.1:8000/download-fixed?${params}`);

      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Download failed");
        return;
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download =
        res.headers.get("content-disposition")?.split("filename=")[1] ||
        "corrected-repo.zip";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert("Download failed: " + e.message);
    }
  };

  // ── Copy helper ───────────────────────────────────
  const copyToClipboard = useCallback((text, key) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    });
  }, []);

  const getSeverityClass = (ruleCode) => {
    if (!ruleCode) return "severity-warning";
    if (ruleCode.startsWith("E9") || ruleCode.startsWith("F8"))
      return "severity-error";
    if (ruleCode.startsWith("F") || ruleCode.startsWith("E7"))
      return "severity-high";
    if (ruleCode.startsWith("W")) return "severity-warning";
    return "severity-medium";
  };

  const getSeverityLabel = (ruleCode) => {
    if (!ruleCode) return "Warning";
    if (ruleCode.startsWith("E9") || ruleCode.startsWith("F8")) return "Error";
    if (ruleCode.startsWith("F") || ruleCode.startsWith("E7")) return "High";
    if (ruleCode.startsWith("W")) return "Warning";
    return "Medium";
  };

  // ── Sorted files for overview ─────────────────────
  const sortedFiles = useMemo(() => {
    return Object.entries(fileGroups).sort((a, b) => b[1] - a[1]);
  }, [fileGroups]);

  // Paginated linter remaining violations
  const paginatedLinterViolations = useMemo(() => {
    if (!linterResult?.violations) return [];
    const start = (linterPage - 1) * LINTER_PAGE_SIZE;
    return linterResult.violations.slice(start, start + LINTER_PAGE_SIZE);
  }, [linterResult, linterPage]);

  const linterTotalPages = linterResult?.violations
    ? Math.max(1, Math.ceil(linterResult.violations.length / LINTER_PAGE_SIZE))
    : 1;

  return (
    <div className="page">
      <div className="card">
        {/* ── Header ─────────────────────────────── */}
        <div className="header-section">
          <h1>AI Coding Standards Enforcer</h1>
          <p className="subtitle">
            Scan repositories for coding standard violations, view detailed
            reports with AI-powered fix suggestions, then auto-apply linters
            &amp; formatters.
          </p>
        </div>

        {/* ── Scan Form ──────────────────────────── */}
        <div className="form-section">
          <div className="source-toggle">
            <button
              className={`toggle-btn ${sourceType === "github" ? "active" : ""}`}
              onClick={() => setSourceType("github")}
            >
              GitHub URL
            </button>
            <button
              className={`toggle-btn ${sourceType === "local" ? "active" : ""}`}
              onClick={() => setSourceType("local")}
            >
              Local Directory
            </button>
          </div>

          {sourceType === "github" ? (
            <div className="input-group">
              <label>GitHub Repository URL</label>
              <input
                placeholder="https://github.com/username/repo"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
              />
            </div>
          ) : (
            <div className="input-group">
              <label>Local Directory Path</label>
              <input
                placeholder="/Users/you/projects/my-repo"
                value={localPath}
                onChange={(e) => setLocalPath(e.target.value)}
              />
            </div>
          )}

          <button className="primary-btn" onClick={scanRepo} disabled={loading}>
            {loading && <span className="spinner" />}
            {loading ? "Scanning…" : "Scan Repository"}
          </button>
        </div>

        {/* ── Live Logs ──────────────────────────── */}
        {logs.length > 0 && (
          <div className="log-panel">
            <div className="log-panel-header">
              <span className="log-panel-title">Scan Logs</span>
              {loading && <span className="log-pulse" />}
            </div>
            <div className="log-panel-body">
              {logs.map((log, i) => (
                <div key={i} className="log-line">
                  <span className="log-time">{log.time}</span>
                  <span className="log-msg">{log.message}</span>
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          </div>
        )}

        {/* ── No Violations ──────────────────────── */}
        {scanResult && !scanResult.violations && (
          <div className="success-box" style={{ marginTop: 32 }}>
            <p>No violations found — your code is clean!</p>
          </div>
        )}

        {/* ── Violations Report ─────────────────── */}
        {scanResult?.violations && (
          <div className="result-section">
            {/* Summary Bar */}
            <div className="result-header">
              <h2>Coding Standards Violations</h2>
              <span className="violation-count">
                {filteredViolations.length.toLocaleString()}
                {activeStandard || debouncedSearch
                  ? ` / ${scanResult.total_violations.toLocaleString()}`
                  : ""}
              </span>
              <div className="header-actions">
                <button className="text-btn" onClick={expandAllOnPage}>
                  Expand Page
                </button>
                <button className="text-btn" onClick={collapseAll}>
                  Collapse All
                </button>
              </div>
            </div>

            {/* Search Bar */}
            <div className="search-section">
              <div className="search-input-wrapper">
                <span className="search-icon">🔍</span>
                <input
                  type="text"
                  className="search-input"
                  placeholder="Search by file, rule code, message, standard…"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                {searchQuery && (
                  <button
                    className="search-clear"
                    onClick={() => {
                      setSearchQuery("");
                      setDebouncedSearch("");
                    }}
                  >
                    ✕
                  </button>
                )}
              </div>
              {debouncedSearch && (
                <span className="search-results-count">
                  {filteredViolations.length.toLocaleString()} result
                  {filteredViolations.length !== 1 ? "s" : ""}
                </span>
              )}
            </div>

            {/* Standards Filter Chips */}
            <div className="standards-summary">
              <h3 className="section-label">Standards Violated</h3>
              <div className="standards-grid">
                <button
                  className={`standard-chip ${!activeStandard ? "active" : ""}`}
                  onClick={() => {
                    setActiveStandard(null);
                    setExpandedCards({});
                    setCurrentPage(1);
                  }}
                >
                  <span className="standard-chip-name">All</span>
                  <span className="standard-chip-count">
                    {scanResult.total_violations.toLocaleString()}
                  </span>
                </button>
                {Object.entries(standardGroups)
                  .sort((a, b) => b[1] - a[1])
                  .map(([standard, count]) => (
                    <button
                      className={`standard-chip ${
                        activeStandard === standard ? "active" : ""
                      }`}
                      key={standard}
                      onClick={() => {
                        setActiveStandard(
                          activeStandard === standard ? null : standard
                        );
                        setExpandedCards({});
                        setCurrentPage(1);
                      }}
                    >
                      <span className="standard-chip-name">{standard}</span>
                      <span className="standard-chip-count">
                        {count.toLocaleString()}
                      </span>
                    </button>
                  ))}
              </div>
            </div>

            {/* Files Overview — collapsible for large datasets */}
            <div className="files-overview">
              <div
                className="files-overview-header"
                onClick={() => setShowFilesOverview((p) => !p)}
              >
                <h3 className="section-label" style={{ margin: 0, cursor: "pointer" }}>
                  Files Affected ({Object.keys(fileGroups).length.toLocaleString()})
                </h3>
                <span className="expand-icon">
                  {showFilesOverview ? "▾" : "▸"}
                </span>
              </div>
              {showFilesOverview && (
                <div className="files-list">
                  {sortedFiles.slice(0, 200).map(([file, count]) => (
                    <div
                      className="file-row"
                      key={file}
                      onClick={() => {
                        setSearchQuery(file);
                      }}
                      title="Click to filter by this file"
                    >
                      <span className="file-icon">📄</span>
                      <span className="file-name">{file}</span>
                      <span className="file-violation-count">
                        {count} violation{count > 1 ? "s" : ""}
                      </span>
                    </div>
                  ))}
                  {sortedFiles.length > 200 && (
                    <div className="files-overflow-note">
                      … and {(sortedFiles.length - 200).toLocaleString()} more
                      files. Use search to find specific files.
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Top Pagination */}
            {renderPagination()}

            {/* Violation Cards — only current page */}
            <div className="violations-list">
              {paginatedViolations.map((v, localIdx) => {
                const globalIdx = getGlobalIndex(localIdx);
                const isExpanded = expandedCards[globalIdx];

                return (
                  <div
                    key={globalIdx}
                    className={`violation-card ${isExpanded ? "expanded" : ""}`}
                  >
                    {/* Card Header */}
                    <div
                      className="violation-card-header"
                      onClick={() => toggleCard(globalIdx)}
                    >
                      <div className="violation-card-top">
                        <span
                          className={`severity-badge ${getSeverityClass(
                            v.rule_code
                          )}`}
                        >
                          {getSeverityLabel(v.rule_code)}
                        </span>
                        <span className="rule-code-badge">{v.rule_code}</span>
                        <span className="file-location">
                          {v.file_relative || v.file}
                          <span className="line-col">
                            :{v.line}:{v.column}
                          </span>
                        </span>
                        <span className="card-index">
                          #{(globalIdx + 1).toLocaleString()}
                        </span>
                        <span className="expand-icon">
                          {isExpanded ? "▾" : "▸"}
                        </span>
                      </div>

                      <div className="violation-card-meta">
                        <span className="standard-tag">
                          {v.rule_standard || "Coding Standard"}
                        </span>
                        <span className="violation-message">{v.violation}</span>
                      </div>
                    </div>

                    {/* Card Body — lazy rendered */}
                    {isExpanded && (
                      <div className="violation-card-body">
                        {/* Rule Info */}
                        <div className="rule-info-section">
                          <div className="rule-info-row">
                            <span className="rule-info-label">Rule</span>
                            <span className="rule-info-value">
                              <strong>{v.rule_code}</strong> —{" "}
                              {v.rule_description || v.violation}
                            </span>
                          </div>
                          <div className="rule-info-row">
                            <span className="rule-info-label">Standard</span>
                            <span className="rule-info-value">
                              {v.rule_standard}
                            </span>
                          </div>
                          <div className="rule-info-row">
                            <span className="rule-info-label">Location</span>
                            <span className="rule-info-value mono">
                              {v.file_relative || v.file} — Line {v.line},
                              Column {v.column}
                            </span>
                          </div>
                        </div>

                        {/* AI Explanation */}
                        {v.explanation && (
                          <div className="explanation-section">
                            <h4 className="section-label">AI Explanation</h4>
                            <p className="explanation-text">{v.explanation}</p>
                          </div>
                        )}

                        {/* Diff View — Lazy loaded */}
                        <div className="diff-section">
                          <h4 className="section-label">Ideal Fix</h4>
                          <div className="diff-labels">
                            <span className="diff-label-original">
                              Current Code
                            </span>
                            <span className="diff-label-fixed">Fixed Code</span>
                          </div>
                          <div className="diff-wrapper">
                            <Suspense
                              fallback={
                                <div className="diff-loading">
                                  <span className="spinner" /> Loading diff…
                                </div>
                              }
                            >
                              <ReactDiffViewer
                                oldValue={v.original_code}
                                newValue={v.suggested_code}
                                splitView
                                useDarkTheme
                              />
                            </Suspense>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Bottom Pagination */}
            {renderPagination()}

            {/* ── Step 2: Apply Linters ─────────── */}
            <div className="linter-section">
              <div className="linter-header">
                <div className="step-badge">Step 2</div>
                <div>
                  <h3 className="linter-title">
                    Apply Linters &amp; Formatters
                  </h3>
                  <p className="linter-desc">
                    Automatically run <strong>autoflake</strong> (remove unused
                    imports), <strong>isort</strong>, <strong>autopep8</strong>,
                    and <strong>black</strong> to fix all formatting and style
                    violations in the cloned repo.
                  </p>
                </div>
              </div>

              <button
                className="linter-btn"
                onClick={applyLinters}
                disabled={linterLoading}
              >
                {linterLoading && <span className="spinner" />}
                {linterLoading
                  ? "Running Linters & Formatters…"
                  : "Run Linters & Formatters"}
              </button>

              {linterResult && (
                <div className="linter-result">
                  <div className="linter-result-header">
                    <span className="linter-result-icon">
                      {linterResult.remaining_violations === 0 ? "✅" : "🔧"}
                    </span>
                    <div>
                      <h4 className="linter-result-title">
                        Linters &amp; Formatters Applied
                      </h4>
                      <p className="linter-result-tools">
                        Tools used:{" "}
                        {linterResult.tools_applied.length > 0
                          ? linterResult.tools_applied.join(", ")
                          : "none available"}
                      </p>
                    </div>
                  </div>

                  <div className="linter-stats">
                    <div className="linter-stat">
                      <span className="linter-stat-number fixed">
                        {(
                          scanResult.total_violations -
                          linterResult.remaining_violations
                        ).toLocaleString()}
                      </span>
                      <span className="linter-stat-label">
                        Violations Fixed
                      </span>
                    </div>
                    <div className="linter-stat">
                      <span className="linter-stat-number remaining">
                        {linterResult.remaining_violations.toLocaleString()}
                      </span>
                      <span className="linter-stat-label">Still Remaining</span>
                    </div>
                  </div>

                  {linterResult.remaining_violations > 0 && (
                    <div className="remaining-list">
                      <h4 className="section-label">
                        Remaining Violations (require manual fix)
                        {linterResult.violations.length > LINTER_PAGE_SIZE && (
                          <span className="remaining-page-info">
                            {" "}
                            — Page {linterPage} of {linterTotalPages}
                          </span>
                        )}
                      </h4>
                      {paginatedLinterViolations.map((v, i) => (
                        <div key={i} className="remaining-item">
                          <span
                            className={`severity-badge ${getSeverityClass(
                              v.rule_code
                            )}`}
                          >
                            {v.rule_code}
                          </span>
                          <span className="remaining-file">
                            {v.file_relative}:{v.line}
                          </span>
                          <span className="remaining-msg">{v.violation}</span>
                        </div>
                      ))}

                      {linterTotalPages > 1 && (
                        <div className="pagination" style={{ marginTop: 16 }}>
                          <button
                            className="page-btn"
                            disabled={linterPage === 1}
                            onClick={() => setLinterPage((p) => p - 1)}
                          >
                            ‹ Prev
                          </button>
                          <span className="page-info">
                            Page {linterPage} of {linterTotalPages} (
                            {linterResult.violations.length.toLocaleString()}{" "}
                            items)
                          </span>
                          <button
                            className="page-btn"
                            disabled={linterPage === linterTotalPages}
                            onClick={() => setLinterPage((p) => p + 1)}
                          >
                            Next ›
                          </button>
                        </div>
                      )}
                    </div>
                  )}

                  {/* ── Download ─────────────────── */}
                  <div className="corrected-actions">
                    <button className="download-btn" onClick={downloadFixed}>
                      <span className="download-icon">⬇</span>
                      Download Corrected Files (.zip)
                    </button>
                    {!correctedFiles && (
                      <button
                        className="corrected-btn"
                        onClick={fetchCorrectedFiles}
                        disabled={correctedLoading}
                      >
                        {correctedLoading && <span className="spinner" />}
                        {correctedLoading
                          ? "Loading…"
                          : "Reload Corrected Code"}
                      </button>
                    )}
                  </div>

                  {/* ── Corrected Files Viewer ─────── */}
                  {correctedFiles && (
                    <div className="corrected-files-section">
                      <div className="corrected-files-header">
                        <h4 className="section-label">
                          Corrected Files (
                          {Object.keys(correctedFiles).length})
                        </h4>
                        <div className="corrected-header-actions">
                          <button
                            className="text-btn"
                            onClick={() => {
                              const allExp = {};
                              Object.keys(correctedFiles).forEach(
                                (f) => (allExp[f] = true)
                              );
                              setExpandedFiles(allExp);
                            }}
                          >
                            Expand All
                          </button>
                          <button
                            className="text-btn"
                            onClick={() => setExpandedFiles({})}
                          >
                            Collapse All
                          </button>
                          <button
                            className="copy-all-btn"
                            onClick={() => {
                              const all = Object.entries(correctedFiles)
                                .map(
                                  ([path, code]) =>
                                    `# ── ${path} ${"─".repeat(
                                      Math.max(0, 50 - path.length)
                                    )}\n${code}`
                                )
                                .join("\n\n");
                              copyToClipboard(all, "__all__");
                            }}
                          >
                            {copiedKey === "__all__"
                              ? "Copied!"
                              : "Copy All Files"}
                          </button>
                        </div>
                      </div>

                      {Object.entries(correctedFiles).map(
                        ([filePath, code]) => (
                          <div key={filePath} className="corrected-file-card">
                            <div
                              className="corrected-file-header"
                              onClick={() =>
                                setExpandedFiles((prev) => ({
                                  ...prev,
                                  [filePath]: !prev[filePath],
                                }))
                              }
                            >
                              <span className="corrected-file-icon">📄</span>
                              <span className="corrected-file-name">
                                {filePath}
                              </span>
                              <button
                                className="copy-file-btn"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  copyToClipboard(code, filePath);
                                }}
                              >
                                {copiedKey === filePath ? "Copied!" : "Copy"}
                              </button>
                              <span className="expand-icon">
                                {expandedFiles[filePath] ? "▾" : "▸"}
                              </span>
                            </div>
                            {expandedFiles[filePath] && (
                              <div className="corrected-file-body">
                                <pre className="corrected-code-block">
                                  <code>{code}</code>
                                </pre>
                              </div>
                            )}
                          </div>
                        )
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
