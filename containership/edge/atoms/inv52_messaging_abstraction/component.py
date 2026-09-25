"""INV-52 - Messaging abstraction.

The messaging abstraction lets an application publish to a topic and subscribe to one without knowing the broker. Every message travels in one envelope -- id, source, type, time, data -- and subscriptions route by rule, with a dead-letter topic for what no rule or handler can take.

This module integrates the local reference runtime with the external ``pk_core``
audit framework.  It exercises selected implementation and security behavior;
production checklist completion still requires external evidence and adjacent
platform components.
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



from .runtime import IncompleteEnvelope, PubSub, TopicDenied, envelope


class MessagingAbstractionComponent(Component):
    """Master-applied component for INV-52."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        ps = PubSub()
        ps.allow("orders", "shop")
        big, small = [], []
        ps.subscribe("orders", lambda m: m["data"]["total"] >= 100, big)
        ps.subscribe("orders", lambda m: m["data"]["total"] < 100, small)
        ps.publish("shop", "orders", envelope("shop", "order.placed", {"total": 250}))
        ps.publish("shop", "orders", envelope("shop", "order.placed", {"total": 5}))
        ps.allow("audit", "shop")
        ps.publish("shop", "audit", envelope("shop", "audit.event", {}))
        _verify(len(big) == 1 and len(small) == 1 and len(ps.dead_letter) == 1, 'check failed: len(big) == 1 and len(small) == 1 and (len(ps.dead_letter) == 1)')
        findings[0] = self.satisfied(
            items[0],
            "Subscriptions route by content rule (large and small orders reach different handlers), and "
            "a message no rule accepts goes to the dead-letter topic with its reason instead of vanishing.",
            *self._evidence("runtime.py::PubSub.publish"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        ps = PubSub()
        ps.allow("payments", "billing")
        denied = incomplete = False
        try:
            ps.publish("shop", "payments", envelope("shop", "x", {}))
        except TopicDenied:
            denied = True
        try:
            ps.publish("billing", "payments", {"id": "1", "type": "t", "time": 0, "data": {}})
        except IncompleteEnvelope:
            incomplete = True
        _verify(denied and incomplete, 'check failed: denied and incomplete')
        findings[0] = self.satisfied(
            items[0],
            "Publishing is scoped per topic, and a message without a source is refused, so every message "
            "on a topic comes from an allowed app and can be traced back to it.",
            *self._evidence("runtime.py::PubSub.publish", "runtime.py::REQUIRED"))
        return findings

COMPONENT = MessagingAbstractionComponent
