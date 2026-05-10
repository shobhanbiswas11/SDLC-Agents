import { useState } from "react";

/**
 * RepoInput — Accepts a GitHub URL or local path for build orchestration.
 * Features:
 *   - GitHub URL mode (default): URL + branch selector
 *   - Local path mode (advanced toggle)
 *   - Input validation
 */
function RepoInput({ onSubmit, loading }) {
  const [mode, setMode] = useState("github"); // "github" | "local"
  const [githubUrl, setGithubUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [localPath, setLocalPath] = useState("");

  const isValidGithubUrl = (url) => {
    return /^https?:\/\/(www\.)?github\.com\/[\w.-]+\/[\w.-]+/.test(url);
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (mode === "github") {
      if (!githubUrl || !isValidGithubUrl(githubUrl)) return;
      onSubmit({ github_url: githubUrl, branch });
    } else {
      if (!localPath) return;
      onSubmit({ project_path: localPath });
    }
  };

  const canSubmit =
    mode === "github"
      ? githubUrl && isValidGithubUrl(githubUrl)
      : localPath.length > 0;

  return (
    <form onSubmit={handleSubmit} className="repo-input">
      {/* Mode Toggle */}
      <div className="mode-toggle">
        <button
          type="button"
          className={`toggle-btn ${mode === "github" ? "active" : ""}`}
          onClick={() => setMode("github")}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
          </svg>
          GitHub
        </button>
        <button
          type="button"
          className={`toggle-btn ${mode === "local" ? "active" : ""}`}
          onClick={() => setMode("local")}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M1 3.5A1.5 1.5 0 012.5 2h3.879a1.5 1.5 0 011.06.44l1.122 1.12A1.5 1.5 0 009.62 4H13.5A1.5 1.5 0 0115 5.5v7a1.5 1.5 0 01-1.5 1.5h-11A1.5 1.5 0 011 12.5v-9z"/>
          </svg>
          Local Path
        </button>
      </div>

      {/* GitHub Mode */}
      {mode === "github" && (
        <div className="input-group">
          <div className="url-input-wrapper">
            <input
              type="url"
              placeholder="https://github.com/user/repo"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              className={`url-input ${githubUrl && !isValidGithubUrl(githubUrl) ? "invalid" : ""}`}
            />
            {githubUrl && !isValidGithubUrl(githubUrl) && (
              <span className="validation-msg">Enter a valid GitHub URL</span>
            )}
          </div>
          <div className="branch-input-wrapper">
            <label>Branch</label>
            <input
              type="text"
              placeholder="main"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              className="branch-input"
            />
          </div>
        </div>
      )}

      {/* Local Mode */}
      {mode === "local" && (
        <div className="input-group">
          <input
            type="text"
            placeholder="/path/to/your/project"
            value={localPath}
            onChange={(e) => setLocalPath(e.target.value)}
            className="url-input"
          />
        </div>
      )}

      {/* Submit */}
      <button
        type="submit"
        disabled={loading || !canSubmit}
        className="submit-btn"
      >
        {loading ? (
          <>
            <span className="spinner"></span>
            Building...
          </>
        ) : (
          <>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M11.251.068a.5.5 0 01.227.58L9.677 6.5H13a.5.5 0 01.364.843l-8 8.5a.5.5 0 01-.842-.49L6.323 9.5H3a.5.5 0 01-.364-.843l8-8.5a.5.5 0 01.615-.089z"/>
            </svg>
            Run Build
          </>
        )}
      </button>
    </form>
  );
}

export default RepoInput;
