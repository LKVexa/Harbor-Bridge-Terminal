"""Engine semantics: MC-008..011, MC-016..020, MC-026-05."""
from __future__ import annotations

import threading
import unittest

from _util import FakeClock  # noqa: F401  (also fixes sys.path)
from inv05_current_control_state_system.errors import (
    CompactedError, FutureRevision, IdempotencyConflict, InvalidArgument, LeaseNotFound, LimitExceeded,
    Overloaded, UnsupportedPredicate,
)
from inv05_current_control_state_system.limits import Limits
from inv05_current_control_state_system.store import Compare, ControlStore, Delete, Put, Range, prefix_end


class ReadApiTest(unittest.TestCase):  # MC-008
    def setUp(self):
        self.s = ControlStore()
        for i in range(10):
            self.s.put(f"a/{i:02d}", i)
        self.s.put("b/x", "bx")

    def test_point_read_current_and_historical(self):
        self.s.put("a/00", 100)
        self.assertEqual(self.s.get("a/00").value, 100)
        self.assertEqual(self.s.get("a/00", revision=1).value, 0)
        self.assertIsNone(self.s.get("a/05", revision=1))

    def test_prefix_order_and_boundaries(self):
        r = self.s.range(Range("a/", prefix=True))
        self.assertEqual([kv.key for kv in r.kvs], [f"a/{i:02d}" for i in range(10)])
        r = self.s.range(Range("a/02", range_end="a/05"))  # inclusive start, exclusive end
        self.assertEqual([kv.key for kv in r.kvs], ["a/02", "a/03", "a/04"])
        self.assertEqual(r.revision, self.s.revision)

    def test_pagination_is_stable_under_concurrent_writes(self):
        r1 = self.s.range(Range("a/", prefix=True, limit=4))
        self.assertTrue(r1.more)
        self.s.put("a/03", "changed")
        self.s.delete("a/07")
        self.s.put("a/055", "new")
        pages, tok = [r1], r1.next_token
        while tok:
            r = self.s.range(Range("a/", prefix=True, limit=4, page_token=tok))
            pages.append(r)
            tok = r.next_token
        keys = [kv.key for p in pages for kv in p.kvs]
        self.assertEqual(keys, [f"a/{i:02d}" for i in range(10)])
        self.assertTrue(all(p.revision == r1.revision for p in pages))
        self.assertEqual([kv.value for p in pages for kv in p.kvs][3], 3)

    def test_compacted_future_and_invalid_revisions(self):
        with self.assertRaises(FutureRevision):
            self.s.get("a/00", revision=self.s.revision + 1)
        self.s.compact(5)
        with self.assertRaises(CompactedError):
            self.s.get("a/00", revision=4)
        self.assertEqual(self.s.get("a/00", revision=5).value, 0)
        for bad in (-1, True, "3", 2**64):
            with self.assertRaises(InvalidArgument):
                self.s.get("a/00", revision=bad)

    def test_page_size_limit(self):
        with self.assertRaises(LimitExceeded):
            self.s.range(Range("a/", prefix=True, limit=10**6))

    def test_tampered_page_token(self):
        with self.assertRaises(InvalidArgument):
            self.s.range(Range("a/", prefix=True, page_token="!!notbase64"))

    def test_prefix_end(self):
        self.assertEqual(prefix_end("a/"), "a0")
        self.assertEqual(prefix_end(""), "")


class DeleteTest(unittest.TestCase):  # MC-009
    def test_delete_tombstone_events_and_recreate(self):
        s = ControlStore()
        s.put("k", 1)
        r = s.delete("k")
        self.assertEqual(r.responses[0]["delete"]["deleted"], 1)
        self.assertIsNone(s.get("k"))
        self.assertEqual(s.get("k", revision=1).value, 1)
        ev = s.events_since(2)[0]
        self.assertEqual((ev.kind, ev.prev_value, ev.version), ("DELETE", 1, 0))
        s.put("k", 2)
        kv = s.get("k")
        self.assertEqual((kv.version, kv.create_revision), (1, 3))  # new incarnation
        self.assertEqual([e.revision for e in s.events_since(1)], [1, 2, 3])

    def test_delete_absent_is_idempotent_and_no_revision(self):
        s = ControlStore()
        r = s.delete("nope")
        self.assertEqual((r.revision, r.responses[0]["delete"]["deleted"]), (0, 0))

    def test_null_value_is_a_value_not_a_delete(self):
        s = ControlStore()
        s.put("k", None)
        self.assertIsNotNone(s.get("k"))

    def test_compare_and_delete(self):
        s = ControlStore()
        s.put("k", 1)
        self.assertFalse(s.txn([Compare("k", "VERSION", "==", 9)], [Delete("k")]).succeeded)
        self.assertTrue(s.txn([Compare("k", "VERSION", "==", 1)], [Delete("k")]).succeeded)

    def test_prefix_delete(self):
        s = ControlStore()
        for k in ("p/1", "p/2", "q/1"):
            s.put(k, 0)
        r = s.delete("p/", prefix=True)
        self.assertEqual(r.responses[0]["delete"]["deleted"], 2)
        self.assertEqual(len(s.events_since(r.revision)), 2)  # one revision, two events


