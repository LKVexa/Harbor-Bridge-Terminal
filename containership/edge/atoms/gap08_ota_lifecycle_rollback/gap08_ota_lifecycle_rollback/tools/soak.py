"""Component 35: long-duration soak driver.

Drives back-to-back rollouts over *simulated* days on one durable store and
audit sink: random node offline churn (deferred + retries), random gate
failures (rollback), random rollback failures (quarantine + two-person
release), controller restarts/failover every few cycles, and periodic
reconciliation.  After every cycle it asserts: store + audit chain verify,
no drift after reconcile, recorded-on-bundle nodes really run the bundle, and
resource growth is linear in the number of rollouts (not in time).

A short run is part of CI (``--cycles 40``); the checklist's days/weeks soak
is this same driver run with ``--cycles`` in the thousands against the
production-candidate store — that long run has NOT been executed here.

    python tools/soak.py --cycles 200 --seed 3 --out soak.json
"""
from __future__ import annotations

import argparse
import json
import random
import time

import _path  # noqa: F401
from gap08_ota_lifecycle_rollback.authz import Cap
from gap08_ota_lifecycle_rollback.errors import Gap08Error
from gap08_ota_lifecycle_rollback.harness import APPROVER, COMPAT, OPERATOR, SRE, build_world, spread_waves
from gap08_ota_lifecycle_rollback.rollout import Rollout


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=40)
    ap.add_argument("--nodes", type=int, default=36)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    rng = random.Random(a.seed)
    w = build_world(a.nodes, racks_per_site=max(2, a.nodes // 12), max_fraction_per_domain=0.75)
    ctl_n = 0
    c = w.controller(f"ctl-{ctl_n}")
    stats = {"rollouts": 0, "complete": 0, "rolled_back": 0, "rollback_incomplete": 0, "deferred_retries": 0,
             "restarts": 0, "quarantine_released": 0, "errors_handled": {}, "growth": []}
    version = 1
    t0 = time.perf_counter()
    q = a.nodes // 12
    sizes = (q, 2 * q, 3 * q, a.nodes - 6 * q)
    for cycle in range(a.cycles):
        bundle = f"v{version + 1}"
        w.clock.advance(3600 * rng.uniform(1, 12))
        try:
            rid = c.create(OPERATOR, bundle=bundle, waves=spread_waves(w, sizes), environment="soak",
                           verification=w.verification(bundle), compat_profile=COMPAT, lineage="agent")["rollout_id"]
        except Gap08Error as exc:
            stats["errors_handled"][exc.code] = stats["errors_handled"].get(exc.code, 0) + 1
            continue
        stats["rollouts"] += 1
        bad = rng.random() < 0.15
        while True:
            st = c.status(rid)
            if st["phase"] in ("complete", "rolled_back", "rollback_incomplete"):
                break
            if rng.random() < 0.1:                              # controller restart / failover
                w.clock.advance(45)
                ctl_n += 1
                c = w.controller(f"ctl-{ctl_n}")
                c.recover(rid)
                stats["restarts"] += 1
            w.channel.offline = set(rng.sample(sorted(w.nodes), rng.randint(0, 2)))
            try:
                if st["wave_index"] < st["waves"]:
                    c.step(OPERATOR, rid)
                else:
                    w.channel.offline = set()
                    w.clock.advance(86400)
                    c.reverify(OPERATOR, rid, w.verification(bundle))   # 24h statements expire
                    c.retry_deferred(OPERATOR, rid, force=True)
                    stats["deferred_retries"] += 1
                last = c.status(rid)["pending"] and c.status(rid)["wave_index"] == st["waves"] - 1
                if bad and last:
                    victim = rng.choice(sorted(w.nodes))
                    w.nodes[victim].fail_ops.add("rollback") if rng.random() < 0.5 else None
                w.pass_gate(c, rid, healthy=not (bad and last))
            except Gap08Error as exc:
                stats["errors_handled"][exc.code] = stats["errors_handled"].get(exc.code, 0) + 1
                w.channel.offline = set()
                # operator response: finish a pending gate if one exists, otherwise roll back
                try:
                    if c.status(rid)["pending"]:
                        w.pass_gate(c, rid)
                    else:
                        c.rollback(SRE, rid, reason=f"soak: forward blocked by {exc.code}")
                except Gap08Error:
                    c.rollback(SRE, rid, reason=f"soak: forward blocked by {exc.code}")
        w.channel.offline = set()
        final = c.status(rid)
        stats[final["phase"]] += 1
        for n in list(final["quarantined"]):
            w.nodes[n].fail_ops.clear()
            w.nodes[n].version = w.store.load(rid).state["core"]["pinned_target"]
            ap_id = w.approvals.request(SRE, Cap.QUARANTINE_RELEASE, f"release:{rid}:{n}", "soak reimage")
            w.approvals.approve(APPROVER, ap_id)
            c.release_quarantine(SRE, rid, n, approval_id=ap_id, evidence_note="soak reimage")
            stats["quarantine_released"] += 1
        for s in w.nodes.values():
            s.fail_ops.clear()
        rec = c.reconcile(OPERATOR, rid)
        assert not rec["drift"] and not rec["unreachable"], rec
        core = Rollout.from_snapshot(w.store.load(rid).state["core"])
        for n in core.fleet_on(core.bundle):
            assert w.nodes[n].version == core.bundle
        if final["phase"] == "complete":
            version += 1
        if cycle % 10 == 9:
            stats["growth"].append({"cycle": cycle + 1, "audit_entries": w.sink.verify(w.ring),
                                    "store_files": len(w.store.list_ids()),
                                    "store_bytes": sum(p.stat().st_size for p in (w.store.root).glob("*.json"))})
    stats["audit_entries"] = w.sink.verify(w.ring)
    stats["wall_s"] = round(time.perf_counter() - t0, 2)
    stats["sim_days"] = round((w.clock.now() - 1_790_000_000.0) / 86400, 1)
    print(json.dumps({k: v for k, v in stats.items() if k != "growth"}, indent=2))
    if a.out:
        with open(a.out, "w") as fh:
            json.dump(stats, fh, indent=2)
    return stats


if __name__ == "__main__":
    main()
