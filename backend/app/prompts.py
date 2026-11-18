# Prompt utilities: system prompt and builders for pipeline/raw/retry

# System prompt – short and strict as required by the spec
SYSTEM_PROMPT = (
    "You are a senior site reliability engineer reading logs. "
    "Use ONLY the log lines provided. Do NOT invent lines, services, or errors. "
    "Line numbers in the input are authoritative; cite lines only by those numbers. "
    "Prefer the earliest error in a causal chain over loud downstream symptoms. "
    "If the logs do not show a cause, say so, set confidence to low, and list what is missing in `limitations`. "
    "Keep the summary to 2-3 plain sentences. Keep fixes concrete and short."
)

def _format_line(line_no: int, text: str) -> str:
    """Return a line formatted as "L<line_no> | <text>" for the prompt."""
    return f"L{line_no} | {text}"

def build_pipeline_prompt(reduced) -> str:
    """Compose the full prompt for pipeline mode from a ReducedLog instance.
    The function follows the ordering and truncation rules defined in the spec.
    """
    sections = []
    # Stats
    stats = (
        f"Stats: total_lines={reduced.total_lines}, events_parsed={reduced.events_parsed}, "
        f"format={reduced.format_detected}, inferred_levels={reduced.inferred_levels}\n"
    )
    sections.append(stats)
    # Top patterns
    pat_lines = []
    for pat in reduced.patterns:
        samples = ", ".join(str(l) for l in pat.sample_lines)
        pat_lines.append(
            f"Pattern: {pat.template} | level={pat.level} | count={pat.count} | first_line={pat.first_line} | samples=[{samples}]"
        )
    sections.append("Top patterns (up to {0}):\n".format(len(reduced.patterns)) + "\n".join(pat_lines))
    # First error with context
    if reduced.first_error:
        ctx = []
        for ev in reduced.first_error_context:
            ctx.append(_format_line(ev.line_no, ev.message))
        ctx_text = "\n".join(ctx)
        sections.append(
            f"First error (line {reduced.first_error.line_no}): {reduced.first_error.message}\nContext:\n{ctx_text}"
        )
    # Request chains
    if reduced.request_chains:
        chain_lines = []
        for ch in reduced.request_chains:
            chain_lines.append(
                f"request_id={ch['request_id']} errors={ch['error_count']} first_error_line={ch['first_error_line']}"
            )
        sections.append("Request chains:\n" + "\n".join(chain_lines))
    # Suspects
    suspect_lines = []
    for s in reduced.suspects:
        suspect_lines.append(f"Suspect: template={s.pattern_template} line={s.first_line} reason={s.reason}")
    if suspect_lines:
        sections.append("Suspects:\n" + "\n".join(suspect_lines))
    # Timeline buckets
    bucket_lines = []
    for b in reduced.buckets:
        bucket_lines.append(f"Bucket: {b.label} count={b.count}")
    if bucket_lines:
        sections.append("Timeline buckets:\n" + "\n".join(bucket_lines))
    # Selected log lines
    line_texts = []
    # We need the original raw lines; they are not stored here, so the caller must supply them.
    # For simplicity we assume the caller will concatenate them after this call.
    sections.append("Log lines (selected for LLM):")
    # The actual lines will be appended by the caller.
    prompt_body = "\n\n".join(sections)
    return SYSTEM_PROMPT + "\n\n" + prompt_body

def build_raw_prompt(raw_text: str) -> str:
    """Build a prompt for raw baseline mode – just number each line and attach system prompt."""
    lines = raw_text.splitlines()
    numbered = [f"L{i+1} | {ln}" for i, ln in enumerate(lines)]
    body = "\n".join(numbered)
    return SYSTEM_PROMPT + "\n\n" + body

def build_retry_message(invalid_items) -> str:
    """Create a short retry instruction listing which citations were invalid.
    `invalid_items` is a list of dicts with keys `line_number` and `text`.
    """
    lines = []
    for itm in invalid_items:
        lines.append(f"Line {itm['line_number']} was cited but does not match the input.")
    return (
        SYSTEM_PROMPT
        + "\n\nThe previous response contained invalid citations. Please correct them using ONLY the real log lines.\n"
        + "\n".join(lines)
    )
