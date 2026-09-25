"""Reproducible benchmark harness and regression gate (WS 11).

    python -m inv32_elastic_virtualization.bench run   --out results.json [--iterations N] [--guests G]
    python -m inv32_elastic_virtualization.bench gate  --baseline baseline.json --results results.json [--waivers W]

Measures the *controller-owned* share of latency against the deterministic fake provider: decision
(policy) latency, provider-call latency as seen by the controller, durable journal+audit cost, and
end-to-end.  Real HyperFlux/guest cooperation latency is out of this component's control and is BLOCKED on
the real adapter (WS1).  Output: ``PK_INV32_BENCH/1`` with environment metadata (CPU, Python, platform,
package version, seed) so a run is reproducible and comparable.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import random
import statistics
import sys
import tempfile
import time
import resource
from pathlib import Path
from typing import Any, Callable

from . import __version__

DEFAULT_THRESHOLDS = {"p50": 1.25, "p95": 1.35, "p99": 1.5}  # ratio vs baseline allowed before failing
SLO_SECONDS = {  # controller-owned targets on reference hardware (durable fsync included)
    "memory_grow": {"p99": 0.050}, "memory_reclaim": {"p99": 0.050}, "vcpu_add": {"p99": 0.050},
    "vcpu_remove": {"p99": 0.050}, "rollback": {"p99": 0.060}, "snapshot": {"p99": 0.005},
    "audit_append": {"p99": 0.020}, "decision_only": {"p99": 0.002},
}


def _pct(samples: list[float], q: float) -> float:
    s = sorted(samples)
    if not s:
        return float("nan")
    k = max(0, min(len(s) - 1, int(round(q * (len(s) - 1)))))
    return s[k]


def summarize(samples: list[float]) -> dict[str, float | None]:
    return {"n": len(samples), "p50": _pct(samples, 0.50), "p95": _pct(samples, 0.95), "p99": _pct(samples, 0.99),
            "p999": _pct(samples, 0.999) if len(samples) >= 1000 else None, "max": max(samples),
            "mean": statistics.fmean(samples)}


def environment() -> dict[str, Any]:
    cpu = "unknown"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    return {"package_version": __version__, "python": platform.python_version(), "implementation":
            platform.python_implementation(), "platform": platform.platform(), "machine": platform.machine(),
            "cpu_model": cpu, "cpu_count": os.cpu_count(), "provider": "fake-hyperflux (reference)",
            "fsync": True, "hardware_class": os.environ.get("INV32_HW_CLASS", "unclassified-ci")}


def _rig(tmp: str, guests: int, seed: int):
    from .adapters import FakeHypervisor
    from .authz import Authenticator, Keyring, Policy
    from .config import ConfigManager
    from .controller import ElasticController
    from .fencing import FileLeaseStore, Ownership
    from .store import DurableStore

    fake = FakeHypervisor(1 << 22, overhead_mib=0, block_mib=128)
    store = DurableStore(Path(tmp) / "state", signing_key=b"b" * 32, segment_max_events=5000)
    own = Ownership(FileLeaseStore(Path(tmp) / "leases"), "bench-host", "bench", duration_s=300)
    own.acquire()
    authn = Authenticator(Keyring({"k": b"k" * 32}, "k"), issuer="bench", audience="inv32")
    cfg = ConfigManager(release_version=__version__)
    cfg.activate(cfg.stage({"site": [{"tenant_rate_per_s": 100000.0, "tenant_burst": 100000,
                                      "max_inflight_per_host": 4096, "max_inflight_per_tenant": 4096}]},
                           author="bench", source="bench"))
    ctl = ElasticController(host="bench-host", controller_id="bench", adapter=fake, store=store, ownership=own,
                            authenticator=authn, policy=Policy(), config=cfg, rng=random.Random(seed))
    for i in range(guests):
        fake.create_guest(f"g{i}", f"t{i % 8}", 1024, 1)
        ctl.register_guest(f"g{i}", tenant=f"t{i % 8}", floor_mib=256, ceiling_mib=8192, vcpu_max=8)
    tok = {t: authn.issue("operator:bench/op", "operator", actions=["memory.adjust", "vcpu.adjust",
                                                                      "adjustment.revert"], ttl=3600)
           for t in ["op"]}["op"]
    return fake, store, ctl, tok


def run(iterations: int = 200, guests: int = 64, seed: int = 1) -> dict[str, Any]:
    rng = random.Random(seed)
    results: dict[str, Any] = {"schema": "PK_INV32_BENCH/1", "env": environment(), "seed": seed,
                               "iterations": iterations, "guests": guests, "ops": {}}
    with tempfile.TemporaryDirectory() as tmp:
        t0 = time.perf_counter()
        fake, store, ctl, tok = _rig(tmp, guests, seed)
        results["cold_start_s"] = time.perf_counter() - t0
        n = [0]

        def req(op: str, g: str, **kw):
            n[0] += 1
            base = {"schema": "PK_RESOURCE_ADJUSTMENT/2", "op": op, "operation_id": f"b{n[0]}", "host": "bench-host",
                    "guest": g, "tenant": f"t{int(g[1:]) % 8}"}
            base.update(kw)
            return base

        samples: dict[str, list[float]] = {k: [] for k in SLO_SECONDS}

        def timed(key: str, fn: Callable[[], Any]) -> Any:
            s = time.perf_counter()
            out = fn()
            samples[key].append(time.perf_counter() - s)
            return out

        for i in range(iterations):
            g = f"g{rng.randrange(guests)}"
            cur = fake.get_guest(g).memory_mib
            up = min(8192, cur + 128 * rng.randrange(1, 8))
            r = timed("memory_grow", lambda: ctl.handle(req("memory_adjust", g, target_mib=up), tok))
            if r["outcome"] == "success" and r["event"]["applied_mib"] != cur:
                timed("rollback", lambda: ctl.handle(req("memory_revert", g, record_event_hash=r["event"]["event_hash"]), tok))
            cur = fake.get_guest(g).memory_mib
            down = max(256, cur - 128 * rng.randrange(1, 4))
            timed("memory_reclaim", lambda: ctl.handle(req("memory_adjust", g, target_mib=down), tok))
            v = fake.get_guest(g).vcpus
            timed("vcpu_add" if v < 8 else "vcpu_remove",
                  lambda: ctl.handle(req("vcpu_adjust", g, target_vcpus=v + 1 if v < 8 else v - 1), tok))
            if fake.get_guest(g).vcpus > 1:
                timed("vcpu_remove", lambda: ctl.handle(req("vcpu_adjust", g, target_vcpus=fake.get_guest(g).vcpus - 1), tok))
            timed("snapshot", ctl.host_snapshot)
            timed("audit_append", lambda: store.append_audit({"kind": "reconciled", "operation_id": f"a{i}"}))
            live = fake.get_guest(g)
            cap = fake.host_capacity()
            allg = fake.list_guests()
            reg = ctl.registration(g)
            timed("decision_only", lambda: ctl._plan(req("memory_adjust", g, target_mib=live.memory_mib),
                                                      "memory_adjust", live, reg, cap, allg))
        results["max_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        results["ops"] = {k: summarize(v) for k, v in samples.items() if v}
        total_mut = sum(len(samples[k]) for k in ("memory_grow", "memory_reclaim", "vcpu_add", "vcpu_remove", "rollback"))
        total_time = sum(sum(samples[k]) for k in ("memory_grow", "memory_reclaim", "vcpu_add", "vcpu_remove", "rollback"))
        results["throughput_mutations_per_s"] = total_mut / total_time if total_time else None
        audit_bytes = sum(p.stat().st_size for p in (Path(tmp) / "state" / "audit").glob("*.jsonl"))
        results["audit_bytes_per_event"] = audit_bytes / max(1, len(store.audit_events))
        journal = (Path(tmp) / "state" / "journal.jsonl").stat().st_size
        results["journal_bytes_per_mutation"] = journal / max(1, total_mut)
    results["slo"] = {k: {"target_p99_s": SLO_SECONDS[k]["p99"], "observed_p99_s": results["ops"][k]["p99"],
                          "pass": results["ops"][k]["p99"] <= SLO_SECONDS[k]["p99"]}
                      for k in results["ops"]}
    return results


def gate(baseline: dict, current: dict, *, waivers: list[dict] | None = None, now: float | None = None,
         thresholds: dict[str, float] = DEFAULT_THRESHOLDS) -> dict[str, Any]:
    now = time.time() if now is None else now
    active = {w["metric"]: w for w in (waivers or []) if w.get("expires_at", 0) > now}
    failures: list[str] = []
    waived: list[str] = []
    for op, base in baseline.get("ops", {}).items():
        cur = current.get("ops", {}).get(op)
        if cur is None:
            failures.append(f"{op}: missing from results")
            continue
        for q, ratio in thresholds.items():
            if base.get(q) and cur.get(q) and cur[q] > base[q] * ratio:
                key = f"{op}.{q}"
                (waived if key in active else failures).append(f"{key}: {cur[q]:.6f}s > {ratio}x baseline {base[q]:.6f}s")
    for op, s in current.get("slo", {}).items():
        if not s["pass"]:
            key = f"{op}.slo"
            (waived if key in active else failures).append(f"{key}: p99 {s['observed_p99_s']:.6f}s > {s['target_p99_s']}s")
    return {"schema": "PK_INV32_BENCH_GATE/1", "pass": not failures, "failures": failures, "waived": waived}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="inv32-bench")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--out", required=True)
    r.add_argument("--iterations", type=int, default=200)
    r.add_argument("--guests", type=int, default=64)
    r.add_argument("--seed", type=int, default=1)
    g = sub.add_parser("gate")
    g.add_argument("--baseline", required=True)
    g.add_argument("--results", required=True)
    g.add_argument("--waivers")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        res = run(a.iterations, a.guests, a.seed)
        Path(a.out).write_text(json.dumps(res, indent=1, sort_keys=True))
        print(json.dumps({k: res["ops"][k]["p99"] for k in res["ops"]}, indent=1))
        return 0
    base = json.loads(Path(a.baseline).read_text())
    cur = json.loads(Path(a.results).read_text())
    waivers = json.loads(Path(a.waivers).read_text()) if a.waivers else []
    out = gate(base, cur, waivers=waivers)
    print(json.dumps(out, indent=1))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
