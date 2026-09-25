"""Fault-injection, disaster and partition-recovery suite (INV-68 MC-21, MC-19, MC-17; C055-C060, C089).

    python -m inv68_resource_packing.tools.faults [--out evidence/]

Each scenario injects one fault through a seam the service already exposes
(capacity source, audit opener, clock, filesystem) and asserts an *objective*
recovery condition.  Results go to ``FAULTS.json``; any failed assertion makes
the file ``result: FAIL``.

=====  ===========================================  ===================================================
id     fault                                        recovery assertion
=====  ===========================================  ===================================================
F01    capacity source unreachable                  CIRCUIT_OPEN after threshold; status degraded;
                                                    closes after reset + one good probe
F02    stale capacity (partition, no updates)       STALE_CAPACITY, never packs on stale data
F03    partition heals (reconnect)                  first fresh snapshot packs normally
F04    node loss (capacity halves mid-run)          next pack uses new capacity; no host above limits
F05    audit sink down                              pack continues (buffered); config change refused;
                                                    loss marker chained on recovery; chain verifies
F06    audit buffer exhausted                       drops counted; ``audit.loss`` record appears
F07    corrupt active snapshot (disk damage)        restart recovers last intact config, status degraded
F08    torn journal line (crash mid-append)         ignored; store still loads
F09    crash between snapshot and pointer swap      old config remains active (atomicity)
F10    stale controller (split brain)               lower epoch refused with STALE_EPOCH
F11    freeze during load                           in-flight completes, new requests FROZEN, state kept
F12    clock skew on tokens                         within skew accepted, beyond refused
F13    overload burst                               sheds with OVERLOADED; in-flight never exceeds limit
F14    backup/restore disaster drill                restored store serves the same config digest
=====  ===========================================  ===================================================
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import threading
import time
from pathlib import Path

from .common import PKG, write

from inv68_resource_packing.audit import AuditLog  # noqa: E402
from inv68_resource_packing.auth import Authorizer, mint  # noqa: E402
from inv68_resource_packing.config import ConfigStore, compose, defaults  # noqa: E402
from inv68_resource_packing.errors import PackError  # noqa: E402
from inv68_resource_packing.service import PackingService  # noqa: E402

KEY = {"k": b"q" * 32}


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


def tok(**kw):
    base = dict(kid="k", sub="sch", kind="workload-scheduler", tenants=["t"], caps=["pack:submit"])
    base.update(kw)
    return mint(KEY["k"], **base)


def op_tok():
    return mint(KEY["k"], kid="k", sub="alice", kind="operator", tenants=["*"], caps=["control:freeze"])


BODY = {"tenant": "t", "workloads": [{"name": f"w{i}", "cpu": 1, "mem": 4} for i in range(20)]}


def build(tmp, **kw):
    audit = kw.pop("audit", None) or AuditLog(Path(tmp) / "audit.jsonl")
    store = ConfigStore(Path(tmp) / "cfg", audit=audit)
    if store.active() is None:
        store.activate(compose(defaults().document, ("faults", {"tenants": {"overrides": {"t": {
            "max_requests_per_minute": 100000}}}})), actor="bootstrap", epoch=1)
    return PackingService(store, Authorizer(KEY, clock=kw.pop("auth_clock", time.time)), audit, **kw)


def code_of(fn):
    try:
        fn()
        return "OK"
    except PackError as e:
        return e.code


def scenario(fid, title):
    def deco(fn):
        fn.fid, fn.title = fid, title
        return fn
    return deco


@scenario("F01", "capacity source unreachable -> breaker opens, recovers")
def f01(tmp):
    mono, now = Clock(0.0), Clock(1000.0)
    up = {"ok": False}

    def src(_t):
        if not up["ok"]:
            raise TimeoutError("partition")
        return {"cpu": 16, "mem": 64, "observed_at": now.t}
    svc = build(tmp, capacity_source=src, monotonic=mono, clock=now)
    codes = [code_of(lambda: svc.pack(dict(BODY), tok())) for _ in range(5)]
    degraded = svc.status()["state"] == "degraded"
    up["ok"] = True
    mono.t += 6
    healed = code_of(lambda: svc.pack(dict(BODY), tok()))
    ok = "CIRCUIT_OPEN" in codes and degraded and healed == "OK" and svc.breaker.state == "closed"
    return ok, {"codes": codes, "degraded_while_open": degraded, "after_reset": healed}


@scenario("F02", "stale capacity during partition")
def f02(tmp):
    now = Clock(1000.0)
    svc = build(tmp, capacity_source=lambda _t: {"cpu": 16, "mem": 64, "observed_at": 1000.0}, clock=now)
    first = code_of(lambda: svc.pack(dict(BODY), tok()))
    now.t = 1000.0 + 3600
    stale = code_of(lambda: svc.pack(dict(BODY), tok()))
    return first == "OK" and stale == "STALE_CAPACITY", {"fresh": first, "after_1h": stale}


@scenario("F03", "partition heals")
def f03(tmp):
    now, mono = Clock(1000.0), Clock(0.0)
    snap = {"observed_at": 0.0}
    svc = build(tmp, capacity_source=lambda _t: {"cpu": 16, "mem": 64, **snap}, clock=now, monotonic=mono)
    stale = code_of(lambda: svc.pack(dict(BODY), tok()))
    snap["observed_at"] = now.t
    mono.t += 10
    healed = code_of(lambda: svc.pack(dict(BODY), tok()))
    return stale == "STALE_CAPACITY" and healed == "OK", {"during": stale, "after": healed}


@scenario("F04", "node loss halves capacity")
def f04(tmp):
    cap = {"cpu": 16, "mem": 64}
    now = Clock(1000.0)
    svc = build(tmp, capacity_source=lambda _t: dict(cap, observed_at=now.t), clock=now)
    a = svc.pack(dict(BODY), tok())
    cap.update(cpu=8, mem=32)
    b = svc.pack(dict(BODY), tok())
    limit_ok = all(h["used"]["mem"] <= 32 * 0.9 + 1e-9 for h in b["result"]["hosts"])
    return b["hosts_used"] > a["hosts_used"] and limit_ok, {"hosts_before": a["hosts_used"],
                                                            "hosts_after": b["hosts_used"], "limits_respected": limit_ok}


@scenario("F05", "audit sink down: pack buffers, config refused, loss chained on recovery")
def f05(tmp):
    state = {"down": False}
    real_open = lambda p: p.open("a", encoding="utf-8")

    def opener(p):
        if state["down"]:
            raise OSError("EIO")
        return real_open(p)
    audit = AuditLog(Path(tmp) / "audit.jsonl", opener=opener, buffer_limit=3)
    svc = build(tmp, audit=audit)
    ctl = mint(KEY["k"], kid="k", sub="ctl", kind="controller", tenants=["*"], caps=["config:activate"])
    state["down"] = True
    body = dict(BODY, host_capacity={"cpu": 16, "mem": 64})
    packs = [code_of(lambda: svc.pack(dict(body), tok())) for _ in range(6)]
    cfg_code = code_of(lambda: svc.activate_config(ctl, compose(defaults().document, ("x", {"headroom": 0.2}))))
    dropped = audit.dropped
    state["down"] = False
    svc.pack(dict(body), tok())
    ops = [r["operation"] for r in audit.records()]
    n = audit.verify()
    ok = all(c == "OK" for c in packs) and cfg_code == "AUDIT_UNAVAILABLE" and dropped > 0 and "audit.loss" in ops
    return ok, {"pack_codes": packs, "config_change": cfg_code, "dropped": dropped, "chain_records": n,
                "loss_marker": "audit.loss" in ops}


@scenario("F06", "audit buffer exhaustion is counted, never silent")
def f06(tmp):
    audit = AuditLog(Path(tmp) / "a.jsonl", opener=lambda p: (_ for _ in ()).throw(OSError("full")), buffer_limit=2)
    for i in range(10):
        audit.append("pack.decision", actor="x", outcome="ok")
    return audit.dropped == 8 and audit.buffered == 2, {"dropped": audit.dropped, "buffered": audit.buffered}


@scenario("F07", "corrupt active snapshot recovered on restart")
def f07(tmp):
    svc = build(tmp)
    good = svc.store.active().digest
    ctl = mint(KEY["k"], kid="k", sub="ctl", kind="controller", tenants=["*"], caps=["config:activate"])
    svc.activate_config(ctl, compose(svc.config.document, ("x", {"headroom": 0.2})))
    bad = svc.store.active().digest
    (Path(tmp) / "cfg" / "snapshots" / f"{bad}.json").write_bytes(b"\x00garbage")
    svc2 = build(tmp)
    st = svc2.status()
    return svc2.config.digest == good and st["state"] == "degraded", {"recovered_to": good[:12],
                                                                        "state": st["state"]}


@scenario("F08", "torn journal line")
def f08(tmp):
    build(tmp)
    with open(Path(tmp) / "cfg" / "journal.jsonl", "a") as fh:
        fh.write('{"digest": "abc')
    svc = build(tmp)
    return svc.config is not None and code_of(lambda: svc.pack(dict(BODY, host_capacity={"cpu": 16, "mem": 64}),
                                                               tok())) == "OK", {}


@scenario("F09", "crash between snapshot write and pointer swap")
def f09(tmp):
    svc = build(tmp)
    before = svc.store.active().digest
    new = compose(svc.config.document, ("x", {"headroom": 0.3}))
    store = svc.store
    orig = store._write_atomic

    def crash(path, data):
        if path.name == "ACTIVE":
            raise SystemExit("simulated power loss")
        return orig(path, data)
    store._write_atomic = crash
    try:
        store.activate(new, actor="ctl", epoch=1)
    except SystemExit:
        pass
    fresh = ConfigStore(Path(tmp) / "cfg")
    return fresh.active().digest == before, {"active_after_crash": fresh.active().digest[:12], "expected": before[:12]}


@scenario("F10", "stale controller fenced")
def f10(tmp):
    svc = build(tmp)
    ctl = mint(KEY["k"], kid="k", sub="ctl", kind="controller", tenants=["*"], caps=["config:activate"])
    svc.store.activate(svc.config, actor="ctl-new", epoch=7)
    code = code_of(lambda: svc.activate_config(ctl, compose(svc.config.document, ("x", {"headroom": 0.2}))))
    return code == "STALE_EPOCH", {"old_controller_epoch": svc.epoch, "owner_epoch": 7, "code": code}


@scenario("F11", "freeze during load")
def f11(tmp):
    svc = build(tmp)
    body = dict(BODY, host_capacity={"cpu": 16, "mem": 64})
    results = []

    def worker():
        for _ in range(20):
            results.append(code_of(lambda: svc.pack(dict(body), tok())))
    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    time.sleep(0.01)
    svc.freeze(op_tok(), "fault drill F11")
    for t in threads:
        t.join()
    after = code_of(lambda: svc.pack(dict(body), tok()))
    ok = after == "FROZEN" and set(results) <= {"OK", "FROZEN", "OVERLOADED"} and svc.store.active() is not None
    return ok, {"codes": {c: results.count(c) for c in set(results)}, "after_freeze": after}


@scenario("F12", "token clock skew")
def f12(tmp):
    clock = Clock(time.time())
    svc = build(tmp, auth_clock=clock)
    body = dict(BODY, host_capacity={"cpu": 16, "mem": 64})
    within = code_of(lambda: svc.pack(dict(body), tok(now=clock.t + 20)))
    beyond = code_of(lambda: svc.pack(dict(body), tok(now=clock.t + 120)))
    return within == "OK" and beyond == "UNAUTHENTICATED", {"skew_20s": within, "skew_120s": beyond}


@scenario("F13", "overload burst sheds")
def f13(tmp):
    svc = build(tmp)
    ctl = mint(KEY["k"], kid="k", sub="ctl", kind="controller", tenants=["*"], caps=["config:activate"])
    svc.activate_config(ctl, compose(svc.config.document, ("tight", {"limits": {"max_concurrency": 2, "max_queue": 1}})))
    body = dict(BODY, host_capacity={"cpu": 16, "mem": 64},
                workloads=[{"name": f"w{i}", "cpu": 0.5, "mem": 1} for i in range(1500)])
    codes = []
    barrier = threading.Barrier(12)

    def worker():
        t = tok()
        barrier.wait()
        codes.append(code_of(lambda: svc.pack(dict(body), t)))
    threads = [threading.Thread(target=worker) for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    peak = svc.admission.peak_in_flight
    return "OVERLOADED" in codes and peak <= 2, {"codes": {c: codes.count(c) for c in set(codes)}, "peak_in_flight": peak}


@scenario("F14", "backup/restore disaster drill")
def f14(tmp):
    svc = build(Path(tmp) / "site-a")
    bundle = json.loads(json.dumps(svc.store.export()))
    restored = ConfigStore.restore(Path(tmp) / "site-b" / "cfg", bundle)
    svc_b = build(Path(tmp) / "site-b")
    same = restored.active().digest == svc.config.digest == svc_b.config.digest
    body = dict(BODY, host_capacity={"cpu": 16, "mem": 64})
    a = svc.pack(dict(body), tok())["result"]
    b = svc_b.pack(dict(body), tok())["result"]
    return same and a == b, {"digest": svc.config.digest[:12], "identical_decisions": a == b}


SCENARIOS = [f01, f02, f03, f04, f05, f06, f07, f08, f09, f10, f11, f12, f13, f14]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PKG / "evidence"))
    a = ap.parse_args(argv)
    rows = []
    for fn in SCENARIOS:
        with tempfile.TemporaryDirectory() as tmp:
            t0 = time.perf_counter()
            try:
                ok, obs = fn(tmp)
            except Exception as exc:  # noqa: BLE001
                ok, obs = False, {"exception": f"{type(exc).__name__}: {exc}"[:300]}
            rows.append({"id": fn.fid, "title": fn.title, "result": "PASS" if ok else "FAIL",
                         "seconds": round(time.perf_counter() - t0, 3), "observed": obs})
    failed = [r["id"] for r in rows if r["result"] != "PASS"]
    write(Path(a.out) / "FAULTS.json", {"schema": "PK_PACK_FAULTS/1", "scenarios": rows, "failed": failed,
                                        "result": "PASS" if not failed else "FAIL"})
    for r in rows:
        print(f"{r['id']} {r['result']:<4} {r['title']}  {json.dumps(r['observed'])[:140]}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
