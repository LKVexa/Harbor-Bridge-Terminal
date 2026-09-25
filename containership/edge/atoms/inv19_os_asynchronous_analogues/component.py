"""INV-19 - OS asynchronous analogues.

OS asynchronous analogues are the mapping between the component world's streams and futures and what the host operating system actually offers -- epoll, kqueue, io_uring, IOCP. Each has a different shape (readiness versus completion), and the mapping has to be honest about which, because a readiness API pretending to be a completion API loses errors.

The component answers all 100 requirements of the INV-19 checklist.  Bands
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



from .backend import BACKENDS, FALLBACK, AsyncBackend, DescriptorBudget, NoBackend, select


class OsAsynchronousAnaloguesComponent(Component):
    """Master-applied component for INV-19."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        _verify(select(["epoll", "io_uring"]) == "io_uring", "check failed: select(['epoll', 'io_uring']) == 'io_uring'")
        _verify(select(["epoll"]) == "epoll", "check failed: select(['epoll']) == 'epoll'")
        _verify(select([]) == FALLBACK, 'check failed: select([]) == FALLBACK')
        _verify(select(["something-invented"]) == FALLBACK, "check failed: select(['something-invented']) == FALLBACK")
        findings[0] = self.satisfied(
            items[0],
            "The backend is detected rather than assumed: completion mechanisms are preferred, a readiness "
            f"mechanism is used when that is all there is, and an empty or unrecognised set falls back to "
            f"'{FALLBACK}', which is available by construction.",
            *self._evidence("backend.py::select", "backend.py::BACKENDS"))

        comp = AsyncBackend("io_uring")
        comp.arm(3)
        comp.post(3, None, error="ECONNRESET")
        ready = AsyncBackend("epoll")
        ready.arm(3)
        ready.post(3, None, error="ECONNRESET")
        _verify(comp.reap(3) == ("error", "ECONNRESET"), "check failed: comp.reap(3) == ('error', 'ECONNRESET')")
        _verify(ready.reap(3) == ("retry", None), "check failed: ready.reap(3) == ('retry', None)")
        findings[1] = self.satisfied(
            items[1],
            "Each backend is mapped according to its real semantics class: a completion backend delivers "
            "the error with the event, while a readiness backend returns 'retry' because it genuinely "
            "cannot carry one -- the error is surfaced by re-attempting, not invented.",
            *self._evidence("backend.py::AsyncBackend.post", "backend.py::AsyncBackend.reap"))
        return findings

    def assess_interfaces(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_interfaces(items)
        outcomes = set()
        for name in BACKENDS:
            b = AsyncBackend(name)
            b.arm(1)
            b.post(1, "payload")
            outcomes.add(b.reap(1)[0])
        _verify(outcomes <= {"value", "retry"}, "check failed: outcomes <= {'value', 'retry'}")
        findings[3] = self.satisfied(
            items[3],
            f"Across all {len(BACKENDS)} backends a successful event reaches the component as one of the "
            f"same small tagged set {sorted(outcomes)}, so guest-visible behaviour does not vary with the "
            "host kernel.",
            *self._evidence("backend.py::AsyncBackend.reap"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        b = AsyncBackend("epoll", max_descriptors=2)
        b.arm(1)
        b.arm(2)
        bounded = False
        try:
            b.arm(3)
        except DescriptorBudget:
            bounded = True
        _verify(bounded, 'check failed: bounded')
        findings[2] = self.satisfied(
            items[2],
            f"Armed descriptors are bounded ({b.max_descriptors} here); the arm past the budget is refused "
            "rather than letting one workload consume the host's descriptor table.",
            *self._evidence("backend.py::AsyncBackend.arm"))
        return findings

COMPONENT = OsAsynchronousAnaloguesComponent
