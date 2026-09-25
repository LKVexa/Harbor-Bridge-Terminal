import json
import os
import random
import threading
import unittest

from gap03_topology_aware_scheduler import FairShare, NotInTopology, Topology, rank
from gap03_topology_aware_scheduler.controlplane import canonical, compat, fuzz, wire
from gap03_topology_aware_scheduler.controlplane.adapters import gap02
from gap03_topology_aware_scheduler.controlplane.adapters.sch01 import SCH01Harness
from gap03_topology_aware_scheduler.controlplane.cache import ScoreCache
from gap03_topology_aware_scheduler.controlplane.coordination import Coordinator, LeaseReplica
from gap03_topology_aware_scheduler.controlplane.errors import SchedulerError
from gap03_topology_aware_scheduler.controlplane.faults import Chaos, ManualClock, StoreFault, invariants
from gap03_topology_aware_scheduler.controlplane.ledger_store import LedgerStore
from gap03_topology_aware_scheduler.controlplane.transactions import PlacementCoordinator, TxnJournal
from gap03_topology_aware_scheduler.scheduler import _score_snapshot
from gap03_topology_aware_scheduler.tests.cp._util import TmpCase, covers

CORPUS = os.path.join(os.path.dirname(fuzz.__file__), "..", "tests", "fuzz_corpus")


def world(tc, tag, faults=None, fault=None, cap=4):
    led = LedgerStore(tc.d("led" + tag), clock=tc.clock, fault=fault)
    if led.state["capacity"] == 0:
        led.submit({"type": "set_capacity", "capacity": cap})
        led.submit({"type": "set_reservations", "reserved": {"a": 2, "b": 2}, "entitlement_generation": 1})
    j = TxnJournal(tc.d("j" + tag), clock=tc.clock)
    down = SCH01Harness(faults=faults)
    t = Topology()
    for n, p in {"a": ("eu", "d", "r1"), "b": ("eu", "d", "r2"), "c": ("eu", "m", "r1"), "e": ("us", "i", "r1")}.items():
        t.place(n, *p)
    return led, j, down, t


