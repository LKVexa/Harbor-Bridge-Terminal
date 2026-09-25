"""MC-26 - Soak, burst, fleet and disaster harness.

    python tools/soak.py --duration 300 --out evidence/soak.json

Soak: continuous mixed traffic for ``--duration`` seconds, sampling fd count,
RSS, thread count, queue depth and p99 latency each interval, then fitting a
least-squares slope to detect cumulative leaks.  The release policy requires
a multi-hour soak (``REQUIRED_SOAK_S``); a shorter run is recorded as
evidence but reported ``BLOCKED`` for the release criterion.

Burst: sudden 10x submit spike, completion spike, cancellation storm, retry
storm (retryable failures through RetryPolicy), tenant churn.
Fleet: 200 workload identities over 20 tenants, one hot tenant; checks
isolation (other tenants still served) and metric cardinality bound.
Disaster: backend closed underneath, audit sink loss, key-service outage,
invalid config push, forced process kill + restart (child process).
"""
from __future__ import annotations

import argparse
import errno
import json
import os
import pathlib
import random
import resource
import signal
import subprocess
import sys
import threading
import time

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))

from inv19_os_asynchronous_analogues.hostio import errors  # noqa: E402
from inv19_os_asynchronous_analogues.hostio.audit import AuditUnavailable  # noqa: E402
from inv19_os_asynchronous_analogues.hostio.config import ConfigError, ConfigStore  # noqa: E402
from inv19_os_asynchronous_analogues.hostio.driver import AsyncHost, Health  # noqa: E402
from inv19_os_asynchronous_analogues.hostio.policy import Overloaded, RetryableFailure, RetryPolicy  # noqa: E402
from inv19_os_asynchronous_analogues.hostio.resources import QuotaExceeded  # noqa: E402
from inv19_os_asynchronous_analogues.hostio.security import Unauthorized  # noqa: E402

REQUIRED_SOAK_S = 4 * 3600


def slope(xs, ys):
    n = len(xs)
    if n < 2:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs) or 1.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


def nb_pipe():
    r, w = os.pipe()
    os.set_blocking(r, False); os.set_blocking(w, False)
    return r, w


def soak(duration: float, backend: str) -> dict:
    h = AsyncHost(override=backend)
    caps = [h.mint(f"t{i % 4}", f"w{i}") for i in range(16)]
    samples = []
    end = time.monotonic() + duration
    t0 = time.monotonic()
    ops = 0
    lat = []
    while time.monotonic() < end:
        interval_end = time.monotonic() + max(1.0, duration / 30)
        lat.clear()
        while time.monotonic() < interval_end:
            r, w = nb_pipe()
            c = random.choice(caps)
            a = time.perf_counter()
            h.run_until(h.write(c, w, b"s" * 64))
            h.run_until(h.read(c, r, 64))
            lat.append(time.perf_counter() - a)
            os.close(r); os.close(w)
            ops += 2
        lat.sort()
        samples.append({"t": time.monotonic() - t0, "fds": len(os.listdir("/proc/self/fd")),
                        "rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                        "threads": threading.active_count(), "queue": len(h._pending),
                        "p99_s": lat[int(0.99 * (len(lat) - 1))], "audit_records": len(h.audit.records),
                        "spans": len(h.tracer.spans), "logs": len(h.logger.sink)})
        # bounded diagnostic buffers must not grow without bound
        h.audit.records = h.audit.records[-10000:]
    ts = [s["t"] for s in samples]
    res = {"backend": backend, "duration_s": duration, "ops": ops, "samples": samples,
           "slopes_per_s": {k: slope(ts, [s[k] for s in samples]) for k in ("fds", "rss_kb", "threads", "queue", "p99_s")}}
    res["leak_detected"] = (res["slopes_per_s"]["fds"] > 0.01 or res["slopes_per_s"]["threads"] > 0.01
                            or res["slopes_per_s"]["queue"] > 0.01)
    res["accounting_at_baseline"] = h.shutdown()["accounting_at_baseline"]
    res["release_criterion"] = ("PASS" if duration >= REQUIRED_SOAK_S and not res["leak_detected"]
                                else f"BLOCKED: soak {duration:.0f}s < required {REQUIRED_SOAK_S}s")
    return res


