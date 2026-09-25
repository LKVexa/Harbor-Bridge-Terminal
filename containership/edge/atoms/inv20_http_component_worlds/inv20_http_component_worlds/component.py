"""INV-20 - HTTP component worlds.

An HTTP component world is the smallest useful thing a serverless component can be: a world that imports an outgoing-request capability and exports an incoming-request handler, with both bodies as streams and trailers as completions. Because the world is explicit, a component that was never granted outgoing HTTP simply cannot make a call.

The component answers all 100 requirements of the INV-20 checklist.  Bands
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



from .runtime import (
    BodyStream, BodyTooLarge, Completion, CompletionAlreadyResolved,
    EgressDenied, HttpMessage, HttpWorld, NoOutgoingCapability,
)


class HttpComponentWorldsComponent(Component):
    """Master-applied component for INV-20."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        w = HttpWorld("api", allowed_hosts=frozenset({"upstream.internal"}), outgoing_granted=True)
        w.export_handler(lambda req: ("200", req))
        _verify(w.handle({"path": "/"}) == ("200", {"path": "/"}), "check failed: w.handle({'path': '/'}) == ('200', {'path': '/'})")
        duplicated = False
        try:
            w.export_handler(lambda req: None)
        except ValueError:
            duplicated = True
        _verify(duplicated, 'check failed: duplicated')
        findings[0] = self.satisfied(
            items[0],
            "A world exports exactly one incoming-request handler; a second export is refused, so the "
            "entry point of a component is unambiguous at link time.",
            *self._evidence("component.py::HttpWorld.export_handler"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        granted = HttpWorld("api", allowed_hosts=frozenset({"upstream.internal"}), outgoing_granted=True)
        _verify(granted.fetch("upstream.internal") == ("ok", "upstream.internal"), "check failed: granted.fetch('upstream.internal') == ('ok', 'upstream.internal')")
        denied = False
        try:
            granted.fetch("169.254.169.254")
        except EgressDenied:
            denied = True

        sealed = HttpWorld("pure")
        no_cap = False
        try:
            sealed.fetch("upstream.internal")
        except NoOutgoingCapability:
            no_cap = True
        _verify(denied and no_cap and granted.egress_denials == 1, 'check failed: denied and no_cap and (granted.egress_denials == 1)')
        findings[0] = self.satisfied(
            items[0],
            "Egress is a property of the world: an allow-listed host succeeds, the metadata address is "
            "denied, and a world that imports no outgoing HTTP cannot reach anything at all -- so a "
            "component's reachable surface is reviewable before it runs.",
            *self._evidence("component.py::HttpWorld.fetch"))
        return findings

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        body = BodyStream(limit=1 << 20)
        forwarded = 0
        for _ in range(64):
            body.write(b"x" * 1024)
            forwarded += len(body.forward())
        _verify(body.peak_buffered == 1 and forwarded == 64 * 1024, 'check failed: body.peak_buffered == 1 and forwarded == 64 * 1024')
        oversized = False
        small = BodyStream(limit=16)
        try:
            small.write(b"y" * 17)
        except BodyTooLarge:
            oversized = True
        _verify(oversized, 'check failed: oversized')
        message = HttpMessage()
        message.trailers.resolve({"digest": "sha-256=:example:"})
        _verify(message.trailers.resolved and message.trailers.result()["digest"].startswith("sha-256"), 'check failed: trailer completion')
        duplicate_completion = False
        try:
            message.trailers.resolve({})
        except CompletionAlreadyResolved:
            duplicate_completion = True
        _verify(duplicate_completion, 'check failed: trailer completion single-resolution')
        findings[0] = self.satisfied(
            items[0],
            f"A {forwarded}-byte body is forwarded a chunk at a time with at most "
            f"{body.peak_buffered} chunk held, and a body over the workload's limit is refused rather "
            "than buffered; trailers are delivered through a single-resolution completion.",
            *self._evidence("component.py::BodyStream"))
        return findings

COMPONENT = HttpComponentWorldsComponent