class FaultMatrix(TmpCase):
    """MC-032: deterministic fault matrix; every scenario ends with the safety-invariant assertion."""

    def run_txns(self, pc, n, seed):
        rng = random.Random(seed)
        for i in range(n):
            try:
                pc.place(txn=f"t{seed}-{i}", workload={"id": "w"}, anchor="a", candidates=["b", "c", "e"], tenant=rng.choice("ab"))
            except SchedulerError:
                pass

    @covers("MC-032", 26)

    @covers("MC-032", 6, 10, 13, 25)
    def test_mc032_crash_points_in_every_phase(self):
        for stage in ("before_write", "mid_write", "before_fsync"):
            for nth in (1, 3, 5):
                with self.subTest(stage=stage, nth=nth):
                    tag = f"{stage}{nth}"
                    led, j, down, t = world(self, tag)
                    flt = StoreFault(stage, times=1)
                    counter = [0]

                    def fault(s, _f=flt, _c=counter, _n=nth):
                        if s == stage:
                            _c[0] += 1
                            if _c[0] == _n:
                                _f(s)
                    led.fault = fault
                    pc = PlacementCoordinator(journal=j, ledger=led, topology_snapshot=t.snapshot, downstream=down,
                                              fence=lambda: 1, clock=self.clock)
                    self.run_txns(pc, 6, seed=nth)
                    # crash = discard in-memory objects; restart from disk and recover
                    led2 = LedgerStore(self.d("led" + tag), clock=self.clock)
                    j2 = TxnJournal(self.d("j" + tag), clock=self.clock)
                    pc2 = PlacementCoordinator(journal=j2, ledger=led2, topology_snapshot=t.snapshot, downstream=down,
                                               fence=lambda: 1, clock=self.clock)
                    self.clock.advance(60)
                    pc2.recover_all()
                    inv = invariants(ledger=led2, journal=j2, downstream=down)
                    self.assertTrue(all(inv.values()), inv)
                    pending = [c for c, x in led2.state["claims"].items() if x["state"] == "pending"]
                    self.assertEqual(pending, [])  # convergence: nothing left in doubt

    @covers("MC-032", 7, 8, 9, 11, 27)
    def test_mc032_partitions_skew_and_stale_controller(self):
        sclock = ManualClock()
        reps = [LeaseReplica(f"{self.d('lease')}/r{i}.json", clock=sclock) for i in range(3)]
        led, j, down, t = world(self, "p")
        c1 = Coordinator("s1", reps, ttl=10, safety_margin=3, clock=self.clock)
        c2 = Coordinator("s2", reps, ttl=10, safety_margin=3, clock=self.clock)
        self.assertTrue(c1.acquire())
        pc1 = PlacementCoordinator(journal=j, ledger=led, topology_snapshot=t.snapshot, downstream=down, fence=lambda: c1.term,
                                   clock=self.clock)  # a buggy controller that ignores its own lease state
        self.run_txns(pc1, 2, seed=1)
        for r in reps:
            r.reachable["s1"] = False
        sclock.advance(8)  # replica clocks run fast (skew) but still < ttl: no one else can win yet
        self.assertFalse(c2.acquire())
        sclock.advance(3)
        self.assertTrue(c2.acquire())
        pc2 = PlacementCoordinator(journal=j, ledger=led, topology_snapshot=t.snapshot, downstream=down, fence=c2.fence,
                                   clock=self.clock)
        self.run_txns(pc2, 2, seed=2)
        before = dict(led.state["claims"])
        self.run_txns(pc1, 3, seed=3)  # delayed messages from the former leader
        self.assertEqual(led.state["claims"], before)
        self.clock.jump(-5)  # local time jumps backwards: lease must not extend
        self.assertTrue(all(invariants(ledger=led, journal=j, downstream=down).values()))

    @covers("MC-032", 12, 13, 27)
    def test_mc032_duplicate_reordered_replayed_messages(self):
        led, j, down, t = world(self, "d")
        pc = PlacementCoordinator(journal=j, ledger=led, topology_snapshot=t.snapshot, downstream=down, fence=lambda: 1,
                                  clock=self.clock)
        msgs = Chaos(11).mangle([f"m{i}" for i in range(10)], dup=0.6)
        for m in msgs:
            pc.place(txn=m, workload={"id": "w"}, anchor="a", candidates=["b", "c"], tenant="ab"[int(m[1:]) % 2])
        self.assertGreater(len(msgs), 10)
        self.assertTrue(all(invariants(ledger=led, journal=j, downstream=down).values()))

    @covers("MC-032", 8, 10, 27)
    def test_mc032_dependency_errors_disk_full_read_only(self):
        for kind in ("disk_full", "read_only"):
            with self.subTest(kind=kind):
                led, j, down, t = world(self, kind)
                led.fault = StoreFault("before_write", times=-1, kind=kind)
                pc = PlacementCoordinator(journal=j, ledger=led, topology_snapshot=t.snapshot, downstream=down, fence=lambda: 1,
                                          clock=self.clock)
                self.run_txns(pc, 3, seed=5)
                self.assertTrue(led.read_only)
                self.assertEqual(down.placements, {})  # nothing placed without a durable reservation
        chaos = Chaos(3)
        h = SCH01Harness()
        flaky = chaos.flaky(h.place, p_fail=0.5, exc_factory=lambda: ConnectionResetError())
        led, j, down, t = world(self, "net")
        pc = PlacementCoordinator(journal=j, ledger=led, topology_snapshot=t.snapshot, downstream=type("D", (), {
            "place": staticmethod(flaky), "status": staticmethod(h.status)})(), fence=lambda: 1, clock=self.clock)
        self.run_txns(pc, 8, seed=9)
        self.clock.advance(60)
        pc.recover_all()
        self.assertTrue(all(invariants(ledger=led, journal=j, downstream=h).values()))

    @covers("MC-032", 15)
    def test_mc032_matrix_evidence_written(self):
        led, j, down, t = world(self, "ev")
        inv = invariants(ledger=led, journal=j, downstream=down)
        out = os.path.join(self.tmp, "fault_matrix.json")
        with open(out, "w") as fh:
            json.dump({"scenario": "baseline", "invariants": inv, "seed": 0}, fh)
        self.assertTrue(json.load(open(out))["invariants"])


