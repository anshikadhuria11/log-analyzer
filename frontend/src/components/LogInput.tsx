// LogInput.tsx — Paste area, mode selection, and submit button
import React, { useState } from "react";
import type { AnalyzeResponse } from "../types";

interface Props {
  onResult: (data: AnalyzeResponse) => void;
  onError:  (msg: string) => void;
}

export default function LogInputPanel({ onResult, onError }: Props) {
  const [logs, setLogs]     = useState("");
  const [mode, setMode]     = useState<"pipeline" | "raw">("pipeline");
  const [loading, setLoading] = useState(false);

  const lineCount = logs ? logs.split("\n").length : 0;
  const charCount = logs.length;

  async function handleAnalyze() {
    if (!logs.trim()) return;
    setLoading(true);
    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ logs, mode, save: false }),
      });

      if (!res.ok) {
        // Read the body ONCE as text, then try to parse JSON from it.
        // Calling res.json() and then res.text() on the same Response throws
        // "body stream already read" — avoid by reading text first.
        let detail = `HTTP ${res.status}`;
        try {
          const bodyText = await res.text();
          try {
            const json = JSON.parse(bodyText);
            detail = json.detail ?? JSON.stringify(json);
          } catch {
            if (bodyText.trim()) detail = bodyText;
          }
        } catch { /* ignore read error */ }
        onError(detail);
        return;
      }

      const data: AnalyzeResponse = await res.json();
      onResult(data);
    } catch (err: any) {
      onError(err?.message ?? "Network error — is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      {/* Card header */}
      <div className="card-header">
        <span className="card-header-icon">📄</span>
        <div>
          <div className="card-title">Paste your logs</div>
          <div className="card-subtitle">Supports Python, Node, Java, Nginx, Docker, and more</div>
        </div>
      </div>

      {/* Mode selector */}
      <div className="mode-selector">
        <button
          id="mode-pipeline"
          className={`mode-btn ${mode === "pipeline" ? "active" : ""}`}
          onClick={() => setMode("pipeline")}
          type="button"
        >
          <span className="mode-btn-label">🔗 Pipeline</span>
          <span className="mode-btn-desc">Full parse → reduce → LLM analysis. Best for structured logs.</span>
        </button>
        <button
          id="mode-raw"
          className={`mode-btn ${mode === "raw" ? "active" : ""}`}
          onClick={() => setMode("raw")}
          type="button"
        >
          <span className="mode-btn-label">⚡ Raw</span>
          <span className="mode-btn-desc">Direct LLM pass. Best for short or unstructured text.</span>
        </button>
      </div>

      {/* Textarea */}
      <textarea
        id="log-textarea"
        className="log-textarea"
        value={logs}
        onChange={(e) => setLogs(e.target.value)}
        placeholder={`Paste log output here…\n\nExample:\n2024-01-15 10:23:45 ERROR database connection failed: timeout after 30s\n2024-01-15 10:23:46 ERROR retry 1/3 failed\n2024-01-15 10:23:47 FATAL service shutting down`}
        rows={10}
        spellCheck={false}
      />

      {/* Char / line count */}
      <div className="textarea-footer">
        <span>{lineCount} line{lineCount !== 1 ? "s" : ""}</span>
        <span>{charCount.toLocaleString()} chars</span>
      </div>

      {/* Submit */}
      <button
        id="analyze-btn"
        className="analyze-btn"
        onClick={handleAnalyze}
        disabled={loading || !logs.trim()}
        type="button"
      >
        {loading ? (
          <><span className="spinner" /> Analyzing…</>
        ) : (
          <><span>🔍</span> Analyze Logs</>
        )}
      </button>
    </div>
  );
}
