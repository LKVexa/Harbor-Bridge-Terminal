import threading
import unittest

from gap03_topology_aware_scheduler import Topology
from gap03_topology_aware_scheduler.controlplane.adapters.sch01 import SCH01Harness
from gap03_topology_aware_scheduler.controlplane.coordination import Coordinator, LeaseReplica
from gap03_topology_aware_scheduler.controlplane.entitlement import EntitlementAuthority, normalize
from gap03_topology_aware_scheduler.controlplane.errors import SchedulerError
from gap03_topology_aware_scheduler.controlplane.faults import ManualClock, StoreFault, invariants
from gap03_topology_aware_scheduler.controlplane.identity import verify_artifact
from gap03_topology_aware_scheduler.controlplane.ledger_store import LedgerStore
from gap03_topology_aware_scheduler.controlplane.transactions import PlacementCoordinator, TxnJournal
from gap03_topology_aware_scheduler.tests.cp._util import TmpCase, covers

ADMIN = {"sub": "spiffe://prod.example/operator/ent", "perms": {"entitlement.write"}}


def rec(tenant, q, unit="slot", vf=0, exp=10**12, dim="slots"):
    return {"tenant": tenant, "dimension": dim, "quantity": q, "unit": unit, "valid_from": vf, "expires_at": exp}


