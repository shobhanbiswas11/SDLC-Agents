import { useState, useEffect } from "react";

/**
 * ApprovalModal — HITL approval interface.
 * Shows error analysis, LLM reasoning, proposed fix, and action buttons.
 * User can approve, reject, or modify the proposed command.
 */
function ApprovalModal({ approval, taskId, onClose }) {
  const [decision, setDecision] = useState(null); // "approve" | "reject" | "modify"
  const [modifiedCommand, setModifiedCommand] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [timeLeft, setTimeLeft] = useState(300); // 5 min timeout

  const apiBase = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

  const fixDetails = approval?.fix_details || {};
  const analysis = fixDetails.analysis || {};
  const reasoning = fixDetails.reasoning || {};
  const bestFix = reasoning.best_fix || {};

  useEffect(() => {
    setModifiedCommand(bestFix.command || "");
  }, [bestFix.command]);

  // Countdown timer
  useEffect(() => {
    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          onClose?.();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [onClose]);

  const formatTime = (s) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  const getRiskColor = (risk) => {
    if (risk === "low") return "#22c55e";
    if (risk === "medium") return "#f59e0b";
    return "#ef4444";
  };

  const getConfidencePct = (c) => Math.round((c || 0) * 100);

  const handleSubmit = async (dec) => {
    setDecision(dec);
    setSubmitting(true);

    try {
      const body = { decision: dec };
      if (dec === "modify") {
        body.modified_command = modifiedCommand;
      }

      await fetch(`${apiBase}/api/hitl/${taskId}/respond`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      onClose?.();
    } catch (err) {
      console.error("HITL response failed:", err);
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="approval-modal">
        {/* Header */}
        <div className="modal-header">
          <div className="modal-title">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" className="shield-icon">
              <path fillRule="evenodd" d="M10 1a.75.75 0 01.57.27l6 7a.75.75 0 01-.07 1.03l-6 5a.75.75 0 01-.96 0l-6-5a.75.75 0 01-.07-1.03l6-7A.75.75 0 0110 1z" clipRule="evenodd"/>
            </svg>
            <span>Approval Required</span>
          </div>
          <div className="timer" style={{ color: timeLeft < 60 ? "#ef4444" : "#94a3b8" }}>
            {formatTime(timeLeft)}
          </div>
        </div>

        {/* Iteration Badge */}
        <div className="iteration-badge">
          Iteration {fixDetails.iteration || "?"}
        </div>

        {/* Error Analysis */}
        <div className="modal-section">
          <h3 className="section-title error-title">Error Analysis</h3>
          <div className="detail-grid">
            <div className="detail-item">
              <span className="detail-label">Type</span>
              <span className="detail-value error-type">{analysis.error_type || "unknown"}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Confidence</span>
              <span className="detail-value">{getConfidencePct(analysis.confidence)}%</span>
            </div>
            <div className="detail-item full-width">
              <span className="detail-label">Message</span>
              <span className="detail-value mono">{analysis.message || "N/A"}</span>
            </div>
          </div>
        </div>

        {/* Hypotheses */}
        {reasoning.hypotheses?.length > 0 && (
          <div className="modal-section">
            <h3 className="section-title">Hypotheses</h3>
            <ul className="hypotheses-list">
              {reasoning.hypotheses.map((h, i) => (
                <li key={i}>
                  <span className="hypothesis-cause">{h.cause}</span>
                  <span className="hypothesis-prob">{Math.round((h.probability || 0) * 100)}%</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Proposed Fix */}
        <div className="modal-section fix-section">
          <h3 className="section-title fix-title">Proposed Fix</h3>
          <div className="detail-grid">
            <div className="detail-item">
              <span className="detail-label">Action</span>
              <span className="detail-value action-badge">{bestFix.action || "N/A"}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Risk</span>
              <span className="detail-value risk-badge" style={{ color: getRiskColor(reasoning.risk) }}>
                {(reasoning.risk || "unknown").toUpperCase()}
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Confidence</span>
              <span className="detail-value">{getConfidencePct(reasoning.confidence)}%</span>
            </div>
          </div>

          {bestFix.explanation && (
            <div className="fix-explanation">
              {bestFix.explanation}
            </div>
          )}

          <div className="command-box">
            <label>Command</label>
            <textarea
              value={modifiedCommand}
              onChange={(e) => setModifiedCommand(e.target.value)}
              rows={2}
              className="command-input"
            />
          </div>
        </div>

        {/* Actions */}
        <div className="modal-actions">
          <button
            onClick={() => handleSubmit("reject")}
            disabled={submitting}
            className="action-btn reject-btn"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M4.646 4.646a.5.5 0 01.708 0L8 7.293l2.646-2.647a.5.5 0 01.708.708L8.707 8l2.647 2.646a.5.5 0 01-.708.708L8 8.707l-2.646 2.647a.5.5 0 01-.708-.708L7.293 8 4.646 5.354a.5.5 0 010-.708z"/>
            </svg>
            Reject
          </button>

          <button
            onClick={() => handleSubmit("modify")}
            disabled={submitting || !modifiedCommand}
            className="action-btn modify-btn"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M12.146.146a.5.5 0 01.708 0l3 3a.5.5 0 010 .708l-10 10a.5.5 0 01-.168.11l-5 2a.5.5 0 01-.65-.65l2-5a.5.5 0 01.11-.168l10-10z"/>
            </svg>
            Modify & Approve
          </button>

          <button
            onClick={() => handleSubmit("approve")}
            disabled={submitting}
            className="action-btn approve-btn"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M13.854 3.646a.5.5 0 010 .708l-7 7a.5.5 0 01-.708 0l-3.5-3.5a.5.5 0 11.708-.708L6.5 10.293l6.646-6.647a.5.5 0 01.708 0z"/>
            </svg>
            Approve
          </button>
        </div>
      </div>
    </div>
  );
}

export default ApprovalModal;
