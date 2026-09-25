"""INV-42 - Capability descriptors certification adapter.

The security-sensitive runtime is isolated in :mod:`descriptors`; this module
binds that behavior into the shared ``pk_core`` checklist/certification model.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .descriptors import (
    Descriptor,
    DescriptorClosed,
    DescriptorTable,
    ForeignDescriptor,
    InvalidDescriptor,
    TypeMismatch,
    WIRE_SCHEMA,
)


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class CapabilityDescriptorsComponent(Component):
    """Master-applied component for INV-42."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        table = DescriptorTable("w1")
        fd = table.open("stream", object())
        wire = fd.to_wire()
        _verify(wire["schema"] == WIRE_SCHEMA, "wire schema is not current")
        _verify("auth" in wire, "wire descriptor is not authenticated")
        # C033: secure defaults. Authentication and bounded allocation are on
        # by default and cannot be disabled with a configuration switch.
        findings[2] = self.satisfied(
            items[2],
            "Secure defaults are intrinsic: every opened descriptor is authenticated with a "
            "table-local key and both live and per-session allocation are bounded.",
            *self._evidence("descriptors.py::DescriptorTable.open"),
        )
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        mine, theirs = DescriptorTable("w1"), DescriptorTable("w2")
        fd = theirs.open("stream", object())
        try:
            mine.resolve(fd)
        except ForeignDescriptor:
            findings[5] = self.satisfied(
                items[5],
                "A descriptor issued by another workload's table is refused, preserving workload "
                "isolation even when descriptor numbers collide.",
                *self._evidence("descriptors.py::DescriptorTable.resolve"),
            )
        else:
            raise AssertionError("expected ForeignDescriptor was not raised")

        table = DescriptorTable("w3")
        first = table.open("stream", "A")
        forged = Descriptor(
            first.number,
            first.resource_type,
            first.table_id,
            "0" * 64,
        )
        try:
            table.resolve(forged)
        except InvalidDescriptor:
            pass
        else:
            raise AssertionError("expected forged descriptor authentication to fail")

        table.close(first)
        second = table.open("socket", "B")
        _verify(second.number != first.number, "closed number was reused")
        try:
            table.resolve(first)
        except DescriptorClosed:
            findings[9] = self.satisfied(
                items[9],
                "Adversarial spoof/replay checks are exercised: altered authentication tags fail, "
                "and a valid stale descriptor remains permanently closed after subsequent allocation.",
                *self._evidence("descriptors.py::DescriptorTable._authenticate_locked"),
                *self._evidence("descriptors.py::DescriptorTable.close"),
            )
        else:
            raise AssertionError("expected DescriptorClosed was not raised")
        return findings

    def assess_interfaces(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_interfaces(items)
        table = DescriptorTable("w1")
        fd = table.open("stream", object())
        wire = fd.to_wire()
        _verify(table.from_wire(wire) == fd, "v2 wire round-trip failed")
        findings[1] = self.satisfied(
            items[1],
            f"The externally visible descriptor uses the explicit versioned schema {WIRE_SCHEMA}; "
            "the parser rejects unknown fields and unauthenticated v1 payloads.",
            *self._evidence("descriptors.py::DescriptorTable.from_wire"),
        )
        findings[3] = self.satisfied(
            items[3],
            "Resolution requires possession of a descriptor authenticated by the issuing table; a "
            "number, table id and claimed type are insufficient to exercise authority.",
            *self._evidence("descriptors.py::DescriptorTable._authenticate_locked"),
        )
        try:
            table.resolve(fd, expect="socket")
        except TypeMismatch as exc:
            _verify(exc.code == "type_mismatch", "error code is not stable")
            findings[5] = self.satisfied(
                items[5],
                "Boundary failures use typed exceptions with stable machine-readable codes; type "
                "confusion is rejected instead of returning the wrong resource.",
                *self._evidence("descriptors.py::DescriptorError.as_dict"),
                *self._evidence("descriptors.py::DescriptorTable.resolve"),
            )
        else:
            raise AssertionError("expected TypeMismatch was not raised")
        return findings


COMPONENT = CapabilityDescriptorsComponent
