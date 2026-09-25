"""INV-44 - Wasm hardening system.

The component binds the standalone fail-closed runtime model in ``runtime.py``
to the wider ``pk_core`` checklist/conformance framework.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .runtime import (
    REQUIRED_HARDENING,
    Engine,
    FuelExhausted,
    HardeningIncomplete,
    Instance,
    InstanceConstructionDenied,
    MemoryCeiling,
    OutputUnverified,
)


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class WasmHardeningSystemComponent(Component):
    """Master-applied component for INV-44."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        # C034: security-critical configuration must be validated and fail closed.
        partial = Engine("swivel-reference", REQUIRED_HARDENING - {"cfi"})
        try:
            partial.instantiate("svc", output_valid=True, fuel=10)
        except HardeningIncomplete:
            findings[3] = self.satisfied(
                items[3],
                "Security-critical hardening configuration is checked before activation; "
                "an engine missing CFI is refused before instance construction.",
                *self._evidence("runtime.py::Engine.check"),
            )
        else:
            raise AssertionError("partial hardening configuration was not refused")
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        proven = []
        for feature in sorted(REQUIRED_HARDENING):
            partial = Engine("swivel-reference", REQUIRED_HARDENING - {feature})
            try:
                partial.instantiate("svc", output_valid=True, fuel=10)
            except HardeningIncomplete:
                proven.append(feature)
        _verify(len(proven) == len(REQUIRED_HARDENING), proven)
        findings[5] = self.satisfied(
            items[5],
            f"All {len(REQUIRED_HARDENING)} declared hardening features are individually "
            "load-bearing; removing any one prevents instance creation.",
            *self._evidence("runtime.py::Engine.check"),
        )

        engine = Engine("swivel-reference", REQUIRED_HARDENING)
        try:
            engine.instantiate("svc", output_valid=False, fuel=10)
        except OutputUnverified:
            pass
        else:
            raise AssertionError("unverified compiled output was not refused")

        try:
            Instance("svc", engine, 10, 1)
        except InstanceConstructionDenied:
            pass
        else:
            raise AssertionError("direct Instance construction bypass was not refused")
        return findings

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        engine = Engine("swivel-reference", REQUIRED_HARDENING, memory_page_ceiling=8)
        instance = engine.instantiate("svc", output_valid=True, fuel=5, pages=2)
        _verify(instance.step(5) == 0, "fuel accounting mismatch")
        try:
            instance.step(1)
        except FuelExhausted:
            _verify(instance.trapped == "fuel exhausted", "fuel trap was not sticky")
        else:
            raise AssertionError("fuel exhaustion was not enforced")

        memory = engine.instantiate("svc-memory", output_valid=True, fuel=10, pages=8)
        try:
            memory.grow(1)
        except MemoryCeiling:
            pass
        else:
            raise AssertionError("memory ceiling was not enforced")

        findings[6] = self.satisfied(
            items[6],
            "Execution fuel and linear-memory growth are both bounded and enforced at the "
            "runtime boundary; exhaustion/overflow attempts are refused deterministically.",
            *self._evidence("runtime.py::Instance"),
        )
        return findings

    def assess_testing(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_testing(items)
        # C087: security tests derived from the runtime threat model.
        engine = Engine("swivel-reference", REQUIRED_HARDENING)
        cases = 0
        try:
            engine.instantiate("svc", output_valid=False, fuel=10)
        except OutputUnverified:
            cases += 1
        try:
            Instance("svc", engine, 10, 1)
        except InstanceConstructionDenied:
            cases += 1
        instance = engine.instantiate("svc2", output_valid=True, fuel=1)
        try:
            instance.step(0)
        except ValueError:
            cases += 1
        _verify(cases == 3, f"security test cases passed: {cases}/3")
        findings[6] = self.satisfied(
            items[6],
            "Adversarial unit tests exercise unverified output, direct-construction bypass, "
            "and zero-cost metering bypass attempts.",
            *self._evidence("tests/test_component.py::RuntimeSecurityTest"),
        )
        return findings


COMPONENT = WasmHardeningSystemComponent