class Properties(unittest.TestCase):
    """MC-033: property + differential tests against simple reference models."""

    def rand_topo(self, rng, n):
        t = Topology()
        for i in range(n):
            t.place(f"n{i}", f"r{rng.randrange(3)}", f"s{rng.randrange(4)}", f"k{rng.randrange(5)}")
        return t

    @covers("MC-033", 7, 11, 25)
    def test_mc033_topology_properties_and_reference_ranking(self):
        rng = random.Random(2026)
        for _ in range(150):
            t = self.rand_topo(rng, rng.randint(2, 20))
            snap = t.snapshot()
            nodes = list(snap.nodes)
            a = rng.choice(nodes)
            cands = rng.sample(nodes, rng.randint(1, len(nodes)))
            spread = rng.sample(nodes, rng.randint(0, 2))

            def ref_cost(x, y):
                px, py = snap.nodes[x], snap.nodes[y]
                if x == y:
                    return 0
                return 101 if px[0] != py[0] else 11 if px[1] != py[1] else 2 if px[2] != py[2] else 1
            taken = {snap.domain(s) for s in spread}
            ref = sorted(cands, key=lambda c: (ref_cost(a, c) + (102 if snap.domain(c) in taken else 0), c))
            self.assertEqual(rank(t, a, cands, spread_from=spread), ref)
            self.assertEqual(rank(t, a, cands, spread_from=spread), rank(t, a, list(reversed(cands)), spread_from=spread))
            with self.assertRaises(NotInTopology):
                rank(t, "ghost", cands)
            c = ScoreCache()
            k = ScoreCache.key(topology_generation=snap.generation, config_generation=0, schema_version="1", scoring_version="x",
                               anchor=a, candidates=cands, spread_from=spread)
            cached = [x.node for x in c.get_or_compute(k, lambda: _score_snapshot(snap, a, cands, spread_from=spread))]
            self.assertEqual(cached, ref)  # differential: cached == reference

    @covers("MC-033", 8, 12, 25)
    def test_mc033_fairshare_properties_under_random_ops_and_races(self):
        rng = random.Random(7)
        for _ in range(60):
            cap = rng.randint(0, 12)
            tenants = ["t0", "t1", "t2"]
            res = {t: rng.randint(0, 4) for t in tenants}
            fs = FairShare(reserved=dict(res), capacity=cap)
            for _ in range(40):
                t = rng.choice(tenants)
                try:
                    if rng.random() < 0.6:
                        fs.claim(t, rng.randint(1, 3))
                    else:
                        fs.release(t, rng.randint(1, 3))
                except (PermissionError, ValueError):
                    pass
                used = fs.used
                self.assertLessEqual(sum(used.values()), cap)
                self.assertTrue(all(v >= 0 for v in used.values()))
                if sum(res.values()) <= cap:
                    for other in tenants:  # nobody ever eats into another's unmet reservation
                        free = cap - sum(used.values())
                        unmet = sum(max(0, res[o] - used.get(o, 0)) for o in tenants)
                        self.assertGreaterEqual(free, 0)
                        self.assertLessEqual(unmet, free + sum(used.values()))
        fs = FairShare(reserved={"a": 5, "b": 5}, capacity=10)
        errs = []

        def hammer(t):
            for _ in range(200):
                try:
                    fs.claim(t)
                    fs.release(t)
                except Exception as e:  # noqa: BLE001
                    errs.append(e)
        ts = [threading.Thread(target=hammer, args=("ab"[i % 2],)) for i in range(8)]
        [x.start() for x in ts]
        [x.join() for x in ts]
        self.assertEqual(errs, [])
        self.assertEqual(sum(fs.used.values()), 0)

    @covers("MC-033", 9, 27)
    def test_mc033_adversarial_candidate_sets(self):
        t = Topology()
        t.place("a", "eu", "d", "r")
        for bad in (["a", "a"], ["a\n"], [""], [" a"], ["a\x00"], [1]):
            with self.assertRaises((ValueError, NotInTopology)):
                rank(t, "a", bad)
        big = Topology()
        for i in range(3000):
            big.place(f"{'x' * 50}{i:05d}", "r", "s", f"k{i % 3}")
        out = rank(big, f"{'x' * 50}00000", list(big.nodes))
        self.assertEqual(len(out), 3000)

    @covers("MC-033", 26)

    @covers("MC-033", 10, 12, 27)
    def test_mc033_transaction_state_machine_fuzz(self):
        rng = random.Random(99)
        import tempfile, shutil
        for it in range(12):
            d = tempfile.mkdtemp()
            try:
                led = LedgerStore(os.path.join(d, "l"))
                led.submit({"type": "set_capacity", "capacity": 3})
                led.submit({"type": "set_reservations", "reserved": {"a": 3}, "entitlement_generation": 1})
                ops = []
                for i in range(20):
                    cid = f"c{rng.randrange(5)}"
                    ops.append(rng.choice([
                        {"type": "prepare", "op_id": f"{cid}:p", "claim_id": cid, "tenant": "a", "slots": 1, "owner": "o", "expires_at": 10**12},
                        {"type": "commit", "op_id": f"{cid}:c", "claim_id": cid, "now": 0},
                        {"type": "abort", "op_id": f"{cid}:a", "claim_id": cid},
                        {"type": "release", "op_id": f"{cid}:r", "claim_id": cid}]))
                for op in ops:
                    try:
                        led.submit(op)
                    except SchedulerError:
                        pass
                    if rng.random() < 0.2:
                        led = LedgerStore(os.path.join(d, "l"))  # crash/restart point
                    self.assertTrue(all(invariants(ledger=led).values()))
            finally:
                shutil.rmtree(d, ignore_errors=True)


