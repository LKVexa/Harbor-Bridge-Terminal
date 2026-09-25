"""Store/OCC (4, 6), informer (2), work queue (3), lease/fencing (5),
journal/idempotency/audit (21, 22, 50)."""
from __future__ import annotations

import os
import tempfile
import threading
import unittest

import _support  # noqa: F401
from _support import FakeClock
from inv04_current_orchestration.runtime.errors import (AlreadyExists, Conflict, FencedOut, Gone, IdempotencyMismatch,
                                                        JournalCorrupt, NotLeader, StaleCache)
from inv04_current_orchestration.runtime.journal import AuditTrail, IdempotencyRegistry, Journal
from inv04_current_orchestration.runtime.lease import FencingGuard, LeaderElector
from inv04_current_orchestration.runtime.store import Informer, VersionedStore
from inv04_current_orchestration.runtime.workqueue import WorkQueue, run_workers


class StoreTest(unittest.TestCase):
    def test_cas_rejects_stale_writer_and_bumps_generation_only_on_spec_change(self):
        s = VersionedStore()
        r = s.create("Deployment", "ns/web", {"replicas": 3})
        r2 = s.update("Deployment", "ns/web", {"replicas": 4}, expected_rv=r.resource_version)
        self.assertEqual(r2.generation, 2)
        with self.assertRaises(Conflict):
            s.update("Deployment", "ns/web", {"replicas": 5}, expected_rv=r.resource_version)
        r3 = s.update_status("Deployment", "ns/web", {"ready": 4}, expected_rv=r2.resource_version, observed_generation=2)
        self.assertEqual((r3.generation, r3.observed_generation), (2, 2))
        with self.assertRaises(StaleCache):
            s.update_status("Deployment", "ns/web", {}, expected_rv=r3.resource_version, observed_generation=9)
        with self.assertRaises(AlreadyExists):
            s.create("Deployment", "ns/web", {})

    def test_uid_precondition_detects_recreated_object(self):
        s = VersionedStore()
        r = s.create("Pod", "ns/a", {})
        s.delete("Pod", "ns/a")
        r2 = s.create("Pod", "ns/a", {})
        self.assertNotEqual(r.uid, r2.uid)
        with self.assertRaises(Conflict):
            s.update("Pod", "ns/a", {"x": 1}, expected_rv=r2.resource_version, uid=r.uid)

    def test_durable_store_survives_restart_and_torn_tail(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "desired.jsonl")
            s = VersionedStore(path=path)
            r = s.create("Deployment", "ns/web", {"replicas": 3})
            s.update("Deployment", "ns/web", {"replicas": 5}, expected_rv=r.resource_version)
            with open(path, "a") as fh:
                fh.write('{"op": "put", "kind": "Depl')  # crash mid-write
            s2 = VersionedStore(path=path)
            rec = s2.get("Deployment", "ns/web")
            self.assertEqual(rec.spec, {"replicas": 5})
            self.assertEqual(rec.generation, 2)
            self.assertEqual(s2.resource_version, s.resource_version)


class InformerTest(unittest.TestCase):
    def test_watch_applies_events_ignores_duplicates_and_bookmarks(self):
        s = VersionedStore()
        seen = []
        inf = Informer(s, "Pod", on_event=lambda t, r: seen.append((t, r.key)))
        self.assertFalse(inf.has_synced())
        s.create("Pod", "a", {})
        inf.poll()
        self.assertTrue(inf.has_synced())
        s.create("Pod", "b", {})
        s.delete("Pod", "a")
        inf.poll()
        self.assertEqual(sorted(inf.cache), ["b"])
        self.assertEqual(inf.poll(), 0)  # replay yields nothing new
        inf.require_fresh(0)

    def test_expired_watch_relists_and_synthesizes_tombstones(self):
        s = VersionedStore(window=3)
        inf = Informer(s, "Pod")
        s.create("Pod", "a", {})
        inf.poll()
        s.delete("Pod", "a")
        for i in range(6):
            s.create("Pod", f"x{i}", {})
        with self.assertRaises(StaleCache):
            inf.require_fresh(2)
        with self.assertRaises(Gone):
            s.events_since(inf.last_rv, "Pod")
        inf.poll()
        self.assertEqual(inf.relists, 2)
        self.assertEqual([t.key for t in inf.tombstones], ["a"])
        self.assertNotIn("a", inf.cache)
        self.assertEqual(len(inf.cache), 6)


