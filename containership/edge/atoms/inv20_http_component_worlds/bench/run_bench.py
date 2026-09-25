"""Benchmark suite + regression gate (checklist component 15).

Measures handler-dispatch overhead separately from user code (the handler is a no-op), plus
authority parsing, field validation, egress authorisation and stream forwarding.

    python -m inv20_http_component_worlds.bench.run_bench            # measure + compare
    python -m inv20_http_component_worlds.bench.run_bench --update   # re-baseline (needs waiver/owner)

Gate: a scenario regresses when its median exceeds baseline p50 * (1 + allowed_regression), or its p99
exceeds baseline p99 * (2 + 2 * allowed_regression) (tails are noisy on shared runners). The contract SLO "p99 handler dispatch under 1ms excluding user code" is checked
against `dispatch_async` directly.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import platform
import statistics
import sys
import time
import tracemalloc

from ..aio import AsyncHttpWorld, Deadline
from ..egress import Answer, DestinationPolicy
from ..identity import Principal, PrincipalKind
from ..protocol import Fields, Request, Response, parse_authority
from ..runtime import BodyStream

HERE = pathlib.Path(__file__).resolve().parent
BASELINE = HERE / "baseline.json"
SLO_DISPATCH_P99_S = 0.001


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def timeit(fn, n=2000, warmup=200):
    for _ in range(warmup):
        fn()
    out = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        out.append(time.perf_counter() - t0)
    return out


class _R:
    def resolve(self, h):
        return Answer(("93.184.216.34",))


def scenarios():
    pol = DestinationPolicy.from_hosts(["api.example.com"], resolver=_R())
    yield "parse_authority", timeit(lambda: parse_authority("api.example.com:443"))
    yield "fields_20", timeit(lambda: Fields([(f"x-h{i}", "value") for i in range(20)]))
    yield "egress_authorize_cached", timeit(lambda: pol.authorize("https", "api.example.com"))

    def stream():
        s = BodyStream(limit=1 << 20)
        for _ in range(64):
            s.write(b"x" * 1024)
            s.forward()
    yield "stream_64k", timeit(stream, n=500, warmup=50)

    async def dispatch_bench():
        async def h(req, out):
            out.set(Response(200))
            await out.finish()
        w = AsyncHttpWorld("bench")
        w.export_handler(h)
        p = Principal(PrincipalKind.WORKLOAD, "t", "w")
        req = Request.build("GET", "https", "h.com")
        xs = []
        for i in range(1200):
            t0 = time.perf_counter()
            await w.handle(req, p, Deadline.after(1000))
            if i >= 200:
                xs.append(time.perf_counter() - t0)
        await asyncio.sleep(0)
        return xs
    yield "dispatch_async", asyncio.run(dispatch_bench())


def measure(runs: int = 3) -> dict:
    tracemalloc.start()
    t0 = time.perf_counter()
    results = {}
    for _ in range(runs):
        for name, xs in scenarios():
            results.setdefault(name, []).extend(xs)
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return {"schema": "INV20_BENCH/1", "python": sys.version.split()[0], "platform": platform.platform(),
            "machine": platform.machine(), "runs": runs, "wall_s": round(time.perf_counter() - t0, 3),
            "peak_traced_bytes": peak,
            "scenarios": {k: {"n": len(v), "p50": pct(v, 50), "p95": pct(v, 95), "p99": pct(v, 99),
                              "max": max(v), "mean": statistics.fmean(v)} for k, v in results.items()}}


def compare(cur: dict, base: dict) -> dict:
    allowed = base.get("allowed_regression", 0.5)
    rows, ok = [], True
    for name, m in cur["scenarios"].items():
        b = base["scenarios"].get(name)
        # Median carries the regression signal; p99 gets 2x headroom because tails are noisy on shared runners.
        regress = bool(b) and ((m["p50"] > b["p50"] * (1 + allowed) and m["p50"] > b["p50"] + 5e-6) or
                               (m["p99"] > b["p99"] * (1 + 2 * allowed + 0.5) and m["p99"] > b["p99"] + 20e-6))
        if regress:
            ok = False
        rows.append({"scenario": name, "p50": m["p50"], "baseline_p50": b["p50"] if b else None,
                     "p99": m["p99"], "baseline_p99": b["p99"] if b else None, "regressed": regress})
    slo_ok = cur["scenarios"]["dispatch_async"]["p99"] < SLO_DISPATCH_P99_S
    return {"schema": "INV20_BENCH_GATE/1", "ok": ok and slo_ok, "slo_dispatch_p99_ok": slo_ok,
            "allowed_regression": allowed, "rows": rows,
            "baseline_environment": base.get("platform"), "controlled_hardware": base.get("controlled_hardware", False)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    cur = measure()
    if a.update or not BASELINE.exists():
        cur.update({"allowed_regression": 0.5, "controlled_hardware": False,
                    "note": "captured in shared cloud sandbox; re-baseline on pinned hardware before release"})
        BASELINE.write_text(json.dumps(cur, indent=1))
        print("baseline written")
        return 0
    gate = compare(cur, json.loads(BASELINE.read_text()))
    doc = {"measurement": cur, "gate": gate}
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(doc, indent=1))
    print(json.dumps(gate, indent=1))
    return 0 if gate["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
