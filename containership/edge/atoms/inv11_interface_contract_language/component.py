"""INV-11 - Interface contract language.

The interface contract language is WIT: the typed vocabulary that says what crosses a component boundary. It is the only thing standing between two components written in different languages and a memory-safety incident, so compatibility here is structural and checked, never assumed from a version number.

The component answers all 100 requirements of the INV-11 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


def _verify(condition: bool, message: str = "behavioural check failed") -> None:
    """Fail a behavioural check even under ``python -O``.

    Bare ``assert`` statements are stripped by the optimiser, which silently turned
    exercised checks into declared-only ones (and, where an assert carried a side
    effect, broke the element outright).  Every check goes through here instead.
    """
    if not condition:
        raise AssertionError(message)


from .interface_model import (
    ADDITIVE,
    BREAKING,
    Func,
    Incompatible,
    Interface,
    check_link,
    classify,
)


class InterfaceContractLanguageComponent(Component):
    """Master-applied component for INV-11."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        get = Func("get", (("key", "string"),), ("ok", "not-found"))
        v1 = Interface("wasi:kv/store", "1.0.0", frozenset({get}))
        v2 = Interface("wasi:kv/store", "1.1.0",
                       frozenset({get, Func("delete", (("key", "string"),), ("ok",))}))
        change = classify(v1, v2)
        _verify(change["class"] == ADDITIVE and change["linkable"], "check failed: change['class'] == ADDITIVE and change['linkable']")
        _verify(check_link(v2, v1)["linked"], "an older consumer could not link to a newer producer")
        findings[5] = self.satisfied(
            items[5],
            f"Adding a function is classified {change['class']} and an older consumer still links to the "
            "newer producer, because compatibility is computed from structure.",
            *self._evidence("interface_model.py::classify", "interface_model.py::check_link"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        v1 = Interface("i", "1.0.0", frozenset({Func("f", (("a", "string"),), ("ok",))}))
        narrowed = Interface("i", "1.0.1", frozenset({Func("f", (("a", "u32"),), ("ok",))}))
        change = classify(v1, narrowed)
        _verify(change["class"] == BREAKING and not change["linkable"], "check failed: change['class'] == BREAKING and (not change['linkable'])")
        findings[6] = self.satisfied(
            items[6],
            f"A parameter type change shipped as a patch version ({change['from']} -> {change['to']}) is "
            "still classified breaking, so the version string cannot launder a type confusion.",
            *self._evidence("interface_model.py::classify"))
        try:
            check_link(narrowed, v1)
        except Incompatible:
            findings[5] = self.satisfied(
                items[5],
                "Structurally mismatched signatures refuse to link, which is the boundary keeping two "
                "differently-compiled languages from disagreeing about memory.",
                *self._evidence("interface_model.py::check_link"))
        else:
            raise AssertionError(
                "expected Incompatible was not raised; the refusal this finding claims did not happen"
            )
        return findings

    def assess_requirements(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_requirements(items)
        v1 = Interface("i", "1.0.0", frozenset({Func("f", (), ("ok", "err"))}))
        v2 = Interface("i", "2.0.0", frozenset({Func("f", (), ("ok", "err", "throttled"))}))
        change = classify(v1, v2)
        _verify(change["class"] == BREAKING, "check failed: change['class'] == BREAKING")
        findings[3] = self.satisfied(
            items[3],
            "Adding a result case is breaking, not additive: an existing consumer has no arm for "
            "'throttled', so the change is refused rather than shipped as backward compatible.",
            *self._evidence("interface_model.py::classify"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        v1 = Interface("i", "1.0.0", frozenset({Func("f", (), ("ok",)),
                                                Func("g", (), ("ok",))}))
        v2 = Interface("i", "1.1.0", frozenset({Func("f", (), ("ok",))}))
        change = classify(v1, v2)
        _verify(change["class"] == BREAKING and "removed" in change["reasons"][0], "check failed: change['class'] == BREAKING and 'removed' in change['reasons'][0]")
        findings[0] = self.satisfied(
            items[0],
            "Removing a function is detected as breaking with the removed names reported, so the failure "
            "is explained rather than discovered by a consumer at run time.",
            *self._evidence("interface_model.py::classify"))
        return findings

COMPONENT = InterfaceContractLanguageComponent
