"""INV-18 - Completion primitive.

The completion primitive is the one-shot counterpart to a stream: exactly one value, delivered once, to exactly one receiver. Having it as its own type rather than a stream of length one means the compiler knows there is no second value coming, so the receiver needs no loop and the writer cannot accidentally send twice.

The component answers all 100 requirements of the INV-18 checklist.  Bands
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



from .future import Abandoned, AlreadyResolved, AlreadyTaken, Future


class CompletionPrimitiveComponent(Component):
    """Master-applied component for INV-18."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        f = Future(str)
        f.resolve("done")
        twice = False
        try:
            f.resolve("again")
        except AlreadyResolved:
            twice = True
        _verify(twice and f.take() == ("ok", "done"), "check failed: twice and f.take() == ('ok', 'done')")
        second = False
        try:
            f.take()
        except AlreadyTaken:
            second = True
        _verify(second, 'check failed: second')
        findings[0] = self.satisfied(
            items[0],
            "A future resolves at most once and is taken by at most one receiver; the second resolution "
            "and the second take both raise rather than overwriting or duplicating the value.",
            *self._evidence("component.py::Future.resolve", "component.py::Future.take"))

        e = Future(str)
        e.resolve_error("upstream refused")
        _verify(e.take() == ("error", "upstream refused"), "check failed: e.take() == ('error', 'upstream refused')")
        findings[1] = self.satisfied(
            items[1],
            "An error resolution is an ordinary outcome carried in the same handle, so a receiver reads a "
            "tagged result rather than distinguishing failure by a side channel.",
            *self._evidence("component.py::Future.resolve_error"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        f = Future(str)
        f.abandon()
        orphaned = False
        try:
            f.take()
        except Abandoned:
            orphaned = True
        _verify(orphaned, 'check failed: orphaned')
        findings[0] = self.satisfied(
            items[0],
            "A writer dropped without resolving raises on the receiver instead of leaving it waiting "
            "forever, so an abandoned completion is a failure the caller can handle.",
            *self._evidence("component.py::Future.take"))
        return findings

    def assess_interfaces(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_interfaces(items)
        f = Future(int)
        wrong = False
        try:
            f.resolve("not an int")
        except TypeError:
            wrong = True
        _verify(wrong and not f.resolved, 'check failed: wrong and (not f.resolved)')
        findings[1] = self.satisfied(
            items[1],
            "The value type is part of the handle, so a mistyped resolution is refused and leaves the "
            "future unresolved rather than delivering a value the receiver cannot lift.",
            *self._evidence("component.py::Future.resolve"))
        return findings

COMPONENT = CompletionPrimitiveComponent
