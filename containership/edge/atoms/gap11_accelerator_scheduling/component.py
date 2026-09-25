"""GAP-11 - Accelerator scheduling.

Accelerator scheduling treats a GPU, NPU, FPGA, or other declared accelerator as an exclusive, attestable resource rather than a divisible number. A device is either wholly assigned, partitioned into declared slices, or not available -- and a device is scrubbed between tenants before it is handed on.

The component integrates with the 100-requirement GAP-11 checklist. Bands
whose defaults would merely restate the contract are overridden below so key
claims are backed by exercised allocator behaviour. Production-completeness
gaps are tracked separately in ``MISSING_COMPONENTS.md``.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build

def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``.

    Bare ``assert`` statements are stripped by the optimiser, which silently turned
    exercised checks into declared-only ones (and, where an assert carried a side
    effect, broke the element outright).  Every check goes through here instead.
    """
    if not condition:
        raise AssertionError(message)



from .allocator import (
    Accelerator,
    AcceleratorPool,
    NoMatchingAccelerator,
    PartitionSpec,
    ScrubRequired,
    UndeclaredPartition,
)


class AcceleratorSchedulingComponent(Component):
    """Master-applied component for GAP-11."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        pool = AcceleratorPool([
            Accelerator("gpu0", "gen9", 24, frozenset({"fp8"}), partitions=(PartitionSpec("half", 12), PartitionSpec("quarter", 6))),
            Accelerator("gpu1", "gen9", 80, frozenset({"fp8", "nvlink"})),
        ])
        small = pool.allocate(tenant="t1", workload="w1", memory_gb=16, features={"fp8"})
        _verify(small["device"] == "gpu0", "did not choose the smallest sufficient device")
        big = pool.allocate(tenant="t1", workload="w2", memory_gb=64, features={"nvlink"})
        _verify(big["device"] == "gpu1", "check failed: big['device'] == 'gpu1'")
        findings[5] = self.satisfied(
            items[5],
            "Allocation matches generation, memory and features and picks the smallest sufficient device, "
            "leaving larger accelerators for workloads that need them.",
            *self._evidence("component.py::AcceleratorPool.allocate"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        pool = AcceleratorPool([Accelerator("gpu0", "gen9", 24)])
        pool.allocate(tenant="t1", workload="w1")
        try:
            pool.allocate(tenant="t2", workload="w2")
        except NoMatchingAccelerator:
            findings[5] = self.satisfied(
                items[5],
                "An allocated device is invisible to another tenant's request: there is no path to "
                "concurrent cross-tenant allocation.",
                *self._evidence("component.py::AcceleratorPool.allocate"))
        else:
            raise AssertionError('expected NoMatchingAccelerator was not raised; the refusal this finding claims did not happen')
        pool.release("gpu0")
        try:
            pool.allocate(tenant="t2", workload="w2")
        except ScrubRequired:
            findings[2] = self.satisfied(
                items[2],
                "A released device is dirty by default: handing it to a different tenant is refused until "
                "a scrub completes, closing the residual-data path.",
                *self._evidence("component.py::AcceleratorPool.release"))
        else:
            raise AssertionError('expected ScrubRequired was not raised; the refusal this finding claims did not happen')
        pool.devices[0].scrub()
        _verify(pool.allocate(tenant="t2", workload="w2")["device"] == "gpu0", "check failed: pool.allocate(tenant='t2', workload='w2')['device'] == 'gpu0'")
        findings[6] = self.satisfied(
            items[6],
            "After a completed scrub the device serves the next tenant; the scrub is the gate, not a "
            "best-effort courtesy.",
            *self._evidence("component.py::Accelerator.scrub"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        pool = AcceleratorPool([Accelerator("gpu0", "gen9", 24, partitions=(PartitionSpec("half", 12),))])
        try:
            pool.allocate(tenant="t1", workload="w", partition="third")
        except UndeclaredPartition:
            findings[6] = self.satisfied(
                items[6],
                "A partition the device does not declare cannot be allocated, so the scheduler cannot "
                "invent slices the hardware does not enforce.",
                *self._evidence("component.py::AcceleratorPool.allocate"))
        else:
            raise AssertionError('expected UndeclaredPartition was not raised; the refusal this finding claims did not happen')
        pool.allocate(tenant="t1", workload="w")
        pool.release("gpu0")
        result = pool.devices[0].scrub(succeeds=False)
        _verify(result["quarantined"], "check failed: result['quarantined']")
        try:
            pool.allocate(tenant="t1", workload="w2")
        except ScrubRequired:
            findings[1] = self.satisfied(
                items[1],
                "A device whose scrub failed is quarantined and refused even to its previous tenant, "
                "degrading capacity rather than risking residue.",
                *self._evidence("component.py::Accelerator.scrub"))
        else:
            raise AssertionError('expected ScrubRequired was not raised; the refusal this finding claims did not happen')
        return findings

COMPONENT = AcceleratorSchedulingComponent
