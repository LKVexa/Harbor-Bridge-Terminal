"""Reproducible performance harness for INV-52 (C061-C066, C069, C070, C088).

    python -m inv52_messaging_abstraction.bench --out evidence/perf.json
    python -m inv52_messaging_abstraction.bench --quick --check perf/baseline.json

Numbers are environment-specific and are recorded with a host fingerprint.
Power/thermal (C068) cannot be measured by a Python harness and is reported
``NOT_MEASURED`` with its reason, never as zero.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import statistics
import sys
import threading
import time
import tracemalloc
from typing import Any, Callable

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "inv52_messaging_abstraction"

from .adapters import InMemoryBroker, Outbox  # noqa: E402
from .resilience import QuotaAdmission  # noqa: E402
from .runtime import MessagingError, PubSub, envelope  # noqa: E402
from .security import TenantBus, TokenAuthority  # noqa: E402

KEY = {"bench": os.urandom(32)}


def _pct(xs: list[int], q: float) -> int:
    s = sorted(xs)
    return s[min(len(s) - 1, int(q * len(s)))]


def _summ(xs: list[int]) -> dict[str, Any]:
    return {"n": len(xs), "p50_ns": _pct(xs, .5), "p95_ns": _pct(xs, .95), "p99_ns": _pct(xs, .99),
            "max_ns": max(xs), "mean_ns": int(statistics.fmean(xs))}


def _timed(fn: Callable[[], Any], n: int) -> list[int]:
    out = []
    pc = time.perf_counter_ns
    for _ in range(n):
        t = pc()
        fn()
        out.append(pc() - t)
    return out


def _bus(routes: int = 1, **kw) -> PubSub:
    b = PubSub(max_dead_letters=1000, max_decisions=1000, **kw)
    b.allow("t", "a")
    for i in range(routes):
        b.subscribe("t", (lambda m, i=i: m["data"]["n"] % max(1, routes) == i % max(1, routes)) if routes > 1
                    else (lambda m: True), _Null())
    return b


class _Null:
    def append(self, _m: Any) -> None:
        pass


MSG = {"id": "m-1", "source": "a", "type": "e", "time": 0, "data": {"n": 1, "items": list(range(20))}}


def _publish_fn(bus: PubSub) -> Callable[[], Any]:
    return lambda: bus.publish("a", "t", MSG)


def run(quick: bool = False) -> dict[str, Any]:
    n = 2_000 if quick else 20_000
    res: dict[str, Any] = {}
    gc.collect()
    # baseline direct call vs abstraction (overhead SLO in contract.py)
    sink = _Null()
    from copy import deepcopy
    direct = _timed(lambda: sink.append(deepcopy(MSG)), n)
    via = _timed(_publish_fn(_bus(1)), n)
    res["publish_latency"] = _summ(via)
    res["direct_call"] = _summ(direct)
    res["overhead_p99_ns"] = max(0, res["publish_latency"]["p99_ns"] - res["direct_call"]["p99_ns"])
    # steady throughput
    b = _bus(1)
    t0 = time.perf_counter()
    for _ in range(n):
        b.publish("a", "t", MSG)
    res["steady_rps"] = int(n / (time.perf_counter() - t0))
    # burst: 8 threads at once
    b = _bus(1)
    per = n // 8

    def worker() -> None:
        for _ in range(per):
            b.publish("a", "t", MSG)
    ths = [threading.Thread(target=worker) for _ in range(8)]
    t0 = time.perf_counter()
    for th in ths:
        th.start()
    for th in ths:
        th.join()
    res["burst"] = {"threads": 8, "messages": per * 8, "rps": int(per * 8 / (time.perf_counter() - t0)),
                    "published_counter": b.metrics()["published"]}
    # overload: admission sheds, accepted latency stays bounded
    b = _bus(1, admission=QuotaAdmission(per_app_rate=1000, per_app_burst=200))
    shed, lat = 0, []
    for _ in range(n):
        t = time.perf_counter_ns()
        try:
            b.publish("a", "t", MSG)
            lat.append(time.perf_counter_ns() - t)
        except MessagingError:
            shed += 1
    res["overload"] = {"offered": n, "shed": shed, "shed_ratio": round(shed / n, 4),
                       "accepted_latency": _summ(lat) if lat else None}
    # scale-out / scale-in (routes per topic)
    scale = {}
    for r in (1, 8, 64):
        scale[str(r)] = _summ(_timed(_publish_fn(_bus(r)), n // 4))
    b = _bus(64)
    ids = list(b._route_ids["t"])
    for sid in ids[1:]:
        b.unsubscribe(sid)
    scale["64->1"] = _summ(_timed(_publish_fn(b), n // 4))
    res["scale_routes"] = scale
    # copy analysis (C065/C066): per-route deepcopy vs one frozen view
    copies = {}
    for view in ("copy", "frozen"):
        copies[view] = _summ(_timed(_publish_fn(_bus(16, predicate_view=view)), n // 4))
    copies["deepcopies_per_publish_copy_mode"] = "1 canonical + 1 per route (predicate) + 1 per delivery"
    copies["deepcopies_per_publish_frozen_mode"] = "1 canonical + 1 frozen view + 1 per delivery"
    copies["p50_saving_ratio"] = round(1 - copies["frozen"]["p50_ns"] / copies["copy"]["p50_ns"], 3)
    res["copy_analysis"] = copies
    # per-tenant overhead (authn + namespacing + audit chain)
    auth = TokenAuthority(lambda: KEY, "bench", nonce_capacity=n * 4 + 10)
    tb = TenantBus(PubSub(max_dead_letters=100, max_decisions=100), auth)
    tb.grant("acme", "a", "publish:t", "subscribe:t")
    tok = auth.issue("a", "acme")
    tb.subscribe(tok, "t", lambda m: True, _Null())
    tokens = [auth.issue("a", "acme") for _ in range(n // 4)]
    it = iter(tokens)
    tenant = _summ(_timed(lambda: tb.publish(next(it), "t", MSG), n // 4))
    raw = _summ(_timed(_publish_fn(_bus(1)), n // 4))
    del it
    res["per_tenant_overhead"] = {"tenant_bus": tenant, "raw_bus": raw,
                                  "p50_delta_ns": tenant["p50_ns"] - raw["p50_ns"],
                                  "note": "a fresh signed token per publish: HMAC verify + replay-cache insert + capability check + tenant namespacing + audit-chain append"}
    # tenants scale: 1 vs 100 tenants on one bus
    b = PubSub(max_dead_letters=100, max_decisions=100)
    for i in range(100):
        b.allow(f"t{i}::x", "a")
        b.subscribe(f"t{i}::x", lambda m: True, _Null())
    res["tenants_100_latency"] = _summ(_timed(lambda: b.publish("a", "t57::x", MSG), n // 4))
    # recovery: outbox replay after outage
    broker = InMemoryBroker()
    ob = Outbox(broker, capacity=n)
    broker.available = False
    for i in range(n // 4):
        ob.publish("t", envelope("a", "e", {"n": i}))
    broker.available = True
    t0 = time.perf_counter_ns()
    fl = ob.flush()
    res["recovery_replay"] = {"messages": fl["sent"], "ns": time.perf_counter_ns() - t0,
                              "delivered": len(broker.topics.get("t", []))}
    # startup
    from .lifecycle import bootstrap
    boots = _timed(lambda: bootstrap([{"topics": [{"name": "t", "publishers": ["a"]}]}], author="bench"), 50)
    res["startup"] = _summ(boots)
    # memory growth bound: two equal rounds after warm-up
    b = _bus(0)
    for _ in range(3000):
        b.publish("a", "t", MSG)
    tracemalloc.start()
    s1 = tracemalloc.take_snapshot()
    for _ in range(3000):
        b.publish("a", "t", MSG)
    s2 = tracemalloc.take_snapshot()
    for _ in range(3000):
        b.publish("a", "t", MSG)
    s3 = tracemalloc.take_snapshot()
    tracemalloc.stop()
    g1 = sum(x.size_diff for x in s2.compare_to(s1, "filename"))
    g2 = sum(x.size_diff for x in s3.compare_to(s2, "filename"))
    res["memory"] = {"round1_growth_bytes": g1, "round2_growth_bytes": g2,
                     "bounded": g2 <= max(g1, 0) * 1.25 + 262_144}
    res["power_thermal"] = {"status": "NOT_MEASURED",
                            "reason": "requires an instrumented edge node (RAPL/INA219/thermal zone); none available"}
    return res


def fingerprint() -> dict[str, Any]:
    return {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
            "machine": platform.machine(), "system": platform.system(), "cpus": os.cpu_count()}


def check(res: dict[str, Any], baseline: dict[str, Any]) -> list[str]:
    th = baseline["thresholds"]
    fails = []
    pl = res["publish_latency"]
    for q in ("p50", "p95", "p99"):
        if pl[f"{q}_ns"] > th[f"publish_{q}_ns"]:
            fails.append(f"publish {q} {pl[f'{q}_ns']} > {th[f'publish_{q}_ns']}")
    if pl["max_ns"] > th["publish_worst_ns"]:
        fails.append(f"publish worst {pl['max_ns']} > {th['publish_worst_ns']}")
    if res["overhead_p99_ns"] > th["overhead_p99_ns"]:
        fails.append("overhead p99 above contract SLO")
    if res["steady_rps"] < th["steady_rps_min"]:
        fails.append(f"steady rps {res['steady_rps']} < {th['steady_rps_min']}")
    if res["startup"]["p99_ns"] > th["startup_p99_ns"]:
        fails.append("startup p99 above threshold")
    if not res["memory"]["bounded"]:
        fails.append("memory growth not bounded")
    if res["recovery_replay"]["delivered"] != res["recovery_replay"]["messages"]:
        fails.append("recovery replay lost messages")
    return fails


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="bench")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--check")
    a = ap.parse_args(argv)
    res = {"schema": "INV52_PERF/1", "host": fingerprint(), "quick": a.quick, "results": run(a.quick)}
    if a.check:
        with open(a.check, encoding="utf-8") as fh:
            base = json.load(fh)
        res["regressions"] = check(res["results"], base)
        res["thresholds_status"] = base["status"]
    text = json.dumps(res, indent=2)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)
    return 1 if res.get("regressions") else 0


if __name__ == "__main__":
    raise SystemExit(main())
