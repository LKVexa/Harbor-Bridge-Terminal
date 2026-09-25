"""INV-64 - Application model.

The application model is the declarative description of an application: its components, the providers they link to, and the traits -- scaling, spread -- attached to each. Its value is validation before anything runs: a link to a component that does not exist, a trait on a component that is not there, or a schema version the platform does not speak is refused at submit.

The component integrates with the 100-requirement INV-64 checklist. Bands
with direct local behavior are overridden below so parser/identity claims are
backed by executable checks; repository-wide gaps are tracked separately in
REQUIREMENTS_TRACEABILITY.md.
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



from .manifest import canonical, validate


class ApplicationModelComponent(Component):
    """Master-applied component for INV-64."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_requirements(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_requirements(items)
        good = {"schema": "app/v1",
                "components": [{"name": "api"}, {"name": "worker"}],
                "providers": [{"name": "kv"}],
                "links": [{"from": "api", "to": "kv"}],
                "traits": [{"type": "spread", "component": "api"}]}
        bad = dict(good, schema="app/v9",
                   links=[{"from": "api", "to": "redis"}],
                   traits=[{"type": "scaler", "component": "ghost"}])
        errs = validate(bad)
        _verify(validate(good) == [] and len(errs) == 3, 'check failed: validate(good) == [] and len(errs) == 3')
        findings[0] = self.satisfied(
            items[0],
            f"A manifest with an unknown schema, a dangling link and an orphan trait is refused at submit "
            f"with all {len(errs)} errors reported together, while the well-formed manifest validates clean.",
            *self._evidence("component.py::validate"))
        return findings

    def assess_interfaces(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_interfaces(items)
        a = {"schema": "app/v1", "components": [{"name": "x"}, {"name": "y"}], "links": [], "traits": [], "providers": []}
        b = dict(a, components=[{"name": "y"}, {"name": "x"}])
        c = dict(a, components=[{"name": "x"}])
        _verify(canonical(a) == canonical(b) != canonical(c), 'check failed: canonical(a) == canonical(b) != canonical(c)')
        findings[0] = self.satisfied(
            items[0],
            "Manifests have a canonical digest: reordering components does not change it, removing one "
            "does, so diffing and signing operate on meaning rather than formatting.",
            *self._evidence("component.py::canonical"))
        return findings

COMPONENT = ApplicationModelComponent
