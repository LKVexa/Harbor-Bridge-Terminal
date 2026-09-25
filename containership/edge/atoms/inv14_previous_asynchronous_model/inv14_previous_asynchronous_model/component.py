"""INV-14 - Previous asynchronous model.

The previous asynchronous model is the poll-based one: a component hands the host a list of pollables and blocks until one is ready. It works, it is simple, and it does not compose -- which is exactly why the new ABI exists. This element keeps it running honestly while it is still deployed, and states what it cannot do.

The component answers all 100 requirements of the INV-14 checklist.  Bands
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



from .polling import (
    ForeignPollable, MIGRATION_TARGET, PollSet, Pollable,
)


class PreviousAsynchronousModelComponent(Component):
    """Master-applied component for INV-14."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        a, b = Pollable("net", "inst-1"), Pollable("timer", "inst-1")
        ps = PollSet("inst-1")
        idle = ps.poll([a, b], timeout_ticks=10)
        _verify(idle["timed_out"] and idle["deprecated"], "check failed: idle['timed_out'] and idle['deprecated']")
        b.signal()
        woken = ps.poll([a, b], timeout_ticks=10)
        _verify(woken["ready"] == ["timer"] and not woken["timed_out"], "check failed: woken['ready'] == ['timer'] and (not woken['timed_out'])")
        findings[5] = self.satisfied(
            items[5],
            "Polling is bounded and deterministic: an idle set times out, and a signalled pollable is "
            f"reported ready. Every result carries the deprecation and names {MIGRATION_TARGET}.",
            *self._evidence("polling.py::PollSet.poll"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        p = Pollable("net", "inst-1")
        ps = PollSet("inst-1")
        p.signal()                      # readiness races the poll
        result = ps.poll([p], timeout_ticks=5)
        _verify(result["ready"] == ["net"], "a wakeup that raced the poll was lost")
        findings[0] = self.satisfied(
            items[0],
            "A readiness signal that arrives while a poll is in flight is folded in before the verdict, "
            "so the classic lost-wakeup stall cannot happen.",
            *self._evidence("polling.py::PollSet.poll"))
        proven = []
        for label, args in [("unbounded blocking", ([Pollable("x", "inst-1")], 0)),
                            ("empty set", ([], 10))]:
            try:
                ps.poll(args[0], timeout_ticks=args[1])
            except ValueError:
                proven.append(label)
        _verify(len(proven) == 2, 'check failed: len(proven) == 2')
        findings[5] = self.satisfied(
            items[5],
            f"Both ways of blocking forever are refused ({', '.join(proven)}), so the legacy model cannot "
            "be used to pin a component.",
            *self._evidence("polling.py::PollSet.poll"))
        return findings

    def assess_architecture(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_architecture(items)
        ps = PollSet("inst-1")
        try:
            ps.poll([Pollable("other", "inst-2")], timeout_ticks=5)
        except ForeignPollable:
            findings[7] = self.satisfied(
                items[7],
                "Pollables do not cross component boundaries -- that non-composability is the model's "
                "defining limit and the reason INV-15 exists, so it is enforced rather than papered over.",
                *self._evidence("polling.py::PollSet.poll", "contract.py"))
        else:
            raise AssertionError('expected ForeignPollable was not raised; the refusal this finding claims did not happen')
        return findings

    def assess_operations(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_operations(items)
        ps = PollSet("inst-1")
        ps.poll([Pollable("a", "inst-1")], timeout_ticks=1)
        ps.poll([Pollable("b", "inst-1")], timeout_ticks=1)
        _verify(ps.deprecated_uses == 2, 'check failed: ps.deprecated_uses == 2')
        findings[8] = self.satisfied(
            items[8],
            f"Deprecated use is counted per instance ({ps.deprecated_uses} so far), so migration progress "
            "off this model is a measurable number rather than an intention.",
            *self._evidence("polling.py::PollSet"))
        return findings

COMPONENT = PreviousAsynchronousModelComponent
