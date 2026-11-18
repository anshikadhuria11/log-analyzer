// App.tsx — Root component, layout and state management
import React, { useState, useEffect } from "react";
import LogInputPanel from "./components/LogInput";
import ResultPanel from "./components/ResultPanel";
import type { AnalyzeResponse } from "./types";

export default function App() {
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [error, setError]   = useState<string | null>(null);
  const [backendOk, setBackendOk] = useState<"checking" | "online" | "offline">("checking");

  // Ping /api/health on mount to show backend status in header
  useEffect(() => {
    fetch("/api/health")
      .then((r) => (r.ok ? setBackendOk("online") : setBackendOk("offline")))
      .catch(() => setBackendOk("offline"));
  }, []);

  function handleResult(data: AnalyzeResponse) {
    setError(null);
    setResult(data);
  }

  function handleError(msg: string) {
    setResult(null);
    setError(msg);
  }

  const statusLabel = backendOk === "checking" ? "Connecting…" : backendOk === "online" ? "API online" : "API offline";

  return (
    <div className="app-wrapper">
      {/* ── Header ── */}
      <header className="header">
        <div className="container">
          <div className="header-brand">
            <div className="brand-icon">🔍</div>
            <div>
              <div className="brand-title">Log Analyzer</div>
            </div>
            <span className="brand-badge">AI</span>
          </div>
          <div className="header-status">
            <div className={`status-dot ${backendOk === "checking" ? "checking" : backendOk === "offline" ? "offline" : ""}`} />
            <span>{statusLabel}</span>
          </div>
        </div>
      </header>

      {/* ── Main ── */}
      <main className="main-content">
        <div className="container">

          {/* Hero */}
          <div className="hero">
            <span className="hero-eyebrow">AI-Powered Debugging</span>
            <h1>Find the root cause of your<br /><span>logs instantly</span></h1>
            <p className="hero-sub">
              Paste any application log — Python, Node, Java, Nginx — and get a structured breakdown of what went wrong, with evidence and fix suggestions.
            </p>
          </div>

          {/* Input panel */}
          <LogInputPanel onResult={handleResult} onError={handleError} />

          {/* Error state */}
          {error && (
            <div className="error-banner" style={{ marginTop: "1.25rem" }}>
              <span className="error-banner-icon">⚠️</span>
              <div className="error-banner-text">
                <strong>Analysis failed:</strong> {error}
                {error.includes("offline") || error.includes("ECONNREFUSED") || error.includes("Failed to fetch") ? (
                  <><br /><small>Make sure the backend is running: <code>uvicorn backend.app.main:app --reload --port 8000</code></small></>
                ) : null}
              </div>
            </div>
          )}

          {/* Result panel */}
          {result && <ResultPanel data={result} />}

          {/* Empty hint when nothing shown yet */}
          {!result && !error && (
            <div className="hint-box" style={{ marginTop: "1.5rem" }}>
              <div className="hint-icon">📋</div>
              <div>Paste your logs above and hit <strong>Analyze</strong> to see the AI report here.</div>
            </div>
          )}

        </div>
      </main>

      {/* ── Footer ── */}
      <footer className="footer">
        <div className="container">
          Built with ❤️ &nbsp;·&nbsp; <a href="https://github.com/your-username/log-analyzer" target="_blank" rel="noopener noreferrer">View on GitHub</a>
        </div>
      </footer>
    </div>
  );
}
