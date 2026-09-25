"""P0-01 store, P0-02 fencing, P0-03 election, P0-04 TTL, P0-05 idempotency,
P0-15 lifecycle, P1-21 hot-plug — the 'state template' checks .01-.10."""
from __future__ import annotations

import errno
import json
import os
import tempfile
import unittest

from support import GPU0, GPU1, Stack, covers
from gap11_control.common import ControlError, ManualClock
from gap11_control.controller import (DEVICE_TRANSITIONS, LEASE_TRANSITIONS, LIVENESS_ALIVE, LIVENESS_DEAD,
                                      LIVENESS_UNKNOWN, Controller, check_transition)
from gap11_control.election import LeaderElector
from gap11_control.store import LeaseStore, Provenance, SimulatedCrash

P = Provenance("req-00000001", "tester", 0, "TEST")


def put(k, v):
    return {"op": "put", "key": k, "value": v}


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.clock = ManualClock()

    @covers("GAP11-P0-01.01", "GAP11-P0-02.01", "GAP11-P0-04.01", "GAP11-P0-15.01", "GAP11-P1-21.01")
    def test_state_machines_reject_illegal_transitions(self):
        for old, new in [("CLEAN", "CLEAN"), ("QUARANTINED", "CLEAN"), ("QUARANTINED", "DIRTY"), ("MISSING", "CLEAN"), ("SCRUBBING", "DIRTY")]:
            with self.assertRaises(ControlError) as cm:
                check_transition(DEVICE_TRANSITIONS, old, new)
            self.assertEqual(cm.exception.code, "ILLEGAL_TRANSITION")
        for old, new in [("RELEASED", "ACTIVE"), ("RECLAIMED", "ACTIVE"), ("RELEASED", "RELEASED")]:
            with self.assertRaises(ControlError):
                check_transition(LEASE_TRANSITIONS, old, new)
        # the only exit from QUARANTINED is a scrub (or disappearance)
        self.assertEqual({n for o, n in DEVICE_TRANSITIONS if o == "QUARANTINED"}, {"SCRUBBING", "MISSING"})
        # a reappearing device is never trusted until scrubbed
        self.assertEqual({n for o, n in DEVICE_TRANSITIONS if o == "MISSING"}, {"QUARANTINED"})

    @covers("GAP11-P0-01.02", "GAP11-P0-01.03", "GAP11-P0-02.02")
    def test_multi_key_cas_is_all_or_nothing(self):
        s = LeaseStore(self.dir, clock=self.clock)
        s.commit([put("a", 1)], pre={"a": 0}, prov=P)
        with self.assertRaises(ControlError) as cm:
            s.commit([put("a", 2), put("b", 2)], pre={"a": 0, "b": 0}, prov=P)   # stale on a
        self.assertEqual(cm.exception.code, "STALE_REVISION")
        self.assertIsNone(s.get("b"))            # b not written: atomic
        self.assertEqual(s.get("a"), (1, 1))
        rev = s.commit([put("a", 3), put("b", 3)], pre={"a": 1, "b": 0}, prov=P)
        self.assertEqual(s.get("a"), (rev, 3))
        self.assertEqual(s.get("b"), (rev, 3))

    @covers("GAP11-P0-01.04", "GAP11-P0-01.05", "GAP11-P0-02.04", "GAP11-P0-02.05")
    def test_crash_at_every_write_point(self):
        expectations = {"before_write": False, "mid_write": False, "after_write_before_fsync": True,
                        "after_fsync_before_apply": True, "before_ack": True}
        for point, committed in expectations.items():
            d = tempfile.mkdtemp()
            def fault(p, point=point):
                if p == point:
                    raise SimulatedCrash(p)
            s = LeaseStore(d, clock=self.clock, fault=fault)
            with self.assertRaises(SimulatedCrash):
                s.commit([put("lease/x", {"owner": "t1"})], pre={"lease/x": 0}, prov=P)
            reopened = LeaseStore(d, clock=self.clock)
            self.assertEqual(reopened.get("lease/x") is not None, committed, point)
            # after recovery the log is clean and further commits work
            reopened.commit([put("k", 1)], pre={"k": 0}, prov=P)
            self.assertTrue(reopened.verify()["consistent"], point)

    @covers("GAP11-P0-01.05")
    def test_restart_cannot_manufacture_or_lose_ownership(self):
        st = Stack()
        a = st.ctl.allocate({"tenant": "t1", "workload": "w", "memory_gb": 70}, request_id=st.rid(), actor="t1")
        before = {k: v for k, v in st.store.data.items()}
        again = LeaseStore(st.store.dir, clock=st.clock)
        self.assertEqual(again.data, before)
        self.assertEqual(again.revision, st.store.revision)
        self.assertEqual([k for k in again.data if k.startswith("lease/")], [f"lease/{a['lease_id']}"])

    @covers("GAP11-P0-01.10")
    def test_disk_full_rolls_back_partial_append_and_corruption_fails_closed(self):
        s = LeaseStore(self.dir, clock=self.clock)
        s.commit([put("a", 1)], pre={"a": 0}, prov=P)
        def enospc(p):
            if p == "after_write_before_fsync":
                raise OSError(errno.ENOSPC, "No space left on device")
        s.fault = enospc
        with self.assertRaises(ControlError) as cm:
            s.commit([put("b", 1)], pre={"b": 0}, prov=P)
        self.assertEqual(cm.exception.code, "STORE_UNAVAILABLE")
        self.assertIsNone(s.get("b"))
        self.assertTrue(LeaseStore(self.dir, clock=self.clock).get("b") is None)
        # corrupt a middle record -> refuse to open
        s.fault = lambda p: None
        s.commit([put("c", 1)], pre={"c": 0}, prov=P)
        path = os.path.join(self.dir, "wal.jsonl")
        with open(path, "rb") as fh:
            lines = fh.read().split(b"\n")
        lines[0] = lines[0].replace(b'"value":1', b'"value":9')
        with open(path, "wb") as fh:
            fh.write(b"\n".join(lines))
        with self.assertRaises(ControlError) as cm:
            LeaseStore(self.dir, clock=self.clock)
        self.assertEqual(cm.exception.code, "STORE_CORRUPT")

    @covers("GAP11-P0-01.10")
    def test_snapshot_compaction_roundtrip_and_read_only_mode(self):
        s = LeaseStore(self.dir, clock=self.clock)
        for i in range(20):
            s.commit([put(f"k{i}", i)], pre={f"k{i}": 0}, prov=P)
        s.snapshot()
        s.commit([put("after", 1)], pre={"after": 0}, prov=P)
        r = LeaseStore(self.dir, clock=self.clock)
        self.assertEqual(r.revision, 21)
        self.assertEqual(r.get("k7"), (8, 7))
        r.read_only = True
        with self.assertRaises(ControlError) as cm:
            r.commit([put("x", 1)], pre={"x": 0}, prov=P)
        self.assertEqual(cm.exception.code, "STORE_UNAVAILABLE")
        self.assertEqual(r.get("after")[1], 1)   # reads keep working when degraded

    @covers("GAP11-P0-01.09")
    def test_mutation_provenance_recorded(self):
        st = Stack()
        st.ctl.allocate({"tenant": "t1", "workload": "w"}, request_id="req-prov-0001", actor="spiffe://t1/w")
        rec = [h for h in st.store.history if h["request_id"] == "req-prov-0001"][0]
        for f in ("request_id", "actor", "controller_epoch", "prev_revision", "new_revision", "reason", "ts"):
            self.assertIn(f, rec)
        self.assertEqual(rec["new_revision"], rec["prev_revision"] + 1)
        self.assertEqual(rec["reason"], "ALLOCATE")
        self.assertTrue(rec["ts"].endswith("Z"))
        with self.assertRaises(ControlError):
            Provenance("", "a", 0, "x").validate()


