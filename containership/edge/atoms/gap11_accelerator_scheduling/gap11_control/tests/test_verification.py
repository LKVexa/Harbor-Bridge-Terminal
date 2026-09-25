"""P0-16 split-brain tests and the P2-33..39 verification components — 'verification
template' .01-.10. Concurrency, fault matrix, benchmarks with thresholds, hermeticity."""
from __future__ import annotations

import ast
import json
import random
import statistics
import threading
import time
import unittest
from pathlib import Path

from support import GPU0, GPU1, GPU2, Stack, covers
from gap11_control.common import ControlError, ManualClock
from gap11_control.controller import LIVENESS_DEAD, Controller
from gap11_control.election import LeaderElector
from gap11_control.store import LeaseStore, SimulatedCrash

PKG = Path(__file__).resolve().parents[1]
T = lambda c, *n: tuple(f"GAP11-{c}.{i:02d}" for i in n)


class SplitBrainTests(unittest.TestCase):
    @covers(*T("P0-16", 4, 6), *T("P2-38", 4, 6), *T("P2-36", 4))
    def test_partitioned_old_leader_with_delayed_messages_cannot_double_allocate(self):
        clock = ManualClock()
        st = Stack(clock=clock, devices=[GPU1])
        old = st.ctl
        clock.advance(11)                                                              # A partitioned away
        b_el = LeaderElector(st.store, "ctl-b"); self.assertTrue(b_el.try_acquire())
        new = Controller(st.store, b_el)
        lease = new.allocate({"tenant": "t2", "workload": "w"}, request_id="req-sb-00001", actor="t2")
        # delayed message from A's queue arrives, A still thinks it leads
        st.elector._expires = clock.monotonic() + 100
        with self.assertRaises(ControlError) as cm:
            old.allocate({"tenant": "t1", "workload": "w"}, request_id="req-sb-00002", actor="t1")
        self.assertIn(cm.exception.code, ("STALE_FENCE", "CAPACITY_EXHAUSTED"))
        # replay of B's request through A: idempotent read, never a second lease
        st.elector._expires = clock.monotonic() + 100
        try:
            again = old.allocate({"tenant": "t2", "workload": "w"}, request_id="req-sb-00001", actor="t2")
            self.assertEqual(again["lease_id"], lease["lease_id"])
        except ControlError as exc:
            self.assertEqual(exc.code, "STALE_FENCE")
        self.assertEqual(len(new.leases()), 1)
        # A regains leadership later: epoch strictly higher, sees B's lease from durable truth
        b_el.step_down()
        self.assertTrue(st.elector.try_acquire())
        self.assertGreater(st.elector.epoch, b_el.epoch or 0)
        self.assertIn(lease["lease_id"], st.ctl.leases())

    @covers(*T("P0-16", 5), *T("P2-36", 5, 1, 2))
    def test_barrier_collisions_allocate_release_scrub_reconcile_failover(self):
        """Threads start together on a barrier against ONE durable store."""
        for seed in range(5):
            clock = ManualClock()
            st = Stack(clock=clock, devices=[GPU0, GPU1, GPU2])
            st.elector.ttl = 10_000; st.elector.renew()
            seed_lease = st.ctl.allocate({"tenant": "t1", "workload": "seed", "memory_gb": 70}, request_id=st.rid(), actor="t1")
            barrier = threading.Barrier(6)
            results, errors = [], []
            def run(fn):
                barrier.wait()
                try:
                    results.append(fn())
                except ControlError as e:
                    errors.append(e.code)
            ops = [
                lambda: st.ctl.allocate({"tenant": "t2", "workload": "a", "memory_gb": 70}, request_id=f"req-bar-a-{seed}", actor="t2"),
                lambda: st.ctl.allocate({"tenant": "t3", "workload": "b", "memory_gb": 70}, request_id=f"req-bar-b-{seed}", actor="t3"),
                lambda: st.ctl.release(seed_lease["lease_id"], request_id=f"req-bar-r-{seed}", actor="t1"),
                lambda: st.ctl.scrub(seed_lease["device"], request_id=f"req-bar-s-{seed}", actor="op"),
                lambda: st.ctl.reconcile(lambda l: LIVENESS_DEAD),
                lambda: LeaderElector(st.store, "ctl-z").try_acquire(),
            ]
            ts = [threading.Thread(target=run, args=(f,)) for f in ops]
            [t.start() for t in ts]; [t.join(10) for t in ts]
            leases = [l for _, (_, l) in st.ctl.leases().items()]
            by_dev = {}
            for l in leases:
                by_dev.setdefault(l["device"], []).append(l)
            for dev, ls in by_dev.items():
                self.assertEqual(len(ls), 1, (seed, dev, ls))
                self.assertEqual(st.store.get(f"dev/{dev}")[1]["security_tenant"], ls[0]["tenant"])
            self.assertTrue(set(errors) <= {"STALE_REVISION", "CAPACITY_EXHAUSTED", "ILLEGAL_TRANSITION", "LEASE_NOT_FOUND"}, errors)
            self.assertTrue(LeaseStore(st.store.dir, clock=clock).verify()["consistent"])

    @covers(*T("P2-36", 3, 9))
    def test_soak_many_threads_idempotent_retries(self):
        st = Stack(devices=[{**GPU1, "device": f"g{i}"} for i in range(8)])
        st.elector.ttl = 10_000; st.elector.renew()
        def worker(i):
            for j in range(15):
                rid = f"req-soak-{i}-{j}"
                try:
                    a = st.ctl.allocate({"tenant": f"t{i}", "workload": "w"}, request_id=rid, actor="x")
                    b = st.ctl.allocate({"tenant": f"t{i}", "workload": "w"}, request_id=rid, actor="x")
                    assert a == b
                    st.ctl.release(a["lease_id"], request_id=rid + "-r", actor="x")
                except ControlError:
                    pass
        ts = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        [t.start() for t in ts]; [t.join(30) for t in ts]
        self.assertEqual(st.ctl.leases(), {})
        self.assertTrue(st.store.verify()["consistent"])


