# LLM factory – builds LangChain chat model for Groq, Google, or a deterministic fake provider.
# The returned object must expose an async `with_structured_output(...).ainvoke(messages)` interface.

import os
from typing import Any

from ..config import settings

# Custom exception types for the analyzer to map to HTTP errors
class LLMError(RuntimeError):
    pass

class LLMRateLimitError(RuntimeError):
    pass

# Fake provider implementation – deterministic, no external calls.
class FakeChatModel:
    def __init__(self, reduced):
        self.reduced = reduced
        # The fake model just builds a minimal report based on reduced data.

    def with_structured_output(self, schema):
        # Return self – the fake model already knows how to produce the schema.
        return self

    async def ainvoke(self, messages: list[dict[str, Any]]) -> Any:
        # The messages list contains a system prompt and then the user prompt.
        # We'll ignore the content and construct a deterministic AnalysisReport.
        from ..schemas import AnalysisReport, RootCause, EvidenceItem, TimelineItem, ValidationInfo, Meta
        # Build a simple root cause from the first error (if any)
        first_error = self.reduced.first_error
        if first_error:
            rc = RootCause(
                title=first_error.message[:80] + ("..." if len(first_error.message) > 80 else ""),
                explanation="The earliest error appears to be the root cause.",
                category="unknown",
            )
            evidence = [
                EvidenceItem(
                    line_number=first_error.line_no,
                    text=first_error.message,
                    why="earliest error",
                )
            ]
            confidence = "high"
        else:
            rc = RootCause(title="No error detected", explanation="No error lines were found.", category="unknown")
            evidence = []
            confidence = "low"
        report = AnalysisReport(
            summary="Demo mode – deterministic report based on reduced log.",
            root_cause=rc,
            evidence=evidence,
            timeline=[],
            suggested_fixes=[],
            confidence=confidence,
            confidence_reason="deterministic fallback",
            limitations=None,
        )
        meta = Meta(
            mode="pipeline",
            model="fake",
            provider="fake",
            duration_ms=0,
            input_chars=0,
            input_lines=0,
            prompt_chars=0,
            tokens_estimate=0,
            truncated=False,
            notice=None,
            validation=ValidationInfo(cited=0, valid=0, invalid=0, retried=False, corrected=0, dropped=0),
            demo=True,
        )
        # The analyzer expects a dict with 'report' and other fields – we'll let the caller wrap it.
        return {"report": report, "meta": meta}

def get_chat_model():
    """Return a LangChain chat model (or fake) based on the Settings.
    Raises LLMError if required API key is missing.
    """
    provider = settings.LLM_PROVIDER.lower()
    model_id = settings.LLM_MODEL
    if provider == "fake":
        # The reducer will be passed later; we return a placeholder that expects `.with_structured_output` to be called.
        # The analyzer will instantiate FakeChatModel with the reduced data before invoking.
        return "FAKE_PLACEHOLDER"
    if provider == "groq":
        api_key = settings.GROQ_API_KEY
        if not api_key:
            raise LLMError("Groq API key is missing. Set GROQ_API_KEY in the environment.")
        try:
            from langchain_groq import ChatGroq
        except ImportError as e:
            raise LLMError("langchain_groq package not installed.")
        return ChatGroq(model=model_id, temperature=0, api_key=api_key)
    if provider == "google":
        api_key = settings.GOOGLE_API_KEY
        if not api_key:
            raise LLMError("Google API key is missing. Set GOOGLE_API_KEY in the environment.")
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as e:
            raise LLMError("langchain_google_genai package not installed.")
        return ChatGoogleGenerativeAI(model=model_id, temperature=0, api_key=api_key)
    raise LLMError(f"Unsupported LLM provider: {provider}")
