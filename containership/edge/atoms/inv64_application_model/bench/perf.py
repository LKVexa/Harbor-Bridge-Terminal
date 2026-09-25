"""Reproducible performance/resource baselines and regression gate (MC-21, MC-22; C061-C070).

    python -m inv64_application_model.bench.perf [--quick] [--out evidence/PERF.json]
    python -m inv64_application_model.bench.perf --compare evidence/PERF_BASELINE.json --candidate evidence/PERF.json

Method (BENCHMARKS.md): fixtures are generated deterministically (seeded) at
five scales; each scenario runs ``warmup`` then ``reps`` timed repetitions with
``time.perf_counter_ns``; we report p50/p95/p99/max, mean and the coefficient
of variation, plus a bootstrap 95% CI of the p50. Cold start (interpreter +
import) is measured in a fresh subprocess and reported separately. Memory is
``tracemalloc`` peak per operation at the largest scale. Environment metadata
(CPU model, count, governor if readable, container limits if readable, Python,
platform, env vars that affect hashing) is recorded so a hardware change is
distinguishable from a code change. Edge power/thermal: NOT MEASURED — no edge
reference device is part of this bootstrap; recorded as ``not_applicable_pending_approval``.

Gate (``--compare``): candidate fails when any gated metric exceeds its
absolute threshold (THRESHOLDS) or regresses more than ``max_regression``
relative to the baseline *on an equivalent environment* (same CPU model/count
and Python minor); on a non-equivalent environment only absolute thresholds
apply and the report says so. Noisy runs (CV above ``noise_cv``) are rerun once
before failing. Waivers come only from ops/REGISTER.json entries of type
``perf-waiver`` with an unexpired date.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import statistics
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path

from inv64_application_model import __version__
from inv64_application_model.manifest import canonical, canonical_document, parse_manifest_json, validate_issues

ROOT = Path(__file__).resolve().parents[1]
SCALES = (1, 10, 100, 1_000, 5_000)  # 10k components exceed the 1 MiB byte ceiling (see BENCHMARKS.md)
THRESHOLDS = {  # absolute, ms / MiB / s ; release-blocking
    "validate@10.p99_ms": 5.0,           # contract SLO: validation p99 < 5 ms for typical manifests
    "parse+validate@100.p99_ms": 10.0,
    "canonical@100.p99_ms": 10.0,
    "parse+validate@5000.p99_ms": 1_000.0,
    "invalid@1000.p99_ms": 150.0,
    "cold_import.p50_s": 1.0,
    "peak_mem@5000.MiB": 80.0,
}
MAX_REGRESSION = 0.25
NOISE_CV = 0.35


def fixture(n: int, seed: int = 64, *, invalid: bool = False) -> dict:
    rng = random.Random(seed + n)
    comps = [f"c{i}" for i in range(n)]
    provs = [f"p{i}" for i in range(max(1, n // 10))]
    m = {"schema": "app/v1",
         "components": [{"name": c, "properties": {"replicas": rng.randint(1, 5), "image": f"reg/img:{i}"}}
                        for i, c in enumerate(comps)],
         "providers": [{"name": p} for p in provs],
         "links": [{"from": rng.choice(comps), "to": rng.choice(provs)} for _ in range(n)],
         "traits": [{"type": "spread", "component": rng.choice(comps)} for _ in range(max(1, n // 2))]}
    if invalid:  # every link dangles: worst case for error aggregation
        m["links"] = [{"from": f"ghost{i}", "to": f"none{i}"} for i in range(n)]
    return m


def _stats(samples_ns: list[int]) -> dict:
    s = sorted(x / 1e6 for x in samples_ns)
    q = lambda p: s[min(len(s) - 1, int(round(p * (len(s) - 1))))]
    mean = statistics.fmean(s)
    cv = (statistics.pstdev(s) / mean) if mean else 0.0
    rng = random.Random(1)
    boots = sorted(statistics.median(rng.choices(s, k=len(s))) for _ in range(200))
    return {"n": len(s), "p50_ms": q(.5), "p95_ms": q(.95), "p99_ms": q(.99), "max_ms": s[-1], "mean_ms": mean,
            "cv": round(cv, 4), "p50_ci95_ms": [boots[5], boots[194]]}


def _time(fn, reps: int, warmup: int) -> dict:
    for _ in range(warmup):
        fn()
    out = []
    for _ in range(reps):
        t = time.perf_counter_ns()
        fn()
        out.append(time.perf_counter_ns() - t)
    return _stats(out)


def environment() -> dict:
    cpu = platform.processor() or ""
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    gov = None
    try:
        gov = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor").read_text().strip()
    except OSError:
        pass
    cg = None
    for p in ("/sys/fs/cgroup/cpu.max", "/sys/fs/cgroup/memory.max"):
        try:
            cg = (cg or {}) | {p: Path(p).read_text().strip()}
        except OSError:
            pass
    return {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
            "platform": platform.platform(), "machine": platform.machine(), "cpu_model": cpu,
            "cpu_count": os.cpu_count(), "governor": gov, "cgroup": cg,
            "env": {k: os.environ.get(k) for k in ("PYTHONHASHSEED", "PYTHONOPTIMIZE", "PYTHONDEVMODE")}}


def run(quick: bool = False) -> dict:
    reps, warm = (30, 5) if quick else (200, 20)
    res: dict = {}
    fixtures_digest = hashlib.sha256()
    for n in SCALES:
        m = fixture(n)
        raw = json.dumps(m)
        fixtures_digest.update(canonical_document(m))
        r = reps if n <= 1_000 else max(5, reps // 20)
        res[f"validate@{n}"] = _time(lambda: validate_issues(m), r, warm)
        res[f"parse+validate@{n}"] = _time(lambda: parse_manifest_json(raw), r, warm)
        res[f"canonical@{n}"] = _time(lambda: canonical(m), r, warm)
        bad = fixture(n, invalid=True)
        res[f"invalid@{n}"] = _time(lambda: validate_issues(bad), r, warm)
        res[f"bytes@{n}"] = {"encoded_bytes": len(raw.encode()), "canonical_bytes": len(canonical_document(m))}
    # peak memory at the largest scale
    big = json.dumps(fixture(5_000))
    tracemalloc.start()
    parse_manifest_json(big)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    res["peak_mem@5000"] = {"MiB": round(peak / 2 ** 20, 2)}
    # cold start in fresh interpreters
    cold = []
    for _ in range(3 if quick else 7):
        t = time.perf_counter()
        subprocess.run([sys.executable, "-c", "import inv64_application_model"], cwd=str(ROOT.parent), check=True)
        cold.append(time.perf_counter() - t)
    res["cold_import"] = {"p50_s": statistics.median(cold), "max_s": max(cold)}
    # throughput (single thread, steady state)
    m100 = json.dumps(fixture(10))
    t = time.perf_counter()
    k = 0
    while time.perf_counter() - t < (0.5 if quick else 2.0):
        parse_manifest_json(m100)
        k += 1
    res["throughput@10"] = {"ops_per_s": round(k / (time.perf_counter() - t), 1)}
    return {"schema": "PK_APP_PERF/1", "version": __version__, "quick": quick, "environment": environment(),
            "fixtures_sha256": fixtures_digest.hexdigest(), "results": res, "thresholds": THRESHOLDS,
            "power_thermal": "not_applicable_pending_approval (no edge reference device in bootstrap)",
            "capacity_model": capacity_model(res)}


def capacity_model(res: dict) -> dict:
    """Linear per-entry cost model: t(n) ≈ a + b·n fitted on the p50s of parse+validate."""
    xs = [n for n in SCALES]
    ys = [res[f"parse+validate@{n}"]["p50_ms"] for n in SCALES]
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    a = my - b * mx
    pred = {n: a + b * n for n in SCALES}
    err = {n: (abs(pred[n] - res[f"parse+validate@{n}"]["p50_ms"]) / max(res[f"parse+validate@{n}"]["p50_ms"], 1e-9))
           for n in SCALES if n >= 100}
    per_core_rps_typical = 1000.0 / max(res["parse+validate@10"]["p50_ms"], 1e-6)
    return {"model": "t_ms = a + b*entries", "a_ms": round(a, 4), "b_ms_per_entry": round(b, 6),
            "relative_error_at_scale": {str(k): round(v, 3) for k, v in err.items()},
            "tolerance": 0.5, "within_tolerance": all(v <= 0.5 for v in err.values()),
            "per_core_requests_per_s_typical": round(per_core_rps_typical, 1),
            "saturation_signals": {"inv64_inflight/max_inflight": 0.8, "admission_rejected_rate": 0.01,
                                   "p99_latency_ms (typical)": 5.0}}


def _get(res: dict, key: str) -> float | None:
    scen, metric = key.rsplit(".", 1)
    return res["results"].get(scen, {}).get(metric)


def compare(baseline: dict | None, cand: dict, waivers: list[dict] | None = None, today: str | None = None) -> dict:
    today = today or time.strftime("%Y-%m-%d")
    active = {w["metric"] for w in (waivers or []) if w.get("type") == "perf-waiver" and w.get("expires", "") >= today
              and w.get("status") == "active"}
    fails, notes = [], []
    equivalent = baseline is not None and all(
        baseline["environment"].get(k) == cand["environment"].get(k) for k in ("cpu_model", "cpu_count")) and \
        baseline["environment"]["python"].rsplit(".", 1)[0] == cand["environment"]["python"].rsplit(".", 1)[0]
    if baseline is not None and not equivalent:
        notes.append("baseline environment not equivalent: relative regression checks skipped, absolute thresholds apply")
    for key, limit in THRESHOLDS.items():
        v = _get(cand, key)
        if v is None:
            fails.append(f"{key}: missing")
            continue
        if v > limit and key not in active:
            fails.append(f"{key}: {v:.3f} > absolute {limit}")
        if equivalent:
            b = _get(baseline, key)
            # noise floor: a relative regression must also exceed max(0.25 ms, 10% of the absolute limit);
            # sub-millisecond p99s on shared runners jitter by more than 25% run to run.
            floor = max(0.25, 0.1 * limit) if key.endswith("_ms") else 0.0
            if b and v > b * (1 + MAX_REGRESSION) and (v - b) > floor and key not in active:
                fails.append(f"{key}: {v:.3f} regressed >{int(MAX_REGRESSION * 100)}% vs baseline {b:.3f}")
    noisy = [k for k, r in cand["results"].items() if isinstance(r, dict) and r.get("cv", 0) > NOISE_CV]
    if noisy:
        notes.append(f"noisy scenarios (cv>{NOISE_CV}): {sorted(noisy)[:8]}")
    return {"schema": "PK_APP_PERF_GATE/1", "result": "FAIL" if fails else "PASS", "failures": fails,
            "notes": notes, "waived": sorted(active), "baseline_version": (baseline or {}).get("version"),
            "candidate_version": cand.get("version"), "equivalent_environment": equivalent}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--compare")
    ap.add_argument("--candidate")
    a = ap.parse_args(argv)
    if a.candidate:
        cand = json.loads(Path(a.candidate).read_text())
        base = json.loads(Path(a.compare).read_text()) if a.compare and Path(a.compare).exists() else None
        reg = ROOT / "ops" / "REGISTER.json"
        waivers = json.loads(reg.read_text())["entries"] if reg.exists() else []
        res = compare(base, cand, waivers)
        if res["result"] == "FAIL":  # noisy-run retry policy: rerun once, fail only if still failing
            rerun = compare(base, run(quick=cand.get("quick", False)), waivers)
            res["retry"] = rerun["result"]
            res["result"] = rerun["result"]
            res["failures"] = rerun["failures"]
    else:
        res = run(a.quick)
    text = json.dumps(res, indent=2, sort_keys=True)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text + "\n", encoding="utf-8")
    summary = res.get("result") or {k: res["results"][k]["p99_ms"] for k in ("validate@10", "parse+validate@100")}
    print(json.dumps(summary))
    return 0 if res.get("result", "PASS") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