class WorkQueueTest(unittest.TestCase):
    def test_dedupe_dirty_processing_and_shutdown(self):
        q = WorkQueue()
        q.add("a"); q.add("a"); q.add("b")
        self.assertEqual(q.depth(), 2)
        k = q.get(timeout=0)
        self.assertEqual(k, "a")
        q.add("a")  # re-added while processing -> dirty, not queued twice
        self.assertEqual(q.depth(), 1)
        q.done("a")
        self.assertEqual(q.depth(), 2)
        q.shutdown()
        self.assertFalse(q.add("c"))
        self.assertEqual({q.get(), q.get()}, {"a", "b"})
        self.assertIsNone(q.get())

    def test_backpressure_sheds_when_full(self):
        q = WorkQueue(max_depth=2)
        self.assertTrue(q.add(1)); self.assertTrue(q.add(2))
        self.assertFalse(q.add(3))
        self.assertEqual(q.dropped, 1)

    def test_rate_limited_retries_are_bounded(self):
        clock = FakeClock()
        q = WorkQueue(clock=clock, max_retries=2)
        self.assertTrue(q.add_rate_limited("k"))
        self.assertTrue(q.add_rate_limited("k"))
        self.assertFalse(q.add_rate_limited("k"))
        clock.advance(100)
        self.assertEqual(q.get(timeout=0), "k")
        q.forget("k")
        self.assertEqual(q.num_requeues("k"), 0)

    def test_no_key_processed_concurrently_by_two_workers(self):
        q = WorkQueue()
        active: dict[str, int] = {}
        violations = []
        lock = threading.Lock()
        done = threading.Event()
        count = [0]

        def handler(key):
            with lock:
                active[key] = active.get(key, 0) + 1
                if active[key] > 1:
                    violations.append(key)
            for _ in range(200):
                pass
            with lock:
                active[key] -= 1
                count[0] += 1
                if count[0] >= 5:
                    done.set()

        threads = run_workers(q, handler, workers=4)
        for i in range(400):
            q.add(f"k{i % 5}")
        done.wait(5)
        import time as _t
        end = _t.monotonic() + 5
        while (q.depth() or q.in_flight()) and _t.monotonic() < end:
            _t.sleep(0.01)
        q.shutdown()
        for t in threads:
            t.join(5)
        self.assertEqual(violations, [])


class LeaseTest(unittest.TestCase):
    def test_single_leader_takeover_after_expiry_and_fencing(self):
        clock = FakeClock()
        store = VersionedStore()
        a = LeaderElector(store, "inv04", "a", lease_seconds=15, renew_deadline=10, clock=clock)
        b = LeaderElector(store, "inv04", "b", lease_seconds=15, renew_deadline=10, clock=clock)
        self.assertTrue(a.try_acquire_or_renew())
        self.assertFalse(b.try_acquire_or_renew())
        token_a = a.require_leader()
        clock.advance(16)  # a paused past its lease
        self.assertFalse(a.is_leader())
        with self.assertRaises(NotLeader):
            a.require_leader()
        self.assertTrue(b.try_acquire_or_renew())
        token_b = b.require_leader()
        self.assertGreater(token_b, token_a)
        guard = FencingGuard()
        guard.check(token_b)
        with self.assertRaises(FencedOut):
            guard.check(token_a)  # stale ex-leader write is rejected
        self.assertFalse(a.try_acquire_or_renew())

    def test_release_allows_immediate_handover(self):
        clock = FakeClock()
        store = VersionedStore()
        a = LeaderElector(store, "l", "a", clock=clock)
        b = LeaderElector(store, "l", "b", clock=clock)
        a.try_acquire_or_renew()
        a.release()
        self.assertTrue(b.try_acquire_or_renew())


class JournalTest(unittest.TestCase):
    def test_hash_chain_detects_tamper_and_tolerates_torn_tail(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "j.jsonl")
            j = Journal(path)
            j.append("op1", "drain", "requested", {"node": "n1", "token": "s3cret"})
            j.append("op1", "drain", "completed")
            self.assertEqual(j.entries[0].data["token"], "[REDACTED]")
            with open(path, "a") as fh:
                fh.write('{"seq": 3, "broken')
            j2 = Journal(path)
            self.assertTrue(j2.torn_tail)
            self.assertEqual(len(j2.entries), 2)
            self.assertTrue(j2.verify())
            import pathlib
            p = pathlib.Path(path)
            lines = p.read_text().splitlines()
            lines[0] = lines[0].replace("n1", "n9")
            p.write_text("\n".join(lines) + "\n")
            with self.assertRaises(JournalCorrupt):
                Journal(path)

    def test_idempotency_replays_and_rejects_mismatch_across_restart(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "j.jsonl")
            calls = []
            reg = IdempotencyRegistry(Journal(path))
            r, replayed = reg.execute("key-0001", {"node": "n1"}, lambda: calls.append(1) or {"ok": True})
            self.assertFalse(replayed)
            reg2 = IdempotencyRegistry(Journal(path))  # restart
            r2, replayed2 = reg2.execute("key-0001", {"node": "n1"}, lambda: calls.append(1) or {"ok": False})
            self.assertTrue(replayed2)
            self.assertEqual(r2, {"ok": True})
            self.assertEqual(len(calls), 1)
            with self.assertRaises(IdempotencyMismatch):
                reg2.execute("key-0001", {"node": "n2"}, lambda: None)

    def test_audit_requires_actor_and_is_queryable(self):
        audit = AuditTrail(Journal())
        audit.record(actor="alice", action="drain", target="n1", outcome="completed")
        with self.assertRaises(JournalCorrupt):
            audit.record(actor="", action="drain", target="n1", outcome="completed")
        self.assertEqual(len(audit.query(actor="alice")), 1)


if __name__ == "__main__":
    unittest.main()
