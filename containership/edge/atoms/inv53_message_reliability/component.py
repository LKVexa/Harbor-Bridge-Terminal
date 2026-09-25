"""INV-53 - Message reliability component integration.

The framework-independent state machine lives in :mod:`.reliability`; this file
binds it to ``pk_core`` and supplies behavioural evidence for the master checklist.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .reliability import IdempotentConsumer, ReliableQueue


def _verify(condition: bool, message: str = "behavioural check failed") -> None:
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class MessageReliabilityComponent(Component):
    """Master-applied component for INV-53."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)

        q = ReliableQueue(visibility=5)
        q.put({"id": "m1", "data": 1})
        first = q.receive(now=0)  # consumer takes it, then crashes without ack
        _verify(first is not None, "first delivery missing")
        _verify(q.receive(now=1) is None, "message became visible before deadline")
        again = q.receive(now=6)
        _verify(again is not None and again.message_id == "m1", "message was not redelivered")
        _verify(q.redeliveries == 1, "redelivery counter did not advance")
        _verify(not q.ack(first, now=6), "stale lease was able to acknowledge a newer delivery")
        _verify(q.ack(again, now=6), "current lease acknowledgement failed")
        findings[0] = self.satisfied(
            items[0],
            "A crashed consumer cannot lose a message: the lease expires, the message is redelivered under "
            "a new fencing token, a stale acknowledgement is rejected, and only the active lease can settle it.",
            *self._evidence(
                "reliability.py::ReliableQueue.receive",
                "reliability.py::ReliableQueue._expire_locked",
                "reliability.py::ReliableQueue.ack",
            ),
        )

        p = ReliableQueue(visibility=1, max_attempts=3)
        p.put({"id": "poison"})
        _verify(p.receive(now=0) is not None, "poison attempt 1 missing")
        _verify(p.receive(now=1) is not None, "poison attempt 2 missing")
        _verify(p.receive(now=2) is not None, "poison attempt 3 missing")
        _verify(p.receive(now=3) is None, "poison message exceeded delivery cap")
        dlq = p.dlq
        _verify(len(dlq) == 1 and dlq[0].attempts == 3, "dead-letter attempt history incorrect")
        findings[1] = self.satisfied(
            items[1],
            f"A message that fails every time is delivered exactly {p.max_attempts} times and then parked "
            "in the dead-letter queue with the terminal reason and attempt count, instead of looping forever.",
            *self._evidence("reliability.py::ReliableQueue._expire_locked", "reliability.py::DeadLetter"),
        )
        return findings

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        consumer = IdempotentConsumer(max_entries=10)
        msg = {"id": "m9"}
        _verify(consumer.handle(msg), "first unique effect was not admitted")
        _verify(not consumer.handle(msg), "duplicate effect was admitted")
        _verify(consumer.effects == 1 and consumer.skipped == 1, "dedupe counters incorrect")
        findings[0] = self.satisfied(
            items[0],
            "At-least-once delivery is paired with scope-aware consumer deduplication by message id: a "
            "redelivered message is recognised and produces no second reference effect. The in-memory "
            "reference is hard-bounded and fails closed at capacity.",
            *self._evidence("reliability.py::IdempotentConsumer"),
        )
        return findings


COMPONENT = MessageReliabilityComponent
