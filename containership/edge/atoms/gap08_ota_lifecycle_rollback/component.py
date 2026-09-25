"""GAP-08 - OTA lifecycle/rollback checklist integration.

The safety-critical state machine lives in :mod:`.rollout`; this module binds
that behaviour to the Post-Kubernetes checklist framework.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .rollout import (
    BundleRejected,
    GateFailed,
    InvalidRollout,
    Rollout,
    StateIntegrityError,
)


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


def _verification(bundle: str) -> dict:
    """Minimal exact-subject verification fixture used by conformance checks."""
    return {
        "schema": "PK_VERIFICATION/1",
        "verified": True,
        "kind": "bundle",
        "bundle": bundle,
    }


class OtaLifecycleRollbackComponent(Component):
    """Master-applied component for GAP-08."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        fleet = {f"n{i}": "v1" for i in range(1, 4)}
        rollout = Rollout("v2", waves=[["n1"], ["n2", "n3"]])
        rollout.pin(fleet)
        rollout.admit(_verification(rollout.bundle))
        rollout.run_wave(healthy=True)
        result = rollout.rollback(reason="operator requested rollback")
        _verify(result["complete"] and rollout.fleet_on("v1") == sorted(fleet))
        # C038: automatic and operator-driven rollback.
        findings[7] = self.satisfied(
            items[7],
            "The same pinned-target rollback primitive is callable by the automatic gate path and by an "
            "operator path; the exercised operator rollback restored every touched node.",
            *self._evidence("rollout.py::Rollout.rollback"),
        )
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        fleet = {"n1": "v1"}
        rollout = Rollout("v2", waves=[["n1"]])
        rollout.pin(fleet)

        try:
            rollout.admit({"verified": True, "kind": "bundle", "bundle": "other"})
        except BundleRejected:
            pass
        else:
            raise AssertionError("verification for a different bundle was accepted")
        rollout.admit(_verification(rollout.bundle))
        findings[4] = self.satisfied(
            items[4],
            "Admission fails closed unless verification is true, bundle-scoped, schema-compatible, and "
            "bound to the exact bundle identifier; malformed SHA-256 digests are also rejected.",
            *self._evidence("rollout.py::Rollout.admit"),
        )

        _verify(rollout.verify_audit_chain())
        snapshot = rollout.snapshot()
        tampered = dict(snapshot)
        tampered["audit_log"] = [dict(event) for event in snapshot["audit_log"]]
        tampered["audit_log"][0]["payload"] = dict(tampered["audit_log"][0]["payload"])
        tampered["audit_log"][0]["payload"]["target"] = "v0"
        # Recompute the outer digest to prove the inner chained audit record still catches tampering.
        import hashlib, json
        body = dict(tampered)
        body.pop("state_digest", None)
        tampered["state_digest"] = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        try:
            Rollout.from_snapshot(tampered)
        except StateIntegrityError:
            findings[8] = self.satisfied(
                items[8],
                "Security-sensitive transitions are hash-chained; an internally tampered event is rejected "
                "even if an attacker recomputes the outer snapshot digest.",
                *self._evidence("rollout.py::Rollout.verify_audit_chain"),
            )
        else:
            raise AssertionError("tampered audit chain was accepted")
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        fleet = {f"n{i}": "v1" for i in range(1, 5)}

        deferred = Rollout("v2", waves=[["n1", "n2"], ["n3", "n4"]])
        deferred.pin(fleet)
        deferred.admit(_verification(deferred.bundle))
        first = deferred.run_wave(healthy=True, offline={"n2"})
        _verify(first["deferred"] == ["n2"] and deferred.versions["n2"] == "v1")
        retry = deferred.retry_deferred(healthy=True)
        _verify(retry["touched"] == ["n2"] and deferred.versions["n2"] == "v2")
        # C056: degraded operation under noncritical dependency/network loss.
        findings[5] = self.satisfied(
            items[5],
            "Offline nodes are explicitly deferred rather than misreported as updated, and a separately "
            "gated catch-up path can safely retry them later.",
            *self._evidence("rollout.py::Rollout.retry_deferred"),
        )

        snapshot = deferred.snapshot()
        restored = Rollout.from_snapshot(snapshot)
        _verify(restored.wave_index == deferred.wave_index and restored.versions == deferred.versions)
        # C057: crash-consistency/restart/resume.
        findings[6] = self.satisfied(
            items[6],
            "Mutable rollout state can be snapshotted with an integrity digest, restored, and rejected if "
            "the snapshot or its chained audit history was altered.",
            *self._evidence("rollout.py::Rollout.snapshot", "rollout.py::Rollout.from_snapshot"),
        )

        try:
            Rollout("v2", waves=[["n1"], ["n1"]])
        except InvalidRollout:
            findings[7] = self.satisfied(
                items[7],
                "Topology validation rejects duplicate node execution across waves before rollout begins, "
                "eliminating one local duplicate-execution path.",
                *self._evidence("rollout.py::Rollout._validated_waves"),
            )
        else:
            raise AssertionError("duplicate execution topology was accepted")

        bad = Rollout("v-bad", waves=[["n1"], ["n2", "n3", "n4"]])
        bad.pin(fleet)
        bad.admit(_verification(bad.bundle))
        verdict = bad.run_wave(healthy=False, rollback_failures={"n1"})
        _verify(verdict["rolled_back"] and not verdict["rollback_complete"])
        _verify(bad.quarantined == ["n1"] and bad.rollback_failed == ["n1"])
        # C059: quarantine/freeze/disable control.
        findings[8] = self.satisfied(
            items[8],
            "A node that fails rollback is retained on the bad version only as an explicit rollback failure "
            "and is quarantined; the rollback is never reported as complete.",
            *self._evidence("rollout.py::Rollout.rollback"),
        )
        # C060: exercised fault-injection behaviour.
        findings[9] = self.satisfied(
            items[9],
            "The conformance path injects a first-wave health failure plus a rollback failure and verifies "
            "containment, incomplete-rollback reporting, and quarantine semantics.",
            *self._evidence("component.py::OtaLifecycleRollbackComponent.assess_resilience"),
        )
        return findings

    def assess_operations(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_operations(items)
        fleet = {f"n{i}": "v1" for i in range(1, 8)}
        rollout = Rollout("v2", waves=[["n1"], ["n2", "n3"], ["n4", "n5", "n6", "n7"]])
        rollout.pin(fleet)
        rollout.admit(_verification(rollout.bundle))
        rollout.run_wave(healthy=True, gate_id="canary")
        rollout.run_wave(healthy=True, gate_id="middle")
        rollout.run_wave(healthy=True, gate_id="fleet")
        _verify(rollout.fleet_on("v2") == sorted(fleet))
        # C092: canary, staged rollout, rollback, emergency-disable procedures.
        findings[1] = self.satisfied(
            items[1],
            "The exercised release procedure uses a one-node canary followed by progressively larger gated "
            "waves; any failed gate invokes the same pinned rollback primitive.",
            *self._evidence("rollout.py::Rollout.run_wave", "rollout.py::Rollout.rollback"),
        )
        return findings


COMPONENT = OtaLifecycleRollbackComponent
