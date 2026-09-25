"""GAP04-C38 performance baseline + C39 soak/burst/fleet + C40 capacity inputs.

  python tests/perf/bench.py [--decisions N] [--fleet N] [--soak-days D] [--out evidence/perf_baseline.json]

Measures on the *current host* (results are host-specific evidence, not SLO claims):
decide() latency distribution with real fsync, throughput, CPU time, peak RSS,
journal bytes/decision (write amplification), reconnect/reconcile time and bytes
per decision sent to GAP-05, cold-start recovery time vs journal length, multi-day
logical partition soak, concurrent reconnect storm, and fleet-scale instantiation.
"""
import argparse, json, os, platform, resource, statistics, sys, tempfile, threading, time, shutil
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE.parents[2]))
from _util import node, T  # noqa
from gap04_disconnected_operation_controller.runtime import canonical
from gap04_disconnected_operation_controller.runtime.adapters import ReferenceReplication
from gap04_disconnected_operation_controller.runtime.config import default_config


def pct(xs, p):
    xs = sorted(xs); k = max(0, min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1)))))
    return xs[k]


def cfg_big():
    c = default_config(); c["admission"]["max_concurrency"] = 64; c["admission"]["max_queue"] = 100000
    c["max_decisions_per_partition"] = 1_000_000; c["journal"]["max_bytes"] = 1 << 30; c["journal"]["reserve_bytes"] = 4 << 20
    return c


def bench_decide(n_dec):
    d = Path(tempfile.mkdtemp(prefix="gap04-bench-"))
    try:
        cfg = cfg_big(); rep = ReferenceReplication()
        n, cp, m = node(d, config=cfg, replication=rep)
        T.bring_up(n, cp, m); T.go_dark(n, m)
        lat = []
        cpu0 = time.process_time(); w0 = time.perf_counter(); size0 = n.journal.size
        for i in range(n_dec):
            t = time.perf_counter()
            n.decide("restart", f"ns/w{i}", f"req-{i:010d}")
            lat.append(time.perf_counter() - t)
        wall = time.perf_counter() - w0; cpu = time.process_time() - cpu0
        bytes_per = (n.journal.size - size0) / n_dec
        plain = sum(len(canonical.dumps(x)) for x in n.controller.decisions) / n_dec
        T.come_back(n, cp, m)
        batches = []
        orig = rep.submit
        rep.submit = lambda b: (batches.append(len(canonical.dumps(b))), orig(b))[1]
        t = time.perf_counter(); n.reconnect(); rec_s = time.perf_counter() - t
        n.close()
        # cold start recovery with n_dec decisions pending
        n, cp, m = node(d, config=cfg, cp=cp)
        T.bring_up(n, cp, m) if False else None
        n.close()
        return {"decisions": n_dec,
                "decide_latency_ms": {"p50": pct(lat, 50) * 1e3, "p95": pct(lat, 95) * 1e3, "p99": pct(lat, 99) * 1e3,
                                      "max": max(lat) * 1e3, "mean": statistics.mean(lat) * 1e3},
                "throughput_decisions_per_s": n_dec / wall, "cpu_s_per_1k_decisions": cpu / n_dec * 1000,
                "journal_bytes_per_decision": bytes_per, "decision_record_bytes_plain": plain,
                "write_amplification": bytes_per / plain,
                "reconcile_s": rec_s, "reconcile_bytes_per_decision_to_GAP05": sum(batches) / n_dec, "reconcile_batches": len(batches)}
    finally:
        shutil.rmtree(d, ignore_errors=True)


def bench_recovery(n_dec):
    d = Path(tempfile.mkdtemp(prefix="gap04-rec-"))
    try:
        cfg = cfg_big()
        n, cp, m = node(d, config=cfg); T.bring_up(n, cp, m); T.go_dark(n, m)
        for i in range(n_dec):
            n.decide("restart", f"ns/w{i}", f"req-{i:010d}")
        n.close()
        t = time.perf_counter(); n2, _, _ = node(d, config=cfg, cp=cp, mono=m); s = time.perf_counter() - t
        ok = len(n2.controller.decisions) == n_dec
        n2.close()
        return {"pending_decisions": n_dec, "cold_start_recovery_s": s, "recovered_all": ok}
    finally:
        shutil.rmtree(d, ignore_errors=True)