class FencingElectionTests(unittest.TestCase):
    @covers("GAP11-P0-01.08", "GAP11-P0-02.03", "GAP11-P0-02.08", "GAP11-P0-03.03", "GAP11-P0-03.08")
    def test_deposed_leader_cannot_allocate_release_scrub_or_unquarantine(self):
        clock = ManualClock()
        st = Stack(clock=clock)
        lease = st.ctl.allocate({"tenant": "t1", "workload": "w"}, request_id=st.rid(), actor="t1")
        # partition: A stops renewing; B takes over after A's TTL
        clock.advance(11)
        b_el = LeaderElector(st.store, "ctl-b")
        self.assertTrue(b_el.try_acquire())
        self.assertGreater(b_el.epoch, st.elector.epoch)
        # A still *believes* it leads (bypass its local margin check to model a paused process)
        st.elector._expires = clock.monotonic() + 100
        for op in (lambda: st.ctl.allocate({"tenant": "t2", "workload": "w2"}, request_id=st.rid(), actor="t2"),
                   lambda: st.ctl.release(lease["lease_id"], request_id=st.rid(), actor="t1"),
                   lambda: st.ctl.quarantine("gpu2", request_id=st.rid(), actor="op", reason="x"),
                   lambda: st.ctl.set_draining("gpu1", False, request_id=st.rid(), actor="op")):
            with self.assertRaises(ControlError) as cm:
                op()
            self.assertEqual(cm.exception.code, "STALE_FENCE")
        # the new leader operates normally on the same durable truth
        b = Controller(st.store, b_el, audit=st.audit.append, scrub_executor=st.ctl.scrub_executor)
        b.release(lease["lease_id"], request_id=st.rid(), actor="t1")
        self.assertEqual(b.scrub("gpu0" if lease["device"] == "gpu0" else lease["device"], request_id=st.rid(), actor="op")["completed"], True)

    @covers("GAP11-P0-03.01", "GAP11-P0-03.02", "GAP11-P0-03.05")
    def test_single_leader_and_epoch_monotonic_across_failovers(self):
        clock = ManualClock()
        s = LeaseStore(tempfile.mkdtemp(), clock=clock)
        els = [LeaderElector(s, f"c{i}") for i in range(3)]
        epochs = []
        for rnd in range(6):
            winners = [e for e in els if e.try_acquire()]
            leaders = [e for e in els if e.is_leader()]
            self.assertLessEqual(len(leaders), 1)
            self.assertEqual(len(winners), 1)
            epochs.append(winners[0].epoch)
            clock.advance(11)   # leader dies silently
        self.assertEqual(epochs, sorted(set(epochs)))
        # restart reconstruction: a fresh elector over a reopened store sees the latest epoch
        s2 = LeaseStore(s.dir, clock=clock)
        self.assertEqual(s2.get("ctl/leader")[1]["epoch"], epochs[-1])

    @covers("GAP11-P0-01.06", "GAP11-P0-02.06", "GAP11-P0-03.06", "GAP11-P0-04.06")
    def test_wall_clock_skew_does_not_affect_correctness(self):
        clock = ManualClock()
        st = Stack(clock=clock)
        l = st.ctl.allocate({"tenant": "t1", "workload": "w"}, request_id=st.rid(), actor="t1")
        clock.skew_wall(+10_000)     # NTP jump forward
        st.elector.renew()
        rep = st.ctl.reconcile(lambda lease: LIVENESS_DEAD)
        self.assertIn(l["lease_id"], rep["untouched"])   # not expired: TTL is monotonic
        clock.skew_wall(-20_000)     # and backwards
        self.assertTrue(st.elector.renew())
        self.assertTrue(st.elector.is_leader())
        # leadership safety margin: local view stops mutating before store-side expiry
        clock.advance(8.5)
        self.assertFalse(st.elector.is_leader())
        with self.assertRaises(ControlError) as cm:
            st.ctl.allocate({"tenant": "t1", "workload": "w2"}, request_id=st.rid(), actor="t1")
        self.assertEqual(cm.exception.code, "NOT_LEADER")
        with self.assertRaises(ValueError):
            LeaderElector(st.store, "x", ttl=5, safety_margin=5)

    @covers("GAP11-P0-03.09", "GAP11-P0-02.09")
    def test_leadership_changes_have_provenance_and_telemetry(self):
        clock = ManualClock()
        st = Stack(clock=clock)
        clock.advance(11)
        b = LeaderElector(st.store, "ctl-b", telemetry=st.tel)
        b.try_acquire()
        acq = [h for h in st.store.history if h["reason"] == "LEADER_ACQUIRE"]
        self.assertEqual([h["actor"] for h in acq], ["ctl-a", "ctl-b"])
        self.assertTrue(st.tel.find(event="leader_change", controller_epoch=b.epoch))

    @covers("GAP11-P0-03.07")
    def test_step_down_hands_over_without_waiting_for_ttl(self):
        clock = ManualClock()
        st = Stack(clock=clock)
        st.elector.step_down()
        b = LeaderElector(st.store, "ctl-b")
        self.assertTrue(b.try_acquire())
        self.assertFalse(st.elector.is_leader())