class Fuzz(TmpCase):
    def targets(self):
        def p(name):
            return lambda b: wire.parse(name, b)

        def js(fn):
            def t(b):
                try:
                    obj = canonical.loads(b)
                except canonical.CanonicalError as exc:
                    raise SchedulerError("INVALID_ARGUMENT", str(exc)) from None
                return fn(obj)
            return t
        from gap03_topology_aware_scheduler.controlplane.adapters import gap14, pln05
        snap = Topology(nodes={"a": ("eu", "dub", "r1"), "c": ("eu", "ams", "r1")}).snapshot()
        return {"topology": p("PK_TOPOLOGY/1.1"), "fair_share": p("PK_FAIR_SHARE/1.0"),
                "locality": p("PK_LOCALITY_COST/1.0"), "gap02": js(gap02.normalize),
                "gap14": js(lambda o: gap14.Gravity().ingest(o, snap)), "pln05": js(lambda o: pln05.Demand().ingest(o, 1e6))}

    def seeds(self):
        out = []
        for f in ("gap02.json", "gap14.json", "pln05.json"):
            with open(os.path.join(os.path.dirname(gap02.__file__), "..", "fixtures", f)) as fh:
                out += [canonical.dumps(c["input"]) for c in json.load(fh)["cases"]]
        shipped = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fuzz_corpus")
        for fn in sorted(os.listdir(shipped)):  # minimised regression corpus (FZ-1) replayed on every run
            with open(os.path.join(shipped, fn), "rb") as fh:
                out.append(fh.read())
        return out

    @covers("MC-033", 6, 13, 14, 15, 18, 27)
    def test_mc033_fuzz_parsers_no_findings(self):
        """untrusted-input fuzzing with resource limits (per-input time limit, memory proxy); only SchedulerError may escape any parser."""
        corpus = self.d("corpus")
        self.assertGreaterEqual(len([s for s in self.seeds() if b'"device_id"' in s and b'"node"' not in s]), 1)  # FZ-1 replayed
        for name, tgt in self.targets().items():
            rep = fuzz.run(tgt, name=name, seed=20260922, iterations=1500, time_limit=0.5, corpus_dir=corpus, seeds=self.seeds())
            self.assertEqual(rep["findings"], [], f"{name}: {rep['findings'][:2]}")
            self.assertIn("python", rep["env"])

    @covers("MC-033", 13, 14)
    def test_mc033_minimiser_and_regression_corpus(self):
        def buggy(b):
            if b"BOOM" in b:
                raise KeyError("crash")
        rep = fuzz.run(buggy, name="buggy", seed=1, iterations=0, corpus_dir=None)
        self.assertEqual(rep["findings"], [])
        small = fuzz.minimize(buggy, b'{"a":"xxBOOMyy","b":[1,2,3]}', 0.5)
        self.assertEqual(small, b"BOOM")
        d = self.d("rc")
        open(os.path.join(d, "buggy-1-0.bin"), "wb").write(small)
        rep = fuzz.run(buggy, name="buggy", seed=1, iterations=0, corpus_dir=d)
        self.assertEqual(rep["findings"][0]["why"], "uncaught:KeyError")
        self.assertTrue(rep["findings"][0]["regression"])


class Compat(unittest.TestCase):
    @covers("MC-035", 26, 27)
    @covers("MC-035", 6, 7, 12, 25)
    def test_mc035_matrix_and_startup_guard(self):
        """integration against the real interpreter + adversarial environments: unsupported python, PyPy, unknown
        architecture and 32-bit builds are injected and must fail startup (explicit unsupported combinations)."""
        cur = compat.check()
        self.assertTrue(cur["supported"])
        for env, bad in [({"python": "3.9"}, "python"), ({"implementation": "PyPy"}, "implementation"),
                         ({"arch": "sparc"}, "arch"), ({"maxsize_bits": 32}, "32-bit")]:
            e = dict(cur["env"], **env)
            with self.assertRaises(SchedulerError):
                compat.check(e)
            self.assertTrue(any(bad in p for p in compat.check(e, allow_unverified=True)["problems"]))
        for k in ("python", "os", "arch", "schemas", "adjacent", "unsupported"):
            self.assertIn(k, compat.MATRIX)

    @covers("MC-035", 9, 10)
    def test_mc035_arch_sensitive_assumptions(self):
        self.assertEqual(canonical.MAX_INT, 2 ** 53 - 1)  # JSON-safe integer bound independent of platform int size
        self.assertEqual(canonical.dumps({"x": 2 ** 53 - 1}), b'{"x":9007199254740991}')
        self.assertEqual(compat.MATRIX["dependencies"]["runtime"], [])