class TxnTest(unittest.TestCase):  # MC-010, MC-011
    def test_failure_branch_executes(self):
        s = ControlStore()
        r = s.txn([Compare("k", "EXISTS", "==", True)], [Put("k", "s")], [Put("k", "f"), Range("k")])
        self.assertFalse(r.succeeded)
        self.assertEqual(s.get("k").value, "f")
        self.assertEqual(r.responses[1]["range"]["kvs"], [])  # range sees pre-txn state

    def test_one_revision_per_txn_and_per_op_results(self):
        s = ControlStore()
        r = s.txn((), [Put("a", 1), Put("b", 2), Range("a")])
        self.assertEqual(r.revision, 1)
        self.assertEqual({s.get("a").mod_revision, s.get("b").mod_revision}, {1})
        self.assertEqual(len(r.responses), 3)

    def test_ambiguous_branches_rejected(self):
        s = ControlStore()
        with self.assertRaises(InvalidArgument):
            s.txn((), [Put("a", 1), Put("a", 2)])
        with self.assertRaises(InvalidArgument):
            s.txn((), [Put("a/x", 1), Delete("a/", prefix=True)])
        self.assertEqual(s.revision, 0)

    def test_rich_predicates(self):
        s = ControlStore()
        s.put("k", {"b": 1, "a": 2})
        kv = s.get("k")
        ok = [Compare("k", "EXISTS", "==", True), Compare("k", "VALUE", "==", {"a": 2, "b": 1}),
              Compare("k", "VERSION", ">=", 1), Compare("k", "CREATE", "==", kv.create_revision),
              Compare("k", "MOD", "<", 99), Compare("k", "LEASE", "==", 0), Compare("z", "EXISTS", "==", False)]
        self.assertTrue(s.txn(ok, [Put("k2", 1)]).succeeded)
        mixed = ok + [Compare("k", "VALUE", "!=", {"a": 2, "b": 1})]
        r = s.txn(mixed, [Put("k3", 1)])
        self.assertFalse(r.succeeded)
        self.assertEqual(r.compare_results[-1], False)
        self.assertEqual(len(r.compare_results), len(mixed))  # no short-circuit

    def test_unsupported_predicates_rejected_before_execution(self):
        s = ControlStore()
        for c in (Compare("k", "VALUE", "<", 1), Compare("k", "NOPE", "==", 1), Compare("k", "EXISTS", "==", 1),
                  Compare("k", "FENCE", "==", 1), Compare("k", "MOD", "==", -1)):
            with self.assertRaises(InvalidArgument):
                s.txn([c], [Put("x", 1)])
        self.assertEqual(s.revision, 0)
        self.assertTrue(issubclass(UnsupportedPredicate, InvalidArgument))

    def test_contenders_single_winner(self):
        s = ControlStore()
        s.put("lock", "seed")
        exp = s.get("lock").mod_revision
        wins = []
        barrier = threading.Barrier(24)

        def go(i):
            barrier.wait()
            if s.cas("lock", exp, f"n{i}").succeeded:
                wins.append(i)
        ts = [threading.Thread(target=go, args=(i,)) for i in range(24)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(wins), 1)
        self.assertEqual(s.get("lock").value, f"n{wins[0]}")

    def test_limits(self):
        s = ControlStore(Limits(max_txn_ops=2, max_txn_compares=1, max_key_bytes=8, max_value_bytes=10,
                                max_history_events=3))
        with self.assertRaises(LimitExceeded):
            s.txn((), [Put("a", 1), Put("b", 1), Put("c", 1)])
        with self.assertRaises(LimitExceeded):
            s.txn([Compare("a", "EXISTS", "==", False)] * 2, [])
        with self.assertRaises(LimitExceeded):
            s.put("k" * 9, 1)
        with self.assertRaises(LimitExceeded):
            s.put("k", "x" * 20)
        for i in range(3):
            s.put(f"k{i}", i)
        with self.assertRaises(Overloaded):
            s.put("k9", 1)

    def test_key_policy(self):
        s = ControlStore()
        for bad in ("", "a\x00b", "a\nb", "é", "\ud800", 5, None):
            with self.assertRaises(InvalidArgument):
                s.put(bad, 1)

    def test_idempotent_request_id(self):
        s = ControlStore()
        r1 = s.txn((), [Put("k", 1)], request_id="r1")
        r2 = s.txn((), [Put("k", 1)], request_id="r1")
        self.assertTrue(r2.replayed)
        self.assertEqual((r1.revision, s.revision), (r2.revision, 1))
        with self.assertRaises(IdempotencyConflict):
            s.txn((), [Put("k", 2)], request_id="r1")


