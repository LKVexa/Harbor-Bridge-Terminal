"""Dependency-free unit tests for the INV-07 in-memory GitOps reference model."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import importlib.util
import math
from pathlib import Path
import sys
import unittest

PKG_DIR = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("inv07_gitops_model_standalone", PKG_DIR / "gitops_model.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load gitops_model.py for standalone tests")
MODEL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODEL
SPEC.loader.exec_module(MODEL)

GitOps = MODEL.GitOps
InvalidState = MODEL.InvalidState
NothingToSync = MODEL.NothingToSync
Unsigned = MODEL.Unsigned
canonical_state_bytes = MODEL.canonical_state_bytes
sign = MODEL.sign


class GitOpsModelTest(unittest.TestCase):
    def test_canonical_signature_is_key_order_independent(self):
        left = {"b": [2, {"x": True}], "a": 1}
        right = {"a": 1, "b": [2, {"x": True}]}
        self.assertEqual(canonical_state_bytes(left), canonical_state_bytes(right))
        self.assertEqual(sign(b"secret", left), sign(b"secret", right))

    def test_rejects_unsafe_or_nondeterministic_state(self):
        for state in ({"x": math.nan}, {"x": {1: "bad"}}, {"x": object()}):
            with self.subTest(state=state):
                with self.assertRaises(InvalidState):
                    canonical_state_bytes(state)

    def test_commit_state_is_detached_from_caller_mutation(self):
        state = {"service": {"replicas": 2}, "ports": [80]}
        g = GitOps({"release": b"k"})
        sha = g.commit(state, "release", sign(b"k", state))
        state["service"]["replicas"] = 99
        state["ports"].append(443)
        g.sync()
        self.assertEqual(g.applied, [sha])
        self.assertEqual(g.live, {"service": {"replicas": 2}, "ports": [80]})

    def test_bad_signature_fails_closed_and_preserves_live_state(self):
        g = GitOps({"release": b"good"})
        good = {"api": "v1"}
        g.commit(good, "release", sign(b"good", good))
        g.sync()
        g.commit({"api": "evil"}, "release", sign(b"wrong", {"api": "evil"}))
        with self.assertRaises(Unsigned):
            g.sync()
        self.assertEqual(g.live, good)
        self.assertEqual(len(g.applied), 1)

    def test_drift_reconciliation_reports_add_change_and_delete(self):
        desired = {"api": "v1", "replicas": 3, "region": "west"}
        g = GitOps({"release": b"k"})
        sha = g.commit(desired, "release", sign(b"k", desired))
        g.sync()
        g.live["replicas"] = 9
        del g.live["region"]
        g.live["manual"] = True
        g.sync()
        self.assertEqual(g.live, desired)
        self.assertEqual(g.applied, [sha], "same-head drift reconciliation must be idempotent in history")
        self.assertEqual(g.reports[-1]["reverted"], ["manual", "region", "replicas"])
        self.assertEqual(g.reports[-1]["detected_against_commit"], sha)
        self.assertEqual(g.reports[-1]["reconciled_to_commit"], sha)

    def test_revert_targets_prior_applied_commit_not_refused_raw_commit(self):
        g = GitOps({"release": b"k"})
        v1 = {"api": "v1"}
        v2 = {"api": "v2"}
        g.commit(v1, "release", sign(b"k", v1))
        g.sync()
        g.commit(v2, "release", sign(b"k", v2))
        g.sync()
        g.commit({"api": "unsigned"}, "release", "00")
        with self.assertRaises(Unsigned):
            g.sync()
        revert_sha = g.revert("release")
        self.assertNotIn(revert_sha, g.applied)
        g.sync()
        self.assertEqual(g.live, v1)
        self.assertEqual(g.applied[-1], revert_sha)

    def test_revert_requires_prior_applied_revision_and_allowed_key(self):
        g = GitOps({"release": b"k"})
        with self.assertRaises(Unsigned):
            g.revert("unknown")
        state = {"api": "v1"}
        g.commit(state, "release", sign(b"k", state))
        g.sync()
        with self.assertRaises(NothingToSync):
            g.revert("release")

    def test_commit_ids_are_full_sha256_and_unique_under_parallel_appends(self):
        g = GitOps({"release": b"k"})

        def append(i: int) -> str:
            state = {"revision": i}
            return g.commit(state, "release", sign(b"k", state))

        with ThreadPoolExecutor(max_workers=8) as pool:
            ids = list(pool.map(append, range(64)))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(len(sha) == 64 for sha in ids))
        self.assertTrue(all(set(sha) <= set("0123456789abcdef") for sha in ids))

    def test_status_does_not_expose_key_material(self):
        g = GitOps({"release": b"super-secret"})
        state = {"api": "v1"}
        sha = g.commit(state, "release", sign(b"super-secret", state))
        g.sync()
        status = g.status()
        self.assertEqual(status["head"], sha)
        self.assertTrue(status["in_sync"])
        self.assertEqual(status["allowed_key_ids"], ["release"])
        self.assertNotIn("super-secret", repr(status))


if __name__ == "__main__":
    unittest.main()
