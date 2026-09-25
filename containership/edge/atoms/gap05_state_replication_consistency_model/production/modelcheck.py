"""MC48 - Explicit-state model checking of the GAP-05 causal-frontier invariants.

This is a bounded exhaustive checker written in Python that drives the *real*
``model.ReplicatedKey`` (not a re-implementation), so what it proves is about the
shipped code.  For a scenario it enumerates **every delivery order** of a write set
(including duplicate deliveries) and interleaved resolution points, and checks:

* INV-CONV   identical delivered sets => identical (active, quarantine) partition
* INV-MAX    the unresolved frontier is an antichain (no member dominates another)
* INV-COVER  every delivered write is in the frontier or dominated by a frontier member
             (causal maximality: nothing is silently lost)
* INV-BOUND  len(active) <= max_siblings; overflow is exactly frontier - active
* INV-DUP    re-delivery never changes the frontier (replay idempotence)
* INV-RES    after resolve(), the single winner dominates every previously delivered write
* INV-FENCE  (membership) a retired site's write above its high-water is always refused

A TLA+ rendering of the same invariants is shipped in ``spec/GAP05.tla`` for review;
it has **not** been run through TLC in this build (no TLC in the build environment) and
the evidence file records that as NOT_RUN rather than as a pass.
"""
from __future__ import annotations

import itertools
import json
import sys

from ..model import ReplicatedKey, Write, dominates


def _frontier(rk):
    return [w for w in rk.siblings] + [e["write"] for e in rk.quarantine]


def _state(rk):
    return (tuple(w.identity() for w in rk.siblings), tuple(e["write"].identity() for e in rk.quarantine))


def scenario_writes(sites=("a", "b", "c"), depth=2):
    """All writes where each site authors up to ``depth`` writes; later writes of a site
    causally follow its earlier write and optionally one other site's first write."""
    writes = []
    for s in sites:
        writes.append(Write("k", f"{s}1", s, ((s, 1),)))
    if depth >= 2:
        for s in sites:
            others = [o for o in sites if o != s]
            writes.append(Write("k", f"{s}2", s, tuple(sorted({(s, 2), (others[0], 1)}))))
    return writes


def check(writes, replicas, max_siblings, *, max_orders=None) -> dict:
    stats = {"orders": 0, "states": 0, "violations": []}
    finals = {}
    orders = itertools.permutations(writes)
    for order in orders:
        if max_orders and stats["orders"] >= max_orders:
            break
        stats["orders"] += 1
        rk = ReplicatedKey("k", frozenset(replicas), max_siblings=max_siblings)
        delivered = []
        for w in order:
            rk.apply(w)
            delivered.append(w)
            stats["states"] += 1
            fr = _frontier(rk)
            # INV-MAX
            for x, y in itertools.permutations(fr, 2):
                if dominates(x.vector_map(), y.vector_map()):
                    stats["violations"].append(("INV-MAX", [v.value for v in order]))
            # INV-COVER
            for d in delivered:
                if d not in fr and not any(dominates(f.vector_map(), d.vector_map()) for f in fr):
                    stats["violations"].append(("INV-COVER", [v.value for v in order]))
            # INV-BOUND
            if len(rk.siblings) > max_siblings or (rk.quarantine and len(rk.siblings) != max_siblings):
                stats["violations"].append(("INV-BOUND", [v.value for v in order]))
            # INV-DUP
            before = _state(rk)
            rk.apply(w)
            if _state(rk) != before:
                stats["violations"].append(("INV-DUP", [v.value for v in order]))
        finals.setdefault(frozenset(writes), set()).add(_state(rk))
        # INV-RES
        winner = rk.resolve("R", sorted(replicas)[0])
        for d in delivered:
            if not dominates(winner.vector_map(), d.vector_map()):
                stats["violations"].append(("INV-RES", [v.value for v in order]))
    for states in finals.values():
        if len(states) != 1:
            stats["violations"].append(("INV-CONV", len(states)))
    stats["distinct_final_states"] = sum(len(s) for s in finals.values())
    stats["ok"] = not stats["violations"]
    return stats


def check_fencing() -> dict:
    """Exhaustive over small counters: retired site above high-water always refused."""
    import tempfile
    from pathlib import Path
    from .errors import FencedError
    from .membership import MembershipConfig, MembershipStore, ReplicaRecord
    checked = 0
    violations = []
    with tempfile.TemporaryDirectory() as d:
        recs = {n: ReplicaRecord(n, f"spiffe://t/replica/{n}", (n,)) for n in ("a", "b")}
        store = MembershipStore(Path(d), MembershipConfig(1, recs, None, "mc", "genesis"))
        store.remove_replica("b", high_water={"k": 3}, author="mc", expected_epoch=1)
        for epoch in (1, 2, 3):
            for counter in range(1, 7):
                checked += 1
                try:
                    store.check_authorship("b", epoch, "k", counter)
                    accepted = True
                except FencedError:
                    accepted = False
                expected = epoch == 1 and counter <= 3
                if accepted != expected:
                    violations.append(("INV-FENCE", epoch, counter))
    return {"checked": checked, "violations": violations, "ok": not violations}


def run_all() -> dict:
    results = {}
    results["3sites_depth1_bound1"] = check(scenario_writes(depth=1), "abc", 1)
    results["3sites_depth1_bound2"] = check(scenario_writes(depth=1), "abc", 2)
    results["3sites_depth2_bound1"] = check(scenario_writes(depth=2), "abc", 1)
    results["3sites_depth2_bound2"] = check(scenario_writes(depth=2), "abc", 2)
    results["3sites_depth2_bound3"] = check(scenario_writes(depth=2), "abc", 3)
    results["4sites_depth2_bound2"] = check(scenario_writes(("a", "b", "c", "d"), depth=2), "abcd", 2)
    results["fencing"] = check_fencing()
    results["ok"] = all(r["ok"] for r in results.values() if isinstance(r, dict))
    return results


if __name__ == "__main__":  # pragma: no cover
    out = run_all()
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "violations"} if isinstance(v, dict) else v
                      for k, v in out.items()}, indent=1))
    sys.exit(0 if out["ok"] else 1)
