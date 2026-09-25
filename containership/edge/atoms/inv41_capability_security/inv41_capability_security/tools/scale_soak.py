"""Scale, soak, burst/overload, partition/reconnect and restart scenarios (Section 22).

Every scenario emits a machine-readable record with environment, duration,
load profile, build hash, metrics, invariant violations and pass/fail against
the thresholds below.  ``--tier pr`` runs seconds; ``--tier nightly`` runs
minutes; the release tier (hours/days) is a scheduled job — see
BLOCKERS.json B-SOAK-01: it has not been run in this pass.
Output: evidence/scale_soak.json.
"""
from __future__ import annotations

import gc
from array import array
import hashlib
import json
import pathlib
import sys
import threading
import time
import tracemalloc

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))

from inv41_capability_security import errors  # noqa: E402
from inv41_capability_security.audit import AuditChain, verify_chain  # noqa: E402
from inv41_capability_security.broker import Broker  # noqa: E402
from inv41_capability_security.capabilities import (  # noqa: E402
    MAX_HOLDER_ENTRIES, MAX_MEMBRANE_DEPTH, MAX_OPERATIONS, Authority, LimitExceeded, Membrane, Revoked,
)
from inv41_capability_security.identity import HmacTokenAdapter, make_token  # noqa: E402
from inv41_capability_security.resilience import FaultInjector  # noqa: E402

TIERS = {"pr": 3.0, "nightly": 120.0, "release": 4 * 3600.0}
THRESHOLDS = {"leak_bytes_per_1k_ops": 2048, "latency_drift_ratio": 3.0, "invariant_violations": 0,
              "recovery_s": 2.0, "error_rate_unexpected": 0.0}


def build_hash() -> str:
    h = hashlib.sha256()
    for p in sorted(PKG.glob("*.py")):
        h.update(p.read_bytes())
    return h.hexdigest()


def scenario_scale() -> dict:
    t0 = time.time()
    viol = []
    auths = [Authority({"s": {"read"}}) for _ in range(2000)]
    big_policy = Authority({f"r{i}": {f"o{j}" for j in range(MAX_OPERATIONS)} for i in range(64)})
    refs = [auths[0].grant("s") for _ in range(50_000)]
    h = auths[0].bind_holder("h", {f"a{i}": refs[i] for i in range(MAX_HOLDER_ENTRIES)})
    try:
        auths[0].bind_holder("h", {f"a{i}": refs[i] for i in range(MAX_HOLDER_ENTRIES + 1)})
        viol.append("holder limit not enforced")
    except LimitExceeded:
        pass
    ref = refs[0]
    for i in range(MAX_MEMBRANE_DEPTH):
        ref = Membrane(f"d{i}").wrap(ref)
    try:
        Membrane("over").wrap(ref)
        viol.append("depth limit not enforced")
    except LimitExceeded:
        pass
    wide = Membrane("wide")
    kids = [wide.wrap(refs[1]) for _ in range(20_000)]
    killed = wide.revoke()["references_killed"]
    if killed != len(kids):
        viol.append(f"accounting {killed} != {len(kids)}")
    if any(True for k in kids[:1000] if not _dead(k)):
        viol.append("wide revoke escaped")
    return {"scenario": "scale", "authorities": len(auths), "live_references": len(refs), "holder_entries": len(h.held),
            "policy_resources": len(big_policy.policy), "membrane_depth": MAX_MEMBRANE_DEPTH, "wide_descendants": len(kids),
            "violations": viol, "duration_s": round(time.time() - t0, 2), "pass": not viol}


def _dead(ref) -> bool:
    try:
        ref.invoke("read")
        return False
    except Revoked:
        return True


