"""M29 - bounded soak: N client threads against one node for --seconds, with a
killer thread that drops client connections at random. Reports error mix, RSS at
start/end, and whether the audit chain still verifies. Exit 1 on any unexpected
error kind or audit break.

    python tools/soak.py --seconds 60 --clients 8 --out evidence/soak.json
"""
from __future__ import annotations
import argparse, json, os, random, resource, sys, threading, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from wrpc import controls, node, ops, security, wit  # noqa: E402

WIT = "package s:k@1.0.0; interface i { inc: func(n: u64) -> u64; }"
EXPECTED = {"ok", "transport", "overloaded", "circuit-open", "deadline-exceeded"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--clients", type=int, default=8)
    ap.add_argument("--out")
    a = ap.parse_args()
    pkg = wit.parse(WIT)
    kr = security.Keyring(); psk = os.urandom(32); kid = kr.add("c", psk, 86400)
    cfg, _ = ops.ConfigStore.build(("soak", {"log_level": "ERROR", "trace_sample_ratio": 0.0, "max_inflight": 4,
                                             "max_queue": 4, "per_tenant_inflight": 4}))
    nd = node.Node(cfg, kr, pkg, {("s:k/i", "inc"): lambda n: n + 1}, {"c": "t"},
                   controls.Authorizer([controls.Grant("t", "c", "*", "*")]))
    h, p = nd.start()
    rss0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    counts, lock, stop = {}, threading.Lock(), time.time() + a.seconds
    clients = [node.Client(h, p, "c", kid, psk, cfg["node_id"], pkg, retry=controls.RetryPolicy(base_s=0.005))
               for _ in range(a.clients)]

    def work(c):
        i = 0
        while time.time() < stop:
            r = c.call("i", "inc", [i], timeout_s=1.0)
            k = "ok" if "ok" in r and r["ok"] == i + 1 else r.get("error", "wrong-result")
            with lock:
                counts[k] = counts.get(k, 0) + 1
            i += 1

    def killer():
        rng = random.Random(29)
        while time.time() < stop:
            time.sleep(0.2)
            c = rng.choice(clients)
            s = c._sock
            if s:
                try:
                    s.shutdown(2)
                except OSError:
                    pass
    ts = [threading.Thread(target=work, args=(c,)) for c in clients] + [threading.Thread(target=killer)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    nd.stop()
    ok_chain = ops.AuditLog.verify(nd.audit.records, nd.audit.head(), window=True)[0]
    res = {"schema": "INV61_SOAK/1", "seconds": a.seconds, "clients": a.clients, "outcomes": counts,
           "unexpected": sorted(set(counts) - EXPECTED), "rss_kb_start": rss0,
           "rss_kb_end": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, "audit_chain_ok": ok_chain,
           "audit_records": nd.audit.head()[0]}
    text = json.dumps(res, indent=2)
    if a.out:
        open(a.out, "w").write(text)
    print(text)
    return 1 if res["unexpected"] or not ok_chain else 0


if __name__ == "__main__":
    sys.exit(main())
