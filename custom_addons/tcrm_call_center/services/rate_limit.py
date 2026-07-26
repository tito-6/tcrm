# -*- coding: utf-8 -*-
"""Simple in-process rate limiter for token issuance (per DB/user)."""
from __future__ import annotations

import threading
import time

_lock = threading.Lock()
_buckets: dict[str, list[float]] = {}


def allow(key: str, *, limit: int = 20, window_seconds: int = 60) -> bool:
    now = time.time()
    with _lock:
        hits = _buckets.get(key, [])
        hits = [t for t in hits if now - t < window_seconds]
        if len(hits) >= limit:
            _buckets[key] = hits
            return False
        hits.append(now)
        _buckets[key] = hits
        return True
