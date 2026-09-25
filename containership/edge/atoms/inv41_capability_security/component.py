"""INV-41 - Capability security estate integration.

The security primitives live in :mod:`capabilities` and have no ``pk_core``
dependency.  This module adapts those primitives to the 100-item estate gate.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .capabilities import Authority, Forged, Membrane, Reference, Revoked, Widening
from .contract import ELEMENT_ID, ELEMENT_NAME, build


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class CapabilitySecurityComponent(Component):
    """Master-applied component for INV-41."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    @staticmethod
    def _fixture():
        authority = Authority({"state-store": {"read", "write"}}, authority_id="inv41-assessment")
        store = authority.grant("state-store")
        holder = authority.bind_holder("api", {"store": store})
        return authority, store, holder

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        _authority, store, component = self._fixture()
        _verify(component.use("store", "read")["permitted"], "held capability did not permit read")
        narrowed = component.delegate("store", {"read"})
        _verify(narrowed.operations == frozenset({"read"}), "attenuation did not narrow authority")
        _verify(narrowed.token != store.token, "attenuation reused a bearer token")
        findings[5] = self.satisfied(
            items[5],
            "A component acts only through an immutable holder explicitly bound to one authority domain; "
            "delegation mints a distinct sealed reference with an equal-or-narrower operation set.",
            *self._evidence("capabilities.py::Authority.bind_holder"),
        )
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        authority, _store, component = self._fixture()
        proven = []
        try:
            component.use("secrets", "read")
        except Forged:
            proven.append("no lookup for an unheld reference")
        else:
            raise AssertionError("unheld reference lookup unexpectedly succeeded")

        try:
            component.delegate("store", {"read", "write", "admin"})
        except Widening:
            proven.append("no widening on delegation")
        else:
            raise AssertionError("authority widening unexpectedly succeeded")

        try:
            component.use("store", "admin")
        except Forged:
            proven.append("no operation outside the reference")
        else:
            raise AssertionError("unauthorized operation unexpectedly succeeded")

        try:
            authority.grant("secrets", {"read"})
        except PermissionError:
            proven.append("bootstrap policy refuses undeclared resources")
        else:
            raise AssertionError("undeclared bootstrap resource unexpectedly granted")

        _verify(len(proven) == 4, proven)
        findings[2] = self.satisfied(
            items[2],
            f"Ambient authority has no supported entry point: {'; '.join(proven)}. Holders are immutable and "
            "bound to one explicit authority domain.",
            *self._evidence("capabilities.py::Holder"),
        )
        findings[1] = self.satisfied(
            items[1],
            "References use guarded construction plus an authenticated per-process seal; direct construction, "
            "cross-domain injection, and mutation are refused. This is an API-level control, not a hostile-Python sandbox.",
            *self._evidence("capabilities.py::Reference"),
        )
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        authority = Authority({"store": {"read", "write"}}, authority_id="inv41-revocation")
        inner = Membrane("session-42")
        outer = Membrane("request-7")
        base = authority.grant("store")
        first = inner.wrap(base)
        second = first.attenuate({"read"})
        nested = outer.wrap(second)
        _verify(nested.invoke("read")["permitted"], "nested reference was unusable before revocation")
        result = inner.revoke()
        killed = 0
        for ref in (first, second, nested):
            try:
                ref.invoke("read")
            except Revoked:
                killed += 1
            else:
                raise AssertionError("revoked membrane was bypassed")
        _verify(killed == 3, f"expected 3 revoked references, saw {killed}")
        _verify(result["references_killed"] == 3, "revocation accounting omitted derived references")
        findings[6] = self.satisfied(
            items[6],
            "Revoking an inner membrane invalidates every still-live wrapped or attenuated descendant, including "
            "references re-wrapped by an outer membrane; weak-reference accounting reports the affected live set.",
            *self._evidence("capabilities.py::Membrane.revoke"),
        )
        return findings


COMPONENT = CapabilitySecurityComponent