def burst(backend: str) -> dict:
    cs = ConfigStore()
    cs.activate([("soak", {"quota.max_inflight": 512, "quota.per_tenant_descriptors": 512,
                           "quota.per_workload_descriptors": 512, "quota.global_descriptors": 2048})], actor="soak")
    h = AsyncHost(config=cs, override=backend)
    cap = h.mint("b", "w")
    out = {}
    pipes = [nb_pipe() for _ in range(600)]
    acc = rej = 0
    futs = []
    for r, _ in pipes:  # submit spike beyond capacity
        try:
            futs.append(h.read(cap, r, 1)); acc += 1
        except (Overloaded, QuotaExceeded):
            rej += 1
    out["submit_spike"] = {"accepted": acc, "rejected": rej}
    for _, w in pipes[:acc]:
        os.write(w, b"!")  # completion spike
    t = time.perf_counter()
    while h._pending and time.perf_counter() - t < 5:
        h.poll(0.001)
    out["completion_spike_drain_s"] = time.perf_counter() - t
    futs = [h.read(cap, r, 1) for r, _ in pipes[:300]]
    t = time.perf_counter()
    cancelled = sum(h.cancel(cap, f) for f in futs)  # cancellation storm
    out["cancel_storm"] = {"cancelled": cancelled, "s": time.perf_counter() - t,
                           "duplicates": sum(f.duplicate_resolutions for f in futs)}
    rp = RetryPolicy(max_attempts=5, budget_s=0.5, base_s=0.0005, cap_s=0.005)
    attempts = [0]
    def flaky():
        attempts[0] += 1
        raise RetryableFailure(errors.translate(backend, errno.EAGAIN))
    storms = 0
    for _ in range(100):  # retry storm
        try:
            rp.run("nop", flaky)
        except RetryableFailure:
            storms += 1
    out["retry_storm"] = {"calls": 100, "attempts": attempts[0], "max_per_call": 6, "bounded": attempts[0] <= 600}
    churn = 0
    for i in range(500):  # workload churn
        c = h.mint(f"churn{i % 50}", f"w{i}")
        r, w = nb_pipe()
        h.run_until(h.write(c, w, b"c")); churn += 1
        os.close(r); os.close(w)
    out["workload_churn_ops"] = churn
    out["back_to_baseline"] = h.shutdown()["accounting_at_baseline"]
    for r, w in pipes: os.close(r); os.close(w)
    out["bounded_and_recovered"] = out["back_to_baseline"] and out["retry_storm"]["bounded"] and \
        out["cancel_storm"]["duplicates"] == 0
    return out


def fleet(backend: str) -> dict:
    cs = ConfigStore()
    cs.activate([("soak", {"quota.max_inflight": 2048, "quota.per_tenant_descriptors": 64,
                           "quota.per_workload_descriptors": 16, "quota.global_descriptors": 4096})], actor="soak")
    h = AsyncHost(config=cs, override=backend)
    caps = {(t, w): h.mint(f"tenant{t}", f"wl{w}") for t in range(20) for w in range(10)}
    hot_refused = 0
    pipes = []
    for i in range(300):  # hot tenant 0 floods
        r, w = nb_pipe(); pipes.append((r, w))
        try:
            h.read(caps[(0, i % 10)], r, 1)
        except (Overloaded, QuotaExceeded):
            hot_refused += 1
    served = 0
    for (t, wl), c in caps.items():
        if t == 0:
            continue
        r, w = nb_pipe()
        if h.run_until(h.write(c, w, b"q"))[0] == "value":
            served += 1
        os.close(r); os.close(w)
    exp = h.metrics.exposition()
    series = sum(1 for line in exp.splitlines() if line and not line.startswith("#"))
    out = {"identities": len(caps), "tenants": 20, "hot_tenant_refused": hot_refused,
           "other_tenants_served": served, "expected_served": 190, "metric_series": series,
           "cardinality_bounded": 'tenant="' not in exp and 'workload="' not in exp and series < 2000}
    h.shutdown()
    for r, w in pipes: os.close(r); os.close(w)
    out["isolation_ok"] = served == 190 and hot_refused > 0
    return out


