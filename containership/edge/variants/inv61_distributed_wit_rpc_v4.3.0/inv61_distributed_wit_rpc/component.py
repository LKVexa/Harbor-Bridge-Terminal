"""INV-61 - Distributed WIT RPC.

Distributed WIT RPC carries typed interface calls between components on different hosts. Each frame names the interface, version and function and carries a fingerprint of the caller's signature; the receiver checks that fingerprint against its own before decoding a byte, so two sides that drifted apart fail with a clear error instead of misreading each other's arguments.

The component answers all 100 requirements of the INV-61 checklist.  Bands
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



from .rpc import Endpoint, fingerprint, make_frame as frame


class DistributedWitRpcComponent(Component):
    """Master-applied component for INV-61."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_interfaces(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_interfaces(items)
        ep = Endpoint("kv", "0.2.0")
        ep.export("get", ["string"], ["option<u64>"], lambda k: 7)
        ok = ep.handle(frame("kv", "0.2.0", "get", ["string"], ["option<u64>"], ["a"], 10), now=0)
        version_drift = ep.handle(frame("kv", "0.1.0", "get", ["string"], ["option<u64>"], ["a"], 10), now=0)
        signature_drift = ep.handle(frame("kv", "0.2.0", "get", ["string"], ["u64"], ["a"], 10), now=0)
        _verify(
            ok == {"ok": 7}
            and version_drift["error"] == "version-mismatch"
            and signature_drift["error"] == "signature-mismatch"
            and ep.mismatches == 1,
            "version/signature compatibility enforcement failed",
        )
        findings[0] = self.satisfied(
            items[0],
            "Every frame carries a signature fingerprint that the receiver checks before decoding: a "
            "matching caller gets its result, while version drift and signature drift are rejected "
            "before argument dispatch instead of being decoded against a different contract.",
            *self._evidence("component.py::Endpoint.handle", "component.py::fingerprint"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        ep = Endpoint("kv", "1")
        ep.export("boom", [], [], lambda: 1 / 0)
        late = ep.handle(frame("kv", "1", "boom", [], [], [], deadline=5), now=6)
        trap = ep.handle(frame("kv", "1", "boom", [], [], [], deadline=5), now=1)
        _verify(late == {"error": "deadline-exceeded"} and trap["error"] == "callee-trap", "check failed: late == {'error': 'deadline-exceeded'} and trap['error'] == 'callee-trap'")
        findings[0] = self.satisfied(
            items[0],
            "A frame past its deadline is refused without running, and a callee trap comes back as a "
            "typed error rather than a hung or dropped connection.",
            *self._evidence("component.py::Endpoint.handle"))
        return findings

COMPONENT = DistributedWitRpcComponent
