"""Reproducible benchmark suite (MC-33, MC-34, MC-38, MC-55).

    python -m pln07_security_plane.bench.bench [--quick] [--out bench/results.json]

Measures verify latency across chain depths 0..5, service issue/verify/revoke
throughput, a burst test through admission control and a soak loop, and
compares against ``bench/baseline.json`` budgets.  Exit 1 on regression.
"""
from __future__ import annotations

import argparse, json, pathlib, platform, statistics, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pln07_security_plane.grants import Grant, Verifier  # noqa: E402
from pln07_security_plane.tests.test_v43 import make_service, issue, CTX, cred  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent


def pct(samples, p):
    s = sorted(samples)
    return s[min(len(s) - 1, int(round(p / 100 * (len(s) - 1))))]


def lat(fn, n):
    out = []
    for _ in range(n):
        t = time.perf_counter_ns(); fn(); out.append(time.perf_counter_ns() - t)
    return {"p50_us": pct(out, 50) / 1e3, "p95_us": pct(out, 95) / 1e3, "p99_us": pct(out, 99) / 1e3,
            "max_us": max(out) / 1e3, "mean_us": statistics.fmean(out) / 1e3, "n": n}


def run(quick: bool) -> dict:
    n = 500 if quick else 5000
    res = {"env": {"python": platform.python_version(), "machine": platform.machine(), "system": platform.system()},
           "verify_by_depth": {}}
    g = Grant("c", "t1", {"s"}, 10 ** 9)
    v = Verifier()
    for d in range(6):
        res["verify_by_depth"][str(d)] = lat(lambda: v.verify(g, 1, "s", "t1"), n)
        if d < 5:
            g = g.attenuate(subject=f"d{d}")
    svc, tok, fc = make_service()
    svc._admission.rate = svc._admission.burst = 10 ** 9
    svc.quota.default = 10 ** 9
    r = issue(svc, tok, fc)
    res["service_issue"] = lat(lambda: issue(svc, tok, fc), n // 5)
    res["service_verify"] = lat(lambda: svc.verify({"api_version": "1", "grant": r["grant"], "context": CTX}), n)
    # burst through default admission (MC-27/55)
    svc2, tok2, fc2 = make_service()
    t0 = time.perf_counter(); codes = [issue(svc2, tok2, fc2)["code"] for _ in range(1500)]
    res["burst"] = {"requests": 1500, "admitted": codes.count("grant.issued"),
                    "shed": codes.count("admission.overloaded"), "seconds": time.perf_counter() - t0}
    # soak: verify loop for fixed duration, watch latency drift
    dur = 1.0 if quick else 10.0
    end, count, windows, w = time.perf_counter() + dur, 0, [], []
    while time.perf_counter() < end:
        t = time.perf_counter_ns(); svc.verify({"api_version": "1", "grant": r["grant"], "context": CTX})
        w.append(time.perf_counter_ns() - t); count += 1
        if len(w) == 500:
            windows.append(pct(w, 99) / 1e3); w = []
    res["soak"] = {"seconds": dur, "ops": count, "ops_per_s": count / dur,
                   "p99_first_us": windows[0] if windows else None, "p99_last_us": windows[-1] if windows else None}
    return res


def compare(res: dict, base: dict) -> list[str]:
    fails = []
    for d, b in base["verify_by_depth_p99_us"].items():
        if res["verify_by_depth"][d]["p99_us"] > b:
            fails.append(f"verify depth {d} p99 {res['verify_by_depth'][d]['p99_us']:.1f}us > {b}us")
    if res["service_verify"]["p99_us"] > base["service_verify_p99_us"]:
        fails.append("service verify p99 over budget")
    if res["service_issue"]["p99_us"] > base["service_issue_p99_us"]:
        fails.append("service issue p99 over budget")
    if res["soak"]["p99_first_us"] and res["soak"]["p99_last_us"] > base["soak_drift_factor"] * res["soak"]["p99_first_us"]:
        fails.append("soak latency drift over factor")
    return fails


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); ap.add_argument("--out")
    a = ap.parse_args()
    res = run(a.quick)
    fails = compare(res, json.loads((HERE / "baseline.json").read_text()))
    res["regressions"] = fails
    txt = json.dumps(res, indent=2)
    if a.out:
        pathlib.Path(a.out).write_text(txt)
    print(txt)
    sys.exit(1 if fails else 0)