def disaster(backend: str) -> dict:
    out = {}
    h = AsyncHost(override=backend)
    cap = h.mint("d", "w")
    h.backend.close()                           # backend becomes unusable
    h.poll(0)
    out["backend_unusable"] = {"health": h.health.value}
    h.recover("disaster:backend-unusable")
    r, w = nb_pipe()
    out["backend_unusable"]["recovered_io"] = h.run_until(h.write(cap, w, b"x"))[0]
    h.audit.sink_up = False                     # audit sink loss
    h.audit.max_buffer = h.audit.buffered + 5
    refused = 0
    for _ in range(10):
        try:
            h.run_until(h.write(cap, w, b"y"))
        except AuditUnavailable:
            refused += 1
    out["audit_sink_loss"] = {"refused_after_buffer": refused, "fail_closed": refused > 0}
    h.audit.sink_up = True; h.audit.max_buffer = 4096; h.audit.flush()
    h.keys.available = False                    # identity/key service outage
    try:
        h.write(cap, w, b"z"); out["key_outage"] = "FAIL_OPEN"
    except Unauthorized as e:
        out["key_outage"] = f"fail-closed:{e.reason.split(':')[0]}"
    h.keys.available = True
    before = h.config.active.digest             # config service pushes garbage
    try:
        h.config.activate([("push", {"ring.sq_entries": -5})], actor="cfgsvc")
    except ConfigError:
        pass
    out["bad_config_push"] = {"unchanged": h.config.active.digest == before}
    h.shutdown(); os.close(r); os.close(w)
    # forced termination + restart: a child is SIGKILLed mid-traffic; a fresh
    # process must start clean (no persisted half-state to reconcile).
    code = ("import sys,os,time;sys.path.insert(0,%r);from inv19_os_asynchronous_analogues.hostio.driver import AsyncHost;"
            "h=AsyncHost();c=h.mint('k','w');r,w=os.pipe();os.set_blocking(r,False);[h.read(c,r,1) for _ in range(1)];"
            "print('ready',flush=True);time.sleep(30)") % str(PKG.parent)
    p = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    p.stdout.readline()
    p.send_signal(signal.SIGKILL); p.wait(5)
    q = subprocess.run([sys.executable, "-c", code.replace("time.sleep(30)", "print(h.shutdown()['accounting_at_baseline'])")],
                       capture_output=True, text=True, timeout=30)
    out["forced_restart"] = {"killed_rc": p.returncode, "restart_clean": q.stdout.strip().endswith("True")}
    out["network_partition"] = "NOT_APPLICABLE: INV-19 has no network-attached control dependency in-process"
    out["safe_states"] = (out["backend_unusable"]["recovered_io"] == "value" and out["audit_sink_loss"]["fail_closed"]
                          and out["key_outage"].startswith("fail-closed") and out["bad_config_push"]["unchanged"]
                          and out["forced_restart"]["restart_clean"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=float, default=60)
    ap.add_argument("--backend", default="")
    ap.add_argument("--out", default=str(PKG / "evidence" / "soak.json"))
    a = ap.parse_args()
    from inv19_os_asynchronous_analogues.hostio import capabilities as capmod
    b = a.backend or capmod.choose(capmod.detect()).backend
    from inv19_os_asynchronous_analogues.tools.supply_chain import source_revision
    res = {"schema": "PK_SOAK/1", "source_revision": source_revision(), "backend": b, "soak": soak(a.duration, b), "burst": burst(b),
           "fleet": fleet(b), "disaster": disaster(b)}
    ok = (not res["soak"]["leak_detected"] and res["burst"]["bounded_and_recovered"]
          and res["fleet"]["isolation_ok"] and res["fleet"]["cardinality_bounded"] and res["disaster"]["safe_states"])
    res["verdict"] = "PASS" if ok else "FAIL"
    pathlib.Path(a.out).write_text(json.dumps(res, indent=1, sort_keys=True))
    print(json.dumps({"verdict": res["verdict"], "soak": res["soak"]["release_criterion"],
                      "slopes": res["soak"]["slopes_per_s"]}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
