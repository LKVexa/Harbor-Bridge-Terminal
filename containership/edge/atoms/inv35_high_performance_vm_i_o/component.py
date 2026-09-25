"""INV-35 - High-performance VM I/O.

High-performance VM I/O is virtio done properly: shared-memory rings, notification suppression and a vhost-style datapath that keeps the VMM out of the hot path. Every one of those tricks is also a way for a guest to corrupt the host, so descriptor validation here is not optional.

The component binds the 100-item INV-35 checklist to the shared ``pk_core``
assessment framework. Security-critical datapath invariants are exercised here;
repository-level production readiness still depends on the evidence and missing
components documented by this package.
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



from .io_model import (
    MAX_CHAIN,
    QUEUE_DEPTH,
    Descriptor,
    DescriptorInvalid,
    MemoryRegion,
    QueueFull,
    VirtQueue,
)


class HighPerformanceVmIOComponent(Component):
    """Master-applied component for INV-35."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        regions = (MemoryRegion(0x10000, 0x10000),)
        q = VirtQueue("vq0", regions)
        chain = {0: Descriptor(0, 0x10000, 256, 1), 1: Descriptor(1, 0x10100, 256)}
        result = q.submit(chain, head=0)
        _verify(result["validated"] and result["bytes"] == 512 and result["descriptors"] == [0, 1], "check failed: result['validated'] and result['bytes'] == 512 and (result['descriptors'] == [0, 1])")
        findings[5] = self.satisfied(
            items[5],
            f"A two-descriptor chain is walked and every link bounds-checked before use "
            f"({result['bytes']} bytes across {len(result['descriptors'])} descriptors).",
            *self._evidence("component.py::VirtQueue.submit"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        regions = (MemoryRegion(0x10000, 0x1000),)
        q = VirtQueue("vq0", regions)
        proven = []
        try:
            q.submit({0: Descriptor(0, 0x0, 64)}, head=0)
        except DescriptorInvalid:
            proven.append("host-memory pointer")
        try:
            q.submit({0: Descriptor(0, 0x10000, 64, 1), 1: Descriptor(1, 0x10040, 64, 0)}, head=0)
        except DescriptorInvalid:
            proven.append("chain loop")
        try:
            q.submit({0: Descriptor(0, 0x10000, -1)}, head=0)
        except DescriptorInvalid:
            proven.append("negative length")
        try:
            q.submit({0: Descriptor(0, 0x10000, 64, 9)}, head=0)
        except DescriptorInvalid:
            proven.append("dangling next index")
        _verify(len(proven) == 4, proven)
        findings[6] = self.satisfied(
            items[6],
            f"Four hostile descriptor shapes are refused before dereference: {', '.join(proven)}. The guest "
            "controls the ring, so nothing on it is trusted without validation.",
            *self._evidence("component.py::VirtQueue.submit"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        regions = (MemoryRegion(0x10000, 0x100000),)
        q = VirtQueue("vq0", regions)
        chain = {0: Descriptor(0, 0x10000, 8)}
        for _ in range(QUEUE_DEPTH):
            q.submit(chain, head=0)
        try:
            q.submit(chain, head=0)
        except QueueFull:
            findings[5] = self.satisfied(
                items[5],
                f"In-flight work is bounded at {QUEUE_DEPTH} descriptors per queue, so a guest cannot "
                "flood the host by posting without limit.",
                *self._evidence("component.py::VirtQueue.submit"))
        else:
            raise AssertionError('expected QueueFull was not raised; the refusal this finding claims did not happen')
        # Two in flight: the first completion must notify even though suppression was requested.
        fresh = VirtQueue("vq1", regions)
        fresh.submit(chain, head=0)
        fresh.submit(chain, head=0)
        first = fresh.complete(guest_wants_notification=False)
        second = fresh.complete(guest_wants_notification=False)
        _verify(first["notified"] and not second["notified"], "check failed: first['notified'] and (not second['notified'])")
        findings[8] = self.satisfied(
            items[8],
            "Notification suppression only applies once the queue is drained: with work still pending the "
            "wakeup is sent anyway, so a suppressed notification can never strand the guest.",
            *self._evidence("component.py::VirtQueue.complete"))
        return findings

COMPONENT = HighPerformanceVmIOComponent
