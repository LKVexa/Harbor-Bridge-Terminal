"""INV-05 - Current control-state system.

The current control-state system is the consistent key-value store every controller reads and writes: each change gets a revision number, updates are compare-and-swap, and controllers watch for changes from a revision onward. The trap is compaction -- a watcher that asks for history that has been discarded must be told so, not silently given a gap.

The framework component integrates with all 100 INV-05 checklist requirements.
The behavior-specific bands below exercise the element's own state semantics;
full 100-item evaluation additionally requires the external ``pk_core`` framework.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .state import Compacted, ControlState


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``.

    Bare ``assert`` statements are stripped by the optimiser, which silently turned
    exercised checks into declared-only ones (and, where an assert carried a side
    effect, broke the element outright).  Every check goes through here instead.
    """
    if not condition:
        raise AssertionError(message)


class CurrentControlStateSystemComponent(Component):
    """Master-applied component for INV-05."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        s = ControlState()
        _verify(s.txn({"lease/a": 0}, {"lease/a": "node-1"}), "check failed: s.txn({'lease/a': 0}, {'lease/a': 'node-1'})")
        rev = s.data["lease/a"][1]
        _verify(s.txn({"lease/a": rev}, {"lease/a": "node-2"}), "check failed: s.txn({'lease/a': rev}, {'lease/a': 'node-2'})")
        _verify(not s.txn({"lease/a": rev}, {"lease/a": "node-3"}), "check failed: not s.txn({'lease/a': rev}, {'lease/a': 'node-3'})")
        _verify(s.data["lease/a"][0] == "node-2", "check failed: s.data['lease/a'][0] == 'node-2'")
        findings[0] = self.satisfied(
            items[0],
            "Writes are compare-and-swap on the key's revision: two controllers acting on the same "
            "revision cannot both win, so the second is refused and the first holder keeps the lease.",
            *self._evidence("state.py::ControlState.txn"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        s = ControlState()
        for i in range(10):
            _verify(s.txn({}, {f"k{i}": i}), f"failed to write k{i}")
        _verify(len(s.watch(5)) == 6, 'check failed: len(s.watch(5)) == 6')
        dropped = s.compact(6)
        gap = False
        try:
            s.watch(5)
        except Compacted:
            gap = True
        _verify(gap and dropped == 6 and [h[0] for h in s.watch(7)] == [7, 8, 9, 10], 'check failed: gap and dropped == 6 and ([h[0] for h in s.watch(7)] == [7, 8, 9, 10])')
        findings[0] = self.satisfied(
            items[0],
            f"After compaction discards {dropped} old revisions, a controller asking to resume from a "
            "discarded revision is told explicitly to relist instead of being handed a stream with a "
            "silent gap; watches after the compaction point still receive every change.",
            *self._evidence("state.py::ControlState.watch", "state.py::ControlState.compact"))
        return findings

COMPONENT = CurrentControlStateSystemComponent
