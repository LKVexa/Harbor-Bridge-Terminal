"""INV-15 - New asynchronous ABI checklist/certification integration."""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .abi import (
    AsyncAbi,
    BudgetExhausted,
    ForeignHandle,
    HandleConsumed,
    SubtaskNotReady,
)
from .contract import ELEMENT_ID, ELEMENT_NAME, build


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class NewAsynchronousAbiComponent(Component):
    """Master-applied component for INV-15."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        abi = AsyncAbi("inst-1", budget=2)
        kind, first = abi.call()
        abi.call()
        refused = False
        try:
            abi.call()
        except BudgetExhausted:
            refused = True
        _verify(
            kind == "subtask" and refused and abi.blocked_stacks == 0,
            "subtask allocation/backpressure/nonblocking invariant failed",
        )
        findings[0] = self.satisfied(
            items[0],
            f"A call returns an instance-scoped subtask handle rather than parking a stack "
            f"({abi.blocked_stacks} stacks blocked with {abi.open_subtasks} calls outstanding), and "
            f"the {abi.budget}-call budget refuses the next call instead of growing without bound.",
            *self._evidence("abi.py::AsyncAbi.call"),
        )

        abi2 = AsyncAbi("inst-2")
        _, h = abi2.call()
        premature = False
        try:
            abi2.take(h)
        except SubtaskNotReady:
            premature = True
        _verify(premature, "pending subtask was consumable")
        abi2.complete(h, None)
        _verify(abi2.wait(iter([h])) == [h], "one-shot wait iterator lost readiness")
        _verify(abi2.take(h) is None, "None result was not preserved")
        reused = False
        try:
            abi2.take(h)
        except HandleConsumed:
            reused = True
        _verify(reused, "consumed handle was reusable")
        findings[1] = self.satisfied(
            items[1],
            "Readiness is read from the host-owned table; one-shot wait iterators are consumed exactly "
            "once, pending values cannot be taken, None is a valid payload, and retired handles are rejected.",
            *self._evidence("abi.py::AsyncAbi.wait"),
        )
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        a, b = AsyncAbi("inst-1"), AsyncAbi("inst-2")
        _, h_a = a.call()
        _, h_b = b.call()
        _verify(h_a.sequence == h_b.sequence and h_a != h_b, "per-handle tokens did not disambiguate handles")
        stolen = False
        try:
            b.wait([h_a])
        except ForeignHandle:
            stolen = True
        _verify(stolen, "cross-instance handle was accepted")
        findings[3] = self.satisfied(
            items[3],
            "Every subtask handle carries a fresh 128-bit random token in addition to its diagnostic sequence. Two instances may "
            "mint the same sequence number without making either handle valid in the other instance, and possession of one handle does not authorize synthesis of another.",
            *self._evidence("abi.py::SubtaskHandle"),
        )
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        abi = AsyncAbi("inst-1")
        pending = [abi.call()[1] for _ in range(2)]
        _, ready = abi.call()
        abi.complete(ready, "done")
        cancelled = abi.cancel_all("caller gone")
        _verify(cancelled == len(pending), "not every pending subtask was cancelled")
        _verify(abi.open_subtasks == 0, "caller loss leaked live table rows")
        _verify(abi.abandoned_ready == 1, "ready unread result was not released")
        findings[2] = self.satisfied(
            items[2],
            f"Caller loss cancelled {cancelled} pending subtasks and retired the already-ready unread result, "
            "leaving zero live waitable-table rows.",
            *self._evidence("abi.py::AsyncAbi.cancel_all"),
        )
        return findings


COMPONENT = NewAsynchronousAbiComponent
