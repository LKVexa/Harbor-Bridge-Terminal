"""MC-030 - Capacity / saturation model (GAP03-CAP/1).

service_time(n) = base_us + per_candidate_us * n  (fitted by least squares
from measured runs of the real scorer); commit path adds store_us
(fsync-bound, measured).  Per replica: throughput = cores * util_target *
1e6 / service_time; M/M/c-style headroom via Erlang-C waiting estimate.
A single leader serialises commits (GLOBAL bottleneck), so commit throughput
does not scale with replicas - scale-out helps scoring only.
"""
from __future__ import annotations

import math
import time

UTIL_TARGET = 0.6
BURST_FACTOR = 2.0
MIN_REPLICAS, MAX_REPLICAS = 2, 32


def fit(samples: list[tuple[int, float]]) -> dict:
    n = len(samples)
    if n < 2:
        raise ValueError("need >=2 samples")
    xs, ys = [s[0] for s in samples], [s[1] for s in samples]
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in samples) / sxx if sxx else 0.0
    base = my - slope * mx
    resid = [y - (base + slope * x) for x, y in samples]
    return {"base_us": max(0.0, base), "per_candidate_us": max(0.0, slope),
            "rmse_us": math.sqrt(sum(r * r for r in resid) / n)}


def measure_scoring(counts=(10, 100, 500, 1000, 2000), repeats=15) -> list[tuple[int, float]]:
    from ..scheduler import Topology, _score_snapshot
    out = []
    for n in counts:
        topo = Topology()
        for i in range(n):
            topo.place(f"n{i}", f"r{i % 4}", f"s{i % 16}", f"k{i % 64}")
        snap = topo.snapshot()
        cands = [f"n{i}" for i in range(n)]
        best = []
        for _ in range(repeats):
            t = time.perf_counter()
            _score_snapshot(snap, "n0", cands, spread_from=["n1"])
            best.append((time.perf_counter() - t) * 1e6)
        best.sort()
        out.append((n, best[len(best) // 2]))
    return out


def erlang_c(c: int, a: float) -> float:
    if a >= c:
        return 1.0
    s = sum(a ** k / math.factorial(k) for k in range(c))
    top = a ** c / math.factorial(c) * c / (c - a)
    return top / (s + top)


def plan(model: dict, *, rps: float, candidates: int, cores: int = 2, store_us: float = 2000.0, commit_fraction: float = 1.0,
         p99_target_ms: float = 20.0) -> dict:
    svc_us = model["base_us"] + model["per_candidate_us"] * candidates
    per_replica = cores * UTIL_TARGET * 1e6 / svc_us
    replicas = max(MIN_REPLICAS, math.ceil(rps * BURST_FACTOR / per_replica))
    commit_ceiling = 1e6 / store_us  # single leader, serial fsync
    lam = rps / replicas
    mu = 1e6 / svc_us
    pw = erlang_c(cores, lam / mu)
    wait_ms = pw / (cores * mu - lam) * 1000 if cores * mu > lam else float("inf")
    return {"service_time_us": round(svc_us, 1), "per_replica_rps": round(per_replica, 1), "replicas": min(replicas, MAX_REPLICAS),
            "replicas_capped": replicas > MAX_REPLICAS, "commit_ceiling_rps": round(commit_ceiling, 1),
            "commit_bottleneck": rps * commit_fraction > commit_ceiling, "est_queue_wait_ms": round(wait_ms, 3),
            "meets_p99_target": svc_us / 1000 + wait_ms * 4.6 < p99_target_ms,
            "max_safe_concurrency": cores, "scale_signals": {"scale_out_at_util": 0.7, "scale_in_at_util": 0.3,
                                                             "stabilization_window_s": 300}}


def envelope(model: dict, *, cores: int = 2, p99_target_ms: float = 20.0) -> dict:
    max_cand = int((p99_target_ms * 1000 / 3 - model["base_us"]) / max(model["per_candidate_us"], 1e-9))
    return {"max_candidates_for_p99_target": max_cand, "alert_utilization": 0.8,
            "note": "envelope derived from single-core scoring fit; recalibrate on hardware/implementation change"}


def recalibrate(model: dict, measured: list[tuple[int, float]], tolerance: float = 0.3) -> dict:
    errs = [abs((model["base_us"] + model["per_candidate_us"] * n) - y) / y for n, y in measured if y > 0]
    worst = max(errs) if errs else 0.0
    return {"max_relative_error": round(worst, 3), "recalibrate": worst > tolerance}
