"""Replay benchmark and evidence bundle (MC-42, MC-55 partial, RG-07).

Measures the contract SLO "p99 replay of 1000 events under 100ms" for the
in-memory and SQLite backends, plus append throughput.  Writes a versioned
bundle: raw samples, summary, environment metadata, workload definition,
pass/fail evaluation and a sha256 for each file.

The measurement is only as good as the machine it ran on: the bundle records
that machine, and it is NOT evidence for any other deployment profile.

    python3 -m inv57_durable_execution.tools.benchmark --out bench/ [--samples 200]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from inv57_durable_execution import __version__  # noqa: E402
from inv57_durable_execution.durable import InMemoryHistoryStore, Worker  # noqa: E402
from inv57_durable_execution.identity import WorkflowIdentity  # noqa: E402
from inv57_durable_execution.sqlite_store import SQLiteBackend, SQLiteHistoryStore  # noqa: E402

BUNDLE_SCHEMA = "INV57_BENCH_BUNDLE/1"
ACTIVITIES = 500          # 500 activities = 1000 history events
SLO_P99_MS = 100.0


def _wf(w):
    return [w.activity(f"a{i}", lambda i=i: {"i": i, "p": "x" * 32}) for i in range(ACTIVITIES)]


def pct(xs, p):
    xs = sorted(xs)
    k = (len(xs) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def run(samples: int) -> dict:
    seed = Worker()
    seed.run(_wf)
    text = seed.history_store.to_json()
    mem = []
    for _ in range(samples):
        store = InMemoryHistoryStore.from_json(text)
        t0 = time.perf_counter()
        Worker(store).run(_wf)
        mem.append((time.perf_counter() - t0) * 1000)

    d = tempfile.mkdtemp()
    ident = WorkflowIdentity("bench", "test", "s", "n", "wf", "run-1")
    b = SQLiteBackend(os.path.join(d, "b.db"))
    t0 = time.perf_counter()
    Worker(SQLiteHistoryStore(b, ident, b.acquire(ident, "bench", 3600))).run(_wf)
    append_s = time.perf_counter() - t0
    sq_open, sq_replay = [], []
    for _ in range(max(10, samples // 4)):
        t0 = time.perf_counter()
        store = SQLiteHistoryStore(b, ident, b.acquire(ident, "bench", 3600))
        t1 = time.perf_counter()
        Worker(store).run(_wf)
        t2 = time.perf_counter()
        sq_open.append((t1 - t0) * 1000)
        sq_replay.append((t2 - t1) * 1000)
    b.close()

    def summ(xs):
        return {"n": len(xs), "p50_ms": round(pct(xs, 50), 3), "p95_ms": round(pct(xs, 95), 3),
                "p99_ms": round(pct(xs, 99), 3), "max_ms": round(max(xs), 3),
                "mean_ms": round(statistics.fmean(xs), 3)}
    summary = {
        "replay_inmemory_1000_events": summ(mem),
        "sqlite_open_and_validate_1000_events": summ(sq_open),
        "sqlite_replay_1000_events": summ(sq_replay),
        "sqlite_durable_append_events_per_s": round(2 * ACTIVITIES / append_s, 1),
    }
    evaluation = {
        "slo": f"p99 replay of 1000 events under {SLO_P99_MS} ms",
        "inmemory": "met" if summary["replay_inmemory_1000_events"]["p99_ms"] < SLO_P99_MS else "not_met",
        "sqlite_replay": "met" if summary["sqlite_replay_1000_events"]["p99_ms"] < SLO_P99_MS else "not_met",
        "sqlite_open_plus_replay_p99_ms": round(
            summary["sqlite_open_and_validate_1000_events"]["p99_ms"]
            + summary["sqlite_replay_1000_events"]["p99_ms"], 3),
        "scope": "this machine only; not evidence for edge/fleet profiles (MC-44/MC-55 remain BLOCKED)",
    }
    return {"raw": {"replay_inmemory_ms": mem, "sqlite_open_ms": sq_open, "sqlite_replay_ms": sq_replay},
            "summary": summary, "evaluation": evaluation}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--samples", type=int, default=200)
    ap.add_argument("--baseline", help="previous bundle summary.json for MC-46 regression check")
    ap.add_argument("--max-regression", type=float, default=0.25)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    res = run(a.samples)
    env = {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
           "platform": platform.platform(), "machine": platform.machine(),
           "cpu_count": os.cpu_count(), "package_version": __version__,
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    workload = {"activities": ACTIVITIES, "events": 2 * ACTIVITIES, "payload": "{i:int, p:32 chars}",
                "samples": a.samples, "sqlite": "WAL + synchronous=FULL"}
    regression = None
    if a.baseline:
        base = json.load(open(a.baseline))["replay_inmemory_1000_events"]["p99_ms"]
        now = res["summary"]["replay_inmemory_1000_events"]["p99_ms"]
        regression = {"baseline_p99_ms": base, "current_p99_ms": now,
                      "allowed": a.max_regression, "regressed": now > base * (1 + a.max_regression)}
    files = {"raw_samples.json": res["raw"], "summary.json": res["summary"],
             "evaluation.json": {**res["evaluation"], "regression": regression},
             "environment.json": env, "workload.json": workload}
    hashes = {}
    for name, obj in files.items():
        data = (json.dumps(obj, indent=1, sort_keys=True) + "\n").encode()
        open(os.path.join(a.out, name), "wb").write(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    json.dump({"schema": BUNDLE_SCHEMA, "files": hashes}, open(os.path.join(a.out, "BUNDLE.json"), "w"),
              indent=1, sort_keys=True)
    print(json.dumps({"summary": res["summary"], "evaluation": res["evaluation"],
                      "regression": regression}, indent=1))
    return 1 if regression and regression["regressed"] else 0


if __name__ == "__main__":
    sys.exit(main())