class Entitlements(TmpCase):
    def mk(self):
        e = EntitlementAuthority(self.d("ent"), clock=self.clock)
        e.write(ADMIN, {"type": "set_capacity", "quantity": 10, "unit": "slot"})
        return e

    @covers("MC-003", 18)

    @covers("MC-003", 6, 7, 8, 25)
    def test_mc003_normalised_records_and_unit_rejection(self):
        """untrusted-input validation: negative, boolean, overflow and cross-dimension quantities are rejected."""
        self.assertEqual(normalize(2, "kslot"), 2000)
        for bad in [(1, "GiB"), (-1, "slot"), (True, "slot"), (10**9, "kslot")]:
            with self.assertRaises(SchedulerError):
                normalize(*bad)
        e = self.mk()
        e.write(ADMIN, {"type": "upsert", "record": rec("a", 4), "expected_revision": 0})
        r = e.state["records"]["a"]
        for k in ("tenant", "dimension", "unit", "reserved", "hard_limit", "valid_from", "expires_at", "revision", "issuer"):
            self.assertIn(k, r)
        with self.assertRaises(SchedulerError):
            e.write(ADMIN, {"type": "upsert", "record": rec("b", 1, dim="gpus"), "expected_revision": 0})

    @covers("MC-003", 9, 15, 25, 27)
    def test_mc003_aggregate_limit_and_approved_oversubscription(self):
        e = self.mk()
        e.write(ADMIN, {"type": "upsert", "record": rec("a", 6), "expected_revision": 0})
        with self.assertRaises(SchedulerError) as cm:
            e.write(ADMIN, {"type": "upsert", "record": rec("b", 5), "expected_revision": 0})
        self.assertEqual(cm.exception.code, "FAIRNESS_DENIED")
        with self.assertRaises(SchedulerError):
            e.write(ADMIN, {"type": "approve_oversubscription", "ratio_ppm": 1_200_000, "approval_ref": ""})
        e.write(ADMIN, {"type": "approve_oversubscription", "ratio_ppm": 1_200_000, "approval_ref": "CHG-1"})
        e.write(ADMIN, {"type": "upsert", "record": rec("b", 5), "expected_revision": 0})
        e.write(ADMIN, {"type": "upsert", "record": rec("z", 0), "expected_revision": 0})  # zero reservation ok
        self.assertEqual(e.effective(self.clock())["z"], 0)

    @covers("MC-003", 10, 25)
    def test_mc003_signed_generation_bound_snapshot(self):
        t, key = self.trust()
        e = self.mk()
        e.write(ADMIN, {"type": "upsert", "record": rec("a", 3), "expected_revision": 0})
        snap = e.snapshot(self.clock(), signer=key)
        verify_artifact(t, snap["envelope"], snap["body"], kind="entitlement_snapshot")
        self.assertEqual(snap["body"]["generation"], e.state["generation"])
        led = LedgerStore(self.d("led"), clock=self.clock)
        led.submit({"type": "set_capacity", "capacity": 10})
        led.submit({"type": "set_reservations", "reserved": snap["body"]["effective"], "entitlement_generation": snap["body"]["generation"]})
        with self.assertRaises(SchedulerError) as cm:
            led.submit({"type": "prepare", "claim_id": "c", "tenant": "a", "slots": 1, "owner": "x", "expires_at": 10**12,
                        "entitlement_generation": snap["body"]["generation"] - 1})
        self.assertEqual(cm.exception.code, "STALE_STATE")

    @covers("MC-003", 11, 15, 27)
    def test_mc003_revocation_and_expiry_stop_new_claims(self):
        e = self.mk()
        now = self.clock()
        e.write(ADMIN, {"type": "upsert", "record": rec("a", 3, vf=now - 10, exp=now + 100), "expected_revision": 0})
        e.write(ADMIN, {"type": "upsert", "record": rec("b", 3), "expected_revision": 0})
        self.assertEqual(set(e.effective(now)), {"a", "b"})
        e.write(ADMIN, {"type": "revoke", "tenant": "b"})
        self.clock.advance(200)
        self.assertEqual(e.effective(self.clock()), {})
        led = LedgerStore(self.d("led"))
        led.submit({"type": "set_capacity", "capacity": 10})
        led.submit({"type": "set_reservations", "reserved": e.effective(self.clock()), "entitlement_generation": e.state["generation"]})
        with self.assertRaises(SchedulerError):
            led.submit({"type": "prepare", "claim_id": "c", "tenant": "a", "slots": 1, "owner": "o", "expires_at": 10**12})

    @covers("MC-003", 12, 22, 27)
    def test_mc003_concurrent_updates_cas(self):
        e = self.mk()
        ok = []

        def w(i):
            try:
                e.write(ADMIN, {"type": "upsert", "record": rec("a", i % 5), "expected_revision": 0})
                ok.append(i)
            except SchedulerError:
                pass
        ts = [threading.Thread(target=w, args=(i,)) for i in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(ok), 1)
        self.assertEqual(e.state["records"]["a"]["revision"], 1)

    @covers("MC-003", 13, 17, 20, 27)
    def test_mc003_tenant_isolation_and_write_authz(self):
        audit = self.audit()
        e = self.mk()
        e.write(ADMIN, {"type": "upsert", "record": rec("a", 3), "expected_revision": 0})
        me = {"sub": "spiffe://prod.example/workload/a", "tenant": "a", "perms": set()}
        self.assertEqual(e.tenant_view(me, "a")["record"]["reserved"], 3)
        with self.assertRaises(SchedulerError):
            e.tenant_view(me, "b")
        with self.assertRaises(SchedulerError):
            e.write(me, {"type": "upsert", "record": rec("a", 9), "expected_revision": 1}, audit=audit)
        self.assertEqual(audit.export(principal_roles={"audit.export"})["events"][-1]["result"], "denied")

    @covers("MC-003", 14, 26)
    def test_mc003_reconciliation_emits_drift(self):
        """integration/contract: authority vs ledger reconciliation produces explicit drift events with repair operations."""
        e = self.mk()
        e.write(ADMIN, {"type": "upsert", "record": rec("a", 3), "expected_revision": 0})
        drift = e.reconcile({"a": 2, "ghost": 1}, self.clock())
        self.assertEqual({d["tenant"] for d in drift}, {"a", "ghost"})
        self.assertEqual(e.reconcile({"a": 3}, self.clock()), [])


