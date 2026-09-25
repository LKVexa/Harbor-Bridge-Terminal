"""INV-09 - Portable compute ISA.

The component answers all 100 requirements of the INV-09 checklist. Bands whose
base answers would merely restate the contract are overridden below so selected
claims are backed by exercised validator behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .validator import (
    MAX_BYTES,
    MAX_SECTIONS,
    NON_DETERMINISTIC,
    PROFILES,
    FeatureRefused,
    Module,
    ValidationFailed,
    validate,
)


def _verify(condition: object, message: str = "behavioural check failed") -> None:
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class PortableComputeIsaComponent(Component):
    """Master-applied component for INV-09."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        core = frozenset({"core", "bulk-memory"})
        module = Module("svc", core, core)
        result = validate(module, profile="deterministic")
        _verify(
            result["valid"] and result["deterministic"],
            "check failed: valid deterministic module was not accepted",
        )
        _verify(
            validate(module, profile="deterministic") == result,
            "check failed: validation result is not deterministic",
        )
        findings[5] = self.satisfied(
            items[5],
            "Validation is repeatable and reports the features actually used "
            f"({', '.join(result['used'])}) rather than inferring them from declarations.",
            *self._evidence("validator.py::validate"),
        )
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)

        sneaky = Module("sneaky", frozenset({"core"}), frozenset({"core", "threads"}))
        try:
            validate(sneaky, profile="permissive")
        except ValidationFailed:
            findings[6] = self.satisfied(
                items[6],
                "A module using a feature it did not declare fails validation even under the "
                "permissive profile, so declaration-only gating cannot authorize hidden use.",
                *self._evidence("validator.py::validate"),
            )
        else:
            raise AssertionError("expected ValidationFailed for used-but-undeclared feature")

        simd = Module("simd", frozenset({"core", "simd"}), frozenset({"core", "simd"}))
        try:
            validate(simd, profile="deterministic")
        except FeatureRefused:
            findings[5] = self.satisfied(
                items[5],
                "A feature outside the environment profile is refused; the profile is a hard ceiling.",
                *self._evidence("validator.py::PROFILES"),
            )
        else:
            raise AssertionError("expected FeatureRefused for feature outside selected profile")

        declared_only = Module(
            "declared-only",
            frozenset({"core", "threads"}),
            frozenset({"core"}),
        )
        try:
            validate(declared_only, profile="deterministic")
        except FeatureRefused:
            pass
        else:
            raise AssertionError("expected FeatureRefused for unsupported declared capability")
        return findings

    def assess_requirements(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_requirements(items)
        risky = Module("risky", frozenset({"core", "threads"}), frozenset({"core", "threads"}))
        result = validate(risky, profile="permissive")
        _verify(
            result["valid"] and not result["deterministic"],
            "check failed: nondeterministic feature was not reflected in verdict",
        )
        findings[4] = self.satisfied(
            items[4],
            "The determinism class is computed from used features: a threads-using module validates "
            "under the permissive profile but is reported non-deterministic.",
            *self._evidence("validator.py::NON_DETERMINISTIC"),
        )
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        proven: list[str] = []
        for label, module in [
            ("malformed", Module("a", frozenset(), frozenset(), well_formed=False)),
            ("section explosion", Module("b", frozenset(), frozenset(), sections=MAX_SECTIONS + 1)),
            ("oversize", Module("c", frozenset(), frozenset(), size_bytes=MAX_BYTES + 1)),
        ]:
            try:
                validate(module, profile="deterministic")
            except ValidationFailed:
                proven.append(label)
        _verify(len(proven) == 3, "check failed: one or more resource refusals did not occur")
        findings[5] = self.satisfied(
            items[5],
            f"Resource limits are enforced at validation ({', '.join(proven)}), so hostile "
            "descriptors are rejected before execution admission.",
            *self._evidence("validator.py::validate"),
        )
        return findings


COMPONENT = PortableComputeIsaComponent
