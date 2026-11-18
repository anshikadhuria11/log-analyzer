# Analyzer service – pipeline mode (reduce → LLM → validate → optional retry)

import time
from typing import Any, Dict

from ..config import settings
from ..schemas import AnalyzeResponse, AnalysisReport, ValidationInfo, Meta, ReducedLog
from .parser import parse_logs
from .reducer import reduce_events
from .llm import get_chat_model, LLMError, LLMRateLimitError, FakeChatModel
from .validator import validate_report
from ..prompts import build_pipeline_prompt, build_retry_message


async def analyze_pipeline(logs: str, save: bool = False) -> AnalyzeResponse:
    """Full pipeline analysis.
    Returns an AnalyzeResponse ready to be returned by the API.
    """
    start_ts = time.time()
    # 1️⃣ Parse
    events, fmt, warnings = parse_logs(logs)
    # 2️⃣ Reduce
    reduced: ReducedLog = reduce_events(events, settings)
    # 3️⃣ Build prompt – need the raw lines selected for the prompt
    raw_lines = logs.splitlines()
    selected_text = "\n".join(
        f"L{ln} | {raw_lines[ln - 1]}" for ln in reduced.selected_lines if 1 <= ln <= len(raw_lines)
    )
    user_prompt = build_pipeline_prompt(reduced) + "\n" + selected_text
    # 4️⃣ LLM call – handle fake provider specially
    provider = settings.LLM_PROVIDER.lower()
    if provider == "fake":
        # Fake model does not need the prompt; we pass reduced data directly
        model = FakeChatModel(reduced)
        llm_response = await model.with_structured_output(AnalysisReport).ainvoke([{"role": "system", "content": ""}, {"role": "user", "content": user_prompt}])
    else:
        model = get_chat_model()
        # Add structured output handling – LangChain will raise if parsing fails
        try:
            llm_response = await model.with_structured_output(AnalysisReport).ainvoke([{"role": "system", "content": ""}, {"role": "user", "content": user_prompt}])
        except Exception as exc:
            # If it's a rate‑limit error from the provider, raise immediately
            if getattr(exc, "status_code", None) == 429:
                raise LLMRateLimitError(str(exc)) from exc
            # For any other error (parse failure, transient network blip) retry once
            retry_prompt = (
                "Please return ONLY valid JSON matching the schema. No extra text.\n" + user_prompt
            )
            try:
                llm_response = await model.with_structured_output(AnalysisReport).ainvoke([{"role": "system", "content": ""}, {"role": "user", "content": retry_prompt}])
            except Exception as retry_exc:
                # Both attempts failed – surface a clean LLMError so FastAPI returns 502
                raise LLMError(f"LLM call failed: {retry_exc}") from retry_exc
    # llm_response is expected to be a dict with a "report" key (fake returns that)
    if isinstance(llm_response, dict) and "report" in llm_response:
        report: AnalysisReport = llm_response["report"]
    else:
        report = llm_response  # type: ignore
    # 5️⃣ Validate citations
    report, val_info = validate_report(report, raw_lines, validate_only=False)
    # 6️⃣ If any invalid citations and we haven't retried yet, send a retry message
    retried = False
    if val_info.invalid > 0:
        retry_msg = build_retry_message([{"line_number": ev.line_number, "text": ev.text} for ev in report.evidence])
        # Send a second LLM call (same model) with retry prompt
        if provider == "fake":
            # Fake model returns deterministic corrected report – we just reuse the same report
            pass
        else:
            try:
                llm_response2 = await model.with_structured_output(AnalysisReport).ainvoke([{"role": "system", "content": ""}, {"role": "user", "content": retry_msg}])
                if isinstance(llm_response2, dict) and "report" in llm_response2:
                    report = llm_response2["report"]
                else:
                    report = llm_response2  # type: ignore
            except Exception as exc:
                # If retry also fails, keep the original report but mark validation
                pass
        # Re‑validate after retry
        report, val_info = validate_report(report, raw_lines, validate_only=False)
        retried = True
    # Drop any remaining invalid evidence
    if val_info.invalid > 0:
        # Already dropped in validator; just adjust confidence if needed
        if not report.evidence:
            report.confidence = "low"
            report.confidence_reason = "no valid evidence"
        else:
            report.confidence = "medium"
            report.confidence_reason = "some evidence was invalid and removed"
    # Assemble meta
    duration_ms = int((time.time() - start_ts) * 1000)
    meta = Meta(
        mode="pipeline",
        model=settings.LLM_MODEL,
        provider=settings.LLM_PROVIDER,
        duration_ms=duration_ms,
        input_chars=len(logs),
        input_lines=len(logs.splitlines()),
        prompt_chars=len(user_prompt),
        tokens_estimate=len(user_prompt) // 4,
        truncated=reduced.truncated,
        notice=reduced.notice,
        validation=val_info.model_copy(update={"retried": retried}),
        demo=provider == "fake",
    )
    response = AnalyzeResponse(
        id="demo-id",  # In a real implementation a UUID would be generated
        report=report,
        patterns=reduced.patterns,
        stats={"total_lines": reduced.total_lines, "events_parsed": reduced.events_parsed, "format": fmt},
        meta=meta,
    )
    return response
