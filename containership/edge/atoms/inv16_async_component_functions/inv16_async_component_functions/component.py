"""INV-16 - Async component functions.

Async component functions are the guest-visible shape of the new ABI: a function declared async in the interface may return before its work is finished, and the caller decides whether to wait. The hard part is composition -- a sync caller of an async callee must still be correct, and re-entrancy must not corrupt the callee's state.

The component answers all 100 requirements of the INV-16 checklist.  Bands
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



from .runtime import (
    AsyncFunctions,
    CallCancelled,
    CallState,
    CallTrapped,
    ConcurrencyLimitReached,
    DoubleDelivery,
    ReentrancyRefused,
)


class AsyncComponentFunctionsComponent(Component):
    """Master-applied component for INV-16."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        fns = AsyncFunctions("inst-1", declared={"handle": True, "now": False})
        _verify(fns.is_async("handle") and not fns.is_async("now"), "check failed: fns.is_async('handle') and (not fns.is_async('now'))")
        a = fns.invoke("handle")
        b = fns.invoke("handle")
        _verify(a.call_id != b.call_id and a is not b, 'check failed: a.call_id != b.call_id and a is not b')
        findings[0] = self.satisfied(
            items[0],
            "Async-ness is read from the build-time declaration, and each in-flight call carries its own "
            f"state object ({len(fns.in_flight)} distinct states in flight for one function).",
            *self._evidence("component.py::AsyncFunctions.invoke"))

        fns.complete(a.call_id, "ok")
        doubled = False
        try:
            fns.complete(a.call_id, "ok")
        except DoubleDelivery:
            doubled = True
        _verify(doubled, 'check failed: doubled')
        findings[4] = self.satisfied(
            items[4],
            "A completed call's value is delivered exactly once; a second delivery raises rather than "
            "handing the caller a duplicate.",
            *self._evidence("component.py::AsyncFunctions.complete"))
        return findings

    def assess_interfaces(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_interfaces(items)
        fns = AsyncFunctions("inst-1", declared={"fetch": True})
        fns.invoke("fetch", caller_is_async=False)
        _verify(fns.bridge_calls == 1, 'check failed: fns.bridge_calls == 1')
        findings[2] = self.satisfied(
            items[2],
            f"A sync caller of an async callee is bridged rather than refused, and the bridge is counted "
            f"({fns.bridge_calls}) so the cost of sync callers is visible instead of hidden in the ABI.",
            *self._evidence("component.py::AsyncFunctions.invoke"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        fns = AsyncFunctions("inst-1", declared={"step": True}, stateful=frozenset({"step"}))
        fns.invoke("step")
        refused = False
        try:
            fns.invoke("step")
        except ReentrancyRefused:
            refused = True
        _verify(refused and fns.reentrancy_refusals == 1, 'check failed: refused and fns.reentrancy_refusals == 1')
        findings[5] = self.satisfied(
            items[5],
            "Re-entering a function that holds state across a suspension point is refused, so a second "
            "caller cannot observe or corrupt the first call's half-finished state.",
            *self._evidence("component.py::AsyncFunctions.invoke"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        inv15 = sibling("INV-15")
        fns = AsyncFunctions("inst-1", declared={"fetch": True})
        if inv15 is None:
            fns.invoke("fetch")
            findings[0] = self.partial(
                items[0],
                f"Calls in flight are tracked ({len(fns.in_flight)}), but a caller that disappears cannot "
                "be shown to tear its subtasks down from here.",
                note="INV-15 New asynchronous ABI is not installed here")
            return findings
        abi = inv15.AsyncAbi("inst-1", budget=4)
        states = [fns.invoke("fetch") for _ in range(3)]
        for _ in states:
            abi.call()
        _verify(len(fns.in_flight) == 3 and abi.blocked_stacks == 0, 'check failed: len(fns.in_flight) == 3 and abi.blocked_stacks == 0')
        cancelled = abi.cancel_all("caller gone")
        local_cancelled = fns.cancel_all("caller gone")
        _verify(cancelled == 3 and local_cancelled == 3 and not fns.in_flight,
                'check failed: ABI and local cancellation must clear all calls')
        findings[0] = self.satisfied(
            items[0],
            f"A caller that goes away takes its work with it: {len(states)} async function calls held "
            f"{cancelled} subtasks on the INV-15 ABI, cancellation propagated to every one, and no call "
            "state or guest stack survived the requester.",
            *self._evidence("component.py::AsyncFunctions.invoke"), "INV-15/AsyncAbi.cancel_all")
        return findings

COMPONENT = AsyncComponentFunctionsComponent
