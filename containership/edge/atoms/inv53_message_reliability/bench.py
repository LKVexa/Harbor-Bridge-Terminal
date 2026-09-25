"""Reproducible benchmark harness and regression gate (components 50-54, 56, 58, 59).

``run(profile)`` executes a fixed matrix of load shapes against the in-memory
reference and the durable queue, with a fixed RNG seed, and reports latency
percentiles, worst case, throughput, bytes serialized per op and resource-bound
figures.  ``gate(result, thresholds)`` compares a run with the thresholds file and
returns PASS/FAIL per metric; thresholds are *PROPOSED* until an owner signs them,
so a met threshold reads ``met_under_proposed_threshold`` and never ``PASS`` in
the production exit gate.

Numbers are environment-specific.  The result embeds the interpreter, platform
and CPU count of the run as *evidence*, never as a constant in the repository.
"""
from __future__ import annotations

import json
import os
import platform
import random
import shutil
import statistics
import sys
import tempfile
import time
import tracemalloc
from typing import Any, Callable

from .durable import DurableQueue
from .reliability import ReliableQueue

SHAPES = ("steady", "burst", "redelivery", "large_message", "deep_backlog")


def _pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = min(len(s) - 1, max(0, int(round(p / 100.0 * (len(s) - 1)))))
    return s[k]


def _timed(fn: Callable[[], Any], lat: list[float]) -> Any:
    t = time.perf_counter()
    r = fn()
    lat.append(time.perf_counter() - t)
    return r


def _shape(q: Any, shape: str, n: int, rng: random.Random) -> dict[str, Any]:
    lat: dict[str, list[float]] = {"put": [], "receive": [], "ack": [], "nack": []}
    size = 16_384 if shape == "large_message" else 128
    body = "x" * size
    serialized = 0
    now = 0.0
    t0 = time.perf_counter()
    if shape in ("steady", "large_message", "redelivery"):
        for i in range(n):
            m = {"id": f"m{i}", "payload": body}
            serialized += len(json.dumps(m))
            _timed(lambda: q.put(m), lat["put"])
            d = _timed(lambda: q.receive(now=now), lat["receive"])
            if shape == "redelivery" and rng.random() < 0.3:
                _timed(lambda: q.nack(d, now=now), lat["nack"])
                d = _timed(lambda: q.receive(now=now), lat["receive"])
            _timed(lambda: q.ack(d, now=now), lat["ack"])
            now += 0.001
    else:  # burst / deep_backlog: enqueue everything then drain
        for i in range(n):
            m = {"id": f"m{i}", "payload": body}
            serialized += len(json.dumps(m))
            _timed(lambda: q.put(m), lat["put"])
        while True:
            d = _timed(lambda: q.receive(now=now), lat["receive"])
            if d is None:
                break
            _timed(lambda: q.ack(d, now=now), lat["ack"])
    elapsed = time.perf_counter() - t0
    ops = sum(len(v) for v in lat.values())
    return {
        "messages": n, "ops": ops, "elapsed_s": round(elapsed, 6),
        "throughput_msgs_per_s": round(n / elapsed, 1) if elapsed else None,
        "serialized_bytes_per_msg": serialized // max(n, 1),
        "latency_s": {k: {"p50": _pct(v, 50), "p95": _pct(v, 95), "p99": _pct(v, 99), "max": max(v) if v else 0.0,
                          "mean": statistics.fmean(v) if v else 0.0, "n": len(v)} for k, v in lat.items() if v},
    }


def run(*, n: int = 2_000, seed: int = 53, fsync: bool = False, shapes: tuple[str, ...] = SHAPES) -> dict[str, Any]:
    rng = random.Random(seed)
    results: dict[str, Any] = {}
    for impl in ("memory", "durable"):
        for shape in shapes:
            tmp = tempfile.mkdtemp(prefix="inv53-bench-")
            try:
                tracemalloc.start()
                if impl == "memory":
                    q: Any = ReliableQueue(visibility=30, max_attempts=5)
                else:
                    q = DurableQueue(tmp, visibility=30, max_attempts=5, fsync=fsync, compact_every=0,
                                     max_message_bytes=65_536)
                r = _shape(q, shape, n, rng)
                cur, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                r["peak_traced_bytes"] = peak
                r["peak_bytes_per_msg"] = peak // max(n, 1)
                if impl == "durable":
                    r["journal_bytes"] = os.path.getsize(os.path.join(tmp, "journal.jsonl"))
                    q.close()
                results[f"{impl}/{shape}"] = r
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
    steady = results.get("durable/steady", {})
    model = {}
    if steady.get("throughput_msgs_per_s"):
        # Linear single-writer capacity model: one queue is serialised by its lock and journal.
        per_msg = 1.0 / steady["throughput_msgs_per_s"]
        model = {"single_queue_max_msgs_per_s": steady["throughput_msgs_per_s"],
                 "seconds_per_msg": per_msg,
                 "saturation_predictor": "utilisation = offered_rate * seconds_per_msg; shed above 0.8",
                 "fsync": fsync}
    return {"schema": "inv53.bench/1", "seed": seed, "n": n, "fsync": fsync,
            "environment": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                            "platform": platform.platform(), "cpu_count": os.cpu_count()},
            "results": results, "capacity_model": model,
            "not_measured": ["power/thermal (no RAPL/IPMI access in this harness)",
                             "fleet-scale / multi-host (no fleet)", "context switches (no perf counters)"]}


def gate(result: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, Any]:
    checks = []
    for key, limits in thresholds.get("limits", {}).items():
        impl_shape, op, metric = key.rsplit(".", 2) if key.count(".") >= 2 else (key, None, None)
        r = result["results"].get(impl_shape)
        if r is None or op not in r.get("latency_s", {}):
            checks.append({"metric": key, "status": "NOT_RUN", "reason": "shape/op absent from run"})
            continue
        observed = r["latency_s"][op][metric]
        ok = observed <= limits["max"]
        checks.append({"metric": key, "observed": observed, "limit": limits["max"],
                       "status": ("met" if ok else "FAIL") + ("_under_proposed_threshold" if thresholds.get("status") != "APPROVED" else "")})
    failed = [c for c in checks if c["status"].startswith("FAIL")]
    return {"schema": "inv53.perfgate/1", "thresholds_status": thresholds.get("status", "PROPOSED"),
            "verdict": "FAIL" if failed else ("PASS" if thresholds.get("status") == "APPROVED" else "MET_UNDER_PROPOSED"),
            "checks": checks}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="inv53-bench")
    ap.add_argument("--n", type=int, default=2_000)
    ap.add_argument("--fsync", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--thresholds")
    a = ap.parse_args(argv)
    res = run(n=a.n, fsync=a.fsync)
    if a.thresholds:
        with open(a.thresholds, encoding="utf-8") as fh:
            res["gate"] = gate(res, json.load(fh))
    text = json.dumps(res, indent=1, sort_keys=True)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text + "\n")
    return 1 if res.get("gate", {}).get("verdict") == "FAIL" else 0
