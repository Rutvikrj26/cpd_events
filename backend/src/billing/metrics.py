"""Simple process-local counters for Stripe webhook activity.

Intentionally not a Prometheus client — the ``StripeEvent`` table is the
durable source of truth for counts (query it for dashboards). These counters
are available if a worker wants a cheap recent-history view without hitting
the DB.
"""

from __future__ import annotations

import threading
from collections import defaultdict

_lock = threading.Lock()
_counters: dict[str, int] = defaultdict(int)


def inc(name: str, by: int = 1) -> None:
    with _lock:
        _counters[name] += by


def snapshot() -> dict[str, int]:
    with _lock:
        return dict(_counters)


def reset() -> None:
    with _lock:
        _counters.clear()
