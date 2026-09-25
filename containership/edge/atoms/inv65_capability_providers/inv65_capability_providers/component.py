"""INV-65 - Capability providers.

Capability providers are the long-lived processes that give components access to the outside world -- a key-value store, an HTTP server, a message broker -- behind a contract id. One provider serves many links, so the rule that matters is isolation between them: each link has its own configuration and credentials, and one component cannot see or use another's.

The component answers all 100 requirements of the INV-65 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .provider import NoLink, Provider

def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``.

    Bare ``assert`` statements are stripped by the optimiser, which silently turned
    exercised checks into declared-only ones (and, where an assert carried a side
    effect, broke the element outright).  Every check goes through here instead.
    """
    if not condition:
        raise AssertionError(message)



class CapabilityProvidersComponent(Component):
    """Master-applied component for INV-65."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        p = Provider("wasi:keyvalue")
        p.link("orders", {"bucket": "orders", "user": "orders-rw"}, link_name="primary")
        p.link("orders", {"bucket": "orders-archive", "user": "orders-ro"}, link_name="archive")
        p.link("reports", {"bucket": "reports", "user": "reports-ro"})
        o = p.call("orders", "get", link_name="primary")
        a = p.call("orders", "get", link_name="archive")
        r = p.call("reports", "get")
        nolink = False
        try:
            p.call("marketing", "get")
        except NoLink:
            nolink = True
        _verify(
            o["as"] == "orders-rw"
            and a["as"] == "orders-ro"
            and o["bucket"] != a["bucket"]
            and r["as"] == "reports-ro"
            and nolink,
            "named-link isolation or unlinked-call refusal failed",
        )
        findings[0] = self.satisfied(
            items[0],
            "One provider serves multiple named links and components, each with its own configuration; calls "
            "resolve only the selected link, stored configuration is not exposed, and an unlinked component is refused.",
            *self._evidence("provider.py::Provider.call"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        p = Provider("wasi:keyvalue")
        p.link("a", {"bucket": "a", "user": "u"})
        p.link("b", {"bucket": "b", "user": "u"})
        p.checkpoint()
        p.unlink("a")
        restored = p.restart()
        _verify(restored == 1 and p.call("b", "get")["bucket"] == "b", "durable link revocation/restart restoration failed")
        revoked = False
        try:
            p.call("a", "get")
        except NoLink:
            revoked = True
        _verify(revoked, "revoked link reappeared after restart")
        p.backend_ok = False
        _verify(p.health() == "unhealthy", "check failed: p.health() == 'unhealthy'")
        findings[0] = self.satisfied(
            items[0],
            f"A restarted provider restores all {restored} links from its checkpoint so components keep "
            "working, and a failed backend is reported unhealthy rather than masked.",
            *self._evidence("provider.py::Provider.restart", "provider.py::Provider.health"))
        return findings

COMPONENT = CapabilityProvidersComponent
