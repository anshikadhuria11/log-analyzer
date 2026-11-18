# Baseline service – raw mode (no reduction)
# Sends the raw numbered log lines directly to the LLM and validates citations.

import time
from typing import Any

from ..config import settings
from ..schemas import AnalyzeResponse, AnalysisReport, ValidationInfo, Meta
from .parser import parse_logs
from .llm import get_chat_model, LLMError, LLMRateLimitError, FakeChatModel
from .validator import validate_report
from ..prompts import build_raw_prompt

async def analyze_raw(logs: str, save: bool = False) -> AnalyzeResponse:
    """Raw‑mode analysis: send the entire log (numbered) to the LLM.
    No reduction, no retry – only validation in `validate_only` mode.
    """
    start_ts = time.time()
    # Parse to get lines for validation (still need line numbers for validator)
    events, fmt, warnings = parse_logs(logs)
    raw_lines = logs.splitlines()
    # Build raw prompt (system prompt included inside)
    user_prompt = build_raw_prompt(logs)
    provider = settings.LLM_PROVIDER.lower()
    if provider == "fake":
        model = FakeChatModel(None)  # no reduced data needed
        llm_resp = await model.with_structured_output(AnalysisReport).ainvoke([{"role": "system", "content": ""}, {"role": "user", "content": user_prompt}])
    else:
        model = get_chat_model()
        try:
            llm_resp = await model.with_structured_output(AnalysisReport).ainvoke([{"role": "system", "content": ""}, {"role": "user", "content": user_prompt}])
        except Exception as exc:
            if getattr(exc, "status_code", None) == 429:
                raise LLMRateLimitError(str(exc)) from exc
            raise LLMError(str(exc)) from exc
    if isinstance(llm_resp, dict) and "report" in llm_resp:
        report: AnalysisReport = llm_resp["report"]
    else:
        report = llm_resp  # type: ignore
    # Validate only – do not modify report, just count invalid citations
    _, val_info = validate_report(report, raw_lines, validate_only=True)
    duration_ms = int((time.time() - start_ts) * 1000)
    meta = Meta(
        mode="raw",
        model=settings.LLM_MODEL,
        provider=settings.LLM_PROVIDER,
        duration_ms=duration_ms,
        input_chars=len(logs),
        input_lines=len(raw_lines),
        prompt_chars=len(user_prompt),
        tokens_estimate=len(user_prompt) // 4,
        truncated=False,
        notice=None,
        validation=val_info,
        demo=provider == "fake",
    )
    response = AnalyzeResponse(
        id="demo-id-raw",
        report=report,
        patterns=[],
        stats={"total_lines": len(raw_lines), "events_parsed": len(events), "format": fmt},
        meta=meta,
    )
    return response
