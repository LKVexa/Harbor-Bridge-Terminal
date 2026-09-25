"""Soak / burst / overload / recovery harness (component P2-25; C063, C088).

Drives the full LegacyPollService with W worker threads across T tenants for S
seconds: steady phase, a burst phase at 4x concurrency against a small global
ceiling (overload -> PK_POLL_OVERLOADED / PK_POLL_TENANT_QUOTA sheds), then a
recovery phase.  Invariants checked at the end: no leaked admission slots, no
in-flight lifecycle count, no pollable waiters left, audit chain verifies, every
refusal carried a registered code, recovery-phase success rate >= 0.99.
High-cardinality: tenant count up to thousands exercises the telemetry cap.
Fleet scale (many processes/hosts) is NOT exercised here.
"""
import argparse, json, os, random, sys, tempfile, threading, time
import _path  # noqa
sys.path.insert(0, str(_path.PKG / "tests"))
from _support import make_service, KEY
import polling as P, audit


def run(seconds=3.0, workers=16, tenants=200, seed=3):
    svc, iss, _, tmp = make_service(max_concurrent=8, tenant_max=2)
    rng = random.Random(seed)
    owners = [f"t{i}/app/i{i}" for i in range(tenants)]
    toks = {o: iss.mint(o, ttl_seconds=3600) for o in owners}
    stats = {"steady": {}, "burst": {}, "recovery": {}}
    lock = threading.Lock(); pollables = []
    phase = ["steady"]; stop = threading.Event()

    def worker(wid):
        r = random.Random(seed * 1000 + wid)
        while not stop.is_set():
            ph = phase[0]
            if ph != "burst" and wid >= workers // 4:
                time.sleep(0.001); continue
            o = r.choice(owners); p = P.Pollable("x", o)
            with lock:
                pollables.append(p)
            if r.random() < 0.7:
                threading.Timer(r.random() * 0.002, p.signal).start()
            try:
                res = svc.poll(o, [p], timeout_ticks=r.choice([1, 2, 5]), token=toks[o])
                k = "ready" if res["ready"] else "timeout"
            except Exception as e:
                k = getattr(e, "code", "UNSTRUCTURED:" + type(e).__name__)
            with lock:
                stats[ph][k] = stats[ph].get(k, 0) + 1

    ths = [threading.Thread(target=worker, args=(i,)) for i in range(workers)]
    [t.start() for t in ths]
    time.sleep(seconds * 0.4); phase[0] = "burst"; time.sleep(seconds * 0.3); phase[0] = "recovery"
    time.sleep(seconds * 0.3); stop.set(); [t.join() for t in ths]
    time.sleep(0.02)
    rec = stats["recovery"]; tot = sum(rec.values()) or 1
    ok_rate = (rec.get("ready", 0) + rec.get("timeout", 0)) / tot
    unstructured = sum(v for ph in stats.values() for k, v in ph.items() if k.startswith("UNSTRUCTURED"))
    waiters = sum(len(p._waiters) for p in pollables)
    ver = audit.verify_chain(os.path.join(tmp, "audit.jsonl"), KEY, expected_head=svc.audit.head)
    snap = svc.admission.snapshot()
    inv = {"admission_active_zero": snap["active"] == 0, "lifecycle_in_flight_zero": svc.lifecycle.in_flight() == 0,
           "no_waiters_left": waiters == 0, "audit_chain_ok": ver["ok"], "no_unstructured_errors": unstructured == 0,
           "recovery_success_rate_ge_0.99": ok_rate >= 0.99, "telemetry_series_bounded": svc.telemetry.series_count() <= 64 * 12 + 64}
    return {"seconds": seconds, "workers": workers, "tenants": tenants, "stats": stats, "audit_records": ver["count"],
            "peak_active": snap["peak"], "shed": snap["shed"], "recovery_success_rate": round(ok_rate, 4),
            "invariants": inv, "ok": all(inv.values())}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--workers", type=int, default=16); ap.add_argument("--tenants", type=int, default=200)
    a = ap.parse_args(); r = run(a.seconds, a.workers, a.tenants)
    print(json.dumps(r, indent=1)); raise SystemExit(0 if r["ok"] else 1)
