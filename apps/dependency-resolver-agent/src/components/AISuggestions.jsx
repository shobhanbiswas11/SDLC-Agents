import "./AISuggestions.css";

export default function AISuggestions({ data }) {
  if (!data) {
    return (
      <div className="ai-empty fade-in">
        <div className="empty-icon">AI</div>
        <p>Run a scan to get AI-powered insights</p>
      </div>
    );
  }

  const explanations = data.ai_explanations || [];
  const suggestions = data.ai_suggestions || [];
  const hasContent = explanations.length > 0 || suggestions.length > 0;

  return (
    <div className="ai-panel fade-in">
      <div className="ai-header">
        <h2 className="ai-title">
          <span>AI</span> Intelligence Insights
        </h2>
        {!hasContent && (
          <span className="ai-status-badge ok">No issues to analyze</span>
        )}
      </div>

      {!hasContent && (
        <div className="ai-no-content">
          <div className="no-content-icon">OK</div>
          <h3>Everything looks good!</h3>
          <p>No conflicts detected - nothing for AI to analyze.</p>
        </div>
      )}

      {explanations.length > 0 && (
        <div className="ai-section">
          <h3 className="ai-section-title">
            <span className="section-icon">EX</span>
            Conflict Explanations
          </h3>
          {explanations.map((ex, i) => (
            <div
              key={i}
              className="ai-card explanation-card slide-in"
              style={{ animationDelay: `${i * 0.1}s` }}
            >
              <div className="ai-card-header">
                <span className="ai-card-pkg">{ex.package}</span>
                <span className="ai-badge explanation">explanation</span>
              </div>
              <div className="ai-card-body">
                <p>{ex.explanation}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {suggestions.length > 0 && (
        <div className="ai-section">
          <h3 className="ai-section-title">
            <span className="section-icon">UP</span>
            Upgrade Suggestions
          </h3>
          {suggestions.map((s, i) => (
            <div
              key={i}
              className="ai-card suggestion-card slide-in"
              style={{ animationDelay: `${i * 0.1}s` }}
            >
              <div className="ai-card-header">
                <span className="ai-card-pkg">{s.package}</span>
                <span className="ai-badge suggestion">suggestion</span>
              </div>
              <div className="ai-card-body">
                <p>{s.suggestion}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
