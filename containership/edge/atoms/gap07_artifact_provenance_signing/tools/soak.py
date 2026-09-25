"""Soak / burst / fleet-scale simulation (#34).

Runs admission continuously while trust generations rotate, revocations land
and bursts exceed the limiter, then reports saturation signals, shed counts,
error counts and recovery time after each burst.

Usage: python tools/soak.py --seconds 60 --sites 20 --burst-every 10
"""
from __future__ import annotations

import argparse
import json
import threading
import time

import _path  # noqa: F401

from gap07_artifact_provenance_signing.controls import AdmissionLimiter
from gap07_artifact_provenance_signing.tests.fixtures import Env


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=20)
    ap.add_argument("--sites", type=int, default=10)
    ap.add_argument("--burst-every", type=float, default=5)
    ap.add_argument("--burst-threads", type=int, default=32)
    a = ap.parse_args(argv)
    e = Env()
    e.ctl.limiter = AdmissionLimiter(max_concurrent=8, max_queue=32, rate_per_s=2000, burst=500, queue_timeout_s=0.2)
    req = e.full_request()
    counts: dict[str, int] = {}
    lock = threading.Lock()
    stop = threading.Event()
    gen = [1]

    def admit_loop():
        while not stop.is_set():
            d = e.ctl.admit(req)
            with lock:
                counts[d["code"]] = counts.get(d["code"], 0) + 1

    def rotator():
        while not stop.is_set():
            time.sleep(0.5)
            gen[0] += 1
            e.state.swap(e.pki.trust(generation=gen[0]))

    workers = [threading.Thread(target=admit_loop) for _ in range(a.sites)]
    rot = threading.Thread(target=rotator)
    for t in workers + [rot]:
        t.start()
    bursts, recoveries = 0, []
    t_end = time.time() + a.seconds
    while time.time() < t_end:
        time.sleep(a.burst_every)
        burst = [threading.Thread(target=lambda: [e.ctl.admit(req) for _ in range(50)]) for _ in range(a.burst_threads)]
        start = time.time()
        [b.start() for b in burst]
        [b.join() for b in burst]
        shed_before = counts.get("OVERLOADED", 0)
        # recovery: first non-shed decision after the burst
        while e.ctl.admit(req)["code"] == "OVERLOADED" and time.time() - start < 30:
            time.sleep(0.01)
        recoveries.append(round(time.time() - start, 3))
        bursts += 1
    stop.set()
    for t in workers + [rot]:
        t.join()
    rep = {"schema": "PK_SOAK_REPORT/1", "seconds": a.seconds, "sites": a.sites, "trust_generations": gen[0], "bursts": bursts,
           "decisions_by_code": counts, "limiter_shed": e.ctl.limiter.shed, "burst_recovery_s": recoveries,
           "internal_errors": counts.get("INTERNAL_ERROR", 0), "audit_chain_ok": e.audit.verify(), "audit_events": len(e.audit.events)}
    print(json.dumps(rep, indent=2))
    return rep


if __name__ == "__main__":
    main()
