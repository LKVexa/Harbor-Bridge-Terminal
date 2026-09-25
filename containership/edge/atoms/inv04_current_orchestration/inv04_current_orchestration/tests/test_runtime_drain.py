"""Drain transaction coordinator (8), eviction API (9), crash recovery (7),
journal (21), idempotency (22), fencing (5) and chaos (54, 62)."""
from __future__ import annotations

import os
import random
import tempfile
import unittest

import _support  # noqa: F401
from _support import FakeClock, cluster
from inv04_current_orchestration.runtime import objects as o
from inv04_current_orchestration.runtime.drain import DrainCoordinator, DrainOptions
from inv04_current_orchestration.runtime.errors import DependencyUnavailable, EvictionBlocked
from inv04_current_orchestration.runtime.journal import Journal
from inv04_current_orchestration.runtime.lease import FencingGuard
from inv04_current_orchestration.runtime.resilience import Backoff


class Crash(BaseException):
    """Simulated process death (not an Exception, so nothing may catch it)."""


def coord(api, journal=None, **kw):
    kw.setdefault("clock", FakeClock(1_000.0))
    return DrainCoordinator(api, journal or Journal(), settle=api.run_controllers, sleep=lambda s: None,
                            backoff=Backoff(base=0.0, jitter=0), **kw)


def state(api):
    return ({k: (n.unschedulable, n.meta.resource_version) for k, n in api.nodes.items()}, sorted(api.pods))


class DrainTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock(1_000.0)

    def api(self, **kw):
        return cluster(heartbeat=self.clock(), **kw)

    def test_nominal_drain_cordons_evicts_and_reschedules(self):
        api = self.api(workloads={"web": 3}, min_available={"web": 2})
        res = coord(api, clock=self.clock).drain("n0", op_id="op-a")
        self.assertEqual((res.phase, res.reason), ("completed", "drained"))
        self.assertTrue(api.nodes["n0"].unschedulable)
        self.assertEqual(sum(1 for p in api.pods.values() if p.workload == "web"), 3)
        self.assertFalse(any(p.node == "n0" for p in api.pods.values()))

    def test_budget_refusal_is_atomic_no_cordon_no_eviction(self):
        api = self.api(n_nodes=2, workloads={"db": 2}, min_available={"db": 2})
        before = state(api)
        res = coord(api, clock=self.clock).drain("n0", op_id="op-b")
        self.assertEqual((res.phase, res.reason), ("rejected", "budget_breach"))
        self.assertEqual(state(api), before)
        self.assertEqual(api.evictions, [])

    def test_no_capacity_refusal_is_atomic(self):
        api = self.api(n_nodes=2, workloads={"web": 2}, allocatable={"cpu_m": 100, "memory_mi": 1000,
                                                                      "ephemeral_mi": 1, "pods": 10})
        before = state(api)
        res = coord(api, clock=self.clock).drain("n0", op_id="op-c")
        self.assertEqual(res.reason, "no_capacity")
        self.assertEqual(state(api), before)

    def test_unmanaged_pod_blocks_unless_forced_and_daemonset_is_skipped(self):
        api = self.api()
        api._put_pod(o.make_pod("bare", "", "n0", owner_kind=""))
        api._put_pod(o.make_pod("agent", "agent", "n0", owner_kind="DaemonSet"))
        r1 = coord(api, clock=self.clock).drain("n0", op_id="op-d1")
        self.assertEqual(r1.reason, "drain_policy")
        self.assertFalse(api.nodes["n0"].unschedulable)
        r2 = coord(api, clock=self.clock).drain("n0", op_id="op-d2", options=DrainOptions(force_unmanaged=True))
        self.assertEqual(r2.phase, "completed")
        self.assertIn("default/agent", r2.skipped)
        self.assertIn("default/agent", api.pods)

    def test_dry_run_changes_nothing(self):
        api = self.api()
        before = state(api)
        r = coord(api, clock=self.clock).drain("n0", op_id="op-e", options=DrainOptions(dry_run=True))
        self.assertEqual((r.phase, r.reason), ("completed", "dry_run"))
        self.assertEqual(state(api), before)

    def test_replay_of_terminal_operation_is_idempotent(self):
        api = self.api()
        j = Journal()
        c = coord(api, j, clock=self.clock)
        r1 = c.drain("n0", op_id="op-f")
        n_evictions = len(api.evictions)
        r2 = c.drain("n0", op_id="op-f")
        self.assertEqual(r1.as_dict(), r2.as_dict())
        self.assertEqual(len(api.evictions), n_evictions)

    def test_unknown_node_and_partitioned_node(self):
        api = self.api()
        self.assertEqual(coord(api, clock=self.clock).drain("zz", op_id="op-g").reason, "unknown_node")
        stale = cluster(heartbeat=0.0)  # heartbeats far in the past
        r = coord(stale, clock=self.clock).drain("n0", op_id="op-h")
        self.assertEqual(r.phase, "completed")  # unreachable single node may be drained by policy

    def test_max_unavailable_zero_is_refused_up_front(self):
        api = self.api(workloads={"web": 3})
        api.pdbs = [o.DisruptionBudget(o.Meta("web-pdb"), selector=(("app", "web"),), max_unavailable=0)]
        r = coord(api, clock=self.clock).drain("n0", op_id="op-i")
        self.assertEqual(r.reason, "budget_breach")
        self.assertEqual(api.evictions, [])

    def test_transient_eviction_429_is_retried(self):
        api = self.api(workloads={"web": 3}, min_available={"web": 2})
        hits = [0]

        def fault(op, target):
            if op == "evict" and hits[0] < 2:
                hits[0] += 1
                raise EvictionBlocked("429 too many requests", reason="disruption_budget")
        api.fault_hook = fault
        r = coord(api, clock=self.clock).drain("n0", op_id="op-429")
        self.assertEqual(r.phase, "completed")
        self.assertEqual(hits[0], 2)

    def test_failure_before_first_eviction_rolls_back_cordon(self):
        api = self.api()

        def fault(op, target):
            if op == "evict":
                raise DependencyUnavailable("api down")
        api.fault_hook = fault
        r = coord(api, clock=self.clock).drain("n0", op_id="op-j", options=DrainOptions(eviction_attempts=2))
        self.assertEqual(r.phase, "uncordoned")
        self.assertFalse(api.nodes["n0"].unschedulable)

    def test_failure_after_first_eviction_stays_cordoned(self):
        api = self.api(workloads={"web": 6})
        calls = [0]

        def fault(op, target):
            if op == "evict":
                calls[0] += 1
                if calls[0] > 1:
                    raise DependencyUnavailable("api down")
        api.fault_hook = fault
        r = coord(api, clock=self.clock).drain("n0", op_id="op-k", options=DrainOptions(eviction_attempts=2))
        self.assertEqual(r.phase, "failed_cordoned")
        self.assertTrue(api.nodes["n0"].unschedulable)

    def test_stale_fencing_token_cannot_evict(self):
        api = self.api()
        api.fencing = FencingGuard()
        api.fencing.check(5)  # a newer leader has written
        r = coord(api, clock=self.clock, fencing_token=lambda: 3).drain("n0", op_id="op-l",
                                                                         options=DrainOptions(eviction_attempts=1))
        self.assertEqual(r.phase, "uncordoned")
        self.assertIn("ORCH_FENCED", r.reason)
        self.assertEqual(api.evictions, [])


