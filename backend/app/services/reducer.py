# Reducer service: mask variable data, group patterns, find first error, request chains, spikes, suspects, stats, and select lines for the prompt.
# No LLM calls – pure deterministic logic.

import re
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

from ..schemas import LogEvent, Pattern, Suspect, Bucket, ReducedLog

# Regexes for template masking – order matters
_UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_IP_RE = re.compile(r"(?:\d{1,3}\.){3}\d{1,3}|(?:[a-fA-F0-9]{0,4}:){2,7}[a-fA-F0-9]{0,4}")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}")
_URL_RE = re.compile(r"https?://[^\s]+")
_HEX_RE = re.compile(r"\b0x[0-9a-fA-F]+\b|\b[0-9a-fA-F]{8,}\b")
_STR_RE = re.compile(r"\".*?\"|'.*?'")
_NUM_RE = re.compile(r"\b\d+([.,]\d+)?(ms|s|m|h)?\b")

def _mask_message(msg: str) -> str:
    """Replace variable parts of a log message with placeholders.
    Order: UUID → IP → EMAIL → URL → HEX → STRING → NUMBER.
    """
    msg = _UUID_RE.sub("<UUID>", msg)
    msg = _IP_RE.sub("<IP>", msg)
    msg = _EMAIL_RE.sub("<EMAIL>", msg)
    msg = _URL_RE.sub("<URL>", msg)
    msg = _HEX_RE.sub("<HEX>", msg)
    msg = _STR_RE.sub("<STR>", msg)
    msg = _NUM_RE.sub("<NUM>", msg)
    # Collapse any repeated whitespace
    return re.sub(r"\s+", " ", msg).strip()

