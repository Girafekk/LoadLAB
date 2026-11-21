"""Простой нагрузочный прогон без внешних зависимостей.

Запуск из корня:
    python tools/load_test.py https://localhost:8443 50 30
"""

from __future__ import annotations

import http.client
import json
import ssl
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "https://localhost:8443"
USERS = int(sys.argv[2]) if len(sys.argv) > 2 else 50
SECONDS = int(sys.argv[3]) if len(sys.argv) > 3 else 30
PATH = "/api/v1/courses/current"
PARSED = urlparse(BASE)
CONTEXT = ssl._create_unverified_context()
LOCK = threading.Lock()
LATENCIES: list[float] = []
ERRORS = 0


def new_connection() -> http.client.HTTPConnection:
    if PARSED.scheme == "http":
        return http.client.HTTPConnection(PARSED.hostname, PARSED.port or 80, timeout=10)
    return http.client.HTTPSConnection(
        PARSED.hostname, PARSED.port or 443, context=CONTEXT, timeout=10
    )


def worker(stop: float) -> None:
    global ERRORS
    conn = new_connection()
    while time.monotonic() < stop:
        started = time.perf_counter()
        try:
            conn.request("GET", PATH)
            response = conn.getresponse()
            response.read()
            if response.status >= 500:
                raise RuntimeError(response.status)
            elapsed = (time.perf_counter() - started) * 1000
            with LOCK:
                LATENCIES.append(elapsed)
        except Exception:
            with LOCK:
                ERRORS += 1
            try:
                conn.close()
            finally:
                conn = new_connection()
    conn.close()


def percentile(values: list[float], share: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * share))]


stop_at = time.monotonic() + SECONDS
with ThreadPoolExecutor(max_workers=USERS) as pool:
    list(pool.map(lambda _: worker(stop_at), range(USERS)))

print(
    json.dumps(
        {
            "base": BASE,
            "users": USERS,
            "seconds": SECONDS,
            "requests": len(LATENCIES) + ERRORS,
            "errors": ERRORS,
            "rps": round((len(LATENCIES) + ERRORS) / SECONDS, 1),
            "p50_ms": round(statistics.median(LATENCIES), 1) if LATENCIES else 0,
            "p95_ms": round(percentile(LATENCIES, 0.95), 1),
            "p99_ms": round(percentile(LATENCIES, 0.99), 1),
            "max_ms": round(max(LATENCIES), 1) if LATENCIES else 0,
        },
        ensure_ascii=False,
    )
)