class CrashRecoveryTest(unittest.TestCase):
    def test_crash_mid_eviction_resumes_without_duplicate_effects(self):
        clock = FakeClock(1_000.0)
        api = cluster(workloads={"web": 6}, heartbeat=clock())
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "journal.jsonl")
            calls = [0]

            def crash_after_first(op, target):
                if op == "evict":
                    calls[0] += 1
                    if calls[0] == 2:
                        raise Crash()
            api.fault_hook = crash_after_first
            with self.assertRaises(Crash):
                coord(api, Journal(path), clock=clock).drain("n0", op_id="op-crash")
            evicted_before = list(api.evictions)
            self.assertEqual(len(evicted_before), 1)
            api.fault_hook = None
            # restart: fresh coordinator, journal reloaded from disk
            results = coord(api, Journal(path), clock=clock).recover()
            self.assertEqual([r.phase for r in results], ["completed"])
            self.assertEqual(len(set(api.evictions)), len(api.evictions))  # no double eviction
            self.assertFalse(any(p.node == "n0" for p in api.pods.values()))
            self.assertEqual(sum(1 for p in api.pods.values() if p.workload == "web"), 6)
            self.assertEqual(Journal(path).open_operations(frozenset({"completed", "rejected", "uncordoned",
                                                                      "failed_cordoned"})), [])

    def test_crash_after_cordon_before_eviction_recovers(self):
        clock = FakeClock(1_000.0)
        api = cluster(heartbeat=clock())
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "journal.jsonl")

            def crash(op, target):
                if op == "evict":
                    raise Crash()
            api.fault_hook = crash
            with self.assertRaises(Crash):
                coord(api, Journal(path), clock=clock).drain("n1", op_id="op-x")
            self.assertTrue(api.nodes["n1"].unschedulable)
            api.fault_hook = None
            [r] = coord(api, Journal(path), clock=clock).recover()
            self.assertEqual(r.phase, "completed")


class ChaosTest(unittest.TestCase):
    def test_random_fault_injection_never_breaches_budget_or_loses_replicas(self):
        rng = random.Random(4242)
        for trial in range(60):
            clock = FakeClock(1_000.0)
            api = cluster(n_nodes=4, workloads={"web": 4, "api": 3}, min_available={"web": 2, "api": 2},
                          heartbeat=clock())
            p_fail = rng.choice([0.0, 0.2, 0.5])

            def fault(op, target, rng=rng, p=p_fail):
                if op in ("evict", "cordon", "list") and rng.random() < p:
                    raise DependencyUnavailable(f"injected {op}")
            api.fault_hook = fault
            target = f"n{rng.randrange(4)}"
            try:
                r = coord(api, clock=clock).drain(target, op_id=f"chaos-{trial}",
                                                  options=DrainOptions(eviction_attempts=3))
                phase = r.phase
            except DependencyUnavailable:
                phase = "dependency_error"
            api.fault_hook = None
            api.run_controllers()
            for w, minimum in (("web", 2), ("api", 2)):
                healthy = sum(1 for p in api.pods.values() if p.workload == w and p.ready)
                self.assertGreaterEqual(healthy, minimum, f"trial {trial}: {w} below budget ({phase})")
            if phase in ("uncordoned", "rejected", "dependency_error"):
                self.assertFalse(api.nodes[target].unschedulable and phase != "dependency_error",
                                 f"trial {trial}: node left cordoned after rollback")


if __name__ == "__main__":
    unittest.main()
