"""Probe-latency benchmark and SLO gate (MC-08).

One probe = ``Prober.probe(use_cache=False)``: backend selection, full host evidence
collection, classification, telemetry.  Backend construction/import is excluded
(setup); ``--cold`` adds a fresh Prober per sample.  Timer: ``time.perf_counter_ns``
(monotonic, high resolution).  Percentiles: nearest-rank on the sorted samples.

Exit codes: 0 pass; 1 absolute SLO failure (p99 >= 50 ms); 2 relative regression beyond
``--regress-pct`` against ``--baseline``; 3 noisy environment (load too high) - the
result is still written, never silently retried; 4 active waiver applied (reported).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import pathlib
import platform
import statistics
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))
from inv23_hardware_virtualization_primitive import __version__  # noqa: E402
from inv23_hardware_virtualization_primitive.probe import Prober  # noqa: E402

SLO_P99_MS = 50.0


def pct(sorted_ns, p):
    k = max(0, math.ceil(p / 100 * len(sorted_ns)) - 1)
    return sorted_ns[k]


def commit():
    try:
        return (
            subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HERE.parents[1], timeout=5).stdout.strip()
            or None
        )
    except (OSError, subprocess.SubprocessError):
        return None


def waiver_active(path, now):
    try:
        for w in json.loads(pathlib.Path(path).read_text())["waivers"]:
            if (
                w.get("check", "").startswith("SLO-probe-p99")
                and w.get("expires", "") > now
                and str(w.get("approval", "PENDING")).upper() != "PENDING"
            ):
                return w["id"]
    except (OSError, ValueError, KeyError):
        pass
    return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=2000)
    ap.add_argument("--warmup", type=int, default=100)
    ap.add_argument("--cold", action="store_true")
    ap.add_argument("--out", default=str(HERE.parents[1] / "evidence" / "benchmark-results.json"))
    ap.add_argument("--baseline")
    ap.add_argument("--regress-pct", type=float, default=25.0)
    ap.add_argument("--max-load", type=float, default=float(os.cpu_count() or 1))
    ap.add_argument("--machine-class", default=os.environ.get("INV23_MACHINE_CLASS", "unclassified"))
    ap.add_argument("--waivers", default=str(HERE.parents[1] / "security" / "waivers.json"))
    a = ap.parse_args(argv)
    if a.samples < 100:
        ap.error("need >= 100 samples for a meaningful p99")
    p = Prober(cache_ttl_s=0)
    for _ in range(a.warmup):
        p.probe(use_cache=False)
    load0 = os.getloadavg()[0] if hasattr(os, "getloadavg") else None
    ns = []
    last = None
    for _ in range(a.samples):
        q = Prober(cache_ttl_s=0) if a.cold else p
        t = time.perf_counter_ns()
        last = q.probe(use_cache=False)
        ns.append(time.perf_counter_ns() - t)
    load1 = os.getloadavg()[0] if hasattr(os, "getloadavg") else None
    s = sorted(ns)

    def ms(v):
        return round(v / 1e6, 4)

    stats = {
        "count": len(s),
        "min_ms": ms(s[0]),
        "median_ms": ms(statistics.median(s)),
        "p90_ms": ms(pct(s, 90)),
        "p95_ms": ms(pct(s, 95)),
        "p99_ms": ms(pct(s, 99)),
        "max_ms": ms(s[-1]),
        "mean_ms": ms(statistics.fmean(s)),
        "stdev_ms": ms(statistics.pstdev(s)),
    }
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    res = {
        "schema": "INV23_BENCHMARK/1",
        "generated_at": now,
        "component_version": __version__,
        "commit": commit(),
        "profile": {
            "cold": a.cold,
            "cache": "disabled",
            "warmup": a.warmup,
            "percentile_method": "nearest-rank",
            "timer": "perf_counter_ns",
        },
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "arch": platform.machine(),
            "backend": last.backend,
            "state": last.state,
            "virtualized": last.virtualized,
            "bare_metal": last.bare_metal,
            "machine_class": a.machine_class,
            "loadavg_before": load0,
            "loadavg_after": load1,
        },
        "stats": stats,
        "slo": {"p99_ms_threshold": SLO_P99_MS, "pass": stats["p99_ms"] < SLO_P99_MS},
        "raw_samples_ns": ns if a.samples <= 5000 else None,
    }
    code = 0
    if not res["slo"]["pass"]:
        code = 1
    if a.baseline and code == 0:
        base = json.loads(pathlib.Path(a.baseline).read_text())["stats"]["p99_ms"]
        res["regression"] = {"baseline_p99_ms": base, "pct": round((stats["p99_ms"] - base) / base * 100, 2) if base else None}
        if base and stats["p99_ms"] > base * (1 + a.regress_pct / 100):
            code = 2
    if load1 is not None and load1 > a.max_load:
        res["noisy"] = True
        code = code or 3
    if code in (1, 2):
        w = waiver_active(a.waivers, now)
        if w:
            res["waiver"] = w
            code = 4
    res["exit_code"] = code
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("stats", "slo", "exit_code")}))
    return code


if __name__ == "__main__":
    sys.exit(main())
