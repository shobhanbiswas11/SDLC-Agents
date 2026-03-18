import { useState } from "react";
import "./RepoScanner.css";

export default function RepoScanner({ onScan, loading }) {
  const [repoUrl, setRepoUrl] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (repoUrl.trim()) onScan(repoUrl.trim());
  };

  return (
    <div className="scanner-card fade-in">
      <div className="scanner-header">
        <h2 className="scanner-title">Repository Scanner</h2>
        <p className="scanner-desc">
          Enter a GitHub URL or local path to analyze project dependencies.
        </p>
      </div>

      <form className="scanner-form" onSubmit={handleSubmit}>
        <div className="input-group">
          <span className="input-prefix">SOURCE</span>
          <input
            id="repo-url-input"
            type="text"
            className="scanner-input"
            placeholder="https://github.com/user/repo or /path/to/local/repo"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            disabled={loading}
          />
        </div>

        <button
          id="scan-button"
          type="submit"
          className={`scanner-btn ${loading ? "loading" : ""}`}
          disabled={!repoUrl.trim() || loading}
        >
          {loading ? (
            <>
              <span className="spinner" />
              Analyzing...
            </>
          ) : (
            <>Start Analysis</>
          )}
        </button>
      </form>

      <div className="scanner-hints">
        <span className="hint-label">Sample repositories:</span>
        {[
          "https://github.com/fastapi/fastapi",
          "https://github.com/expressjs/express",
        ].map((url) => (
          <button
            key={url}
            className="hint-chip"
            onClick={() => setRepoUrl(url)}
            disabled={loading}
          >
            {url.split("/").slice(-2).join("/")}
          </button>
        ))}
      </div>
    </div>
  );
}
