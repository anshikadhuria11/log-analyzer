// types.ts — TypeScript interfaces that mirror the backend Pydantic schemas
export interface EvidenceItem {
  line_number: number;
  text: string;
  why: string;
}

export interface TimelineItem {
  label: string;
  line_number?: number;
  timestamp?: string;
}

export interface RootCause {
  title: string;
  explanation: string;
  category: string;
}

export interface AnalysisReport {
  summary: string;
  root_cause: RootCause;
  evidence: EvidenceItem[];
  timeline: TimelineItem[];
  suggested_fixes: string[];
  confidence: "low" | "medium" | "high";
  confidence_reason: string;
  limitations?: string[];
}

export interface Pattern {
  template: string;
  level: string;
  count: number;
  first_line: number;
  last_line: number;
  sample_lines: number[];
}

export interface ValidationInfo {
  cited: number;
  valid: number;
  invalid: number;
  retried: boolean;
  corrected: number;
  dropped: number;
}

export interface Meta {
  mode: "pipeline" | "raw";
  model: string;
  provider: string;
  duration_ms: number;
  input_chars: number;
  input_lines: number;
  prompt_chars: number;
  tokens_estimate: number;
  truncated: boolean;
  notice?: string;
  validation: ValidationInfo;
  demo: boolean;
}

export interface AnalyzeResponse {
  id: string;
  report: AnalysisReport;
  patterns: Pattern[];
  stats: Record<string, unknown>;
  meta: Meta;
}
