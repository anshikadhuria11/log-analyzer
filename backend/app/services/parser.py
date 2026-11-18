# Parser service: detect format and extract LogEvent objects
# Supports plain text, jsonl, and simple cloudwatch lines.
# Keeps original 1‑based line numbers and attaches continuation lines.

import json
import re
from datetime import datetime
from typing import List, Optional, Tuple

from ..schemas import LogEvent

# Helper regexes
_TIMESTAMP_RE = re.compile(r"(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z)?)")
_UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_IP_RE = re.compile(r"(?:\d{1,3}\.){3}\d{1,3}|(?:[a-fA-F0-9]{0,4}:){2,7}[a-fA-F0-9]{0,4}")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}")
_URL_RE = re.compile(r"https?://[^\s]+")

_LEVEL_MAP = {
    "debug": "DEBUG",
    "info": "INFO",
    "warn": "WARN",
    "warning": "WARN",
    "error": "ERROR",
    "fatal": "FATAL",
    "critical": "FATAL",
    "trace": "DEBUG",
}

_KEY_ALIASES = {
    "timestamp": ["timestamp", "time", "ts", "@timestamp"],
    "level": ["level", "severity", "levelname", "log.level"],
    "message": ["message", "msg", "event"],
    "service": ["service", "logger", "app"],
    "request_id": ["request_id", "requestId", "trace_id", "correlation_id"],
}

def _extract_key(obj: dict, canonical: str) -> Optional[str]:
    for alias in _KEY_ALIASES.get(canonical, []):
        if alias in obj:
            return str(obj[alias])
    return None

def _parse_timestamp(text: str) -> Optional[datetime]:
    # Try ISO 8601 first
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        pass
    # Try "YYYY‑MM‑DD HH:MM:SS,ms" or "YYYY‑MM‑DDTHH:MM:SS.ms"
    m = _TIMESTAMP_RE.search(text)
    if m:
        ts = m.group("ts").replace(" ", "T").replace(",", ".")
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            pass
    return None

def _infer_level(message: str) -> str:
    lowered = message.lower()
    keywords = ["exception", "traceback", "failed", "timeout", "refused", "denied", "oom", "killed", "fatal", "panic"]
    if any(k in lowered for k in keywords):
        return "ERROR"
    return "UNKNOWN"

def _detect_format(sample_lines: List[str]) -> str:
    # Simple heuristic: json lines → jsonl, lines with ISO timestamps → cloudwatch, else text
    json_hits = 0
    cloud_hits = 0
    for ln in sample_lines:
        stripped = ln.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
            if isinstance(obj, dict):
                json_hits += 1
                continue
        except Exception:
            pass
        if _TIMESTAMP_RE.search(stripped):
            cloud_hits += 1
    if json_hits > cloud_hits:
        return "jsonl"
    if cloud_hits > 0:
        return "cloudwatch"
    return "text"

def parse_logs(raw: str) -> Tuple[List[LogEvent], str, List[str]]:
    """Parse raw log text.

    Returns a tuple of (events, detected_format, warnings).
    """
    lines = raw.splitlines()
    warnings: List[str] = []
    events: List[LogEvent] = []
    # Determine format from first 20 non‑empty lines
    sample = [ln for ln in lines if ln.strip()][:20]
    fmt = _detect_format(sample)

    current_event: Optional[LogEvent] = None
    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip("\n")
        if not line.strip():
            continue
        # JSONL handling
        if fmt == "jsonl":
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    # Start a new event
                    if current_event:
                        events.append(current_event)
                    timestamp = _parse_timestamp(_extract_key(obj, "timestamp") or "")
                    level_raw = _extract_key(obj, "level")
                    level = _LEVEL_MAP.get((level_raw or "").lower(), "UNKNOWN")
                    message = _extract_key(obj, "message") or ""
                    service = _extract_key(obj, "service")
                    request_id = _extract_key(obj, "request_id")
                    current_event = LogEvent(
                        line_no=idx,
                        timestamp=timestamp,
                        level=level,
                        service=service,
                        request_id=request_id,
                        message=message,
                        continuation_lines=[],
                    )
                    continue
            except Exception:
                # fall through to treat as continuation / warning
                pass
        # Cloudwatch plain line (timestamp then message)
        if fmt == "cloudwatch":
            # Try to split at first whitespace after timestamp
            ts_match = _TIMESTAMP_RE.search(line)
            if ts_match:
                ts_str = ts_match.group("ts")
                timestamp = _parse_timestamp(ts_str)
                after = line[ts_match.end():].lstrip()
                # No explicit level; infer later
                if current_event:
                    events.append(current_event)
                current_event = LogEvent(
                    line_no=idx,
                    timestamp=timestamp,
                    level="UNKNOWN",
                    service=None,
                    request_id=None,
                    message=after,
                    continuation_lines=[],
                )
                continue
        # Plain text handling (fallback)
        # Detect level if present at start of line
        level = "UNKNOWN"
        level_match = re.search(r"\b(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL|TRACE)\b", line, re.IGNORECASE)
        if level_match:
            level = _LEVEL_MAP.get(level_match.group(1).lower(), "UNKNOWN")
        # Continuation detection: indented or starts with a stack‑trace keyword
        if line.startswith(" ") or line.startswith("\t") or line.startswith("Traceback") or line.startswith("at "):
            if current_event:
                # Append to message and record continuation line number
                current_event.message += " " + line.strip()
                current_event.continuation_lines.append(idx)
                continue
        # New event line
        if current_event:
            events.append(current_event)
        timestamp = _parse_timestamp(line)
        # Infer level if still UNKNOWN
        if level == "UNKNOWN":
            level = _infer_level(line)
        current_event = LogEvent(
            line_no=idx,
            timestamp=timestamp,
            level=level,
            service=None,
            request_id=None,
            message=line,
            continuation_lines=[],
        )
    # Append last event
    if current_event:
        events.append(current_event)
    # Cap warnings at 10
    if len(warnings) > 10:
        warnings = warnings[:10]
    return events, fmt, warnings
