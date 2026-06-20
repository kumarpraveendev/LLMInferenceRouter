"""Exact-match response cache with a TTL (ADR-0006).

Correct by construction: keyed on the exact request key, and an entry past its
TTL is never served. Semantic caching is deliberately out of scope until its
false-hit risk is gated by evals (ADR-0006/0007).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class _Entry:
    value: str
    expires_at: float


class ResponseCache:
    def __init__(self, ttl_seconds: float = 3600.0, now_fn: Callable[[], float] = time.monotonic):
        self._ttl = ttl_seconds
        self._now = now_fn
        self._store: dict[str, _Entry] = {}

    def put(self, key: str, value: str) -> None:
        self._store[key] = _Entry(value, self._now() + self._ttl)

    def get(self, key: str) -> Optional[str]:
        entry = self._store.get(key)
        if entry is None:
            return None
        if self._now() >= entry.expires_at:
            del self._store[key]      # stale beyond TTL -> never served
            return None
        return entry.value
