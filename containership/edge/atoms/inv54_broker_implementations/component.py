"""INV-54 - Broker implementations.

Broker implementations are the concrete engines behind the messaging contract. Two ship here: a fan-out broker that copies each message to every subscriber, and a partitioned log that keeps per-key order and lets consumers replay from an offset. They make opposite trade-offs, and the contract is only portable if both pass the same checks.

The component maps the 100 INV-54 checklist items into conformance findings.
Selected bands are overridden below so core reference-broker semantics are
exercised rather than supported only by declarations.
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



from .brokers import FanoutBroker, PartitionedLog


class BrokerImplementationsComponent(Component):
    """Master-applied component for INV-54."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        log = PartitionedLog()
        for i in range(20):
            for acct in ("acct-a", "acct-b", "acct-c"):
                log.append(acct, (acct, i))
        for acct in ("acct-a", "acct-b", "acct-c"):
            p = log.partition_for(acct)
            seq = [m[1] for k, m in log.poll("reader", p, 10_000) if k == acct]
            log.seek("reader", p, 0)
            _verify(seq == list(range(20)), 'check failed: seq == list(range(20))')
        findings[0] = self.satisfied(
            items[0],
            "Messages for each key land in one partition and are read back in publish order (20 per "
            "account across 3 interleaved accounts), so per-key state machines never see reordering.",
            *self._evidence("brokers.py::PartitionedLog"))

        fan = FanoutBroker()
        a, b = fan.subscribe("a"), fan.subscribe("b")
        for i in range(5):
            fan.publish(i)
        _verify(a == b == list(range(5)), 'check failed: a == b == list(range(5))')
        findings[1] = self.satisfied(
            items[1],
            "The fan-out broker delivers every message to every subscriber, identical and complete.",
            *self._evidence("brokers.py::FanoutBroker"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        log = PartitionedLog(partitions=1)
        for i in range(6):
            log.append("k", i)
        log.poll("c1", 0)
        log.poll("c2", 0, limit=2)
        log.seek("c1", 0, 3)
        replay = [m for _, m in log.poll("c1", 0)]
        _verify(replay == [3, 4, 5] and log.offsets[("c2", 0)] == 2, "check failed: replay == [3, 4, 5] and log.offsets['c2', 0] == 2")
        findings[0] = self.satisfied(
            items[0],
            "A consumer can rewind and replay from a retained offset after a bad deploy, and doing so "
            "leaves every other consumer's position untouched.",
            *self._evidence("brokers.py::PartitionedLog.seek"))
        return findings

COMPONENT = BrokerImplementationsComponent
