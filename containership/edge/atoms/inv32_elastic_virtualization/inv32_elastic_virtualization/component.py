"""INV-32 - Elastic virtualization checklist adapter.

The safety-critical state machine lives in :mod:`model` so it can be exercised
without the inventory framework.  This adapter contributes executable evidence
for the checklist bands where the standalone package has concrete behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .model import (
    AuditIntegrityError,
    ElasticHost,
    FloorBreach,
    Guest,
    InvalidAdjustmentRecord,
    ReplayConflict,
    ReserveBreach,
    StaleAdjustment,
    UnknownGuest,
)


def _verify(condition: bool, message: str = "behavioural check failed") -> None:
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class ElasticVirtualizationComponent(Component):
    """Master-applied component for INV-32."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        host = ElasticHost("n1", total_mib=4096)
        host.add(Guest("g1", "t1", memory_mib=1024, floor_mib=256, ceiling_mib=2048))
        grown = host.adjust_memory("g1", 2048, operation_id="grow-g1")
        _verify(grown["applied_mib"] == 2048, "memory growth did not apply")
        shrunk = host.adjust_memory("g1", 512, operation_id="shrink-g1")
        _verify(shrunk["applied_mib"] == 512, "memory shrink did not apply")
        _verify(host.revert(shrunk, operation_id="undo-shrink-g1") == 2048, "revert failed")
        cpu = host.adjust_vcpus("g1", 2, operation_id="cpu-g1")
        _verify(cpu["applied_vcpus"] == 2, "vCPU hot-plug did not apply")
        _verify(host.revert(cpu, operation_id="undo-cpu-g1") == 1, "vCPU revert failed")
        _verify(host.verify_history(), "audit chain did not verify")
        snapshot = host.host_snapshot()
        _verify(snapshot["free_mib"] == host.free_mib, "host snapshot disagrees with live state")
        findings[5] = self.satisfied(
            items[5],
            "Memory and vCPU changes move in both directions within bounds, are reversible, and emit "
            "a hash-chained audit record while the host reserve remains enforced.",
            *self._evidence("model.py::ElasticHost"),
        )
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        host = ElasticHost("n1", total_mib=1024)
        host.add(Guest("g1", "t1", memory_mib=512, floor_mib=128, ceiling_mib=1024))
        try:
            host.adjust_memory("g1", 1024)
        except ReserveBreach:
            findings[5] = self.satisfied(
                items[5],
                f"Growth stops at the host reserve ({host.reserve_mib}MiB of {host.total_mib}MiB).",
                *self._evidence("model.py::ElasticHost.adjust_memory"),
            )
        else:
            raise AssertionError("expected ReserveBreach was not raised")
        try:
            host.adjust_memory("g1", 64)
        except FloorBreach:
            findings[1] = self.satisfied(
                items[1],
                "Reclaim below a guest's declared working-set floor is refused.",
                *self._evidence("model.py::ElasticHost.adjust_memory"),
            )
        else:
            raise AssertionError("expected FloorBreach was not raised")

        valid = host.adjust_vcpus("g1", 2, operation_id="cpu-security")
        forged = dict(valid)
        forged["reversible_to"] = 999
        try:
            host.revert(forged)
        except InvalidAdjustmentRecord:
            pass
        else:
            raise AssertionError("forged v2 rollback record was trusted")
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        host = ElasticHost("n1", total_mib=4096)
        host.add(
            Guest(
                "g1", "t1", memory_mib=1024, floor_mib=256, ceiling_mib=2048, cooperative=False
            )
        )
        record = host.adjust_memory("g1", 512, honoured=False, operation_id="noncoop-1")
        _verify(not record["honoured"] and record["applied_mib"] == 1024, "failed reclaim changed memory")
        claimed = host.adjust_memory("g1", 512, honoured=True, operation_id="noncoop-2")
        _verify(
            not claimed["honoured"] and claimed["applied_mib"] == 1024,
            "a non-cooperative guest was recorded as honouring reclaim",
        )
        host.add(Guest("g2", "t1", memory_mib=1024, floor_mib=256, ceiling_mib=2048))
        first = host.adjust_memory("g2", 1536, operation_id="idem")
        again = host.adjust_memory("g2", 1536, operation_id="idem")
        _verify(first == again, "same idempotency key did not replay the original result")
        try:
            host.adjust_memory("g2", 1400, operation_id="idem")
        except ReplayConflict:
            pass
        else:
            raise AssertionError("conflicting operation_id was accepted")
        later = host.adjust_memory("g2", 1400, operation_id="later")
        try:
            host.revert(first, operation_id="stale-undo")
        except StaleAdjustment:
            pass
        else:
            raise AssertionError("stale rollback overwrote newer state")
        _verify(host.revert(later, operation_id="undo-later") == 1536, "fresh rollback failed")
        findings[0] = self.satisfied(
            items[0],
            "Ballooning is cooperative: unhonoured reclaim leaves memory unchanged and is recorded as such.",
            *self._evidence("model.py::ElasticHost.adjust_memory"),
        )
        findings[4] = self.satisfied(
            items[4],
            "Adjustment IDs are replay-safe, conflicting replays are refused, stale rollbacks are fenced, "
            "and fresh adjustments remain reversible.",
            *self._evidence("model.py::ElasticHost.revert"),
        )
        return findings


COMPONENT = ElasticVirtualizationComponent

__all__ = [
    "COMPONENT",
    "ElasticVirtualizationComponent",
    "ElasticHost",
    "Guest",
    "ReserveBreach",
    "FloorBreach",
    "UnknownGuest",
    "InvalidAdjustmentRecord",
    "StaleAdjustment",
    "ReplayConflict",
    "AuditIntegrityError",
]
