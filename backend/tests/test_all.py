# Jest‑style placeholder tests for the Log Analyzer backend services.
# These tests import the target modules to ensure they load without errors.

import asyncio
import pytest

from backend.app.services.parser import parse_logs
from backend.app.services.reducer import reduce_events
from backend.app.services.validator import validate_report
from backend.app.services.analyzer import analyze_pipeline
from backend.app.services.baseline import analyze_raw
from backend.app.services.storage import save_report, get_report, list_reports

# Sample log strings for quick sanity checks
SAMPLE_TEXT_LOG = """2023-01-01 12:00:00 INFO Service started\n2023-01-01 12:01:00 ERROR Failure occurred\n"""

@pytest.mark.asyncio
async def test_parser_basic():
    events, fmt, warnings = parse_logs(SAMPLE_TEXT_LOG)
    assert isinstance(events, list)
    assert fmt in ("text", "jsonl", "cloudwatch")

@pytest.mark.asyncio
async def test_reducer_basic():
    events, _, _ = parse_logs(SAMPLE_TEXT_LOG)
    reduced = reduce_events(events, settings=None)  # type: ignore
    assert hasattr(reduced, "patterns")

@pytest.mark.asyncio
async def test_validator_basic():
    events, _, _ = parse_logs(SAMPLE_TEXT_LOG)
    reduced = reduce_events(events, settings=None)  # type: ignore
    # Build a mock report that cites line 1 and 2 correctly
    from backend.app.schemas import AnalysisReport, EvidenceItem, ValidationInfo, Meta, RootCause
    report = AnalysisReport(
        summary="test",
        root_cause=RootCause(title="test", explanation="test", category="unknown"),
        evidence=[EvidenceItem(line_number=1, text="INFO Service started", why="test")],
        timeline=[],
        suggested_fixes=[],
        confidence="high",
        confidence_reason="test",
    )
    _, val = validate_report(report, SAMPLE_TEXT_LOG.splitlines(), validate_only=False)
    assert isinstance(val, ValidationInfo)

@pytest.mark.asyncio
async def test_analyze_pipeline():
    response = await analyze_pipeline(SAMPLE_TEXT_LOG)
    assert response.report.summary

@pytest.mark.asyncio
async def test_analyze_raw():
    response = await analyze_raw(SAMPLE_TEXT_LOG)
    assert response.report.summary

@pytest.mark.asyncio
async def test_storage_cycle():
    report = {"dummy": True}
    rid = await save_report(report)
    fetched = await get_report(rid)
    assert fetched["report"]["dummy"] is True
    recent = await list_reports(limit=1)
    assert any(item["id"] == rid for item in recent)