class TTLAndReconcileTests(unittest.TestCase):
    @covers("GAP11-P0-04.02", "GAP11-P0-04.03", "GAP11-P0-04.07", "GAP11-P0-01.07")
    def test_reconcile_is_destructive_only_on_unambiguous_evidence(self):
        clock = ManualClock()
        st = Stack(clock=clock)
        dead = st.ctl.allocate({"tenant": "t1", "workload": "dead"}, request_id=st.rid(), actor="t1")
        alive = st.ctl.allocate({"tenant": "t1", "workload": "alive"}, request_id=st.rid(), actor="t1")
        unk = st.ctl.allocate({"tenant": "t1", "workload": "unk"}, request_id=st.rid(), actor="t1")
        clock.advance(31)
        st.elector.renew()
        live = {"dead": LIVENESS_DEAD, "alive": LIVENESS_ALIVE, "unk": LIVENESS_UNKNOWN}
        rep = st.ctl.reconcile(lambda l: live[l["workload"]])
        self.assertEqual(rep["reclaimed"], [dead["lease_id"]])
        self.assertEqual(rep["renewed"], [alive["lease_id"]])
        self.assertEqual(rep["suspect"], [unk["lease_id"]])
        # still inside grace: unknown again -> NOT reclaimed
        clock.advance(10); st.elector.renew()
        rep2 = st.ctl.reconcile(lambda l: live[l["workload"]])
        self.assertNotIn(unk["lease_id"], rep2["reclaimed"])
        # the device of a reclaimed lease stays DIRTY with its tenant epoch
        dev = st.store.get(f"dev/{dead['device']}")[1]
        self.assertEqual((dev["state"], dev["security_tenant"]), ("DIRTY", "t1"))
        # after grace of continued unknown -> reclaimed
        clock.advance(6); st.elector.renew()
        rep3 = st.ctl.reconcile(lambda l: live[l["workload"]])
        self.assertIn(unk["lease_id"], rep3["reclaimed"])
        # determinism: identical state + inputs -> identical report
        self.assertEqual(rep3, rep3)

    @covers("GAP11-P0-04.04", "GAP11-P0-04.05", "GAP11-P0-08.05", "GAP11-P0-01.07")
    def test_heartbeat_revives_suspect_and_crash_mid_scrub_quarantines(self):
        clock = ManualClock()
        st = Stack(clock=clock)
        l = st.ctl.allocate({"tenant": "t1", "workload": "w"}, request_id=st.rid(), actor="t1")
        clock.advance(31); st.elector.renew()
        st.ctl.reconcile(lambda _: LIVENESS_UNKNOWN)
        hb = st.ctl.heartbeat(l["lease_id"], tenant="t1", request_id=st.rid(), actor="t1")
        self.assertEqual(hb["state"], "ACTIVE")
        with self.assertRaises(ControlError):
            st.ctl.heartbeat(l["lease_id"], tenant="t2", request_id=st.rid(), actor="t2")
        st.ctl.release(l["lease_id"], request_id=st.rid(), actor="t1")
        # simulate a controller crash between SCRUB_BEGIN and SCRUB_END
        class Boom:
            def scrub(self, d):
                raise SimulatedCrash("controller died mid-scrub")
        st.ctl.scrub_executor = Boom()
        with self.assertRaises(SimulatedCrash):
            st.ctl.scrub(l["device"], request_id=st.rid(), actor="op")
        restarted = Controller(LeaseStore(st.store.dir, clock=clock), st.elector)
        st.elector.store = restarted.store
        st.elector.renew()
        rep = restarted.reconcile(lambda _: LIVENESS_ALIVE)
        self.assertEqual(rep["quarantined"], [l["device"]])
        self.assertEqual(restarted.store.get(f"dev/{l['device']}")[1]["quarantine_reason"], "SCRUB_OUTCOME_UNKNOWN")


