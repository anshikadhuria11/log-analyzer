// ResultPanel.tsx — Renders the full structured analysis report
import React, { useState } from "react";
import type { AnalyzeResponse, EvidenceItem, TimelineItem } from "../types";

interface Props {
  data: AnalyzeResponse;
}

export default function ResultPanel({ data }: Props) {
  const { report, meta, stats } = data;
  const [showRaw, setShowRaw] = useState(false);

  const confidenceClass =
    report.confidence === "high"   ? "badge-high" :
    report.confidence === "medium" ? "badge-medium" : "badge-low";

  return (
    <div className="card result-card" style={{ marginTop: "1.25rem" }}>
      {/* Header */}
      <div className="card-header" style={{ justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <span className="card-header-icon">📊</span>
          <div>
            <div className="card-title">Analysis Report</div>
            <div className="card-subtitle">
              {meta.demo ? "⚡ Demo mode (fake provider)" : `Provider: ${meta.provider} · Model: ${meta.model}`}
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setShowRaw(!showRaw)}
          style={{
            background: "none",
            border: "1px solid var(--border)",
            borderRadius: "6px",
            color: "var(--text-muted)",
            fontSize: "0.72rem",
            padding: "0.2rem 0.6rem",
            cursor: "pointer",
            flexShrink: 0,
          }}
        >
          {showRaw ? "Formatted" : "Raw JSON"}
        </button>
      </div>

      {/* Raw JSON toggle */}
      {showRaw ? (
        <pre style={{
          fontFamily: "var(--font-mono)",
          fontSize: "0.76rem",
          lineHeight: 1.6,
          color: "var(--text-secondary)",
          background: "rgba(0,0,0,0.3)",
          padding: "1rem",
          borderRadius: "10px",
          overflowX: "auto",
          maxHeight: "520px",
          overflowY: "auto",
        }}>
          {JSON.stringify(data, null, 2)}
        </pre>
      ) : (
        <>
          {/* Meta chips */}
          <div className="meta-bar">
            <span className="meta-chip">⏱ <strong>{meta.duration_ms}ms</strong></span>
            <span className="meta-chip">📄 <strong>{meta.input_lines}</strong> lines</span>
            <span className="meta-chip">🔡 <strong>{meta.input_chars.toLocaleString()}</strong> chars</span>
            <span className="meta-chip">🧠 <strong>~{meta.tokens_estimate.toLocaleString()}</strong> tokens</span>
            <span className="meta-chip">🔁 mode: <strong>{meta.mode}</strong></span>
            {meta.validation.dropped > 0 && (
              <span className="meta-chip" style={{ color: "var(--warn)" }}>
                ⚠ {meta.validation.dropped} evidence dropped
              </span>
            )}
          </div>

          {/* Summary */}
          <div className="summary-banner">
            💬 {report.summary}
          </div>

          {/* Confidence */}
          <div className="confidence-row">
            <span className="confidence-label">Confidence:</span>
            <span className={`confidence-badge ${confidenceClass}`}>{report.confidence}</span>
            <span className="confidence-reason">{report.confidence_reason}</span>
          </div>

          {/* Root cause */}
          <div className="section-title">🎯 Root Cause</div>
          <div className="root-cause-box" style={{ marginBottom: "1.25rem" }}>
            <div className="root-cause-header">
              <div style={{ flex: 1 }}>
                <div className="root-cause-label">Root Cause Identified</div>
                <div className="root-cause-title">{report.root_cause.title}</div>
                <div className="root-cause-explanation">{report.root_cause.explanation}</div>
                <span className="category-pill">{report.root_cause.category}</span>
              </div>
            </div>
          </div>

          {/* Evidence */}
          {report.evidence.length > 0 && (
            <>
              <div className="section-title">🔎 Evidence ({report.evidence.length})</div>
              <div className="evidence-list">
                {report.evidence.map((ev: EvidenceItem, i: number) => (
                  <div className="evidence-item" key={i}>
                    <div className="evidence-lineno">Line {ev.line_number}</div>
                    <div className="evidence-text">{ev.text}</div>
                    <div className="evidence-why">↳ {ev.why}</div>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Timeline */}
          {report.timeline.length > 0 && (
            <>
              <div className="section-title">🕒 Timeline</div>
              <div className="timeline" style={{ marginBottom: "1.25rem" }}>
                {report.timeline.map((t: TimelineItem, i: number) => (
                  <div className="timeline-item" key={i}>
                    <div className="timeline-left">
                      <div className="timeline-dot" />
                      <div className="timeline-line" />
                    </div>
                    <div className="timeline-content">
                      <div className="timeline-label">{t.label}</div>
                      {(t.line_number || t.timestamp) && (
                        <div className="timeline-meta">
                          {t.line_number ? `L${t.line_number}` : ""}
                          {t.line_number && t.timestamp ? " · " : ""}
                          {t.timestamp ?? ""}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Suggested fixes */}
          {report.suggested_fixes.length > 0 && (
            <>
              <div className="section-title">🛠 Suggested Fixes</div>
              <div className="fixes-list">
                {report.suggested_fixes.map((fix: string, i: number) => (
                  <div className="fix-item" key={i}>
                    <span className="fix-num">#{i + 1}</span>
                    <span>{fix}</span>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Limitations */}
          {report.limitations && report.limitations.length > 0 && (
            <>
              <div className="divider" />
              <div className="section-title">⚠ Limitations</div>
              <ul style={{ paddingLeft: "1.25rem", fontSize: "0.82rem", color: "var(--text-muted)", lineHeight: 1.7 }}>
                {report.limitations.map((lim, i) => <li key={i}>{lim}</li>)}
              </ul>
            </>
          )}
        </>
      )}
    </div>
  );
}
