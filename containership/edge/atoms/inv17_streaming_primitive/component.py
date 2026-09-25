"""INV-17 - Streaming primitive.

The streaming primitive carries many values over time through one typed handle. What makes it worth having as a primitive rather than a convention is that backpressure, end-of-stream and the reader's disappearance are all part of the type -- a writer that ignores a closed reader gets an error, not a silently discarded value.

The component answers all 100 requirements of the INV-17 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
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



from .stream import (
    CreditExhausted,
    ElementTypeMismatch,
    EndDropped,
    Stream,
)


class StreamingPrimitiveComponent(Component):
    """Master-applied component for INV-17."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        s = Stream(str)
        s.grant(2)
        s.write("a")
        s.write("b")
        stalled = False
        try:
            s.write("c")
        except CreditExhausted:
            stalled = True
        _verify(stalled and len(s.buffer) == 2, 'check failed: stalled and len(s.buffer) == 2')
        findings[0] = self.satisfied(
            items[0],
            f"The writer may only place as many elements as the reader granted ({len(s.buffer)} buffered "
            f"against 2 credit, {s.credit_stalls} stall); a slow reader bounds memory instead of growing "
            "the buffer.",
            *self._evidence("component.py::Stream.write"))

        typed = False
        s.grant(1)
        try:
            s.write(42)
        except ElementTypeMismatch:
            typed = True
        _verify(typed, 'check failed: typed')
        findings[1] = self.satisfied(
            items[1],
            "The element type is part of the stream, so a wrong-typed value is refused at the write rather "
            "than discovered by the reader.",
            *self._evidence("component.py::Stream.write"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        s = Stream(str)
        s.grant(1)
        s.drop_reader()
        errored = False
        try:
            s.write("a")
        except EndDropped:
            errored = True
        _verify(errored, 'check failed: errored')

        t = Stream(str)
        t.grant(1)
        t.write("a")
        t.end()
        _verify(t.read() == "a" and t.read() is None, "check failed: t.read() == 'a' and t.read() is None")
        findings[1] = self.satisfied(
            items[1],
            "A write after the reader is dropped errors on the first attempt, and end-of-stream is an "
            "explicit signal the reader observes as None rather than an inference from silence.",
            *self._evidence("component.py::Stream.write", "component.py::Stream.end"))
        return findings

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        s = Stream(int)
        peak = 0
        for i in range(100):
            s.grant(1)
            s.write(i)
            peak = max(peak, len(s.buffer))
            s.read()
        _verify(peak == 1 and s.transferred == 100, 'check failed: peak == 1 and s.transferred == 100')
        findings[0] = self.satisfied(
            items[0],
            f"Over {s.transferred} elements with credit granted one at a time the in-flight buffer never "
            f"exceeded {peak} element, so memory is a function of granted credit and not of stream length.",
            *self._evidence("component.py::Stream"))
        return findings

COMPONENT = StreamingPrimitiveComponent