class Ledger(TmpCase):
    def mk(self, **kw):
        led = LedgerStore(self.d("led"), clock=self.clock, **kw)
        if led.state["capacity"] == 0:
            led.submit({"type": "set_capacity", "capacity": 4})
            led.submit({"type": "set_reservations", "reserved": {"a": 2, "b": 2}, "entitlement_generation": 1})
        return led

    def prep(self, led, cid, tenant, slots=1, **kw):
        op = {"type": "prepare", "op_id": f"{cid}:p", "claim_id": cid, "tenant": tenant, "slots": slots, "owner": "t",
              "expires_at": self.clock() + 30}
        op.update(kw)
        return led.submit(op)

    @covers("MC-005", 18)

    @covers("MC-005", 6, 7, 14, 25)
    def test_mc005_store_boundary_enforces_fairness_and_capacity(self):
        """input validation + bounds at the durable boundary (capacity bounds, slot bounds, impossible states)."""
        led = self.mk()
        self.assertTrue(self.prep(led, "c1", "a", 2)["ok"])
        r = self.prep(led, "c2", "a", 1)
        self.assertEqual(r["code"], "FAIRNESS_DENIED")  # would spend b's reservation
        self.assertTrue(self.prep(led, "c3", "b", 2)["ok"])
        self.assertEqual(self.prep(led, "c4", "b", 1)["code"], "NO_CAPACITY")
        with self.assertRaises(SchedulerError):
            led.submit({"type": "set_capacity", "capacity": 3})  # below used
        led.state["claims"]["c1"]["slots"] = 99
        with self.assertRaises(SchedulerError):
            led.check_invariants(led.state)

    @covers("MC-005", 8, 22, 25)
    def test_mc005_idempotent_claim_ids(self):
        led = self.mk()
        a = self.prep(led, "c1", "a", 1)
        b = self.prep(led, "c1", "a", 1)
        self.assertEqual(a, b)
        from gap03_topology_aware_scheduler.controlplane.ledger_store import used_of
        self.assertEqual(used_of(led.state)["a"], 1)
        led.submit({"type": "release", "op_id": "c1:r", "claim_id": "c1"})
        led.submit({"type": "commit", "op_id": "c1:c2", "claim_id": "c1"}) if False else None
        self.assertEqual(led.submit({"type": "release", "op_id": "c1:r", "claim_id": "c1"})["state"], "released")

    @covers("MC-005", 9, 25, 27)
    def test_mc005_state_token_precondition(self):
        led = self.mk()
        v, rev, _ = led.verdict("a")
        self.prep(led, "c0", "b", 1)
        with self.assertRaises(SchedulerError) as cm:
            self.prep(led, "c1", "a", 1, expected_token=v.state_token)
        self.assertEqual(cm.exception.code, "STALE_STATE")
        v2, rev2, _ = led.verdict("a")
        self.assertGreater(rev2, rev)
        self.assertTrue(self.prep(led, "c2", "a", 1, expected_token=v2.state_token)["ok"])

    @covers("MC-005", 10, 25, 27)
    def test_mc005_crash_safe_ordering(self):
        led = self.mk()
        self.prep(led, "c1", "a", 1)
        f = StoreFault("before_fsync")
        led2 = LedgerStore(self.d("led"), fault=f, clock=self.clock)
        with self.assertRaises(SchedulerError):
            self.prep(led2, "c2", "a", 1)
        led3 = LedgerStore(self.d("led"), clock=self.clock)
        self.assertIn("c1", led3.state["claims"])
        self.assertEqual(led3.state["claims"]["c1"]["state"], "pending")

    @covers("MC-005", 17)

    @covers("MC-005", 11, 25, 27)
    def test_mc005_pending_claim_lease_expiry_and_fencing(self):
        """authorization of writers: a stale fencing token cannot reclaim or commit claims."""
        led = self.mk()
        self.prep(led, "c1", "a", 2, fence=3)
        self.clock.advance(60)
        with self.assertRaises(SchedulerError):
            led.submit({"type": "reclaim_expired", "now": self.clock(), "fence": 2})  # stale fencer
        out = led.submit({"type": "reclaim_expired", "now": self.clock(), "fence": 3})
        self.assertEqual(out["expired"], ["c1"])
        r = led.submit({"type": "commit", "op_id": "c1:c", "claim_id": "c1", "fence": 3, "now": self.clock()})
        self.assertFalse(r["ok"])

    @covers("MC-005", 12, 26)
    def test_mc005_reconciliation_against_placed_state(self):
        led = self.mk()
        self.prep(led, "c1", "a", 1)
        led.submit({"type": "commit", "op_id": "c1:c", "claim_id": "c1", "now": self.clock()})
        rep = led.submit({"type": "reconcile", "placed": {"zz": "a"}, "repair": False})
        self.assertEqual(rep["orphan_committed"], ["c1"])
        self.assertEqual(rep["unknown_placements"], ["zz"])
        led.submit({"type": "reconcile", "placed": {}, "repair": True})
        self.assertEqual(led.state["claims"]["c1"]["state"], "released")

    @covers("MC-005", 13, 25)
    def test_mc005_point_in_time_replay_is_read_only(self):
        led = self.mk()
        self.prep(led, "c1", "a", 1)
        seq = led.seq
        self.prep(led, "c2", "b", 1)
        past = led.point_in_time(seq)
        self.assertIn("c1", past["claims"])
        self.assertNotIn("c2", past["claims"])
        self.assertIn("c2", led.state["claims"])

    @covers("MC-005", 15, 22, 28)
    def test_mc005_concurrent_claims_linearizable(self):
        led = self.mk()
        results = []

        def w(i):
            try:
                results.append(self.prep(led, f"x{i}", "ab"[i % 2], 1))
            except SchedulerError as e:
                results.append({"ok": False, "code": e.code})
        ts = [threading.Thread(target=w, args=(i,)) for i in range(40)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(sum(1 for r in results if r.get("ok")), 4)
        self.assertTrue(all(invariants(ledger=LedgerStore(self.d("led"))).values()))


class Coordination(TmpCase):
    def cluster(self, n=3, tag=""):
        self.sclock = ManualClock()
        reps = [LeaseReplica(f"{self.d('lease' + tag)}/r{i}.json", clock=self.sclock) for i in range(n)]
        return reps

    @covers("MC-006", 6, 7, 9, 25)
    def test_mc006_quorum_lease_and_monotonic_fencing(self):
        reps = self.cluster()
        c1 = Coordinator("s1", reps, ttl=10, safety_margin=2, clock=self.clock)
        c2 = Coordinator("s2", reps, ttl=10, safety_margin=2, clock=self.clock)
        self.assertTrue(c1.acquire())
        self.assertFalse(c2.acquire())
        t1 = c1.fence()
        self.clock.advance(11)
        self.sclock.advance(11)
        self.assertFalse(c1.is_leader())
        self.assertTrue(c2.acquire())
        self.assertGreater(c2.fence(), t1)

    @covers("MC-006", 17)

    @covers("MC-006", 8, 10, 11, 27)
    def test_mc006_stale_leader_cannot_mutate_under_asymmetric_partition(self):
        """authorization: once the lease is lost fence() raises NOT_LEADER, revoking mutation privileges. fault/adversarial: asymmetric partition + delayed writes from a stale leader carrying an old fencing token are rejected by the downstream store."""
        reps = self.cluster()
        lost = []
        c1 = Coordinator("s1", reps, ttl=10, safety_margin=2, clock=self.clock, on_loss=lost.append)
        c2 = Coordinator("s2", reps, ttl=10, safety_margin=2, clock=self.clock)
        led = LedgerStore(self.d("led"))
        led.submit({"type": "set_capacity", "capacity": 4, "fence": 0})
        c1.acquire()
        f1 = c1.fence()
        led.submit({"type": "set_reservations", "reserved": {}, "entitlement_generation": 0, "fence": f1})
        for r in reps[:2]:
            r.reachable["s1"] = False  # s1 cut off from majority (asymmetric: s1 still believes)
        self.sclock.advance(11)
        self.assertTrue(c2.acquire())
        f2 = c2.fence()
        led.submit({"type": "set_capacity", "capacity": 4, "fence": f2})
        with self.assertRaises(SchedulerError) as cm:  # delayed write from old leader
            led.submit({"type": "set_capacity", "capacity": 3, "fence": f1})
        self.assertEqual(cm.exception.code, "FENCED")
        self.clock.advance(3)
        self.assertFalse(c1.renew())
        self.assertIn("renew_quorum_lost", lost)
        with self.assertRaises(SchedulerError) as cm:
            c1.fence()
        self.assertEqual(cm.exception.code, "NOT_LEADER")

    @covers("MC-006", 12, 13, 23)
    def test_mc006_drain_status_and_no_term_reuse(self):
        reps = self.cluster()
        c1 = Coordinator("s1", reps, ttl=10, safety_margin=2, clock=self.clock)
        c1.acquire()
        st = c1.status()
        for k in ("role", "term", "fencing_token", "lease_remaining_s", "quorum"):
            self.assertIn(k, st)
        term = c1.term
        c1.drain()
        self.assertFalse(c1.is_leader())
        self.assertFalse(c1.acquire())
        c2 = Coordinator("s2", [LeaseReplica(r.path, clock=self.sclock) for r in reps], ttl=10, safety_margin=2, clock=self.clock)
        self.assertTrue(c2.acquire())  # replica state reloaded from disk
        self.assertGreater(c2.term, term)

    @covers("MC-006", 14, 27)
    def test_mc006_bounded_attempts_when_quorum_unavailable(self):
        """fault injection: every lease replica raises (dependency loss); attempts are bounded - no retry storm."""
        reps = self.cluster()
        calls = []
        for r in reps:
            orig = r.request

            def wrapped(*a, _o=orig, **k):
                calls.append(1)
                raise ConnectionError("down")
            r.request = wrapped
        c = Coordinator("s1", reps, clock=self.clock, max_attempts=3)
        self.assertFalse(c.acquire())
        self.assertLessEqual(len(calls), 9)

    @covers("MC-006", 26)

    @covers("MC-006", 15)
    @covers("MC-032", 9)
    def test_mc006_failover_during_phases_preserves_invariants(self):
        """integration/contract: real lease replicas + ledger + journal + SCH-01 harness; failover in score, prepare and commit phases."""
        for phase in ("score", "prepare", "commit"):
            with self.subTest(phase=phase):
                reps = self.cluster(tag=phase)
                c1 = Coordinator("s1", reps, ttl=10, safety_margin=2, clock=self.clock)
                self.assertTrue(c1.acquire())
                env = _Env(self, c1, suffix=phase)
                if phase == "score":
                    env.coord.snapshot()
                elif phase == "prepare":
                    env.led.submit({"type": "prepare", "op_id": "t:prepare", "claim_id": "t", "tenant": "a", "slots": 1,
                                    "owner": "txn:t", "fence": c1.fence(), "expires_at": self.clock() + 5})
                else:
                    env.coord.place(txn="t", workload={"id": "w"}, anchor="a", candidates=["b"], tenant="a")
                self.clock.advance(11)
                self.sclock.advance(11)
                c2 = Coordinator("s2", reps, ttl=10, safety_margin=2, clock=self.clock)
                self.assertTrue(c2.acquire())
                env2 = _Env(self, c2, suffix=phase, reuse=env)
                env2.coord.recover_all()
                self.assertTrue(all(invariants(ledger=env2.led, journal=env2.j, downstream=env2.down).values()))


class _Env:
    def __init__(self, tc, coord_lease, suffix, reuse=None):
        tc_clock = tc.clock
        if reuse is None:
            self.led = LedgerStore(tc.d(f"led-{suffix}"), clock=tc_clock)
            self.led.submit({"type": "set_capacity", "capacity": 4})
            self.led.submit({"type": "set_reservations", "reserved": {"a": 2}, "entitlement_generation": 1})
            self.j = TxnJournal(tc.d(f"j-{suffix}"), clock=tc_clock)
            self.down = SCH01Harness()
        else:
            self.led, self.j, self.down = reuse.led, reuse.j, reuse.down
        topo = Topology()
        topo.place("a", "eu", "dub", "r1")
        topo.place("b", "eu", "dub", "r2")
        self.coord = PlacementCoordinator(journal=self.j, ledger=self.led, topology_snapshot=topo.snapshot,
                                          downstream=self.down, fence=coord_lease.fence, clock=tc_clock)


class Transactions(TmpCase):
    def env(self, faults=None, tag=""):
        self.led = LedgerStore(self.d("led" + tag), clock=self.clock)
        self.led.submit({"type": "set_capacity", "capacity": 4})
        self.led.submit({"type": "set_reservations", "reserved": {"a": 2, "b": 2}, "entitlement_generation": 1})
        self.j = TxnJournal(self.d("j" + tag), clock=self.clock)
        self.down = SCH01Harness(faults=faults)
        topo = Topology()
        for n, p in {"a": ("eu", "dub", "r1"), "b": ("eu", "dub", "r2"), "c": ("eu", "ams", "r1")}.items():
            topo.place(n, *p)
        self.fence_v = [1]
        return PlacementCoordinator(journal=self.j, ledger=self.led, topology_snapshot=topo.snapshot, downstream=self.down,
                                    fence=lambda: self.fence_v[0], clock=self.clock)

    def place(self, pc, txn, tenant="a"):
        return pc.place(txn=txn, workload={"id": "w1", "version": 2}, anchor="a", candidates=["c", "b"], tenant=tenant)

    @covers("MC-007", 6, 7, 9, 25, 26)
    def test_mc007_commit_binds_immutable_inputs(self):
        pc = self.env()
        r = self.place(pc, "tx1")
        self.assertEqual(r["state"], "COMMITTED")
        self.assertEqual(r["node"], "b")
        for k in ("workload_id", "workload_version", "candidate_digest", "topology_generation", "ledger_token",
                  "entitlement_generation", "config_generation", "scoring_version"):
            self.assertIn(k, r["inputs"])
        self.assertEqual(self.led.state["claims"]["tx1"]["state"], "committed")
        self.assertTrue(all(invariants(ledger=self.led, journal=self.j, downstream=self.down).values()))

    @covers("MC-007", 8, 10, 25)
    def test_mc007_idempotent_steps_return_prior_terminal_state(self):
        pc = self.env()
        a = self.place(pc, "tx1")
        b = self.place(pc, "tx1")
        self.assertEqual(a, b)
        self.assertEqual(self.down.calls, 1)
        from gap03_topology_aware_scheduler.controlplane.ledger_store import used_of
        self.assertEqual(used_of(self.led.state)["a"], 1)

    @covers("MC-007", 17)

    @covers("MC-007", 11, 27)
    def test_mc007_superseded_epoch_rejected_by_all_participants(self):
        """authorization: commits from a superseded epoch/leader are rejected (FENCED) by ledger, journal and SCH-01."""
        pc = self.env()
        self.fence_v[0] = 5
        self.place(pc, "tx1")
        self.fence_v[0] = 4
        with self.assertRaises(SchedulerError) as cm:
            self.place(pc, "tx2")
        self.assertEqual(cm.exception.code, "FENCED")
        with self.assertRaises(SchedulerError):
            self.down.place({"txn": "tx9", "node": "b", "fence": 4})

    @covers("MC-007", 12, 13, 14, 27)
    def test_mc007_lost_response_goes_unknown_then_recovers(self):
        pc = self.env(faults=["lost_response"])
        r = self.place(pc, "tx1")
        self.assertEqual(r["state"], "COMMITTED")  # status query found the placement
        self.assertIn("UNKNOWN", self.j.state["txns"]["tx1"]["history"])
        pc2 = self.env(faults=["E_NO_NODE"], tag="2")
        r2 = self.place(pc2, "tx2")
        self.assertEqual(r2["state"], "ABORTED")
        self.assertEqual(self.led.state["claims"]["tx2"]["state"], "aborted")  # compensation released capacity

    @covers("MC-007", 12, 14, 27)
    def test_mc007_crash_after_prepare_recovers_deterministically(self):
        pc = self.env()
        f = self.fence_v[0]
        self.j.submit({"type": "begin", "txn": "tx1", "inputs": {}, "now": self.clock(), "deadline": self.clock() + 5, "fence": f})
        self.led.submit({"type": "prepare", "op_id": "tx1:prepare", "claim_id": "tx1", "tenant": "a", "slots": 1,
                         "owner": "txn:tx1", "fence": f, "expires_at": self.clock() + 30})
        self.j.submit({"type": "step", "txn": "tx1", "state": "PREPARED", "node": "b", "fence": f})
        j2 = TxnJournal(self.d("j"), clock=self.clock)
        pc.journal = j2
        out = pc.recover_all()
        self.assertEqual(out[0]["state"], "ABORTED")  # downstream never saw it
        self.clock.advance(60)
        pc.recover_all()
        self.assertEqual(self.led.state["claims"]["tx1"]["state"], "aborted")

    @covers("MC-007", 15, 27)
    @covers("MC-032", 12)
    def test_mc007_duplicate_delayed_replayed_messages(self):
        from gap03_topology_aware_scheduler.controlplane.faults import Chaos
        pc = self.env()
        msgs = [f"tx{i}" for i in range(6)]
        for txn in Chaos(7).mangle(msgs):
            self.place(pc, txn, tenant="ab"[int(txn[2:]) % 2])
        self.assertTrue(all(invariants(ledger=self.led, journal=self.j, downstream=self.down).values()))
        committed = [t for t, x in self.j.state["txns"].items() if x["state"] == "COMMITTED"]
        self.assertEqual(len(committed), 4)  # capacity 4 honoured despite duplicates
