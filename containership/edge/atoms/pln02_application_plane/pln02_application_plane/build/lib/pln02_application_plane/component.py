"""PLN-02 - Application plane conformance adapter.

The application plane resolves a composition of portable components and their
capability requirements into a deterministic application revision.  The
resolver itself lives in :mod:`resolver` and is intentionally independent of
``pk_core``; this module binds it into the Post-Kubernetes conformance system.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .resolver import (
    IncompatibleInterface,
    RevisionIntegrityError,
    UnsatisfiedRequirement,
    ValidationError,
    resolve,
    verify_revision,
)


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class ApplicationPlaneComponent(Component):
    """Master-applied component for PLN-02."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        components = [
            {
                "name": "api",
                "requires": {"state": True, "tracing": False},
                "imports": {"store": "1.2"},
                "exports": {},
            },
            {
                "name": "store",
                "requires": {"state": True},
                "exports": {"store": "1.2"},
                "imports": {},
            },
        ]
        revision = resolve(components, [("store", "api", "store")], {"state": "redis-provider"})
        _verify(
            revision["revision"] and "api:tracing" in revision["dropped_optional"],
            "optional capability handling failed",
        )
        again = resolve(components, [("store", "api", "store")], {"state": "redis-provider"})
        _verify(again["revision"] == revision["revision"], "revision identity is not deterministic")
        _verify(verify_revision(revision), "revision integrity verification failed")

        # Interface declarations are part of the revision identity. This closes
        # a v4.1.0 collision class where only component names were hashed.
        changed = [dict(component) for component in components]
        changed[0] = {**changed[0], "imports": {"store": "1.3"}}
        changed[1] = {**changed[1], "exports": {"store": "1.3"}}
        changed_revision = resolve(
            changed, [("store", "api", "store")], {"state": "redis-provider"}
        )
        _verify(
            changed_revision["revision"] != revision["revision"],
            "interface version change did not change revision identity",
        )

        findings[5] = self.satisfied(
            items[5],
            f"Resolution is canonical and SHA-256 content-addressed (revision {revision['revision'][:12]}); "
            f"{len(revision['bindings'])} binding(s), {len(revision['dropped_optional'])} optional dropped.",
            *self._evidence("resolver.py::resolve", "resolver.py::verify_revision"),
        )
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        proven = 0
        try:
            resolve([{"name": "api", "requires": {"state": True}}], [], {})
        except UnsatisfiedRequirement:
            proven += 1
        else:
            raise AssertionError("missing required capability was not refused")

        try:
            resolve(
                [
                    {"name": "a", "exports": {"i": "1"}},
                    {"name": "b", "imports": {"i": "2"}},
                ],
                [("a", "b", "i")],
                {},
            )
        except IncompatibleInterface:
            proven += 1
        else:
            raise AssertionError("incompatible interface was not refused")

        _verify(proven == 2, "not all declared failure modes were reproduced")
        findings[0] = self.satisfied(
            items[0],
            f"{proven}/2 declared failure modes reproduced as typed refusals rather than partial revisions.",
            *self._evidence("resolver.py::resolve"),
        )

        gap04 = sibling("GAP-04")
        if gap04 is None:
            findings[2] = self.partial(
                items[2],
                "Catalogue unavailability fails resolution closed; offline resolution needs the autonomy "
                "lease that GAP-04 issues.",
                note="GAP-04 Disconnected-operation controller is not installed here",
            )
        else:
            controller = gap04.AutonomyController("site", granted_at=0, lease_ticks=300)
            controller.partition(0)
            decision = controller.decide("admit-known", "cached-catalogue", 10)
            try:
                controller.decide("admit-new", "unknown-capability", 130)
                permitted_new = True
            except gap04.NotPermittedAtTier:
                permitted_new = False
            _verify(not permitted_new, "offline resolution admitted an uncached capability")
            findings[2] = self.satisfied(
                items[2],
                "Offline resolution runs under a GAP-04 autonomy lease: a revision whose capabilities were "
                f"already cached resolves at tier {decision['tier']!r}, while a new, uncached requirement "
                "is refused once the partition reaches the freeze tier.",
                *self._evidence("resolver.py::resolve"),
                "GAP-04/AutonomyController",
            )
        return findings


COMPONENT = ApplicationPlaneComponent

__all__ = [
    "ApplicationPlaneComponent",
    "COMPONENT",
    "IncompatibleInterface",
    "RevisionIntegrityError",
    "UnsatisfiedRequirement",
    "ValidationError",
    "resolve",
    "verify_revision",
]