def soak(days):
    """Logical multi-day partitions compressed in time: one decision per logical minute."""
    d = Path(tempfile.mkdtemp(prefix="gap04-soak-"))
    try:
        cfg = cfg_big(); cfg["lease"]["max_lifetime_s"] = 7 * 86400; cfg["max_policy_staleness_s"] = 30 * 86400
        cfg["tier_schedule"] = [[0, "full"], [86400, "sustain"], [2 * 86400, "freeze"]]
        n, cp, m = node(d, config=cfg); pol, _ = T.bring_up(n, cp, m, ttl=7 * 86400)
        T.go_dark(n, m)
        tiers, acc, den = {}, 0, 0
        t0 = time.perf_counter()
        for i in range(int(days * 1440)):
            m.t += 60
            kind = "restart" if i % 3 else "admit-new"
            try:
                n.decide(kind, f"ns/w{i % 500}", f"req-{i:010d}"); acc += 1
            except Exception:
                den += 1
            tiers[n.controller.tier(n.clock.now())] = tiers.get(n.controller.tier(n.clock.now()), 0) + 1
        T.come_back(n, cp, m); rec = n.reconnect()
        r = {"logical_days": days, "accepted": acc, "denied_by_tier_or_expiry": den, "tier_minutes": tiers,
             "reconciled": rec["decision_count"], "complete": rec["decision_count"] == acc,
             "wall_s": time.perf_counter() - t0, "journal_after_compaction_bytes": n.journal.size}
        n.close(); return r
    finally:
        shutil.rmtree(d, ignore_errors=True)


def storm(nodes, per_node):
    """Reconnect storm: N partitioned nodes reconcile concurrently against one GAP-05 peer."""
    base = Path(tempfile.mkdtemp(prefix="gap04-storm-"))
    try:
        rep = ReferenceReplication(); cp = T.ControlPlane(); ns = []
        for k in range(nodes):
            cfg = default_config(site=f"site-{k}")
            n, _, m = node(base / str(k), cp=cp, replication=rep, config=cfg, owner=f"n{k}")
            n.site = "site-a"  # heartbeats are signed for site-a in the simulator
            T.bring_up(n, cp, m) if False else None
            ns.append((n, m))
        # bring-up uses fixed scope site-a; use site-a config for lease binding
        for n, m in ns:
            n.cfg["scope"]["site"] = "site-a"
            T.bring_up(n, cp, m); T.go_dark(n, m)
            for i in range(per_node):
                n.decide("restart", f"ns/{id(n)}/{i}", f"req-{id(n)}-{i:06d}")
            T.come_back(n, cp, m)
        errs, times = [], []
        def go(n):
            t = time.perf_counter()
            try:
                n.reconnect()
            except Exception as e:
                errs.append(repr(e))
            times.append(time.perf_counter() - t)
        t0 = time.perf_counter()
        th = [threading.Thread(target=go, args=(n,)) for n, _ in ns]
        [x.start() for x in th]; [x.join() for x in th]
        wall = time.perf_counter() - t0
        for n, _ in ns:
            n.close()
        return {"nodes": nodes, "decisions_per_node": per_node, "wall_s": wall, "p99_node_reconcile_s": pct(times, 99),
                "errors": errs, "applied_at_peer": len(rep.applied), "expected": nodes * per_node}
    finally:
        shutil.rmtree(base, ignore_errors=True)


def fleet(nodes):
    base = Path(tempfile.mkdtemp(prefix="gap04-fleet-"))
    try:
        cp = T.ControlPlane(); t = time.perf_counter(); rss0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        ns = []
        for k in range(nodes):
            n, _, m = node(base / str(k), cp=cp, owner=f"n{k}"); T.bring_up(n, cp, m); ns.append(n)
        s = time.perf_counter() - t
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        for n in ns:
            n.close()
        return {"nodes": nodes, "bring_up_s": s, "per_node_ms": s / nodes * 1e3, "rss_growth_kib": rss - rss0}
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--decisions", type=int, default=5000)
    ap.add_argument("--fleet", type=int, default=100)
    ap.add_argument("--soak-days", type=float, default=3)
    ap.add_argument("--storm", type=int, default=25)
    ap.add_argument("--out", default=str(HERE.parents[1] / "evidence" / "perf_baseline.json"))
    a = ap.parse_args()
    r = {"schema": "PK_GAP04_PERF/1", "host": {"python": platform.python_version(), "platform": platform.platform(),
         "cpu_count": os.cpu_count(), "fs_tmp": tempfile.gettempdir()}, "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    r["decide"] = bench_decide(a.decisions)
    r["recovery"] = [bench_recovery(k) for k in (100, 1000, a.decisions)]
    r["soak"] = soak(a.soak_days)
    r["reconnect_storm"] = storm(a.storm, 200)
    r["fleet"] = fleet(a.fleet)
    r["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    r["not_measured"] = ["power impact (no power telemetry in build container)", "network overhead on a real WAN (bytes/decision reported instead)",
                         "ARM/edge hardware", "real GAP-05 peer latency"]
    Path(a.out).write_text(json.dumps(r, indent=2))
    print(json.dumps(r, indent=2))
