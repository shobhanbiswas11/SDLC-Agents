import { useState } from "react";
import RepoScanner from "../components/RepoScanner";
import DependencyGraph from "../components/DependencyGraph";
import ConflictPanel from "../components/ConflictPanel";
import AISuggestions from "../components/AISuggestions";
import { resolveDependencies } from "../services/api";
import "./Dashboard.css";

export default function Dashboard({ activeTab }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleScan = async (repoUrl) => {
    setLoading(true);
    setError(null);
    try {
      const result = await resolveDependencies(repoUrl);
      // If multi-ecosystem, use the first report for now
      if (result.reports) {
        setData(result.reports[0]);
      } else {
        setData(result);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case "scanner":
        return (
          <div className="dashboard-section">
            <RepoScanner onScan={handleScan} loading={loading} />
            {error && (
              <div className="error-banner fade-in">
                <span className="error-icon">!</span>
                <span>{error}</span>
              </div>
            )}
            {data && !loading && (
              <div className="scan-summary fade-in">
                <div className="summary-card">
                  <span className="summary-num">
                    {data.total_packages || (data.dependencies || []).length}
                  </span>
                  <span className="summary-label">Packages</span>
                </div>
                <div className="summary-card">
                  <span className="summary-num">
                    {data.conflict_count || 0}
                  </span>
                  <span className="summary-label">Conflicts</span>
                </div>
                <div className="summary-card">
                  <span className="summary-num">
                    {(data.root_dependencies || []).length}
                  </span>
                  <span className="summary-label">Root Deps</span>
                </div>
                <div className="summary-card">
                  <span className="summary-num">
                    {(data.cycles || []).length}
                  </span>
                  <span className="summary-label">Cycles</span>
                </div>
              </div>
            )}
          </div>
        );
      case "graph":
        return <DependencyGraph data={data} />;
      case "conflicts":
        return <ConflictPanel data={data} />;
      case "ai":
        return <AISuggestions data={data} />;
      default:
        return null;
    }
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div>
          <h1 className="dashboard-title">Dependency Resolution Platform</h1>
          <p className="dashboard-subtitle">
            Analyze repositories, track dependency risk, and resolve conflicts
            with confidence.
          </p>
        </div>
        {data && (
          <div className="header-eco-badge">
            <span className={`eco-pill eco-${data.ecosystem}`}>
              {data.ecosystem}
            </span>
          </div>
        )}
      </header>

      <main className="dashboard-body">{renderContent()}</main>
    </div>
  );
}
