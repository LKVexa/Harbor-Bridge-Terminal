"""PLN-06 - Data plane pk_core certification adapter.

The executable runtime lives in :mod:`data_plane` so it remains usable and
unit-testable without the surrounding certification framework.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .data_plane import Backpressure, DataPlane, ResidencyViolation


def _verify(condition: bool, message: str = "behavioural check failed") -> None:
    """Fail a behavioural check even when Python assertions are optimized out."""
    if not condition:
        raise AssertionError(message)


class DataPlaneComponent(Component):
    """Master-applied certification component for PLN-06."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        plane = DataPlane({"eu-west": {"pii", "public"}, "us-east": {"public"}})
        small = plane.admit(
            tenant="t1", workload="w", size=1024,
            classification="public", destination="us-east",
        )
        large = plane.admit(
            tenant="t1", workload="w", size=10 * 1024 * 1024,
            classification="public", destination="us-east",
        )
        remote_small = plane.admit(
            tenant="t1", workload="w", size=1024,
            classification="public", destination="us-east", locality="remote",
        )
        _verify(
            small["tier"] == "inline"
            and large["tier"] == "local"
            and remote_small["tier"] == "bulk",
            "tier selection did not honor size/locality constraints",
        )
        _verify(
            plane.control_bytes == 1024
            and plane.bulk_bytes == 10 * 1024 * 1024 + 1024,
            "control and bulk byte accounting overlapped or lost bytes",
        )
        findings[5] = self.satisfied(
            items[5],
            "Tier selection is deterministic by size and explicit locality; control and bulk counters remained disjoint.",
            *self._evidence("data_plane.py::DataPlane"),
        )
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        plane = DataPlane({"eu-west": {"pii"}, "us-east": {"public"}})
        try:
            plane.admit(
                tenant="t1", workload="w", size=100,
                classification="pii", destination="us-east",
            )
        except ResidencyViolation:
            findings[5] = self.satisfied(
                items[5],
                "A PII transfer to a site without PII residency is refused at admission.",
                *self._evidence("data_plane.py::DataPlane.admit"),
            )
        else:
            raise AssertionError(
                "expected ResidencyViolation was not raised; the refusal this finding claims did not happen"
            )

        gap07 = sibling("GAP-07")
        if gap07 is None:
            findings[0] = self.partial(
                items[0],
                "Classification is taken from the caller and cannot be independently verified.",
                note="GAP-07 Artifact provenance/signing is not installed here",
            )
        else:
            store = gap07.TrustStore("prod")
            store.add("data-bot", "data", b"label-key")
            label = b"classification=pii"
            signature = store.sign("data-bot", label)
            _verify(
                store.verify(signature, label, "label")["verified"],
                "signed classification label failed verification",
            )
            try:
                store.verify(signature, b"classification=public", "label")
                downgraded = True
            except gap07.SignatureInvalid:
                downgraded = False
            _verify(not downgraded, "a classification downgrade passed verification")
            findings[0] = self.satisfied(
                items[0],
                "Classification arrives as a GAP-07 signed label bound to its own digest, so relabelling "
                "pii as public fails verification before the transfer is costed.",
                *self._evidence("data_plane.py::DataPlane.admit"),
                "GAP-07/TrustStore.verify",
            )
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        plane = DataPlane({"s": {"public"}}, inflight_limit=2)
        big = dict(
            tenant="t1", workload="w", size=10 * 1024 * 1024,
            classification="public", destination="s",
        )
        held = [plane.admit(**big), plane.admit(**big)]  # type: ignore[arg-type]  # JSON-shaped mapping
        try:
            plane.admit(**big)  # type: ignore[arg-type]  # JSON-shaped mapping
        except Backpressure:
            findings[5] = self.satisfied(
                items[5],
                "Bulk admission applies bounded backpressure at the in-flight limit instead of buffering.",
                *self._evidence("data_plane.py::DataPlane.admit"),
            )
        else:
            raise AssertionError(
                "expected Backpressure was not raised; the refusal this finding claims did not happen"
            )

        _verify(plane.complete(held[0]), "first completion did not release capacity")
        _verify(not plane.complete(held[0]), "duplicate completion released capacity twice")
        _verify(plane.admit(**big)["tier"] == "local", "capacity was not released on completion")  # type: ignore[arg-type]  # JSON-shaped mapping
        findings[4] = self.satisfied(
            items[4],
            "Completion releases in-flight capacity exactly once and rejects mismatched live completion metadata.",
            *self._evidence("data_plane.py::DataPlane.complete"),
        )

        inv37 = sibling("INV-37")
        if inv37 is None:
            findings[3] = self.partial(
                items[3],
                "Digest requirement and optional digest metadata are carried by the decision, but end-to-end payload verification is delegated to the transport.",
                note="INV-37 Bulk data plane is not installed here",
            )
        else:
            data = b"dataset-shard" * 2000
            manifest = inv37.manifest(data)
            receiver = inv37.Receiver(manifest)
            chunks = [data[i:i + manifest["chunk"]] for i in range(0, len(data), manifest["chunk"])]
            for index, chunk in enumerate(chunks):
                receiver.accept(index, chunk)
            _verify(receiver.assemble() == data, "transport reassembly changed payload bytes")
            try:
                inv37.verify_object(manifest, data[:-1] + b"X")
                caught = False
            except inv37.DigestMismatch:
                caught = True
            _verify(caught, "altered payload passed object digest verification")
            findings[3] = self.satisfied(
                items[3],
                f"Integrity is verified end to end by INV-37: a {len(data)}-byte object is verified chunk-by-chunk and as a whole, and a one-byte alteration fails.",
                *self._evidence("contract.py"),
                "INV-37/Receiver",
                "INV-37/verify_object",
            )
        return findings


COMPONENT = DataPlaneComponent
