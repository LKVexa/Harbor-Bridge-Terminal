"""INV-10 - Component composition system.

The component composition system is what makes modules into something you can actually wire together: each component states its imports and exports as typed interfaces, and composition is linking them. A composition either closes -- every import satisfied by some export -- or it is not a composition at all.

The component answers all 100 requirements of the INV-10 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build

def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


from .composition import (
    AmbiguousExport,
    CompositionCycle,
    Unit,
    UnsatisfiedImport,
    compose,
)


class ComponentCompositionSystemComponent(Component):
    """Master-applied component for INV-10."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        parts = [
            Unit("store", frozenset(), frozenset({"wasi:kv/store"})),
            Unit("api", frozenset({"wasi:kv/store"}), frozenset({"wasi:http/handler"})),
        ]
        result = compose(parts)
        _verify(result["closed"] and result["order"] == ["store", "api"], "check failed: result['closed'] and result['order'] == ['store', 'api']")
        _verify(result["external_imports"] == [], "check failed: result['external_imports'] == []")
        again = compose(list(reversed(parts)))
        _verify(again["composition"] == result["composition"], "composition id is order-dependent")
        findings[5] = self.satisfied(
            items[5],
            f"Linking is deterministic and produces an instantiation order ({' -> '.join(result['order'])}) "
            f"with a content-addressed id ({result['composition'][:12]}) independent of input order.",
            *self._evidence("composition.py::compose"))
        return findings

    def assess_requirements(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_requirements(items)
        parts = [Unit("api", frozenset({"wasi:http/outgoing"}), frozenset())]
        result = compose(parts, external=frozenset({"wasi:http/outgoing"}))
        _verify(result["external_imports"] == ["wasi:http/outgoing"], "check failed: result['external_imports'] == ['wasi:http/outgoing']")
        findings[8] = self.satisfied(
            items[8],
            "An import the composition does not satisfy internally surfaces as an explicit external "
            "import rather than being quietly deferred to run time.",
            *self._evidence("composition.py::compose"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        try:
            compose([Unit("api", frozenset({"wasi:kv/store"}), frozenset())])
        except UnsatisfiedImport:
            findings[6] = self.satisfied(
                items[6],
                "An import with no export and no external declaration refuses the composition, so nothing "
                "reaches run time hoping an implementation will turn up.",
                *self._evidence("composition.py::compose"))
        else:
            raise AssertionError('expected UnsatisfiedImport was not raised; the refusal this finding claims did not happen')
        try:
            compose([Unit("a", frozenset(), frozenset({"i"})),
                     Unit("b", frozenset(), frozenset({"i"}))])
        except AmbiguousExport:
            findings[0] = self.satisfied(
                items[0],
                "Two components exporting the same interface is ambiguous and refused, so an import "
                "cannot be silently bound to an unintended provider.",
                *self._evidence("composition.py::compose"))
        else:
            raise AssertionError('expected AmbiguousExport was not raised; the refusal this finding claims did not happen')
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        try:
            compose([Unit("a", frozenset({"i-b"}), frozenset({"i-a"})),
                     Unit("b", frozenset({"i-a"}), frozenset({"i-b"}))])
        except CompositionCycle:
            findings[6] = self.satisfied(
                items[6],
                "A dependency cycle is detected at composition time rather than becoming a "
                "non-terminating instantiation at run time.",
                *self._evidence("composition.py::compose"))
        else:
            raise AssertionError('expected CompositionCycle was not raised; the refusal this finding claims did not happen')
        return findings

COMPONENT = ComponentCompositionSystemComponent
