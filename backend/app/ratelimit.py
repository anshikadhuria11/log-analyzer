# Simple in‑memory rate limiter – per client IP
# Prevents abusive request bursts; reset interval is configurable.

import time
from collections import defaultdict
from typing import Dict

from fastapi import Request, HTTPException, status

# Settings are loaded from backend/app/config.py – we expose defaults here for safety.

class RateLimiter:
    """Track request timestamps per IP and enforce a max‑requests‑per‑window limit.
    Usage: call `await limiter.check(request)` inside a route dependency.
    """
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._store: Dict[str, list[float]] = defaultdict(list)

    async def check(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        timestamps = self._store[client_ip]
        # Drop timestamps older than the window
        while timestamps and now - timestamps[0] > self.window:
            timestamps.pop(0)
        if len(timestamps) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again later.",
            )
        timestamps.append(now)

# Global limiter instance – shared across the app.
limiter = RateLimiter()
