"""Scale/latency benchmarks (component 46).  Writes evidence/perf_baseline.json.

Measured (p50/p95/p99/max, n): Ed25519 verify, commit signature verify,
YAML manifest parse, plan over N resources, apply transaction over N
resources, and full reconcile (no-change and 100-resource initial) against a
real local git repository; plus cold start (build + recover), peak RSS and
state/journal bytes.  Numbers are a *local* baseline on the machine that ran
them -- not a fleet-scale or long-duration soak result.
"""
from __future__ import annotations

import json
import os
import platform
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
COMP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(COMP, "tests"))
sys.path.insert(0, os.path.dirname(os.path.dirname(COMP)))
sys.dont_write_bytecode = True


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100.0 * (len(xs) - 1))))]


def measure(name, fn, n):
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return {"name": name, "n": n, "p50": pct(ts, 50), "p95": pct(ts, 95), "p99": pct(ts, 99), "max": max(ts)}


def _rss_kb() -> int | None:
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except ImportError:
        return None


def main(out: str | None = None, quick: bool = False) -> dict:
    import fixtures as F
    from inv07_gitops_transition_layer.components import ed25519, manifests, signing
    from inv07_gitops_transition_layer.components.apply import Transaction, plan
    from inv07_gitops_transition_layer.components.state import ControllerState
    from inv07_gitops_transition_layer.components.target import DirectoryTarget
    from inv07_gitops_transition_layer.components.gitrepo import parse_commit
    import subprocess

    k = 3 if quick else 1
    res = []
    sk, pk = F.KEYS["dev"]
    msg = b"x" * 512
    sig = ed25519.sign(sk, msg)
    res.append(measure("ed25519_verify", lambda: ed25519.verify(pk, msg, sig), 30 // k))
    e = F.Env()
    try:
        oid = e.commit({"a.json": F.configmap()}, provenance=False)
        raw = subprocess.run(["git", "-C", e.work, "cat-file", "commit", oid], capture_output=True).stdout
        roots = signing.TrustRoots.from_doc(F.trust_doc())
        res.append(measure("commit_verify", lambda: signing.verify_commit(parse_commit(oid, raw), roots,
                                                                         ref="refs/heads/main", now=F.NOW), 30 // k))
    finally:
        e.cleanup()
    y = (F.deployment() * 1).encode()
    res.append(measure("yaml_parse_deployment", lambda: manifests.parse_yaml(y), 300 // k))
    N = 1000 // k
    desired = {("", "ConfigMap", "team-a", f"c{i}"): {"apiVersion": "v1", "kind": "ConfigMap",
               "metadata": {"name": f"c{i}", "namespace": "team-a"}, "data": {"v": str(i)}} for i in range(N)}
    res.append(measure(f"plan_{N}_resources", lambda: plan(desired, {}, owner="o", prune=False, revision="r"), 5))
    d = tempfile.mkdtemp()
    t = DirectoryTarget(os.path.join(d, "t"))
    s = ControllerState(os.path.join(d, "s"))
    acts = plan(desired, {}, owner="o", prune=False, revision="r")
    t0 = time.perf_counter()
    Transaction(t, s, owner="o", epoch=1, revision="a" * 40, ref="x").run(acts, desired, {}, at=0)
    res.append({"name": f"apply_txn_{N}_resources", "n": 1, "p50": time.perf_counter() - t0,
                "p95": None, "p99": None, "max": None})
    e = F.Env()
    try:
        e.commit({f"d/c{i}.json": F.configmap(name=f"c{i}") for i in range(100)})
        t0 = time.perf_counter()
        c = e.controller()
        cold = time.perf_counter() - t0
        t0 = time.perf_counter()
        r = c.reconcile("refs/heads/main")
        first = time.perf_counter() - t0
        assert r["outcome"] == "applied", r
        res.append({"name": "cold_start_build_recover", "n": 1, "p50": cold, "p95": None, "p99": None, "max": None})
        res.append({"name": "reconcile_initial_100_resources", "n": 1, "p50": first, "p95": None, "p99": None,
                    "max": None})
        res.append(measure("reconcile_no_change_100_resources", lambda: c.reconcile("refs/heads/main"), 10 // k))
        jb = os.path.getsize(os.path.join(c.tenancy.root, "state", "journal", "journal.wal"))
    finally:
        e.cleanup()
    doc = {"schema": "INV07-PERF/1", "quick": quick, "platform": platform.platform(),
           "python": platform.python_version(), "results": res, "peak_rss_kb": _rss_kb(), "journal_bytes": jb,
           "thresholds_status": "PROPOSED (unapproved; see docs/WAIVERS.json W-004)"}
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1, sort_keys=True)
    return doc


if __name__ == "__main__":
    print(json.dumps(main(os.path.join(COMP, "evidence", "perf_baseline.json"), quick="--quick" in sys.argv),
                     indent=1))