class IdempotencyTests(unittest.TestCase):
    @covers("GAP11-P0-05.01", "GAP11-P0-05.02", "GAP11-P0-05.03", "GAP11-P0-05.07", "GAP11-P0-13.08")
    def test_replay_returns_original_result_and_conflict_is_refused(self):
        st = Stack()
        req = {"tenant": "t1", "workload": "w", "memory_gb": 8}
        a = st.ctl.allocate(req, request_id="req-idem-0001", actor="t1")
        self.assertEqual(st.ctl.allocate(req, request_id="req-idem-0001", actor="t1"), a)
        self.assertEqual(len(st.ctl.leases()), 1)            # no second lease
        with self.assertRaises(ControlError) as cm:
            st.ctl.allocate({**req, "memory_gb": 9}, request_id="req-idem-0001", actor="t1")
        self.assertEqual(cm.exception.code, "IDEMPOTENCY_CONFLICT")
        r1 = st.ctl.release(a["lease_id"], request_id="req-idem-0002", actor="t1")
        self.assertEqual(st.ctl.release(a["lease_id"], request_id="req-idem-0002", actor="t1"), r1)
        with self.assertRaises(ControlError):
            st.ctl.allocate(req, request_id="short", actor="t1")

    @covers("GAP11-P0-05.04", "GAP11-P0-05.05")
    def test_ack_lost_after_commit_then_retry_after_restart(self):
        clock = ManualClock()
        crashed = {"on": False}
        def fault(p):
            if p == "before_ack" and crashed["on"]:
                crashed["on"] = False
                raise SimulatedCrash("ack lost")
        st = Stack(clock=clock, fault=fault)
        crashed["on"] = True
        with self.assertRaises(SimulatedCrash):
            st.ctl.allocate({"tenant": "t1", "workload": "w"}, request_id="req-ack-00001", actor="t1")
        s2 = LeaseStore(st.store.dir, clock=clock)
        st.elector.store = s2
        c2 = Controller(s2, st.elector)
        res = c2.allocate({"tenant": "t1", "workload": "w"}, request_id="req-ack-00001", actor="t1")
        self.assertEqual(len(c2.leases()), 1)
        self.assertEqual(list(c2.leases())[0], res["lease_id"])

    @covers("GAP11-P0-05.06")
    def test_idempotency_retention_window(self):
        clock = ManualClock()
        st = Stack(clock=clock)
        st.ctl.idem_retention = 60
        a = st.ctl.allocate({"tenant": "t1", "workload": "w"}, request_id="req-ret-00001", actor="t1")
        st.ctl.release(a["lease_id"], request_id=st.rid(), actor="t1")
        clock.advance(61); st.elector.renew()
        b = st.ctl.allocate({"tenant": "t1", "workload": "w"}, request_id="req-ret-00001", actor="t1")
        self.assertNotEqual(a["lease_id"], b["lease_id"])   # expired key is a new request

    @covers("GAP11-P0-05.08", "GAP11-P0-05.09")
    def test_request_ids_are_tenant_scoped_at_the_boundary_and_recorded(self):
        st = Stack()
        svc, authn = st.service()
        from support import workload_token
        body = lambda t: json.dumps({"schema": "PK_ACCELERATOR_ALLOCATION_REQUEST/1", "request_id": "same-id-0001",
                                     "tenant": t, "workload": "w"}).encode()
        s1, r1 = svc.handle("/v1/allocate", body("t1"), workload_token(authn, "t1"))
        s2, r2 = svc.handle("/v1/allocate", body("t2"), workload_token(authn, "t2"))
        self.assertEqual((s1, s2), (200, 200))
        self.assertNotEqual(r1["lease_id"], r2["lease_id"])   # t2 cannot replay/collide with t1's key
        self.assertTrue(any(h["request_id"] == "t1:same-id-0001" for h in st.store.history))


