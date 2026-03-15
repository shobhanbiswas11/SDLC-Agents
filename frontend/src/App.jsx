import { Suspense, lazy } from "react";
import "./App.css";

const LiveEditor = lazy(() => import("./LiveEditor"));

function App() {
  return (
    <div className="page">
      <div className="card">
        <div className="header-section">
          <h1>AI Coding Standards Enforcer</h1>
          <p className="subtitle">
            Multi-language AI agent for code quality : paste a repo or write code
            with real-time standards enforcement for Python, C++, Java, JS/TS, Go &amp; Rust.
          </p>
        </div>

        <Suspense
          fallback={
            <div style={{ padding: 40, textAlign: "center" }}>
              <span className="spinner" /> Loading editor…
            </div>
          }
        >
          <LiveEditor />
        </Suspense>
      </div>
    </div>
  );
}

export default App;
