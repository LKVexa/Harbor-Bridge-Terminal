"""INV-70 - Fast agent sandbox.

The fast agent sandbox executes a deliberately small guest bytecode with fuel,
stack/value/memory ceilings, and capability-gated host calls. Host callbacks are
trusted capability implementations and are outside the guest isolation boundary.

The component integrates with the external ``pk_core`` checklist framework. Local
behavioural overrides exercise the runtime directly; inherited checklist findings
must still be validated with the matching ``pk_core`` package present.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .runtime import run

def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``.

    Bare ``assert`` statements are stripped by the optimiser, which silently turned
    exercised checks into declared-only ones (and, where an assert carried a side
    effect, broke the element outright).  Every check goes through here instead.
    """
    if not condition:
        raise AssertionError(message)



class FastAgentSandboxComponent(Component):
    """Master-applied component for INV-70."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        spin = run([("jmp", 0)], fuel=500)
        bomb = run([("push", 1), ("dup",), ("jmp", 1)], fuel=10_000, max_stack=32)
        escape = run([("push", "/etc/passwd"), ("call", "read_file"), ("halt",)],
                     host={"read_file": lambda p: "root:x"})
        allowed = run([("push", 3), ("call", "double"), ("halt",)], caps={"double"},
                      host={"double": lambda x: 2 * x})
        _verify(spin == {"trap": "out of fuel", "fuel": 500}, "check failed: spin == {'trap': 'out of fuel', 'fuel': 500}")
        _verify(bomb["trap"] == "out of memory", "check failed: bomb['trap'] == 'out of memory'")
        _verify(escape["trap"] == "capability denied: read_file" and allowed["ok"] == 6, "check failed: escape['trap'] == 'capability denied: read_file' and allowed['ok'] == 6")
        findings[0] = self.satisfied(
            items[0],
            "An infinite loop stops at exactly its 500 fuel, a stack bomb stops at the memory ceiling, "
            "and a host call without a granted capability traps before the host function is reached, "
            "while a granted one works.",
            *self._evidence("runtime.py::run"))
        return findings

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        prog = [("push", 2), ("push", 3), ("mul",), ("push", 4), ("add",), ("halt",)]
        r = run(prog)
        _verify(r == {"ok": 10, "fuel": 6}, "check failed: r == {'ok': 10, 'fuel': 6}")
        findings[0] = self.satisfied(
            items[0],
            "Fuel is metered per instruction, so cost is exact and predictable: this 6-instruction "
            "program returns 10 having used exactly 6 units.",
            *self._evidence("runtime.py::run"))
        return findings

COMPONENT = FastAgentSandboxComponent