def scenario_soak(seconds: float) -> dict:
    a = Authority({"s": {"read", "write"}})
    viol = []
    # array('q') stores raw machine ints: a first version used lists of Python ints and the harness itself
    # showed up as a 16 KB/1k-op 'leak' (5000 boxed ints).  Kept as a note: measure the subject, not the probe.
    lat_first, lat_last = array('q', [0] * 2000), array('q', [0] * 5000)
    gc.collect()
    tracemalloc.start()
    m0 = None
    ops = 0
    dead_refs = []
    t_end = time.time() + seconds
    t0 = time.time()
    while time.time() < t_end:
        m = Membrane("soak")
        r = m.wrap(a.grant("s"))
        h = a.bind_holder("h", {"s": r})
        t = time.perf_counter_ns()
        h.use("s", "read")
        dt = time.perf_counter_ns() - t
        r.attenuate({"read"})
        m.revoke()
        if ops % 97 == 0 and ops < 2000:  # retained probes are taken before the baseline snapshot
            dead_refs.append(r)
        ops += 1
        if ops == 2000:
            gc.collect()
            m0 = tracemalloc.get_traced_memory()[0]
        if ops < 2000:
            lat_first[ops] = dt
        else:
            lat_last[ops % 5000] = dt
    gc.collect()
    m1 = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    for r in dead_refs:
        if not _dead(r):
            viol.append("revoked reference usable after churn")
    leak = ((m1 - (m0 or m1)) / max(1, ops - 2000)) * 1000
    lat_last = [x for x in lat_last if x]
    med = lambda xs: sorted(xs)[len(xs) // 2] if xs else 0
    drift = (med(lat_last) / med(lat_first)) if lat_first and lat_last else 1.0
    ok = not viol and leak <= THRESHOLDS["leak_bytes_per_1k_ops"] and drift <= THRESHOLDS["latency_drift_ratio"]
    return {"scenario": "soak", "seconds": round(time.time() - t0, 1), "ops": ops, "leak_bytes_per_1k_ops": round(leak, 1),
            "latency_drift_ratio": round(drift, 2), "violations": viol, "pass": ok}


def scenario_burst() -> dict:
    audit = AuditChain(b"k" * 32, max_buffer=1_000_000)
    b = Broker(Authority({"s": {"read"}}), audit=audit, max_concurrent=4, max_queue=8)
    from inv41_capability_security.resilience import Admission
    b.admission = Admission(2, 1, priority_reserve=2, wait_s=0.001)  # tight profile so the burst deterministically exceeds capacity
    b.selfcheck_passed = True
    h = b.bind_holder("h", {"s": b.grant("s")})
    m = Membrane("burst")
    w = b.wrap(m, h.held["s"])
    outcomes = {"allowed": 0, "overloaded": 0, "other": 0}
    lock = threading.Lock()
    revoke_ok = []

    def occupier():  # simulated slow work holding capacity, so the burst really exceeds it
        for _ in range(100):
            try:
                with b.admission():
                    time.sleep(0.005)
            except errors.Overloaded:
                pass

    def hammer():
        for _ in range(400):
            try:
                b.use(h, "s", "read")
                with lock:
                    outcomes["allowed"] += 1
            except errors.Overloaded:
                with lock:
                    outcomes["overloaded"] += 1
            except Exception:
                with lock:
                    outcomes["other"] += 1

    ts = [threading.Thread(target=hammer) for _ in range(24)] + [threading.Thread(target=occupier) for _ in range(8)]
    t0 = time.time()
    for t in ts:
        t.start()
    time.sleep(0.2)
    revoke_ok.append(b.revoke(m)["revoked"])  # priority lane during overload
    for t in ts:
        t.join()
    burst_s = time.time() - t0
    t1 = time.time()
    b.use(h, "s", "read")  # recovery
    recovery = time.time() - t1
    viol = []
    if not revoke_ok[0]:
        viol.append("revocation starved under overload")
    if not _dead(w):
        viol.append("revoked during burst but still usable")
    if b.admission.in_flight != 0:
        viol.append("in-flight slots leaked")
    if outcomes["other"]:
        viol.append(f"{outcomes['other']} unexpected errors")
    return {"scenario": "burst", "threads": "24 users + 8 capacity occupiers", "outcomes": outcomes, "duration_s": round(burst_s, 2),
            "recovery_s": round(recovery, 4), "violations": viol,
            "pass": not viol and outcomes["overloaded"] > 0 and recovery <= THRESHOLDS["recovery_s"]}


def scenario_partition() -> dict:
    fi = FaultInjector()
    now = [1000.0]
    up = [True]
    ad = HmacTokenAdapter(issuer="i", audience="a", keys={"k": b"x" * 32}, clock=lambda: now[0], available=lambda: up[0])
    n = [0]

    def tok(**o):
        n[0] += 1
        return make_token(dict({"kid": "k", "iss": "i", "aud": "a", "sub": "s", "typ": "service", "tenant": "t", "env": "e",
                                "nbf": now[0] - 1, "exp": now[0] + 60, "nonce": f"n{n[0]}"}, **o), b"x" * 32)
    viol = []
    stale = tok()
    for dep in ("identity", "policy", "key", "time", "audit", "telemetry", "control-plane"):
        fi.set(dep, "partition")
        try:
            fi.check(dep)
            viol.append(f"{dep}: partition not observed")
        except errors.Unavailable:
            pass
        fi.set(dep, None)
    up[0] = False
    try:
        ad.authenticate(tok())
        viol.append("auth succeeded during identity partition")
    except errors.Unavailable:
        pass
    now[0] += 3600  # long outage
    up[0] = True
    try:
        ad.authenticate(stale)
        viol.append("stale credential trusted after reconnect")
    except errors.StaleState:
        pass
    ad.authenticate(tok())
    return {"scenario": "partition_reconnect", "dependencies": 7, "violations": viol, "pass": not viol}


def scenario_restart() -> dict:
    a1 = Authority({"s": {"read"}}, authority_id="svc")
    ref = a1.grant("s")
    audit1 = AuditChain(b"k" * 32)
    audit1.emit("grant", outcome="success", reason="x")
    del a1  # "process" loss: reconstruct from config
    a2 = Authority({"s": {"read"}}, authority_id="svc")
    viol = []
    try:
        a2.bind_holder("h", {"s": ref})
        viol.append("old reference accepted by reconstructed authority")
    except Exception:
        pass
    audit2 = AuditChain(b"k" * 32, previous_head=audit1.head)
    if audit2.exported[0]["fields"]["previous_segment_head"] != audit1.head:
        viol.append("new audit segment not anchored")
    if not verify_chain(audit2.exported, b"k" * 32)["valid"]:
        viol.append("new segment invalid")
    return {"scenario": "restart_reconstruct", "violations": viol, "pass": not viol}


def main() -> int:
    tier = sys.argv[sys.argv.index("--tier") + 1] if "--tier" in sys.argv else "pr"
    t0 = time.time()
    results = [scenario_scale(), scenario_soak(TIERS[tier]), scenario_burst(), scenario_partition(), scenario_restart()]
    out = {"schema": "INV41_SCALE_SOAK/1", "tier": tier, "build_sha256": build_hash(), "thresholds": THRESHOLDS,
           "python": sys.version.split()[0], "duration_s": round(time.time() - t0, 1),
           "fleet_distributed": "NOT_RUN — no multi-node deployment exists (BLOCKERS.json B-FLEET-01)",
           "results": results, "pass": all(r["pass"] for r in results)}
    (PKG / "evidence").mkdir(exist_ok=True)
    (PKG / "evidence" / f"scale_soak_{tier}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({r["scenario"]: r["pass"] for r in results}))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
