"""Deterministic fault-injection harness (C060, C089).

Every scenario runs against a fresh runtime, injects one fault, then checks the
state-machine invariants: no future resolved twice, no future taken twice, no
terminal state reverted, registry accounting consistent.  Results are
machine-readable (``run_all()`` -> list of dicts).
"""
from __future__ import annotations

import gc
import random
import threading
import time
from typing import Callable

from .config import ConfigStore
from .errors import FutureError, Rejected
from .future import TERMINAL_STATES
from .runtime import Runtime


def invariants(rt: Runtime, *, telemetry: bool = True) -> list[str]:
    """State invariants always; telemetry-consistency checks only when ``telemetry``.

    Telemetry is best-effort (C056): after a telemetry fault the counters may lag
    the true state, so crash tests check state invariants only.
    """
    problems = []
    if rt.metrics.counter("inv18_invariant_violations_total"):
        problems.append("invariant violation counter non-zero")
    if sum(rt._per_tenant.values()) != rt.outstanding:
        problems.append("tenant accounting drift")
    for fid, e in list(rt._entries.items()):
        if e.future.taken and e.future.state in TERMINAL_STATES:
            problems.append(f"{fid} consumed but not released")
    if not telemetry:
        return problems
    created = rt.metrics.counter("inv18_futures_created_total")
    terminal = (rt.metrics.counter("inv18_values_resolved_total") + rt.metrics.counter("inv18_errors_resolved_total")
                + rt.metrics.counter("inv18_abandonments_total") + rt.metrics.counter("inv18_cancellations_total"))
    if terminal > created:
        problems.append(f"more terminal transitions ({terminal}) than futures ({created})")
    if rt.metrics.counter("inv18_takes_total") > terminal:
        problems.append("more takes than terminal transitions")
    return problems


def _producer_crash(rt):
    def worker(cap_box):
        cap = cap_box.pop()
        raise SystemExit  # dies holding the capability
    rc, qc = rt.create(str)
    box = [rc]
    del rc
    t = threading.Thread(target=lambda: _swallow(worker, box))
    t.start(); t.join()
    gc.collect()
    try:
        rt.take(qc)
    except FutureError as exc:
        return exc.code == "FUTURE_ABANDONED"
    return False


def _swallow(fn, *a):
    try:
        fn(*a)
    except BaseException:
        pass


def _consumer_crash(rt):
    rc, qc = rt.create(int)
    rt.resolve(rc, 7)
    del qc; gc.collect()       # receiver vanished: value is simply never consumed
    return rt.outstanding == 1 and rt.health()["state"] in ("HEALTHY", "DEGRADED")


def _dependency_exception(rt):
    rt.log.sink = lambda s: (_ for _ in ()).throw(OSError("sink down"))
    rc, qc = rt.create(str)
    try:
        rt.resolve(rc, 1)  # type error -> rejection is logged through the failing sink
    except TypeError:
        pass
    rt.resolve(rc, "ok")
    return rt.take(qc) == ("ok", "ok") and "TELEMETRY_SINK_UNAVAILABLE" in rt.health()["reasons"]


def _delayed_scheduling(rt):
    rc, qc = rt.create(int)
    wins = []
    def slow():
        time.sleep(0.02)
        try:
            rt.resolve(rc, 1); wins.append(1)
        except FutureError:
            pass
    def fast():
        try:
            rt.resolve(rc, 2); wins.append(2)
        except FutureError:
            pass
    ts = [threading.Thread(target=slow), threading.Thread(target=fast)]
    [t.start() for t in ts]; [t.join() for t in ts]
    return len(wins) == 1 and rt.take(qc) == ("ok", wins[0])


def _resource_exhaustion(rt):
    rt.config.activate({**dict(rt.config.values()), "max_outstanding": 50, "soft_outstanding": 40,
                        "max_per_tenant": 50}, author="fault")
    caps = [rt.create(int) for _ in range(50)]
    try:
        rt.create(int)
        return False
    except Rejected as exc:
        ok = exc.code == "RESOURCE_EXHAUSTED"
    for r, q in caps[:10]:
        rt.resolve(r, 1); rt.take(q)
    rt.create(int)          # recovers once resources are released
    return ok


def _config_failure(rt):
    before = rt.config.active().revision_id
    try:
        rt.config.activate({**dict(rt.config.values()), "max_outstanding": 10}, author="fault",
                           _fail_after_stage=True)
    except Rejected:
        pass
    return rt.config.active().revision_id == before


def _telemetry_failure(rt):
    rt.log.sink = lambda s: (_ for _ in ()).throw(RuntimeError("exporter down"))
    rc, qc = rt.create(str)
    rt.resolve(rc, "v")
    return rt.take(qc) == ("ok", "v")


def _network_loss(rt):
    from .adapters import Link, RemoteClient, RemoteEndpoint
    from .auth import Authenticator, KeyRing
    kr = KeyRing(); kr.add("k1", b"k" * 32)
    au = Authenticator(kr)
    ep = RemoteEndpoint(rt, au)
    link = Link(ep)
    cli = RemoteClient(link, au, "tenant-a", ["create", "resolve", "receive"])
    fid = cli.create("int")["result"]["future_id"]
    link.drop_responses = 2          # request delivered, responses lost twice
    r = cli.resolve(fid, 5, key="once")
    return r["ok"] and cli.take(fid, "int")["result"] == {"outcome": "ok", "value": 5}


def _duplicate_out_of_order(rt):
    from .adapters import Link, RemoteClient, RemoteEndpoint
    from .auth import Authenticator, KeyRing
    kr = KeyRing(); kr.add("k1", b"k" * 32)
    au = Authenticator(kr)
    cli = RemoteClient(Link(RemoteEndpoint(rt, au)), au, "t", ["create", "resolve", "receive"])
    fid = cli.create("int")["result"]["future_id"]
    a = cli.resolve(fid, 1, key="k-a")
    b = cli.resolve(fid, 2, key="k-b")        # second, different resolution arrives later
    c = cli.resolve(fid, 1, key="k-a")        # duplicate of the first
    return a["ok"] and not b["ok"] and b["error"]["code"] == "FUTURE_ALREADY_RESOLVED" and c == a


SCENARIOS: dict[str, Callable[[Runtime], bool]] = {
    "producer_crash": _producer_crash,
    "consumer_crash": _consumer_crash,
    "dependency_exception": _dependency_exception,
    "delayed_scheduling": _delayed_scheduling,
    "resource_exhaustion": _resource_exhaustion,
    "configuration_failure": _config_failure,
    "telemetry_failure": _telemetry_failure,
    "network_loss_adapter": _network_loss,
    "duplicate_out_of_order": _duplicate_out_of_order,
}


def run_all(seed: int = 18) -> list[dict]:
    random.seed(seed)
    out = []
    for name, fn in SCENARIOS.items():
        rt = Runtime(ConfigStore({"environment": "test"}))
        t0 = time.perf_counter()
        try:
            ok = bool(fn(rt))
            err = None
        except Exception as exc:  # noqa: BLE001
            ok, err = False, f"{type(exc).__name__}: {exc}"
        inv = invariants(rt)
        out.append({"scenario": name, "recovered": ok, "invariants": inv, "error": err,
                    "passed": ok and not inv, "elapsed_s": round(time.perf_counter() - t0, 4)})
    return out