class FaultMatrixTests(unittest.TestCase):
    @covers(*T("P2-38", 1, 2, 3, 5, 7, 10), *T("P0-16", 3))
    def test_fault_matrix(self):
        """Each row: inject -> operation -> expected typed outcome -> invariant holds after."""
        matrix = []
        # store crash at every point during an allocate
        for point in ("before_write", "mid_write", "after_write_before_fsync", "after_fsync_before_apply", "before_ack"):
            armed = {"on": False}
            def fault(p, point=point):
                if armed["on"] and p == point:
                    armed["on"] = False
                    raise SimulatedCrash(point)
            clock = ManualClock()
            st = Stack(clock=clock, fault=fault)
            armed["on"] = True
            try:
                st.ctl.allocate({"tenant": "t1", "workload": "w"}, request_id="req-fm-000001", actor="t1")
                outcome = "ok"
            except SimulatedCrash:
                outcome = "crash"
            s2 = LeaseStore(st.store.dir, clock=clock)
            n = len([k for k in s2.data if k.startswith("lease/")])
            matrix.append({"fault": f"crash:{point}", "outcome": outcome, "leases_after_restart": n})
            self.assertIn(n, (0, 1))
            # retry after restart always converges to exactly one lease
            st.elector.store = s2
            Controller(s2, st.elector).allocate({"tenant": "t1", "workload": "w"}, request_id="req-fm-000001", actor="t1")
            self.assertEqual(len([k for k in s2.data if k.startswith("lease/")]), 1)
        # dependency outages
        st = Stack()
        svc, authn = st.service()
        from support import workload_token
        body = json.dumps({"schema": "PK_ACCELERATOR_ALLOCATION_REQUEST/1", "request_id": "req-fm-dep-01", "tenant": "t1", "workload": "w"}).encode()
        for name, brk, fix in [("identity", lambda: setattr(authn, "available", False), lambda: setattr(authn, "available", True)),
                               ("policy", lambda: setattr(svc.policy, "available", False), lambda: setattr(svc.policy, "available", True)),
                               ("store", lambda: setattr(st.store, "read_only", True), lambda: setattr(st.store, "read_only", False))]:
            brk()
            s, r = svc.handle("/v1/allocate", body, workload_token(authn))
            matrix.append({"fault": f"outage:{name}", "outcome": r.get("code")})
            self.assertIn(r.get("code"), ("DEPENDENCY_UNAVAILABLE", "STORE_UNAVAILABLE"))
            fix()
        self.assertEqual(len(st.ctl.leases()), 0)
        self.__class__.matrix = matrix


class BenchmarkTests(unittest.TestCase):
    THRESHOLDS = {"allocate_p99_ms": 25.0, "release_p99_ms": 25.0, "decode_p99_ms": 2.0}   # PROPOSED, unapproved

    @covers(*T("P2-39", 1, 2, 3, 9, 10), *T("P0-16", 9))
    def test_latency_thresholds_local_reference_host(self):
        st = Stack(devices=[{**GPU1, "device": f"g{i:03d}"} for i in range(64)])
        st.elector.ttl = 10_000; st.elector.renew()
        st.store.fsync = False                  # measures control-path CPU, not the disk; disk is a separate lane
        alloc, rel = [], []
        for i in range(400):
            t = time.perf_counter()
            a = st.ctl.allocate({"tenant": f"t{i % 5}", "workload": "w"}, request_id=f"req-bench-{i:05d}", actor="b")
            alloc.append((time.perf_counter() - t) * 1000)
            t = time.perf_counter()
            st.ctl.release(a["lease_id"], request_id=f"req-bench-r-{i:05d}", actor="b")
            rel.append((time.perf_counter() - t) * 1000)
            if i % 50 == 49:
                st.store.snapshot()
        from gap11_control.wire import decode
        body = json.dumps({"schema": "PK_ACCELERATOR_ALLOCATION_REQUEST/1", "request_id": "req-00000001", "tenant": "t", "workload": "w",
                           "features": ["a", "b"], "memory_gb": 4}).encode()
        dec = []
        for _ in range(2000):
            t = time.perf_counter(); decode(body, "PK_ACCELERATOR_ALLOCATION_REQUEST/1"); dec.append((time.perf_counter() - t) * 1000)
        q = lambda xs, p: sorted(xs)[int(p * (len(xs) - 1))]
        res = {"allocate_p50_ms": q(alloc, .5), "allocate_p99_ms": q(alloc, .99), "release_p99_ms": q(rel, .99),
               "decode_p99_ms": q(dec, .99), "fleet_devices": 64, "ops": 800}
        self.__class__.result = res
        for k, lim in self.THRESHOLDS.items():
            self.assertLess(res[k], lim, (k, res))