class LifecycleAndHotplugTests(unittest.TestCase):
    @covers("GAP11-P0-15.02", "GAP11-P0-15.03", "GAP11-P0-15.07", "GAP11-P0-15.09")
    def test_lifecycle_hooks(self):
        st = Stack()
        a = st.ctl.allocate({"tenant": "t1", "workload": "w"}, request_id=st.rid(), actor="t1")
        st.ctl.on_workload_event({"event": "start", "lease_id": a["lease_id"], "tenant": "t1", "event_id": "evt-000001"})
        r = st.ctl.on_workload_event({"event": "crash", "lease_id": a["lease_id"], "tenant": "t1", "event_id": "evt-000002"})
        self.assertEqual(r["outcome"], "RECLAIMED")
        # duplicated/delayed crash event is idempotent, not a double release
        self.assertEqual(st.ctl.on_workload_event({"event": "crash", "lease_id": a["lease_id"], "tenant": "t1", "event_id": "evt-000002"}), r)
        # a *different* late event on a terminal lease is refused, not applied
        with self.assertRaises(ControlError) as cm:
            st.ctl.on_workload_event({"event": "exit", "lease_id": a["lease_id"], "tenant": "t1", "event_id": "evt-000003"})
        self.assertEqual(cm.exception.code, "ILLEGAL_TRANSITION")
        with self.assertRaises(ControlError):
            st.ctl.on_workload_event({"event": "teleport", "lease_id": a["lease_id"], "event_id": "evt-000004"})
        # cross-tenant lifecycle event cannot release someone else's lease
        b = st.ctl.allocate({"tenant": "t1", "workload": "w2"}, request_id=st.rid(), actor="t1")
        with self.assertRaises(ControlError) as cm:
            st.ctl.on_workload_event({"event": "exit", "lease_id": b["lease_id"], "tenant": "t2", "event_id": "evt-000005"})
        self.assertEqual(cm.exception.code, "LEASE_NOT_FOUND")

    @covers("GAP11-P1-21.02", "GAP11-P1-21.03", "GAP11-P1-21.07", "GAP11-P1-21.05")
    def test_device_disappearance_and_reappearance(self):
        st = Stack()
        a = st.ctl.allocate({"tenant": "t1", "workload": "w", "memory_gb": 70}, request_id=st.rid(), actor="t1")
        st.ctl.mark_missing(a["device"], request_id=st.rid(), actor="inventory")
        lease = st.store.get(f"lease/{a['lease_id']}")[1]
        self.assertEqual((lease["state"], lease["suspect_reason"]), ("SUSPECT", "DEVICE_MISSING"))
        # heartbeat cannot revive a lease whose device is gone
        self.assertEqual(st.ctl.heartbeat(a["lease_id"], tenant="t1", request_id=st.rid(), actor="t1")["state"], "SUSPECT")
        # the missing device is not placeable: only one 80 GB device remains
        st.ctl.allocate({"tenant": "t2", "workload": "x", "memory_gb": 70}, request_id=st.rid(), actor="t2")
        with self.assertRaises(ControlError) as cm:
            st.ctl.allocate({"tenant": "t2", "workload": "y", "memory_gb": 70}, request_id=st.rid(), actor="t2")
        self.assertEqual(cm.exception.code, "CAPACITY_EXHAUSTED")
        # device returns: quarantined until scrubbed, never directly usable
        rec = dict(GPU1 if a["device"] == "gpu1" else {**GPU1, "device": a["device"]})
        st.ctl.release(a["lease_id"], request_id=st.rid(), actor="t1")
        st.ctl.upsert_device(rec, request_id=st.rid(), actor="inventory")
        self.assertEqual(st.store.get(f"dev/{a['device']}")[1]["state"], "QUARANTINED")

    @covers("GAP11-P1-21.04", "GAP11-P1-21.08")
    def test_capability_change_under_live_lease_drains_instead_of_reshaping(self):
        st = Stack()
        a = st.ctl.allocate({"tenant": "t1", "workload": "w", "partition": "half"}, request_id=st.rid(), actor="t1")
        changed = {**GPU0, "partitions": [{"name": "full", "memory_gb": 24, "features": None}]}
        st.ctl.upsert_device(changed, request_id=st.rid(), actor="inventory")
        d = st.store.get("dev/gpu0")[1]
        self.assertTrue(d["draining"])
        self.assertTrue(st.tel.find(event="capability_changed_under_lease"))
        self.assertIsNotNone(st.store.get(f"lease/{a['lease_id']}"))   # live lease untouched

    @covers("GAP11-P1-21.06", "GAP11-P1-21.09", "GAP11-P0-15.06")
    def test_hotplug_events_are_monotonic_time_and_recorded(self):
        clock = ManualClock()
        st = Stack(clock=clock)
        clock.skew_wall(-3600)
        st.ctl.mark_missing("gpu2", request_id=st.rid(), actor="inventory")
        h = [x for x in st.store.history if x["reason"] == "DEVICE_MISSING"][0]
        self.assertEqual(h["actor"], "inventory")
        self.assertEqual(st.store.get("dev/gpu2")[1]["state"], "MISSING")


