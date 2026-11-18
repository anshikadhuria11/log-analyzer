# Optional DynamoDB storage – placeholder implementation for demo mode
# Stores analysis reports keyed by a UUID. In demo mode (FAKE provider) we keep data in‑memory.

import os
import uuid
from typing import Dict, List, Optional

from pydantic import BaseModel

# In‑memory store used when DynamoDB endpoint is not configured.
_IN_MEMORY_DB: Dict[str, dict] = {}

class StorageError(RuntimeError):
    """Raised when persistence fails (e.g., missing credentials)."""
    pass

class HistoryItem(BaseModel):
    id: str
    report: dict
    timestamp: float

async def save_report(report: dict) -> str:
    """Persist an analysis report and return its generated ID.
    If a real DynamoDB table is configured via ``DYNAMODB_TABLE`` env var,
    the function would write to AWS. For this open‑source version we fall
    back to an in‑memory dictionary.
    """
    # In a production build you would use ``aioboto3`` or ``boto3`` async client.
    # Here we simply store the report locally.
    report_id = str(uuid.uuid4())
    _IN_MEMORY_DB[report_id] = {"report": report, "timestamp": time.time()}
    return report_id

async def get_report(report_id: str) -> Optional[dict]:
    """Retrieve a stored report by its ID. Returns ``None`` if not found."""
    return _IN_MEMORY_DB.get(report_id)

async def list_reports(limit: int = 10) -> List[HistoryItem]:
    """Return the most recent ``limit`` reports sorted by timestamp descending."""
    items = [
        HistoryItem(id=rid, report=data["report"], timestamp=data["timestamp"]).dict()
        for rid, data in _IN_MEMORY_DB.items()
    ]
    items.sort(key=lambda x: x["timestamp"], reverse=True)
    return items[:limit]
