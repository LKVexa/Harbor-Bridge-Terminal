"""Property-based/state-machine (55), fuzz (56), concurrency (57) and the
migration parity harness (59).  Deterministic seeds; override with
INV04_SEED / INV04_ITERATIONS for longer runs (soak mode, component 61)."""
from __future__ import annotations

import json
import os
import random
import threading
import unittest

import _support  # noqa: F401
from _support import FakeClock
from inv04_current_orchestration.model import Cluster, OrchestrationError, ConfigurationError
from inv04_current_orchestration.runtime import objects as o
from inv04_current_orchestration.runtime.api import InMemoryClusterAPI
from inv04_current_orchestration.runtime.config import load_config
from inv04_current_orchestration.runtime.drain import DrainCoordinator
from inv04_current_orchestration.runtime.errors import ConfigRejected, Conflict, RuntimeFault, SchemaViolation
from inv04_current_orchestration.runtime.journal import Journal
from inv04_current_orchestration.runtime.resilience import Backoff
from inv04_current_orchestration.runtime.store import VersionedStore
from inv04_current_orchestration.runtime.validation import SCHEMAS, parse_and_validate

SEED = int(os.environ.get("INV04_SEED", "1404"))
ITER = int(os.environ.get("INV04_ITERATIONS", "300"))


def random_cluster(rng):
    nodes = [f"n{i}" for i in range(rng.randint(1, 5))]
    desired = {f"w{i}": rng.randint(0, 5) for i in range(rng.randint(1, 4))}
    mins = {w: rng.randint(0, d) for w, d in desired.items() if rng.random() < 0.7}
    return nodes, desired, mins


class ModelStateMachineTest(unittest.TestCase):
    """Invariants over arbitrary reconcile/drain/scale sequences of the reference model."""

    def test_invariants_hold_for_random_operation_sequences(self):
        rng = random.Random(SEED)
        for it in range(ITER):
            nodes, desired, mins = random_cluster(rng)
            c = Cluster(list(nodes), desired=dict(desired), min_available=dict(mins))
            c.reconcile()
            for _ in range(rng.randint(1, 8)):
                before = (list(c.nodes), list(c.pods))
                op = rng.choice(["drain", "reconcile", "scale", "lose_pod"])
                try:
                    if op == "drain" and c.nodes:
                        c.drain(rng.choice(c.nodes + ["ghost"]))
                    elif op == "reconcile":
                        c.reconcile()
                    elif op == "scale":
                        w = rng.choice(sorted(c.desired))
                        c.desired[w] = rng.randint(max(c.min_available.get(w, 0), 0), 6)
                        c.reconcile()
                    elif op == "lose_pod" and c.pods:
                        c.pods.pop(rng.randrange(len(c.pods)))
                except (OrchestrationError, ConfigurationError, LookupError):
                    if op in ("drain", "reconcile"):
                        self.assertEqual((c.nodes, c.pods), before, f"iter {it}: failed {op} mutated state")
                    continue
                # invariant 1: every pod on a known node, for a managed workload
                self.assertTrue(all(n in c.nodes and w in c.desired for w, n in c.pods))
                # invariant 2: after reconcile/drain/scale the model is converged
                if op != "lose_pod":
                    for w, d in c.desired.items():
                        self.assertEqual(sum(1 for p in c.pods if p[0] == w), d if c.nodes else 0)
                # invariant 3: converged cluster is idempotent
                if op in ("reconcile", "scale"):
                    self.assertEqual(c.reconcile(), 0)


