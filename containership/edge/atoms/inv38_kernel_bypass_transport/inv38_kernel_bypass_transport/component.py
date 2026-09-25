"""INV-38 - Kernel-bypass transport.

Kernel-bypass transport hands network or storage queues straight to user space, skipping the kernel copy. The speed comes from the application touching device-visible memory directly, which is exactly the danger: every access must fall inside a registered region, and the sealed end-to-end channel above it must not be weakened just because the path got faster.

The component answers all 100 requirements of the INV-38 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build

def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``.

    Bare ``assert`` statements are stripped by the optimiser, which silently turned
    exercised checks into declared-only ones (and, where an assert carried a side
    effect, broke the element outright).  Every check goes through here instead.
    """
    if not condition:
        raise AssertionError(message)



from .transport import BypassQueue, NotRegistered, OutOfBounds, RingFull


class KernelBypassTransportComponent(Component):
    """Master-applied component for INV-38."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        q = BypassQueue()
        key = q.register(0x1000, 0x1000)
        _verify(q.post(key, 0x1000, 512, b"ok") == "bypass", "check failed: q.post(key, 4096, 512, b'ok') == 'bypass'")
        escaped = False
        try:
            q.post(key, 0x1F00, 512, b"x")
        except OutOfBounds:
            escaped = True
        q.poll()
        q.deregister(key)
        stale = False
        try:
            q.post(key, 0x1000, 16, b"x")
        except NotRegistered:
            stale = True
        _verify(escaped and stale, 'check failed: escaped and stale')
        findings[0] = self.satisfied(
            items[0],
            "Every descriptor is bounds-checked against its registered region: one crossing the region's "
            "end is refused, and a key reused after deregistration is unknown to the device.",
            *self._evidence("transport.py::BypassQueue.post"))

        inv36 = sibling("INV-36")
        if inv36 is not None:
            a = inv36.Session("a", "b", b"s")
            b = inv36.Session("b", "a", b"s")
            q2 = BypassQueue()
            k2 = q2.register(0, 1 << 16)
            frame = a.seal(b"secret")
            q2.post(k2, 0, len(frame), frame)
            q2.poll()
            carried = q2.completions[0][1]
            _verify(b"secret" not in carried and b.open(carried) == b"secret", "check failed: b'secret' not in carried and b.open(carried) == b'secret'")
            findings[1] = self.satisfied(
                items[1],
                "The fast path carries INV-36 sealed frames without unsealing them: the bytes on the "
                "ring contain no plaintext and still open at the peer, so speed does not cost sealing.",
                *self._evidence("transport.py::BypassQueue"), "INV-36/Session")
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        q = BypassQueue(ring_size=2)
        k = q.register(0, 4096)
        q.post(k, 0, 8, b"1")
        q.post(k, 8, 8, b"2")
        full = False
        try:
            q.post(k, 16, 8, b"3")
        except RingFull:
            full = True
        drained = q.poll()
        down = BypassQueue(available=False)
        _verify(full and drained == 2 and down.post(0, 0, 1, b"z") == "kernel" and down.fallbacks == 1, "check failed: full and drained == 2 and (down.post(0, 0, 1, b'z') == 'kernel') and (down.fallbacks == 1)")
        findings[0] = self.satisfied(
            items[0],
            "A full ring refuses instead of dropping a completion, draining restores capacity, and when "
            "bypass is unavailable the same post falls back to the kernel path transparently.",
            *self._evidence("transport.py::BypassQueue.post", "transport.py::BypassQueue.poll"))
        return findings

COMPONENT = KernelBypassTransportComponent
