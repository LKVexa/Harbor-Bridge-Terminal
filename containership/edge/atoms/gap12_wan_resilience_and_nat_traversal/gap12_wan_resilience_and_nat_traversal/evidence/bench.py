"""Benchmarks with declared regression budgets (G12-H099 and each component's
"-19 measure CPU, memory, descriptors, latency" item).

Every benchmark runs at a REPRESENTATIVE load and at the declared WORST-SUPPORTED
load, measuring wall time per operation, CPU time, peak Python heap
(tracemalloc), open file descriptors and live threads before/after (leak check).
A component's perf item is credited only when both loads are inside budget and
no descriptor or thread leaked.  Budgets are this build's proposals: they are
engineering targets, not owner-approved SLOs.

    python3 -B evidence/bench.py [--out evidence/out/bench.json]
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import sys
import threading
import time
import tracemalloc

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, os.path.dirname(PKG))
sys.dont_write_bytecode = True

from gap12_wan_resilience_and_nat_traversal.path import Partitioned, Path  # noqa: E402
from gap12_wan_resilience_and_nat_traversal.wan import (config, contracts, dns, ice, obs, quality,  # noqa: E402
                                                        security, state, stun, transport, turn)


def fds() -> int:
    return len(os.listdir("/proc/self/fd"))


def measure(fn, n: int) -> dict:
    """Timing and heap are measured in SEPARATE runs: tracemalloc roughly doubles
    Python execution time, so timing a traced run would overstate cost."""
    fd0, th0 = fds(), threading.active_count()
    c0, t0 = time.process_time(), time.perf_counter()
    fn(n)
    wall, cpu = time.perf_counter() - t0, time.process_time() - c0
    tracemalloc.start()
    fn(n)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    time.sleep(0.05)
    return {"n": n, "wall_s": round(wall, 5), "cpu_s": round(cpu, 5), "us_per_op": round(wall / n * 1e6, 2),
            "peak_heap_kb": round(peak / 1024, 1), "fd_leak": fds() - fd0, "thread_leak": threading.active_count() - th0}


# --- workloads -------------------------------------------------------------------------------------

def w_stun_codec(n):
    key = stun.long_term_key("u", "r", "p")
    for _ in range(n):
        m = stun.Message(stun.BINDING, stun.CLS_SUCCESS)
        m.add(stun.A_XOR_MAPPED_ADDRESS, stun.encode_address("198.51.100.1", 40000, xor=True, txid=m.txid))
        d = stun.decode(m.encode(key, fingerprint=True))
        stun.check_integrity(d, key)


def w_stun_binding(n):
    with stun.StunServer([("127.0.0.1", 0)]) as srv:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("127.0.0.1", 0))
        for _ in range(n):
            assert stun.binding(s, srv.addresses[0], rto=0.2, rc=3, rm=2).ok
        s.close()


def w_turn_relay(n):
    with turn.TurnServer(("127.0.0.1", 0), {"a": "p"}) as srv:
        c = turn.TurnClient(srv.address, "a", "p")
        c.allocate()
        peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        peer.bind(("127.0.0.1", 0))
        c.create_permission("127.0.0.1")
        c.channel_bind(peer.getsockname())
        for _ in range(n):
            c.send(peer.getsockname(), b"x" * 1000)
            peer.recvfrom(2048)
        c.close()
        peer.close()


def w_ice(n):
    for i in range(n):
        a = ice.Agent(True, i)
        loc = [ice.Candidate("host", f"10.0.{j}.1", 5000 + j) for j in range(32)]
        rem = [ice.Candidate("srflx", f"198.51.{j}.1", 6000 + j) for j in range(32)]
        a.set_candidates(loc, rem)
        a.run_checks(lambda p: False)


def w_race(n):
    l = socket.socket()
    l.bind(("127.0.0.1", 0))
    l.listen(512)
    for _ in range(n):
        r = transport.race([("127.0.0.1", 1), l.getsockname()], attempt_delay=0.01, deadline_s=1)
        r.sock.close()
        l.accept()[0].close()
    l.close()


def w_dns(n):
    with dns.DnsServer(records={"relay.example": ["192.0.2.1"]}, ttl=0) as d:
        r = dns.Resolver([d.address])
        for _ in range(n):
            assert r.resolve("relay.example").addresses == ["192.0.2.1"]


def w_runner(n):
    run = quality.AttemptRunner(max_workers=8)
    for _ in range(n):
        run.run("direct", lambda c: True, timeout=1)


def w_quality(n):
    q = quality.QualityWindow(size=64)
    for i in range(n):
        q.add(float(i), 0.02 + (i % 7) * 0.001, send_ts=i, recv_ts=i + 0.02)
        if i % 16 == 0:
            q.summary(float(i))


def w_aead(n):
    s = os.urandom(32)
    a = security.SecureChannel(s, me="a", peer="b", initiator=True)
    b = security.SecureChannel(s, me="b", peer="a", initiator=False)
    for _ in range(n):
        b.open(a.seal(b"x" * 1200))


def w_limiter(n):
    r = security.RateLimiter({"source": (10, 10), "global": (1e9, 1e9)}, max_keys=10000)
    for i in range(n):
        r.allow({"source": f"s{i}", "global": "g"})


def w_audit(n):
    log = security.AuditLog()
    for i in range(n):
        log.append("e", reason="OK", actor="a", subject=str(i))


def w_store(n):
    st = state.PathStore(state.FakeClock(), max_peers=n + 1)
    for i in range(n):
        st.transition(f"p{i % 1000}", lambda p, now: p.connect(lambda s: s == "relay", now))


def w_config(n):
    for i in range(n):
        config.validate({**config.defaults(), "environment": "lab", "backoff_ceiling_s": 1 + i % 3000})


def w_metrics(n):
    m = obs.Metrics()
    for i in range(n):
        m.inc("g12_attempts_total", {"strategy": ("direct", "relay")[i % 2], "outcome": "ok"})
        m.observe("g12_establish_seconds", {"strategy": "direct"}, 0.01)
    m.expose()


def w_log(n):
    log = obs.EventLog(suppress_window=0)
    for i in range(n):
        log.emit("G12-E002", "NET_TIMEOUT", peer_token=f"ep-{i}", detail="to 198.51.100.7:3478")


def w_contracts(n):
    p = Path("x", _jitter_seed=1)
    for _ in range(n):
        contracts.validate(p.state(0), "PK_PATH_STATE/1")


def w_path(n):
    for i in range(n):
        p = Path(f"p{i}", _jitter_seed=i)
        try:
            p.connect(lambda s: False, 0)
        except Partitioned:
            pass


# component, name, workload, representative n, worst-supported n, budget us/op, budget peak heap KB at worst
BENCHES = [
    ("G12-A001", "stun_codec", w_stun_codec, 2000, 20000, 60, 512),
    ("G12-A001", "stun_binding_loopback", w_stun_binding, 200, 1000, 1500, 1024),
    ("G12-A002", "turn_channel_relay_1kB", w_turn_relay, 500, 3000, 1500, 2048),
    ("G12-A003", "ice_32x32_checklist", w_ice, 20, 200, 20000, 4096),
    ("G12-A014", "happy_eyeballs_loopback", w_race, 100, 400, 20000, 2048),
    ("G12-B023", "dns_resolve_loopback", w_dns, 200, 1000, 2500, 2048),
    ("G12-C028", "attempt_runner_overhead", w_runner, 500, 3000, 1500, 2048),
    ("G12-C031", "quality_window", w_quality, 5000, 50000, 40, 1024),
    ("G12-D044", "aead_seal_open_1200B", w_aead, 2000, 20000, 150, 2048),
    ("G12-D049", "rate_limiter_new_keys", w_limiter, 10000, 100000, 20, 8192),
    ("G12-D055", "audit_append", w_audit, 2000, 20000, 80, 32768),
    ("G12-E057", "pathstore_transition", w_store, 2000, 20000, 150, 16384),
    ("G12-F068", "config_validate", w_config, 500, 5000, 300, 1024),
    ("G12-G075", "metrics_inc_observe", w_metrics, 10000, 100000, 20, 1024),
    ("G12-G076", "event_emit_redacted", w_log, 2000, 20000, 150, 4096),
    ("G12-H086", "contract_validate", w_contracts, 2000, 20000, 60, 512),
    ("G12-H099", "path_connect_exhaust", w_path, 2000, 20000, 80, 16384),
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "out", "bench.json"))
    a = ap.parse_args(argv)
    rows = []
    for comp, name, fn, rep, worst, us_budget, heap_budget in BENCHES:
        try:
            r1, r2 = measure(fn, rep), measure(fn, worst)
            within = (r1["us_per_op"] <= us_budget and r2["us_per_op"] <= us_budget and r2["peak_heap_kb"] <= heap_budget
                      and r1["fd_leak"] <= 0 and r2["fd_leak"] <= 0 and r2["thread_leak"] <= 0)
            rows.append({"component": comp, "bench": name, "representative": r1, "worst_supported": r2,
                         "budget": {"us_per_op": us_budget, "peak_heap_kb_at_worst": heap_budget}, "within_budget": within})
        except Exception as exc:
            rows.append({"component": comp, "bench": name, "error": f"{type(exc).__name__}: {exc}", "within_budget": False})
        print(("OK  " if rows[-1]["within_budget"] else "OVER"), comp, name, rows[-1].get("worst_supported", rows[-1].get("error")))
    doc = {"schema": "G12-BENCH/1", "python": platform.python_version(), "machine": platform.machine(),
           "cpus": os.cpu_count(), "note": "budgets are proposed engineering targets, not approved SLOs", "results": rows}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump(doc, fh, indent=1)
    return 0 if all(r["within_budget"] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
