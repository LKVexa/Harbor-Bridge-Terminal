"""Standalone safety tests for GAP-08 rollout mechanics; no pk_core required."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("gap08_rollout_standalone", PKG_DIR / "rollout.py")
rollout_mod = importlib.util.module_from_spec(SPEC)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load rollout.py test target")
sys.modules[SPEC.name] = rollout_mod
SPEC.loader.exec_module(rollout_mod)

Rollout = rollout_mod.Rollout
BundleRejected = rollout_mod.BundleRejected
GateFailed = rollout_mod.GateFailed
InvalidRollout = rollout_mod.InvalidRollout
NoRollbackTarget = rollout_mod.NoRollbackTarget
StateIntegrityError = rollout_mod.StateIntegrityError
RolloutState = rollout_mod.RolloutState


def verification(bundle: str, **extra):
    value = {
        "schema": "PK_VERIFICATION/1",
        "verified": True,
        "kind": "bundle",
        "bundle": bundle,
    }
    value.update(extra)
    return value


class RolloutSafetyTest(unittest.TestCase):
    def test_rejects_invalid_topology(self):
        with self.assertRaises(InvalidRollout):
            Rollout("v2", waves=[])
        with self.assertRaises(InvalidRollout):
            Rollout("v2", waves=[["n1"], ["n1"]])
        with self.assertRaises(InvalidRollout):
            Rollout("v2", waves=[[]])
        with self.assertRaises(InvalidRollout):
            Rollout("v2", waves=[["n1", "n2"], ["n3"]])

    def test_pin_rejects_unknown_nodes_and_repin(self):
        r = Rollout("v2", waves=[["n1", "n2"]])
        with self.assertRaises(InvalidRollout):
            r.pin({"n1": "v1"})
        r = Rollout("v2", waves=[["n1"]])
        self.assertEqual(r.pin({"n1": "v1"}), "v1")
        with self.assertRaises(StateIntegrityError):
            r.pin({"n1": "v1"})

    def test_pin_rejects_heterogeneous_or_noop_target(self):
        with self.assertRaises(NoRollbackTarget):
            Rollout("v2", waves=[["n1"]]).pin({"n1": "v1", "n2": "v0"})
        with self.assertRaises(NoRollbackTarget):
            Rollout("v2", waves=[["n1"]]).pin({"n1": "v2"})

    def test_admission_is_exact_bundle_bound(self):
        r = Rollout("v2", waves=[["n1"]])
        r.pin({"n1": "v1"})
        for bad in (
            None,
            {"verified": True, "kind": "bundle"},
            {"verified": True, "kind": "bundle", "bundle": "v3"},
            {"verified": True, "kind": "label", "bundle": "v2"},
            {"verified": True, "kind": "bundle", "bundle": "v2", "schema": "PK_VERIFICATION/9"},
        ):
            with self.subTest(bad=bad), self.assertRaises(BundleRejected):
                r2 = Rollout("v2", waves=[["n1"]])
                r2.pin({"n1": "v1"})
                r2.admit(bad)
        r.admit(verification("v2", digest="sha256:" + "a" * 64))
        self.assertTrue(r.verified)
        with self.assertRaises(StateIntegrityError):
            r.admit(verification("v2"))

    def test_gate_input_is_strict_and_scoped(self):
        r = Rollout("v2", waves=[["n1"]])
        r.pin({"n1": "v1"})
        r.admit(verification("v2"))
        with self.assertRaises(InvalidRollout):
            r.run_wave(healthy=1)  # type: ignore[arg-type]
        with self.assertRaises(InvalidRollout):
            r.run_wave(healthy=True, offline={"n2"})

    def test_failed_gate_rolls_back_and_closes_rollout(self):
        r = Rollout("v2", waves=[["n1"], ["n2"]])
        r.pin({"n1": "v1", "n2": "v1"})
        r.admit(verification("v2"))
        verdict = r.run_wave(healthy=False)
        self.assertTrue(verdict["rolled_back"])
        self.assertEqual(r.fleet_on("v2"), [])
        self.assertEqual(r.state, RolloutState.ROLLED_BACK)
        with self.assertRaises(GateFailed):
            r.run_wave(healthy=True)

    def test_deferred_nodes_have_gated_catchup(self):
        r = Rollout("v2", waves=[["n1", "n2"]])
        r.pin({"n1": "v1", "n2": "v1"})
        r.admit(verification("v2"))
        first = r.run_wave(healthy=True, offline={"n2"})
        self.assertEqual(first["deferred"], ["n2"])
        self.assertEqual(r.state, RolloutState.DEFERRED)
        self.assertFalse(r.run_wave(healthy=True)["complete"])
        retry = r.retry_deferred(healthy=True)
        self.assertEqual(retry["touched"], ["n2"])
        self.assertEqual(r.deferred, [])
        self.assertEqual(r.fleet_on("v2"), ["n1", "n2"])
        self.assertEqual(r.state, RolloutState.COMPLETE)

    def test_rollback_failure_is_quarantined_and_not_hidden(self):
        r = Rollout("v2", waves=[["n1"]])
        r.pin({"n1": "v1"})
        r.admit(verification("v2"))
        verdict = r.run_wave(healthy=False, rollback_failures={"n1"})
        self.assertFalse(verdict["rollback_complete"])
        self.assertEqual(verdict["rollback_failed"], ["n1"])
        self.assertEqual(r.quarantined, ["n1"])
        self.assertEqual(r.state, RolloutState.ROLLBACK_INCOMPLETE)

    def test_snapshot_round_trip_and_outer_tamper_detection(self):
        r = Rollout("v2", waves=[["n1"], ["n2"]])
        r.pin({"n1": "v1", "n2": "v1"})
        r.admit(verification("v2"))
        r.run_wave(healthy=True)
        snap = r.snapshot()
        restored = Rollout.from_snapshot(snap)
        self.assertEqual(restored.snapshot(), snap)
        tampered = dict(snap)
        tampered["wave_index"] = 2
        with self.assertRaises(StateIntegrityError):
            Rollout.from_snapshot(tampered)

    def test_inner_audit_tamper_detected_even_with_outer_digest_recomputed(self):
        r = Rollout("v2", waves=[["n1"]])
        r.pin({"n1": "v1"})
        snap = r.snapshot()
        tampered = json.loads(json.dumps(snap))
        tampered["audit_log"][0]["payload"]["target"] = "v0"
        body = dict(tampered)
        body.pop("state_digest")
        tampered["state_digest"] = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        with self.assertRaises(StateIntegrityError):
            Rollout.from_snapshot(tampered)

    def test_audit_chain_survives_normal_flow(self):
        r = Rollout("v2", waves=[["n1"]])
        r.pin({"n1": "v1"})
        r.admit(verification("v2"))
        r.run_wave(healthy=True, gate_id="g1", evidence={"sample": 42})
        self.assertTrue(r.verify_audit_chain())
        self.assertEqual([e["event"] for e in r.audit_log], ["rollback_target_pinned", "bundle_admitted", "wave_gate"])


if __name__ == "__main__":
    unittest.main()
