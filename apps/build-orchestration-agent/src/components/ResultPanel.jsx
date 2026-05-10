function ResultPanel({ result }) {
  if (result.error) {
    return (
      <div className="error">
        ❌ {result.error}
        {result.details && (
          <pre>{JSON.stringify(result.details, null, 2)}</pre>
        )}
      </div>
    );
  }

  return (
    <div className="result">
      <h2>Status: {result.status}</h2>

      {result.history && result.history.map((step, index) => (
        <div key={index} className="card">
          <h3>Iteration {step.iteration}</h3>

          <p><strong>Error:</strong> {step.analysis?.message}</p>
          <p><strong>Fix:</strong> {step.reasoning?.best_fix?.command}</p>
          <p><strong>Applied:</strong> {step.applied ? "Yes" : "No"}</p>
        </div>
      ))}

      {result.final_result && (
        <div className="card success">
          <h3>Final Result</h3>
          <p>Success: {result.final_result.success ? "Yes" : "No"}</p>
          <p>Duration: {result.final_result.duration}s</p>
        </div>
      )}
    </div>
  );
}

export default ResultPanel;