class LeaseTest(unittest.TestCase):  # MC-018
    def setUp(self):
        self.clock = FakeClock()
        self.s = ControlStore(clock=self.clock)

    def test_expiry_deletes_attached_keys_with_expire_events(self):
        l = self.s.lease_grant(10, owner="me")
        self.s.put("owned", 1, lease=l.id)
        self.clock.advance(5)
        self.s.lease_keepalive(l.id)
        self.clock.advance(9)
        self.assertEqual(self.s.tick(), 0)
        self.clock.advance(2)
        self.assertEqual(self.s.tick(), 1)
        self.assertIsNone(self.s.get("owned"))
        self.assertEqual(self.s.events_since(1)[-1].kind, "EXPIRE")
        with self.assertRaises(LeaseNotFound):
            self.s.lease_keepalive(l.id)

    def test_fencing_blocks_stale_owner(self):
        l1 = self.s.lease_grant(5, owner="a")
        tok = l1.fence
        self.clock.advance(6)
        l2 = self.s.lease_grant(5, owner="b")
        self.assertGreater(l2.fence, tok)
        stale = self.s.txn([Compare(f"lease:{l1.id}", "FENCE", "==", tok)], [Put("res", "a")])
        fresh = self.s.txn([Compare(f"lease:{l2.id}", "FENCE", "==", l2.fence)], [Put("res", "b")])
        self.assertFalse(stale.succeeded)
        self.assertTrue(fresh.succeeded)
        with self.assertRaises(LeaseNotFound):
            self.s.put("x", 1, lease=l1.id)

    def test_lease_compare_and_revoke(self):
        l = self.s.lease_grant(30)
        self.s.put("k", 1, lease=l.id)
        self.assertTrue(self.s.txn([Compare("k", "LEASE", "==", l.id)], []).succeeded)
        self.assertEqual(self.s.lease_revoke(l.id), 1)
        self.assertEqual(self.s.events_since(1)[-1].kind, "DELETE")

    def test_ttl_bounds_and_quota(self):
        with self.assertRaises(InvalidArgument):
            self.s.lease_grant(1)
        with self.assertRaises(InvalidArgument):
            self.s.lease_grant(10**6)
        s = ControlStore(Limits(max_leases_per_identity=1))
        s.lease_grant(5, owner="x")
        with self.assertRaises(LimitExceeded):
            s.lease_grant(5, owner="x")

    def test_remaining_ttl_from_monotonic_clock(self):
        l = self.s.lease_grant(10)
        self.clock.advance(3)
        self.assertAlmostEqual(self.s.lease_get(l.id).remaining(self.clock()), 7)


class CompactionTest(unittest.TestCase):  # MC-019
    def test_protected_revision_blocks_compaction(self):
        s = ControlStore()
        for i in range(10):
            s.put("k", i)
        s.protect("backup", 4)
        with self.assertRaises(InvalidArgument):
            s.compact(6)
        self.assertEqual(s.compact(4), 4)
        s.unprotect("backup")
        s.compact(9)
        self.assertEqual(s.check_invariants(), [])
        self.assertEqual(s.get("k").value, 9)

    def test_compaction_drops_deleted_keys(self):
        s = ControlStore()
        s.put("gone", 1)
        s.delete("gone")
        s.put("stay", 1)
        s.compact(3)
        self.assertNotIn("gone", s.export_state()["keys"])
        self.assertEqual(s.check_invariants(), [])

    def test_cannot_compact_future(self):
        s = ControlStore()
        with self.assertRaises(InvalidArgument):
            s.compact(1)


class SnapshotTest(unittest.TestCase):  # MC-017
    def test_snapshot_then_watch_from_next_revision_has_no_gap_or_dup(self):
        s = ControlStore()
        stop = threading.Event()

        def writer():
            i = 0
            while not stop.is_set():
                s.put(f"w/{i % 50}", i)
                i += 1
        t = threading.Thread(target=writer)
        t.start()
        try:
            snap = s.snapshot("w/")
            state = {kv.key: kv.value for kv in snap.kvs}
            import time
            time.sleep(0.05)
            with s.lock:
                evs = s.events_since(snap.revision + 1, "w/")
                expected = {kv.key: kv.value for kv in s.snapshot("w/").kvs}
            for e in evs:
                state[e.key] = e.value
            self.assertEqual(state, expected)
        finally:
            stop.set()
            t.join()


if __name__ == "__main__":
    unittest.main()
