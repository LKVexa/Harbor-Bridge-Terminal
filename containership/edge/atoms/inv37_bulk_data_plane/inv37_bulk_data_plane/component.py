"""pk_core adapter for INV-37 - Bulk data plane.

The dependency-free implementation lives in :mod:`data_plane`; this module only
maps exercised behavior into the shared Post-Kubernetes checklist framework.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .data_plane import CHUNK, BoundedTransferPool, Receiver, manifest
from .errors import AdmissionRejected, DigestMismatch, TransferIncomplete


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class BulkDataPlaneComponent(Component):
    """Master-applied component for INV-37."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        data = bytes(range(256)) * 64
        m = manifest(data)
        rx = Receiver(m)
        chunks = [data[i : i + CHUNK] for i in range(0, len(data), CHUNK)]
        refused = False
        try:
            rx.accept(0, b"corrupt" + chunks[0][7:])
        except DigestMismatch:
            refused = True
        else:
            _verify(False, "corrupted chunk was accepted")
        for i, chunk in enumerate(chunks):
            rx.accept(i, chunk)
        _verify(refused and rx.assemble() == data, "integrity exercise failed")

        pool = BoundedTransferPool(max_active=1)
        bounded = False
        with pool.slot():
            try:
                with pool.slot(timeout=0):
                    pass
            except AdmissionRejected:
                bounded = True
            else:
                _verify(False, "concurrency limit was not enforced")
        _verify(bounded, "bounded concurrency exercise failed")

        findings[0] = self.satisfied(
            items[0],
            f"A {len(data)}-byte object crosses as {len(chunks)} digested chunks; corrupted chunks are "
            "refused, the assembled object is re-verified end to end, and transfer admission is bounded.",
            *self._evidence("data_plane.py::Receiver", "data_plane.py::verify_object", "data_plane.py::BoundedTransferPool"),
        )
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        data = b"w" * (CHUNK * 5 + 17)
        m = manifest(data)
        rx = Receiver(m)
        chunks = [data[i : i + CHUNK] for i in range(0, len(data), CHUNK)]
        for i in (0, 1, 2):
            rx.accept(i, chunks[i])
        todo = rx.missing()
        partial_refused = False
        try:
            rx.assemble()
        except TransferIncomplete:
            partial_refused = True
        else:
            _verify(False, "partial object was accepted")
        for i in todo:
            rx.accept(i, chunks[i])
        _verify(
            partial_refused and todo == [3, 4, 5] and rx.assemble() == data,
            "resume exercise failed",
        )
        findings[0] = self.satisfied(
            items[0],
            f"An interrupted transfer resumes by re-sending only the {len(todo)} unverified chunks; a "
            "partial object is refused and the resume token identifies the contiguous verified prefix.",
            *self._evidence("data_plane.py::Receiver.missing", "data_plane.py::Receiver.resume_token", "data_plane.py::Receiver.assemble"),
        )
        return findings


COMPONENT = BulkDataPlaneComponent
