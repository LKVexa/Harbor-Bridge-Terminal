"""INV-02 - Container substrate conformance adapter.

The executable registry model lives in :mod:`.registry` so its safety properties can
be tested without the optional ``pk_core`` conformance framework.  This module maps
those behaviours into the estate-wide 100-item assessment surface.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .registry import IntegrityError, MutableTagRefused, Registry, digest


def _verify(condition: bool, message: str = "behavioural check failed") -> None:
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class ContainerSubstrateComponent(Component):
    """Master-applied conformance component for INV-02."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        reg = Registry()
        good = reg.push("api", "1.0", [b"base-os", b"app-v1"])

        # Protected-environment matching is normalized; aliases/case cannot bypass it.
        for environment in ("production", "PRODUCTION", " prod "):
            refused = False
            try:
                reg.resolve("api:1.0", environment)
            except MutableTagRefused:
                refused = True
            _verify(refused, f"mutable tag accepted in protected environment {environment!r}")

        _verify(
            reg.resolve(f"api@{good}", "production") == good,
            "known digest reference was not resolved in production",
        )

        # Moving a tag cannot rewrite the old content-addressed image.
        reg.push("api", "1.0", [b"base-os", b"evil-v1"])
        _verify(
            reg.resolve("api:1.0", "staging") != good and reg.pull(good)[1] == b"app-v1",
            "tag movement changed content pinned by digest",
        )

        # Corruption under a content key fails closed.
        base = digest(b"base-os")
        reg.blobs[base] = b"tampered"
        corrupt = False
        try:
            reg.pull(good)
        except IntegrityError:
            corrupt = True
        _verify(corrupt, "corrupted layer was accepted")

        findings[0] = self.satisfied(
            items[0],
            "Protected environments accept only known digest references; tag movement cannot change "
            "digest-pinned bytes; manifest/layer corruption fails closed. Environment matching is "
            "normalized to prevent case/alias bypasses.",
            *self._evidence(
                "registry.py::Registry.resolve",
                "registry.py::Registry.pull",
                "registry.py::parse_reference",
            ),
        )
        return findings

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        reg = Registry()
        base = b"x" * 10_000
        for i in range(5):
            reg.push(f"svc{i}", "1", [base, f"app{i}".encode()])
        stats = reg.stats()
        _verify(
            stats["layer_blob_count"] == 6,
            "content-addressed layer de-duplication did not store one shared base plus five app layers",
        )
        _verify(reg.blobs[digest(base)] == base, "shared base layer is missing or altered")
        findings[0] = self.satisfied(
            items[0],
            "Five images sharing one base layer produce six unique layer blobs (one base plus five "
            "application layers), demonstrating content-addressed de-duplication.",
            *self._evidence("registry.py::Registry.push", "registry.py::Registry.stats"),
        )
        return findings


COMPONENT = ContainerSubstrateComponent
