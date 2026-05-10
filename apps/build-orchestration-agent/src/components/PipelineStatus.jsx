/**
 * PipelineStatus — Visual pipeline showing the current step in the agent loop.
 * Steps: Clone → Build → Analyze → Reason → Approve → Fix → Rebuild
 */

const PIPELINE_STEPS = [
  { key: "cloning", label: "Clone", icon: "📥" },
  { key: "building", label: "Build", icon: "🔨" },
  { key: "analyzing", label: "Analyze", icon: "🔍" },
  { key: "reasoning", label: "Reason", icon: "🧠" },
  { key: "awaiting_approval", label: "Approve", icon: "👤" },
  { key: "applying_fix", label: "Fix", icon: "🔧" },
  { key: "rebuilding", label: "Rebuild", icon: "🔄" },
];

const FINAL_STATES = {
  success: { label: "Success", className: "step-success" },
  failed: { label: "Failed", className: "step-failed" },
  timeout: { label: "Timeout", className: "step-timeout" },
  rejected: { label: "Rejected", className: "step-rejected" },
};

function PipelineStatus({ currentStatus, message }) {
  if (!currentStatus || currentStatus === "idle") return null;

  // Find active step index
  const activeIndex = PIPELINE_STEPS.findIndex((s) => s.key === currentStatus);
  const isFinal = FINAL_STATES[currentStatus];

  return (
    <div className="pipeline-status">
      <div className="pipeline-track">
        {PIPELINE_STEPS.map((step, i) => {
          let stepClass = "step";

          if (isFinal) {
            stepClass += " step-done";
          } else if (i < activeIndex) {
            stepClass += " step-done";
          } else if (i === activeIndex) {
            stepClass += " step-active";
          } else {
            stepClass += " step-pending";
          }

          return (
            <div key={step.key} className={stepClass}>
              <div className="step-dot">
                {i < activeIndex || isFinal ? (
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M13.854 3.646a.5.5 0 010 .708l-7 7a.5.5 0 01-.708 0l-3.5-3.5a.5.5 0 11.708-.708L6.5 10.293l6.646-6.647a.5.5 0 01.708 0z"/>
                  </svg>
                ) : i === activeIndex ? (
                  <span className="pulse-dot"></span>
                ) : (
                  <span className="empty-dot"></span>
                )}
              </div>
              <span className="step-label">{step.label}</span>
              {i < PIPELINE_STEPS.length - 1 && <div className="step-connector" />}
            </div>
          );
        })}
      </div>

      {/* Final State Badge */}
      {isFinal && (
        <div className={`final-badge ${isFinal.className}`}>
          {isFinal.label}
        </div>
      )}

      {/* Status Message */}
      {message && (
        <div className="pipeline-message">
          {message}
        </div>
      )}
    </div>
  );
}

export default PipelineStatus;