class HermeticityTests(unittest.TestCase):
    @covers(*T("P0-16", 2), *T("P2-33", 2), *T("P2-35", 2))
    def test_control_path_never_reads_wall_clock_or_unseeded_randomness_for_decisions(self):
        for mod in ("controller.py", "store.py", "election.py", "scheduler.py"):
            tree = ast.parse((PKG / mod).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                    self.assertFalse((node.value.id, node.attr) in {("time", "time"), ("time", "monotonic"), ("random", "random"),
                                                                    ("datetime", "now")}, (mod, node.value.id, node.attr))

    @covers(*T("P0-16", 1), *T("P2-33", 1), *T("P2-34", 1), *T("P2-35", 1), *T("P2-37", 1), *T("P2-38", 1), *T("P2-39", 1))
    def test_every_test_is_tagged_and_every_tag_is_a_real_check(self):
        checks = {c["id"] for c in json.loads((PKG.parent / "docs" / "CHECKLIST_ITEMS.json").read_text())["items"]}
        import importlib, inspect, unittest as u
        untagged = []
        for f in sorted(Path(__file__).parent.glob("test_*.py")):
            mod = importlib.import_module(f.stem)
            for _, cls in inspect.getmembers(mod, inspect.isclass):
                if issubclass(cls, u.TestCase):
                    for name, fn in inspect.getmembers(cls, inspect.isfunction):
                        if name.startswith("test_"):
                            tags = getattr(fn, "covers", None)
                            if not tags:
                                untagged.append(f"{f.stem}.{cls.__name__}.{name}")
                            for t in tags or ():
                                self.assertIn(t, checks, f"{name} tags unknown check {t}")
        self.assertEqual(untagged, [])


class ExitGateFalsifierTests(unittest.TestCase):
    """Shop convention: a NO_GO delivery must prove the gate is a gate, not a wall.
    A synthetic world where everything is MET and approved yields GO; removing any
    single input yields NO_GO. The delivered evidence is never touched."""

    @covers("GAP11-P2-50.14", "GAP11-P2-50.18")
    def test_exit_gates_go_only_when_every_input_holds(self):
        import sys
        sys.path.insert(0, str(PKG.parent / "tools"))
        from run_checklist import compute_exit, EXIT_DEPS
        comps = {c["id"]: "MET" for c in json.loads((PKG.parent / "docs" / "CHECKLIST_ITEMS.json").read_text())["components"]}
        owned = "| Accountable owner | NOT_THE_DELIVERED_OWNER |"
        exc_ok = [{"id": "EXC-X", "status": "APPROVED", "owner": "NOT_THE_DELIVERED_OWNER", "approved_on": "2026-01-01"}]
        full = compute_exit(comps, owned, exc_ok)
        self.assertTrue(all(v[0] == "MET" for v in full.values()), full)
        # each single omission flips at least one gate
        self.assertEqual(compute_exit(comps, owned + " UNASSIGNED", exc_ok)["GAP11-EXIT-01"][0], "NOT_MET")
        self.assertEqual(compute_exit(comps, owned, [{**exc_ok[0], "status": "PROPOSED"}])["GAP11-EXIT-10"][0], "NOT_MET")
        self.assertEqual(compute_exit(comps, owned, [{**exc_ok[0], "owner": "UNASSIGNED"}])["GAP11-EXIT-10"][0], "NOT_MET")
        for gate, deps in EXIT_DEPS.items():
            for d in deps:
                r = compute_exit({**comps, d: "NOT_MET"}, owned, exc_ok)
                self.assertEqual(r[gate][0], "NOT_MET", (gate, d))
        # and the delivered state really is NO_GO
        delivered = json.loads((PKG.parent / "evidence" / "EXIT_BUNDLE.json").read_text()) if (PKG.parent / "evidence" / "EXIT_BUNDLE.json").exists() else None
        if delivered is not None:
            self.assertEqual(delivered["verdict"], "NO_GO")


if __name__ == "__main__":
    unittest.main()
