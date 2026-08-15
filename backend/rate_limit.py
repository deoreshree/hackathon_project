"""Lightweight in-memory rate limiting for public API endpoints.

Design notes
------------
* Uses only in-memory state — suitable for a single-process hackathon demo,
  not for multi-worker production deployments.
* Sliding-window counter keyed by a client identifier (client IP by default).
* Configurable via environment variables (see ``create_rate_limiter``) so the
  demo can tighten or disable limits without code changes.
* Returns ``allow() == False`` once the limit is reached; the API layer turns
  that into an HTTP 429 response.
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

DEFAULT_MAX_REQUESTS = 120
DEFAULT_WINDOW_SECONDS = 60.0


class RateLimiter:
    """Sliding-window rate limiter keyed by client identifier."""

    def __init__(
        self,
        max_requests: int = DEFAULT_MAX_REQUESTS,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        *,
        enabled: bool = True,
    ) -> None:
        if max_requests < 1:
            raise ValueError("max_requests must be at least 1.")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive.")

        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.enabled = enabled
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, *, now: float | None = None) -> bool:
        """Record one request for *key* and return True if it is allowed.

        When the limiter is disabled, every request is allowed.
        """
        if not self.enabled:
            return True

        current = now if now is not None else time.monotonic()
        hits = self._hits[key]
        cutoff = current - self.window_seconds

        # Drop hits that have fallen outside the sliding window.
        while hits and hits[0] <= cutoff:
            hits.popleft()

        if len(hits) >= self.max_requests:
            return False

        hits.append(current)
        return True

    def reset(self) -> None:
        """Clear all recorded request history (used by tests)."""
        self._hits.clear()


def create_rate_limiter() -> RateLimiter:
    """Build a RateLimiter from environment variables with safe defaults."""
    def _as_int(name: str, default: int) -> int:
        raw = os.getenv(name)
        if raw is None:
            return default
        try:
            return int(raw)
        except ValueError:
            logger.warning("Invalid integer for %s=%r; using default %s.", name, raw, default)
            return default

    def _as_float(name: str, default: float) -> float:
        raw = os.getenv(name)
        if raw is None:
            return default
        try:
            return float(raw)
        except ValueError:
            logger.warning("Invalid number for %s=%r; using default %s.", name, raw, default)
            return default

    enabled = os.getenv("RATE_LIMIT_ENABLED", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }

    return RateLimiter(
        max_requests=_as_int("RATE_LIMIT_MAX_REQUESTS", DEFAULT_MAX_REQUESTS),
        window_seconds=_as_float("RATE_LIMIT_WINDOW_SECONDS", DEFAULT_WINDOW_SECONDS),
        enabled=enabled,
    )
