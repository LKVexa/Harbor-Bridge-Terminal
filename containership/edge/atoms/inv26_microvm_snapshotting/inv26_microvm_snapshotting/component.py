"""INV-26 - MicroVM snapshotting pk_core assessment adapter."""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .snapshot import (
    CrossTenantRestore,
    EnvironmentMismatch,
    ModelMismatch,
    Snapshot,
    SnapshotStore,
    WorkloadMismatch,
)


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class MicrovmSnapshottingComponent(Component):
    """Master-applied component for INV-26."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        store = SnapshotStore()
        devices = {"virtio-net", "virtio-block"}
        store.capture(name="s1", tenant="t1", workload="w1", environment="prod",
                      devices=devices, memory_mib=256)
        result = store.restore("s1", tenant="t1", workload="w1", environment="prod",
                               devices=devices, elapsed_ms=4)
        _verify(result["within_budget"] and result["entropy_reseeded"] and not result["cold"])
        _verify(bool(result["entropy_proof_sha256"]), "missing entropy proof")
        findings[5] = self.satisfied(
            items[5],
            f"Restore is bounded: {result['restore_ms']}ms against a {result['budget_ms']}ms budget; "
            "fresh entropy material is injected and a non-secret SHA-256 proof is emitted.",
            *self._evidence("snapshot.py::SnapshotStore.restore"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        store = SnapshotStore()
        devices = {"virtio-net"}
        store.capture(name="s1", tenant="t1", workload="w1", environment="prod",
                      devices=devices, memory_mib=128)
        for kwargs, error in [
            ({"tenant": "t2", "workload": "w1", "environment": "prod"}, CrossTenantRestore),
            ({"tenant": "t1", "workload": "w2", "environment": "prod"}, WorkloadMismatch),
            ({"tenant": "t1", "workload": "w1", "environment": "dev"}, EnvironmentMismatch),
        ]:
            try:
                store.restore("s1", devices=devices, **kwargs)
            except error:
                pass
            else:
                raise AssertionError(f"expected {error.__name__} was not raised")
        findings[5] = self.satisfied(
            items[5],
            "Restore enforces tenant, workload, and environment bindings captured with the snapshot; "
            "cross-boundary restores are refused before entropy injection.",
            *self._evidence("snapshot.py::SnapshotStore.restore"))

        before = store.reseeds
        first = store.restore("s1", tenant="t1", workload="w1", environment="prod", devices=devices)
        second = store.restore("s1", tenant="t1", workload="w1", environment="prod", devices=devices)
        _verify(store.reseeds == before + 2)
        _verify(first["entropy_proof_sha256"] != second["entropy_proof_sha256"],
                "two restores reused entropy material")
        findings[6] = self.satisfied(
            items[6],
            "Every successful restore receives fresh 256-bit entropy material; consecutive restores "
            "produce distinct non-secret entropy proofs.",
            *self._evidence("snapshot.py::SnapshotStore.restore"))

        gap07 = sibling("GAP-07")
        if gap07 is None:
            findings[4] = self.partial(
                items[4],
                "Snapshot metadata is canonicalized for signing, but this isolated package does not contain "
                "the optional GAP-07 signing provider.",
                note="GAP-07 Artifact provenance/signing is not installed here")
        else:
            trust = gap07.TrustStore("prod")
            trust.add("snapshot-signer", "release", b"snap-key")
            snap = store.snapshots["s1"]
            blob = snap.canonical()
            signature = trust.sign("snapshot-signer", blob)
            _verify(trust.verify(signature, blob, "bundle")["verified"])
            rebound = Snapshot(snap.name, "t2", snap.workload, snap.environment,
                               snap.fingerprint, snap.memory_mib)
            try:
                trust.verify(signature, rebound.canonical(), "bundle")
                tampered_passed = True
            except gap07.SignatureInvalid:
                tampered_passed = False
            _verify(not tampered_passed, "a tampered snapshot record verified")
            findings[4] = self.satisfied(
                items[4],
                "The canonical capture record (schema, tenant, workload, environment, device fingerprint, "
                "memory and entropy state) is signed through GAP-07; altered metadata fails verification.",
                *self._evidence("snapshot.py::Snapshot.canonical"), "GAP-07/TrustStore.verify")
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        store = SnapshotStore()
        store.capture(name="s1", tenant="t1", workload="w1", environment="prod",
                      devices={"virtio-net"}, memory_mib=128)
        try:
            store.restore("s1", tenant="t1", workload="w1", environment="prod",
                          devices={"virtio-net", "virtio-vsock"})
        except ModelMismatch:
            findings[1] = self.satisfied(
                items[1],
                "A changed device model refuses restore rather than resuming a guest against incompatible hardware.",
                *self._evidence("snapshot.py::model_fingerprint"))
        else:
            raise AssertionError("expected ModelMismatch was not raised")
        return findings


COMPONENT = MicrovmSnapshottingComponent