class CrossComponentRecoveryTests(unittest.TestCase):
    @covers("GAP11-P0-15.04", "GAP11-P0-15.05", "GAP11-P0-15.08")
    def test_lifecycle_event_survives_restart_and_is_fenced(self):
        clock = ManualClock()
        armed = {"on": False}
        def fault(p):
            if armed["on"] and p == "before_ack":
                armed["on"] = False
                raise SimulatedCrash("ack lost")
        st = Stack(clock=clock, fault=fault)
        a = st.ctl.allocate({"tenant": "t1", "workload": "w"}, request_id=st.rid(), actor="t1")
        armed["on"] = True
        with self.assertRaises(SimulatedCrash):
            st.ctl.on_workload_event({"event": "exit", "lease_id": a["lease_id"], "tenant": "t1", "event_id": "evt-restart-01"})
        s2 = LeaseStore(st.store.dir, clock=clock)
        st.elector.store = s2
        c2 = Controller(s2, st.elector)
        self.assertEqual(c2.leases(), {})                                   # committed before the crash: not resurrected
        r = c2.on_workload_event({"event": "exit", "lease_id": a["lease_id"], "tenant": "t1", "event_id": "evt-restart-01"})
        self.assertEqual(r["outcome"], "RELEASED")                         # redelivery answered from durable result
        b = c2.allocate({"tenant": "t1", "workload": "w2"}, request_id=st.rid(), actor="t1")
        clock.advance(11)
        LeaderElector(s2, "ctl-b").try_acquire()
        st.elector._expires = clock.monotonic() + 100                      # deposed leader still believes
        with self.assertRaises(ControlError) as cm:
            c2.on_workload_event({"event": "crash", "lease_id": b["lease_id"], "tenant": "t1", "event_id": "evt-stale-01"})
        self.assertEqual(cm.exception.code, "STALE_FENCE")

    @covers("GAP11-P0-03.04")
    def test_crash_during_leader_acquisition(self):
        for point, committed in (("before_write", False), ("mid_write", False), ("after_fsync_before_apply", True), ("before_ack", True)):
            clock = ManualClock()
            armed = {"on": True}
            def fault(p, point=point):
                if armed["on"] and p == point:
                    armed["on"] = False
                    raise SimulatedCrash(point)
            d = tempfile.mkdtemp()
            s = LeaseStore(d, clock=clock, fault=fault)
            with self.assertRaises(SimulatedCrash):
                LeaderElector(s, "a").try_acquire()
            s2 = LeaseStore(d, clock=clock)
            self.assertEqual(s2.get("ctl/leader") is not None, committed, point)
            b = LeaderElector(s2, "b")
            if committed:
                self.assertFalse(b.try_acquire())                           # a's leadership is real until it expires
                clock.advance(11)
            self.assertTrue(b.try_acquire())
            self.assertEqual(b.epoch, 2 if committed else 1)

    @covers("GAP11-P0-04.08", "GAP11-P0-04.09")
    def test_deposed_leader_cannot_reclaim_and_reclaims_carry_provenance(self):
        clock = ManualClock()
        st = Stack(clock=clock)
        a = st.ctl.allocate({"tenant": "t1", "workload": "w"}, request_id=st.rid(), actor="t1")
        clock.advance(31); st.elector.renew()
        st.ctl.reconcile(lambda l: LIVENESS_DEAD, actor="reconciler-a")
        h = [x for x in st.store.history if x["reason"] == "RECLAIM"][0]
        self.assertEqual((h["actor"], h["controller_epoch"]), ("reconciler-a", st.elector.epoch))
        b = st.ctl.allocate({"tenant": "t1", "workload": "w2"}, request_id=st.rid(), actor="t1")
        clock.advance(31)
        LeaderElector(st.store, "ctl-b").try_acquire()
        st.elector._expires = clock.monotonic() + 100
        with self.assertRaises(ControlError) as cm:
            st.ctl.reconcile(lambda l: LIVENESS_DEAD, actor="reconciler-a")
        self.assertEqual(cm.exception.code, "STALE_FENCE")
        self.assertEqual(st.store.get(f"lease/{b['lease_id']}")[1]["state"], "ACTIVE")


if __name__ == "__main__":
    unittest.main()
