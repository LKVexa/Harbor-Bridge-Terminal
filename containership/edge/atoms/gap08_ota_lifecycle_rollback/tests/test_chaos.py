"""Components 32 and 33: concurrency races and the single controlled chaos campaign.

The campaign exercises, in one rollout: lost acks, a health-service outage,
a stale controller + failover, a state-store failover via verified backup /
restore, an audit-sink outage, a reconnect storm, and a node rollback
failure — asserting after every fault that no invariant is broken, nothing is
reported as success that was not authenticated, and the external audit trail
is complete and verifiable at the end.
"""
from __future__ import annotations

import threading
import unittest

import _path  # noqa: F401
from gap08_ota_lifecycle_rollback.errors import (Conflict, DependencyUnavailable, Gap08Error, IllegalTransition,
                                                 StaleFence, StaleRevision)
from gap08_ota_lifecycle_rollback.harness import COMPAT, OPERATOR, SRE, build_world, spread_waves
from gap08_ota_lifecycle_rollback.store import FileStateStore


def invariant_check(tc, w, rid):
    state = w.store.load(rid).state
    from gap08_ota_lifecycle_rollback.rollout import Rollout
    core = Rollout.from_snapshot(state["core"])       # digest + invariants + audit chain
    for n in core.fleet_on(core.bundle):              # recorded 'on bundle' must be true on the node
        tc.assertEqual(w.nodes[n].version, core.bundle, n)
    return state, core


