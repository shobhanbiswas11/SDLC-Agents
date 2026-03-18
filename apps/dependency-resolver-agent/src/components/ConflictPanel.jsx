import "./ConflictPanel.css";

export default function ConflictPanel({ data }) {
  if (!data) {
    return (
      <div className="conflict-empty fade-in">
        <div className="empty-icon">CA</div>
        <p>Run a scan to check for conflicts</p>
      </div>
    );
  }

  const conflicts = data.conflicts || [];
  const cycles = data.cycles || [];
  const totalPkgs = data.total_packages || 0;
  const conflictCount = data.conflict_count || 0;

  return (
    <div className="conflict-panel fade-in">
      <div className="conflict-header">
        <h2 className="conflict-title">
          <span>CA</span> Conflict Analysis
        </h2>
        <div className="conflict-summary">
          <span
            className={`summary-badge ${conflictCount > 0 ? "danger" : "success"}`}
          >
            {conflictCount > 0
              ? `${conflictCount} conflict${conflictCount > 1 ? "s" : ""} found`
              : "No conflicts"}
          </span>
          <span className="summary-total">{totalPkgs} packages analysed</span>
        </div>
      </div>

      {conflicts.length === 0 && cycles.length === 0 && (
        <div className="conflict-clean">
          <div className="clean-icon">OK</div>
          <h3>All Clear</h3>
          <p>No version conflicts or circular dependencies detected.</p>
        </div>
      )}

      {conflicts.length > 0 && (
        <div className="conflict-list">
          {conflicts.map((c, i) => (
            <div
              key={i}
              className="conflict-card slide-in"
              style={{ animationDelay: `${i * 0.08}s` }}
            >
              <div className="conflict-card-header">
                <span className="conflict-pkg">{c.package}</span>
                <span className="conflict-status-badge">conflict</span>
              </div>
              <div className="conflict-constraints">
                {(c.constraints || []).map((cs, j) => (
                  <code key={j} className="constraint-chip">
                    {cs}
                  </code>
                ))}
              </div>
              {c.sources && c.sources.length > 0 && (
                <div className="conflict-sources">
                  <span className="source-label">Required by:</span>
                  {c.sources.map((s, j) => (
                    <span key={j} className="source-chip">
                      {s}
                    </span>
                  ))}
                </div>
              )}
              {c.description && (
                <p className="conflict-desc">{c.description}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {cycles.length > 0 && (
        <div className="cycles-section">
          <h3 className="section-title">Circular Dependencies</h3>
          {cycles.map((cyc, i) => (
            <div key={i} className="cycle-card">
              <span className="cycle-icon">C</span>
              <span className="cycle-path">{cyc.join(" -> ")}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
