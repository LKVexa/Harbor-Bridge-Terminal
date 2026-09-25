"""PLN-03 - Distributed runtime plane.

The distributed runtime plane provides the sidecar-free building blocks an application uses at run time: state, messaging, secrets, and service invocation, behind stable APIs with pluggable backing infrastructure. Applications bind to capabilities, never to a broker or a database.

The component answers all 100 requirements of the PLN-03 checklist.  Bands
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
    Adapter,
    AdapterUnavailable,
    CapabilityDenied,
    DistributedRuntime,
    PayloadTooLarge,
)


class DistributedRuntimePlaneComponent(Component):
    """Master-applied component for PLN-03."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        state = Adapter("state-local")
        runtime = DistributedRuntime({"api:state": state, "api:messaging": Adapter("bus-local")})
        runtime.state_set("api", "t1", "k", b"v")
        _verify(runtime.state_get("api", "t1", "k") == b"v", "check failed: runtime.state_get('api', 't1', 'k') == b'v'")
        _verify(runtime.state_get("api", "t2", "k") is None, "tenant namespace leaked")
        first = runtime.publish("api", "t1", "orders", b"p", "idem-1")
        second = runtime.publish("api", "t1", "orders", b"p", "idem-1")
        _verify(first and not second, "idempotency key was not honoured")
        findings[3] = self.partial(
            items[3],
            "Runtime binding and caller inputs are validated before use, and invalid tenant namespaces fail closed.",
            *self._evidence("runtime.py::DistributedRuntime"),
            note="No declarative configuration activation pipeline exists in this component archive")
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        runtime = DistributedRuntime({"api:state": Adapter("state-local")})
        try:
            runtime.state_get("api", "t1", "k")
            runtime.publish("api", "t1", "topic", b"x", "i")
        except CapabilityDenied:
            findings[1] = self.satisfied(
                items[1], "Unbound capability calls fail closed with CapabilityDenied.",
                *self._evidence("runtime.py::DistributedRuntime._adapter"))
        else:
            raise AssertionError('expected CapabilityDenied was not raised; the refusal this finding claims did not happen')
        try:
            runtime.state_set("api", "t1/../t2", "k", b"v")
        except ValueError:
            findings[5] = self.partial(
                items[5], "Tenant namespace escape is refused at key construction.",
                *self._evidence("runtime.py::DistributedRuntime._key"),
                note="Execution, memory, network, and device isolation require the adjacent execution/security planes")
        else:
            raise AssertionError('expected ValueError was not raised; the refusal this finding claims did not happen')
        pln04 = sibling("PLN-04")
        if pln04 is None:
            findings[2] = self.partial(
                items[2],
                "Adapters run in-process, so ambient authority is bounded by the host rather than a tier.",
                note="PLN-04 Execution plane is not installed here")
        else:
            node = pln04.Node({"process": True, "wasm": True, "microvm": True})
            tier = pln04.admit(node, "state-adapter", "t1", "third-party")
            _verify(tier in ("unikernel", "microvm"), tier)
            findings[2] = self.satisfied(
                items[2],
                f"Adapters are hosted through the PLN-04 execution plane: a third-party adapter is admitted "
                f"to the {tier!r} tier, so its filesystem, network and device authority is the tier's, not "
                "the host's.",
                *self._evidence("runtime.py::DistributedRuntime"), "PLN-04/admit")
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        runtime = DistributedRuntime({"api:state": Adapter("state-down", available=False)})
        try:
            runtime.state_get("api", "t1", "k")
        except AdapterUnavailable:
            findings[2] = self.partial(
                items[2],
                "Backing-store loss surfaces as AdapterUnavailable without corrupting caller state.",
                *self._evidence("runtime.py::Adapter"),
                note="Bounded retry with backoff and jitter is not implemented by this reference runtime")
        else:
            raise AssertionError('expected AdapterUnavailable was not raised; the refusal this finding claims did not happen')

        bus_runtime = DistributedRuntime({"api:messaging": Adapter("bus-local")})
        try:
            bus_runtime.publish("api", "t1", "orders", b"x" * (1024 * 1024 + 1), "oversize")
        except PayloadTooLarge:
            findings[3] = self.satisfied(
                items[3],
                "Inline message admission is bounded at 1 MiB and oversized payloads fail closed.",
                *self._evidence("runtime.py::MAX_INLINE_BYTES; DistributedRuntime.publish"))
        else:
            raise AssertionError('expected PayloadTooLarge was not raised')

        pln06 = sibling("PLN-06")
        findings[5] = self.partial(
            items[5],
            "The runtime can refuse unavailable adapters and oversized inline payloads, but has no degraded-service or automatic bulk-handoff mode.",
            *self._evidence("runtime.py::DistributedRuntime"),
            note=("PLN-06 Data plane is not installed here" if pln06 is None else
                  "PLN-06 is discoverable, but automatic handoff is not implemented by PLN-03"))
        return findings

COMPONENT = DistributedRuntimePlaneComponent