class Concurrency(unittest.TestCase):
    def test_two_controllers_race_step(self):
        w = build_world()
        a = w.controller("A")
        st = a.create(OPERATOR, bundle="v2", waves=spread_waves(w, (1, 2, 3, 6)), environment="prod",
                      verification=w.verification(), compat_profile=COMPAT)
        rid = st["rollout_id"]
        b = w.controller("B")
        results = []

        def go(c):
            try:
                c.step(OPERATOR, rid)
                results.append("ok")
            except (Conflict, StaleFence, StaleRevision, IllegalTransition) as exc:
                results.append(type(exc).__name__)
        ts = [threading.Thread(target=go, args=(c,)) for c in (a, b, a, b)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(results.count("ok"), 1, results)
        n = spread_waves(w, (1,))[0][0]
        self.assertEqual(w.nodes[n].executions, 1)
        invariant_check(self, w, rid)

    def test_concurrent_rollback_and_gate(self):
        w = build_world()
        c = w.controller()
        rid = c.create(OPERATOR, bundle="v2", waves=spread_waves(w, (1, 2, 3, 6)), environment="prod",
                       verification=w.verification(), compat_profile=COMPAT)["rollout_id"]
        c.step(OPERATOR, rid)
        p = c.status(rid)["pending"]
        w.clock.advance(90)
        ev = w.evidence(rid, p["cohort"], p["nodes"], applied_at=p["applied_at"])
        out = []

        def gate():
            try:
                c.gate(OPERATOR, rid, ev)
                out.append("gate")
            except Gap08Error as exc:
                out.append(type(exc).__name__)

        def rb():
            try:
                c.rollback(SRE, rid, reason="race")
                out.append("rollback")
            except Gap08Error as exc:
                out.append(type(exc).__name__)
        ts = [threading.Thread(target=gate), threading.Thread(target=rb)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        state, core = invariant_check(self, w, rid)
        self.assertIn(state["phase"], ("admitted", "rolled_back"), out)
        if "rollback" in out:
            self.assertTrue(all(v == "v1" for v in w.observed().values()))


    def test_step_racing_rollback_never_leaves_bundle_behind(self):
        for _ in range(10):
            w = build_world()
            c = w.controller()
            rid = c.create(OPERATOR, bundle="v2", waves=spread_waves(w, (1, 2, 3, 6)), environment="prod",
                           verification=w.verification(), compat_profile=COMPAT)["rollout_id"]
            c.step(OPERATOR, rid)
            w.pass_gate(c, rid)
            out = []

            def step():
                try:
                    c.step(OPERATOR, rid)
                    out.append("step")
                except Gap08Error as exc:
                    out.append(type(exc).__name__)

            def rb():
                try:
                    c.rollback(SRE, rid, reason="race")
                    out.append("rollback")
                except Gap08Error as exc:
                    out.append(type(exc).__name__)
            ts = [threading.Thread(target=step), threading.Thread(target=rb)]
            [t.start() for t in ts]
            [t.join() for t in ts]
            state, core = invariant_check(self, w, rid)
            if state["phase"] == "rolled_back":
                self.assertTrue(all(v == "v1" for v in w.observed().values()), (out, w.observed()))


class ChaosCampaign(unittest.TestCase):
    def test_single_controlled_campaign(self):
        w = build_world(24, max_fraction_per_domain=0.75)
        a = w.controller("A")
        rid = a.create(OPERATOR, bundle="v2", waves=spread_waves(w, (2, 4, 8, 10)), environment="prod",
                       verification=w.verification(), compat_profile=COMPAT, lineage="edge")["rollout_id"]
        waves = spread_waves(w, (2, 4, 8, 10))

        # 1. lost acks on the canary: executed once, reported ok only after an authenticated ack
        for n in waves[0]:
            w.channel.drop_ack[n] = 2
        a.step(OPERATOR, rid)
        self.assertTrue(all(w.nodes[n].executions == 1 for n in waves[0]))

        # 2. health-service outage: gate cannot pass; nothing advances
        w.deps.report("health", False)
        with self.assertRaises(DependencyUnavailable):
            w.pass_gate(a, rid)
        w.deps.report("health", True)
        w.pass_gate(a, rid)
        invariant_check(self, w, rid)

        # 3. stale controller: A pauses past its lease, B takes over; A is fenced everywhere
        a.step(OPERATOR, rid)
        w.clock.advance(45)
        b = w.controller("B")
        b.recover(rid)
        with self.assertRaises((Conflict, StaleFence)):
            a.gate(OPERATOR, rid, {})
        w.pass_gate(b, rid)

        # 4. state-store failover: verified backup -> restore into a fresh store -> continue
        bk = w.root / "backup-1"
        w.store.backup(bk)
        new_store = FileStateStore.restore(bk, w.root / "store-failover", clock=w.clock,
                                           fence_check=w.store.fence_check)
        for c in (a, b):
            c.store = new_store
        w.store = new_store
        invariant_check(self, w, rid)

        # 5. audit-sink outage: forward blocked, nothing lost
        w.sink.available = False
        w.deps.report("audit_sink", False)
        with self.assertRaises(DependencyUnavailable):
            b.step(OPERATOR, rid)
        w.sink.available = True
        w.deps.report("audit_sink", True)

        # 6. reconnect storm: a third of wave 3 flaps (lost requests) and duplicates are delivered
        for n in waves[2][::3]:
            w.channel.drop_request[n] = 2
        w.channel.duplicate = True
        b.step(OPERATOR, rid)
        w.channel.duplicate = False
        self.assertTrue(all(w.nodes[n].executions <= 1 for n in w.nodes))
        w.pass_gate(b, rid)

        # 7. bad final wave + a node whose rollback fails -> incomplete rollback, quarantine
        b.step(OPERATOR, rid)
        victim = waves[3][0]
        w.nodes[victim].fail_ops.add("rollback")
        r = w.pass_gate(b, rid, healthy=False)
        self.assertEqual(r["phase"], "rollback_incomplete")
        self.assertEqual(r["quarantined"], [victim])
        others = {n: v for n, v in w.observed().items() if n != victim}
        self.assertTrue(all(v == "v1" for v in others.values()), others)

        # 8. reconciliation confirms reality matches the record before any new mutation
        rec = b.reconcile(OPERATOR, rid)
        self.assertEqual(rec["drift"], {})
        state, core = invariant_check(self, w, rid)
        w.sink.verify(w.ring)
        w.sink.verify_against(core.audit_log)
        self.assertEqual(state["sealed_count"], len(core.audit_log))


if __name__ == "__main__":
    unittest.main()
