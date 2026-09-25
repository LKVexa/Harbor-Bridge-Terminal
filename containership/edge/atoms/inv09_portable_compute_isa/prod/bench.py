"""M29 benchmark harness + M30 release performance gate.

SLO under test (README): validation p99 < 20 ms for modules up to 4 MiB.
The generator builds modules of a target size from many small typed
functions, so the benchmark exercises the type checker rather than only
skipping over data bytes.
"""
from __future__ import annotations

import platform
import random
import statistics
import time

from .fuzz import _u, gen_expr
from .typecheck import validate_module

I32 = 0x7F


def make_module(target_bytes: int, seed: int = 0) -> bytes:
    rng = random.Random(seed)
    bodies = []
    total = 0
    budget = target_bytes - 64  # header, type section, vector/section length prefixes
    while True:
        code = gen_expr(rng, I32, 6, [I32, I32]) + b"\x0b"
        body = b"\x00" + code
        entry = _u(len(body)) + body
        if total + len(entry) + 1 > budget:  # +1: this function's function-section entry
            break
        bodies.append(entry)
        total += len(entry) + 1
    n = len(bodies)

    def sec(i, p):
        return bytes([i]) + _u(len(p)) + p
    return (b"\x00asm\x01\x00\x00\x00" + sec(1, b"\x01\x60\x02\x7f\x7f\x01\x7f")
            + sec(3, _u(n) + b"\x00" * n) + sec(10, _u(n) + b"".join(bodies)))


def run(sizes=(1024, 64 * 1024, 1024 * 1024, 4 * 1024 * 1024 - 64), reps: int = 15) -> dict:
    rows = []
    for size in sizes:
        m = make_module(size)
        validate_module(m)  # warm-up + correctness
        samples = []
        for _ in range(reps):
            t = time.perf_counter()
            validate_module(m)
            samples.append((time.perf_counter() - t) * 1000)
        samples.sort()
        p99 = samples[min(len(samples) - 1, int(round(0.99 * (len(samples) - 1))))]
        rows.append({"target_bytes": size, "actual_bytes": len(m), "reps": reps,
                     "p50_ms": round(statistics.median(samples), 2), "p99_ms": round(p99, 2),
                     "mib_per_s": round(len(m) / 1048576 / (statistics.median(samples) / 1000), 2)})
    return {"schema": "PK_BENCHMARK/1", "python": platform.python_version(),
            "machine": platform.machine(), "rows": rows}


def gate(report: dict, *, slo_ms: float = 20.0, max_bytes: int = 4 * 1024 * 1024) -> dict:
    """M30: PASS only if every in-scope size meets the p99 SLO."""
    breaches = [r for r in report["rows"] if r["actual_bytes"] <= max_bytes and r["p99_ms"] > slo_ms]
    return {"schema": "PK_PERF_GATE/1", "slo_p99_ms": slo_ms,
            "verdict": "PASS" if not breaches else "FAIL", "breaches": breaches}