class StoreConcurrencyTest(unittest.TestCase):
    def test_concurrent_cas_writers_never_lose_updates(self):
        s = VersionedStore()
        s.create("Counter", "c", {"n": 0})
        conflicts = [0]
        lock = threading.Lock()

        def writer():
            for _ in range(200):
                while True:
                    cur = s.get("Counter", "c")
                    try:
                        s.update("Counter", "c", {"n": cur.spec["n"] + 1}, expected_rv=cur.resource_version)
                        break
                    except Conflict:
                        with lock:
                            conflicts[0] += 1
        ts = [threading.Thread(target=writer) for _ in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(s.get("Counter", "c").spec["n"], 1600)

    def test_concurrent_drains_of_different_nodes_never_breach_budget(self):
        rng = random.Random(SEED)
        for trial in range(20):
            clock = FakeClock(1000.0)
            nodes = [o.make_node(f"n{i}", last_heartbeat=clock()) for i in range(4)]
            pods = [o.make_pod(f"web-{i}", "web", f"n{i % 4}") for i in range(4)]
            pdb = o.DisruptionBudget(o.Meta("web"), selector=(("app", "web"),), min_available=3)
            api = InMemoryClusterAPI(nodes, pods, [pdb], desired={"web": 4})
            journal = Journal()
            results = []
            targets = rng.sample(["n0", "n1", "n2", "n3"], 2)

            def run(node, api=api, journal=journal, clock=clock, results=results, trial=trial):
                c = DrainCoordinator(api, journal, clock=clock, sleep=lambda s: None,
                                     settle=api.run_controllers, backoff=Backoff(base=0, jitter=0))
                results.append(c.drain(node, op_id=f"t{trial}-{node}"))
            ts = [threading.Thread(target=run, args=(n,)) for n in targets]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
            healthy = sum(1 for p in api.pods.values() if p.workload == "web" and p.ready)
            self.assertGreaterEqual(healthy, 3, f"trial {trial}: {[r.as_dict() for r in results]}")


class FuzzTest(unittest.TestCase):
    def test_schema_validator_never_crashes_on_mutated_input(self):
        rng = random.Random(SEED)
        seeds = [b'{"node":"n1"}', b'{"nodes":["a"],"pods":[],"desired":{"w":1}}', b'{"web":["n1"]}',
                 b'{"code":"ORCH_CONFLICT","message":"m"}']
        alphabet = b'{}[]":,0123456789-eE.truefalsnul \\\x00\xff'
        for _ in range(ITER * 5):
            raw = bytearray(rng.choice(seeds))
            for _ in range(rng.randint(1, 6)):
                pos = rng.randrange(len(raw) + 1)
                action = rng.random()
                if action < 0.4 and raw:
                    del raw[min(pos, len(raw) - 1)]
                elif action < 0.8:
                    raw.insert(pos, rng.choice(alphabet))
                else:
                    raw[pos:pos] = raw[: rng.randint(0, len(raw))]
            for iface in SCHEMAS:
                try:
                    parse_and_validate(iface, bytes(raw))
                except SchemaViolation:
                    pass

    def test_config_loader_rejects_rather_than_crashes(self):
        rng = random.Random(SEED)
        keys = ["workers", "api_qps", "site", "feature_gates", "lease_seconds", "bogus", "namespace_tenants"]
        values = [0, -1, 1, 3.5, "x", "", None, True, [], {}, {"a": True}, {"a": "b"}, 10 ** 9]
        for _ in range(ITER * 3):
            cand = {rng.choice(keys): rng.choice(values) for _ in range(rng.randint(1, 4))}
            try:
                load_config(cand)
            except ConfigRejected:
                pass

    def test_error_serialisation_is_always_schema_valid(self):
        from inv04_current_orchestration.runtime import errors
        from inv04_current_orchestration.runtime.validation import validate
        rng = random.Random(SEED)
        classes = [c for c in vars(errors).values() if isinstance(c, type) and issubclass(c, RuntimeFault)]
        for _ in range(ITER):
            cls = rng.choice(classes)
            exc = cls("m" + "x" * rng.randint(0, 50), details={"k": rng.randint(0, 9)})
            env = json.loads(json.dumps(exc.as_dict()))
            validate("PK_ORCH_ERROR/1", env)


class ParityHarnessTest(unittest.TestCase):
    """Runs the v4.2 reference model and the v4.3 runtime on identical scenarios
    and compares observable outcomes: accept/refuse decision, refusal class,
    and per-workload replica counts after the operation."""

    def test_drain_parity(self):
        rng = random.Random(SEED)
        compared = 0
        for it in range(ITER):
            nodes, desired, mins = random_cluster(rng)
            if len(nodes) < 1:
                continue
            model = Cluster(list(nodes), desired=dict(desired), min_available=dict(mins))
            model.reconcile()
            clock = FakeClock(1000.0)
            rt_nodes = [o.make_node(n, last_heartbeat=clock()) for n in nodes]
            rt_pods = [o.make_pod(f"{w}-{i}", w, n) for i, (w, n) in enumerate(model.pods)]
            pdbs = [o.DisruptionBudget(o.Meta(f"{w}-pdb"), selector=(("app", w),), min_available=m)
                    for w, m in mins.items()]
            api = InMemoryClusterAPI(rt_nodes, rt_pods, pdbs, desired=dict(desired))
            target = rng.choice(nodes)
            try:
                model.drain(target)
                m_outcome = "completed"
            except OrchestrationError as exc:
                m_outcome = {"ORCH_BUDGET_BREACH": "budget_breach", "ORCH_NO_CAPACITY": "no_capacity"}[exc.code]
            r = DrainCoordinator(api, Journal(), clock=clock, sleep=lambda s: None, settle=api.run_controllers,
                                 backoff=Backoff(base=0, jitter=0)).drain(target, op_id=f"p{it}")
            r_outcome = r.phase if r.phase == "completed" else r.reason
            self.assertEqual(r_outcome, m_outcome, f"iter {it}: model={m_outcome} runtime={r.as_dict()}")
            if m_outcome == "completed":
                for w in desired:
                    m_count = sum(1 for p in model.pods if p[0] == w)
                    r_count = sum(1 for p in api.pods.values() if p.workload == w)
                    self.assertEqual(r_count, m_count, f"iter {it}: {w}")
                    self.assertFalse(any(p.node == target for p in api.pods.values()))
            compared += 1
        self.assertGreater(compared, ITER // 2)


if __name__ == "__main__":
    unittest.main()
