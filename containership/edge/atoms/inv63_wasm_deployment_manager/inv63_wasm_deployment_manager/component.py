"""INV-63 - Wasm deployment manager.

The Wasm deployment manager holds desired state -- which components, how many, spread across which labels -- and reconciles the lattice toward it. Its guarantees are convergence (repeated reconciliation reaches the desired state and then does nothing) and safe rollout (never more than the allowed number of instances unavailable while a version changes).

The component answers all 100 requirements of the INV-63 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
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



from .manager import Manager


class WasmDeploymentManagerComponent(Component):
    """Master-applied component for INV-63."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        m = Manager({"h1": "z1", "h2": "z1", "h3": "z2", "h4": "z3"})
        d = m.diff("api", "v1", 3)
        m.apply(d)
        zones = {m.hosts[h] for _, _, h in m.actual}
        again = m.diff("api", "v1", 3)
        _verify(len(d["start"]) == 3 and zones == {"z1", "z2", "z3"} and again == {"start": [], "stop": []}, "check failed: len(d['start']) == 3 and zones == {'z1', 'z2', 'z3'} and (again == {'start': [], 'stop': []})")
        findings[0] = self.satisfied(
            items[0],
            "Reconciliation starts three instances spread across three zones, and a second reconcile "
            "against the converged lattice emits no actions -- the manager converges and then rests.",
            *self._evidence("component.py::Manager.diff"))
        return findings

    def assess_operations(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_operations(items)
        m = Manager({f"h{i}": f"z{i}" for i in range(4)})
        m.apply(m.diff("api", "v1", 4))
        batches, worst = m.rollout("api", "v2", max_unavailable=1)
        _verify(batches == 4 and worst == 1 and all(v == "v2" for _, v, _ in m.actual), "check failed: batches == 4 and worst == 1 and all((v == 'v2' for _, v, _ in m.actual))")
        findings[0] = self.satisfied(
            items[0],
            f"A version rollout across 4 instances proceeds in {batches} batches with at most {worst} "
            "instance unavailable at any time, ending with every instance on the new version.",
            *self._evidence("component.py::Manager.rollout"))
        return findings

COMPONENT = WasmDeploymentManagerComponent
