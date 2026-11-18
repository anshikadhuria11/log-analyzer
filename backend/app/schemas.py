# Pydantic models for the Log Analyzer API
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

# Log event produced by the parser
# Represents a single log line (or multi‑line event) with optional metadata
class LogEvent(BaseModel):
    line_no: int
    timestamp: Optional[datetime] = None
    level: Literal["DEBUG", "INFO", "WARN", "ERROR", "FATAL", "UNKNOWN"] = "UNKNOWN"
    service: Optional[str] = None
    request_id: Optional[str] = None
    message: str
    continuation_lines: List[int] = Field(default_factory=list)

# Pattern grouping used by the reducer
# Holds a masked template and aggregated statistics
class Pattern(BaseModel):
    template: str
    level: Literal["DEBUG", "INFO", "WARN", "ERROR", "FATAL", "UNKNOWN"]
    count: int
    first_line: int
    last_line: int
    first_timestamp: Optional[datetime] = None
    last_timestamp: Optional[datetime] = None
    sample_lines: List[int] = Field(default_factory=list)

# Suspect candidate for root cause
class Suspect(BaseModel):
    pattern_template: str
    first_line: int
    reason: str

# Bucket for spike detection
class Bucket(BaseModel):
    label: str
    count: int

# Reduced log output from the reducer
class ReducedLog(BaseModel):
    # Basic statistics about the input
    total_lines: int
    events_parsed: int
    level_counts: dict[str, int]
    format_detected: str
    inferred_levels: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    # Aggregated data structures
    patterns: List[Pattern] = Field(default_factory=list)
    first_error: Optional[LogEvent] = None
    first_error_context: List[LogEvent] = Field(default_factory=list)
    request_chains: List[dict] = Field(default_factory=list)  # simplified for now
    suspects: List[Suspect] = Field(default_factory=list)
    buckets: List[Bucket] = Field(default_factory=list)
    # Prompt selection
    selected_lines: List[int] = Field(default_factory=list)
    truncated: bool = False
    notice: Optional[str] = None

# Evidence item returned in the final report
class EvidenceItem(BaseModel):
    line_number: int
    text: str
    why: str

# Timeline entry for the final report
class TimelineItem(BaseModel):
    label: str
    line_number: Optional[int] = None
    timestamp: Optional[datetime] = None

# Root cause classification
class RootCause(BaseModel):
    title: str
    explanation: str
    category: Literal[
        "database",
        "network",
        "memory",
        "deploy",
        "config",
        "dependency",
        "auth",
        "resource",
        "unknown",
    ]

# Final analysis report schema
class AnalysisReport(BaseModel):
    summary: str
    root_cause: RootCause
    evidence: List[EvidenceItem] = Field(default_factory=list)
    timeline: List[TimelineItem] = Field(default_factory=list)
    suggested_fixes: List[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"]
    confidence_reason: str
    limitations: Optional[List[str]] = None

# Validation information returned to the client
class ValidationInfo(BaseModel):
    cited: int
    valid: int
    invalid: int
    retried: bool = False
    corrected: int = 0
    dropped: int = 0

# Meta information about the analysis request
class Meta(BaseModel):
    mode: Literal["pipeline", "raw"]
    model: str
    provider: str
    duration_ms: int
    input_chars: int
    input_lines: int
    prompt_chars: int
    tokens_estimate: int
    truncated: bool = False
    notice: Optional[str] = None
    validation: ValidationInfo
    demo: bool = False

# Request payload for /api/analyze
class AnalyzeRequest(BaseModel):
    logs: str
    mode: Literal["pipeline", "raw"] = "pipeline"
    save: bool = False

# Full response returned by the API
class AnalyzeResponse(BaseModel):
    id: str
    report: AnalysisReport
    patterns: List[Pattern] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)
    meta: Meta
