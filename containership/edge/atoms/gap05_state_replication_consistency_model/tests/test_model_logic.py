"""Standalone unit/property tests for the GAP-05 causal state machine."""
from __future__ import annotations

import importlib
import itertools
import pathlib
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pkg = importlib.import_module(PKG_DIR.name)
InvalidWrite = pkg.InvalidWrite
ReplicatedKey = pkg.ReplicatedKey
UnknownReplica = pkg.UnknownReplica
VectorEquivocationError = pkg.VectorEquivocationError
Write = pkg.Write
concurrent = pkg.concurrent
dominates = pkg.dominates


class WriteValidationTest(unittest.TestCase):
    def test_vector_is_canonicalized(self):
        write = Write("k", "v", "dub", (("dub", 2), ("ams", 1)))
        self.assertEqual(write.vector, (("ams", 1), ("dub", 2)))

    def test_rejects_malformed_vectors(self):
        bad_vectors = [
            (),
            (("dub", 1), ("dub", 2)),
            (("dub", 0),),
            (("dub", -1),),
            (("dub", True),),
            (("dub", "1"),),
            (("dub", 1, "extra"),),
            (("", 1),),
        ]
        for vector in bad_vectors:
            with self.subTest(vector=vector):
                with self.assertRaises(InvalidWrite):
                    Write("k", "v", "dub", vector)
        with self.assertRaises(InvalidWrite):
            Write("k", "v", "dub", (("ams", 1),))

    def test_vector_relations(self):
        self.assertTrue(dominates({"a": 2, "b": 1}, {"a": 1, "b": 1}))
        self.assertFalse(dominates({"a": 1}, {"a": 1}))
        self.assertTrue(concurrent({"a": 1}, {"b": 1}))


class ReplicatedKeyTest(unittest.TestCase):
    def test_constructor_invariants(self):
        with self.assertRaises(ValueError):
            ReplicatedKey("k", frozenset(), max_siblings=1)
        with self.assertRaises(ValueError):
            ReplicatedKey("k", "dub", max_siblings=1)
        with self.assertRaises(ValueError):
            ReplicatedKey("k", frozenset({"a"}), max_siblings=0)
        with self.assertRaises(ValueError):
            ReplicatedKey("", frozenset({"a"}), max_siblings=1)


    def test_rejects_invalid_restored_frontier(self):
        a1 = Write("k", "a1", "a", (("a", 1),))
        a2 = Write("k", "a2", "a", (("a", 2),))
        with self.assertRaises(ValueError):
            ReplicatedKey("k", frozenset({"a"}), siblings=[a1, a2])
        with self.assertRaises(ValueError):
            ReplicatedKey("k", frozenset({"a"}), siblings=[a1, a1])

    def test_unknown_replica_and_key_mismatch(self):
        key = ReplicatedKey("k", frozenset({"a"}))
        with self.assertRaises(UnknownReplica):
            key.apply(Write("k", "v", "b", (("b", 1),)))
        with self.assertRaises(InvalidWrite):
            key.apply(Write("other", "v", "a", (("a", 1),)))

    def test_duplicate_and_equivocation(self):
        key = ReplicatedKey("k", frozenset({"a"}))
        original = Write("k", "v1", "a", (("a", 1),))
        self.assertEqual(key.apply(original), "converged")
        self.assertEqual(key.apply(original), "duplicate")
        with self.assertRaises(VectorEquivocationError):
            key.apply(Write("k", "tampered", "a", (("a", 1),)))

    def test_bounded_frontier_is_order_independent(self):
        writes = [Write("k", f"v{i}", f"s{i}", ((f"s{i}", 1),)) for i in range(5)]
        replicas = frozenset(f"s{i}" for i in range(5))
        expected = None
        for ordering in itertools.permutations(writes):
            key = ReplicatedKey("k", replicas, max_siblings=3)
            for write in ordering:
                key.apply(write)
            state = key.conflict_set()
            if expected is None:
                expected = state
            self.assertEqual(state, expected)
            self.assertEqual(len(key.siblings), 3)
            self.assertEqual(len(key.quarantine), 2)
            self.assertFalse(key.converged)

    def test_replay_of_quarantined_write_is_duplicate(self):
        writes = [Write("k", f"v{i}", f"s{i}", ((f"s{i}", 1),)) for i in range(3)]
        key = ReplicatedKey("k", frozenset({"s0", "s1", "s2"}), max_siblings=1)
        for write in writes:
            key.apply(write)
        quarantined = key.quarantine[-1]["write"]
        q_len = len(key.quarantine)
        self.assertEqual(key.apply(quarantined), "duplicate")
        self.assertEqual(len(key.quarantine), q_len)

    def test_causal_successor_of_quarantined_write_replaces_it(self):
        key = ReplicatedKey("k", frozenset({"a", "b"}), max_siblings=1)
        a1 = Write("k", "a1", "a", (("a", 1),))
        b1 = Write("k", "b1", "b", (("b", 1),))
        b2 = Write("k", "b2", "b", (("b", 2),))
        key.apply(a1)
        key.apply(b1)
        self.assertTrue(any(entry["write"] == b1 for entry in key.quarantine))
        key.apply(b2)
        unresolved = key.siblings + [entry["write"] for entry in key.quarantine]
        self.assertIn(b2, unresolved)
        self.assertNotIn(b1, unresolved)
        self.assertTrue(any(entry["write"] == b1 for entry in key.discarded))

    def test_resolution_covers_active_and_quarantined_frontier(self):
        replicas = frozenset(f"s{i}" for i in range(5))
        key = ReplicatedKey("k", replicas, max_siblings=2)
        writes = [Write("k", f"v{i}", f"s{i}", ((f"s{i}", 1),)) for i in range(5)]
        for write in writes:
            key.apply(write)
        self.assertEqual(len(key.siblings), 2)
        self.assertEqual(len(key.quarantine), 3)
        winner = key.resolve("merged", "s0")
        vector = dict(winner.vector)
        for i in range(5):
            self.assertGreaterEqual(vector[f"s{i}"], 1)
        self.assertEqual(vector["s0"], 2)
        self.assertTrue(key.converged)
        self.assertEqual(key.value(), "merged")
        self.assertEqual(key.quarantine, [])
        self.assertEqual(len(key.discarded), 5)

    def test_threaded_apply_has_deterministic_final_frontier(self):
        writes = [Write("k", f"v{i:02d}", f"s{i:02d}", ((f"s{i:02d}", 1),)) for i in range(20)]
        replicas = frozenset(write.site for write in writes)
        key = ReplicatedKey("k", replicas, max_siblings=8)
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(key.apply, reversed(writes)))
        active = [write.site for write in key.siblings]
        quarantined = [entry["write"].site for entry in key.quarantine]
        self.assertEqual(active, [f"s{i:02d}" for i in range(8)])
        self.assertEqual(quarantined, [f"s{i:02d}" for i in range(8, 20)])


if __name__ == "__main__":
    unittest.main()