def reduce_events(events: List[LogEvent], settings) -> ReducedLog:
    """Reduce a list of LogEvent objects into a ReducedLog.
    The `settings` argument is a Settings object from backend/app/config.py.
    """
    total_lines = max((e.line_no for e in events), default=0)
    level_counts = Counter(e.level for e in events)
    inferred_levels = sum(1 for e in events if e.level == "UNKNOWN")
    start_time = min((e.timestamp for e in events if e.timestamp), default=None)
    end_time = max((e.timestamp for e in events if e.timestamp), default=None)

    # 1️⃣ Template masking and pattern grouping for WARN+ levels
    pattern_dict: Dict[str, Dict] = {}
    for ev in events:
        if ev.level not in ("WARN", "ERROR", "FATAL"):
            continue
        tmpl = _mask_message(ev.message)
        if tmpl not in pattern_dict:
            pattern_dict[tmpl] = {
                "level": ev.level,
                "count": 0,
                "first_line": ev.line_no,
                "last_line": ev.line_no,
                "first_timestamp": ev.timestamp,
                "last_timestamp": ev.timestamp,
                "sample_lines": [],
            }
        rec = pattern_dict[tmpl]
        rec["count"] += 1
        rec["last_line"] = ev.line_no
        rec["last_timestamp"] = ev.timestamp or rec["last_timestamp"]
        if ev.line_no not in rec["sample_lines"] and len(rec["sample_lines"]) < 3:
            rec["sample_lines"].append(ev.line_no)
        # Keep highest severity among occurrences
        if _severity_rank(ev.level) > _severity_rank(rec["level"]):
            rec["level"] = ev.level

    # Convert dict to Pattern objects and sort for timeline & top‑patterns
    patterns = [
        Pattern(
            template=t,
            level=rec["level"],
            count=rec["count"],
            first_line=rec["first_line"],
            last_line=rec["last_line"],
            first_timestamp=rec["first_timestamp"],
            last_timestamp=rec["last_timestamp"],
            sample_lines=rec["sample_lines"],
        )
        for t, rec in pattern_dict.items()
    ]
    # Timeline order: earliest first line, then count
    patterns.sort(key=lambda p: (p.first_line, -p.count))
    top_patterns = patterns[: int(settings.TOP_PATTERNS)]

    # 2️⃣ First error (ERROR or FATAL)
    first_error_evt: LogEvent | None = None
    for ev in events:
        if ev.level in ("ERROR", "FATAL"):
            first_error_evt = ev
            break
    # Context lines around the first error
    first_error_context: List[LogEvent] = []
    if first_error_evt:
        start = max(1, first_error_evt.line_no - settings.CONTEXT_LINES)
        end = first_error_evt.line_no + settings.CONTEXT_LINES
        line_map = {e.line_no: e for e in events}
        for ln in range(start, end + 1):
            if ln in line_map:
                first_error_context.append(line_map[ln])

    # 3️⃣ Request chains – group errors by request_id
    chain_counts: Dict[str, int] = defaultdict(int)
    chain_first_err: Dict[str, LogEvent] = {}
    for ev in events:
        if ev.request_id and ev.level in ("ERROR", "FATAL"):
            chain_counts[ev.request_id] += 1
            if ev.request_id not in chain_first_err:
                chain_first_err[ev.request_id] = ev
    # Keep up to 5 chains with most errors
    top_chains = sorted(chain_counts.items(), key=lambda kv: -kv[1])[:5]
    request_chains = [
        {"request_id": rid, "error_count": cnt, "first_error_line": chain_first_err[rid].line_no}
        for rid, cnt in top_chains
    ]

    # 4️⃣ Spike detection – bucket ERROR+ events
    if start_time and any(ev.timestamp for ev in events if ev.level in ("ERROR", "FATAL")):
        # bucket by minute
        bucket: Dict[datetime, int] = defaultdict(int)
        for ev in events:
            if ev.level in ("ERROR", "FATAL") and ev.timestamp:
                minute = ev.timestamp.replace(second=0, microsecond=0)
                bucket[minute] += 1
        buckets = [Bucket(label=dt.isoformat(), count=c) for dt, c in sorted(bucket.items())]
    else:
        # No timestamps – split into 20 equal slices by line order
        slice_size = max(1, len(events) // 20)
        bucket_counts = []
        for i in range(20):
            start_idx = i * slice_size
            end_idx = start_idx + slice_size
            cnt = sum(1 for ev in events[start_idx:end_idx] if ev.level in ("ERROR", "FATAL"))
            bucket_counts.append(cnt)
        buckets = [Bucket(label=f"slice_{i+1}", count=c) for i, c in enumerate(bucket_counts)]
    # Identify peak bucket
    peak_bucket = max(buckets, key=lambda b: b.count) if buckets else None

    # 5️⃣ Suspect candidates (max 3)
    suspects: List[Suspect] = []
    # a) first error
    if first_error_evt:
        suspects.append(Suspect(pattern_template=_mask_message(first_error_evt.message), first_line=first_error_evt.line_no, reason="earliest error in the input"))
    # b) pattern that appears just before spike
    if peak_bucket and first_error_evt:
        # Find patterns whose first_line is within CONTEXT_LINES before the start of the peak bucket
        # Approximate: use the earliest line of the bucket (if timestamp based) or slice index
        # For simplicity we take the first pattern whose first_line is < first_error line
        for pat in top_patterns:
            if pat.first_line < first_error_evt.line_no:
                suspects.append(Suspect(pattern_template=pat.template, first_line=pat.first_line, reason="new pattern appeared just before the spike"))
                break
    # c) highest‑count pattern
    if top_patterns:
        most = top_patterns[0]
        suspects.append(Suspect(pattern_template=most.template, first_line=most.first_line, reason="most frequent error pattern"))
    # Deduplicate by template
    seen = set()
    uniq_suspects: List[Suspect] = []
    for s in suspects:
        if s.pattern_template not in seen:
            seen.add(s.pattern_template)
            uniq_suspects.append(s)
    suspects = uniq_suspects[:3]

    # 6️⃣ Line selection for prompt (selected_lines = line numbers)
    selected_set = set()
    # All ERROR+ events
    for ev in events:
        if ev.level in ("ERROR", "FATAL"):
            selected_set.add(ev.line_no)
    # Add suspect context windows
    for s in suspects:
        start = max(1, s.first_line - settings.CONTEXT_LINES)
        end = s.first_line + settings.CONTEXT_LINES
        for ln in range(start, end + 1):
            selected_set.add(ln)
    # First and last 5 lines
    for ln in range(1, 6):
        selected_set.add(ln)
    for ln in range(total_lines - 4, total_lines + 1):
        if ln > 0:
            selected_set.add(ln)

    selected = sorted(selected_set)
    truncated = False
    notice = None
    if len(selected) > settings.MAX_ANALYSIS_LINES:
        truncated = True
        notice = f"Input was large, so the {settings.MAX_ANALYSIS_LINES} most relevant lines were analysed."
        # Keep suspect windows first, then earliest errors, then even sampling
        # Build prioritized list
        priority: List[int] = []
        # suspect windows
        for s in suspects:
            start = max(1, s.first_line - settings.CONTEXT_LINES)
            end = s.first_line + settings.CONTEXT_LINES
            priority.extend(range(start, end + 1))
        # earliest error window
        if first_error_evt:
            start = max(1, first_error_evt.line_no - settings.CONTEXT_LINES)
            end = first_error_evt.line_no + settings.CONTEXT_LINES
            priority.extend(range(start, end + 1))
        # add remaining lines by even sampling
        remaining = [ln for ln in range(1, total_lines + 1) if ln not in priority]
        step = max(1, len(remaining) // settings.MAX_ANALYSIS_LINES)
        priority.extend(remaining[::step])
        selected = sorted(set(priority)[: settings.MAX_ANALYSIS_LINES])

    # Assemble ReducedLog
    reduced = ReducedLog(
        total_lines=total_lines,
        events_parsed=len(events),
        level_counts=dict(level_counts),
        format_detected=events[0].level if events else "text",
        inferred_levels=inferred_levels,
        start_time=start_time,
        end_time=end_time,
        patterns=top_patterns,
        first_error=first_error_evt,
        first_error_context=first_error_context,
        request_chains=request_chains,
        suspects=suspects,
        buckets=buckets,
        selected_lines=selected,
        truncated=truncated,
        notice=notice,
    )
    return reduced

def _severity_rank(level: str) -> int:
    """Return an integer ranking for severity (higher is more severe)."""
    order = {"DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3, "FATAL": 4, "UNKNOWN": -1}
    return order.get(level, -1)
