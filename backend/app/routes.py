# FastAPI router – exposes health, config, analyze, and history endpoints
# Uses services defined elsewhere; minimal validation and rate‑limiting.

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from .config import settings
from .schemas import AnalyzeRequest, AnalyzeResponse, AnalysisReport
from .services.parser import parse_logs
from .services.analyzer import analyze_pipeline
from .services.baseline import analyze_raw
from .services.storage import save_report, get_report, list_reports
from .ratelimit import limiter

router = APIRouter()

@router.get("/health", tags=["system"])
async def health_check() -> dict:
    """Simple health endpoint – always returns OK."""
    return {"status": "ok"}

@router.get("/config", tags=["system"])
async def get_config() -> dict:
    """Expose selected runtime configuration (read‑only)."""
    return {
        "model": settings.LLM_MODEL,
        "provider": settings.LLM_PROVIDER,
        "max_tokens": settings.LLM_MAX_TOKENS,
        "rate_limit": {
            "max_requests": limiter.max_requests,
            "window_seconds": limiter.window,
        },
    }

@router.post("/analyze", response_model=AnalyzeResponse, tags=["analysis"])
async def analyze(request: Request, payload: AnalyzeRequest) -> AnalyzeResponse:
    """Main analysis endpoint – supports ``pipeline`` and ``raw`` modes.
    ``save`` flag triggers persistence via the optional storage service.
    """
    from .services.llm import LLMError, LLMRateLimitError
    await limiter.check(request)
    try:
        if payload.mode == "pipeline":
            response = await analyze_pipeline(payload.logs, save=payload.save)
        elif payload.mode == "raw":
            response = await analyze_raw(payload.logs, save=payload.save)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported mode")
    except LLMRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"LLM rate limit: {exc}")
    except LLMError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"LLM error: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return response

@router.get("/history", tags=["history"])
async def history(limit: int = 10) -> list[dict]:
    """Return the most recent analysis reports (if storage is enabled)."""
    reports = await list_reports(limit=limit)
    return reports

@router.get("/history/{report_id}", tags=["history"])
async def get_history(report_id: str) -> dict:
    """Fetch a single stored report by its identifier."""
    report = await get_report(report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report

# NOTE: No additional routes are required for the specification.
