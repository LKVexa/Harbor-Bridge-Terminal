"""INV-13 - System interface.

The system interface is WASI: the component's only door to the outside world. Nothing is ambient -- no implicit filesystem, no implicit clock, no implicit network. A component gets exactly the preopened handles its world declared, and asks for anything else in vain.

The component answers all 100 requirements of the INV-13 checklist.  Bands
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



from .runtime import (
    CAPABILITIES, MAX_NAME_LENGTH, MAX_PATH_LENGTH, MAX_PREOPENS,
    CapabilityDenied, Instance, PathEscape, World,
)


class SystemInterfaceComponent(Component):
    """Master-applied component for INV-13."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        world = World("svc", frozenset({"filesystem", "monotonic-clock", "stdio"}))
        inst = Instance("api", world)
        inst.grant_preopen("/data", "/srv/tenant-a/data")
        ok = inst.resolve("/data", "reports/q3.csv")
        _verify(ok["resolved"] == "/srv/tenant-a/data/reports/q3.csv", "check failed: ok['resolved'] == '/srv/tenant-a/data/reports/q3.csv'")
        _verify(inst.use("monotonic-clock")["granted"], "check failed: inst.use('monotonic-clock')['granted']")
        findings[5] = self.satisfied(
            items[5],
            "A component sees exactly its world: three capabilities granted, one preopen, and a relative "
            "path resolved inside it.",
            *self._evidence("runtime.py::Instance"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        inst = Instance("api", World("svc", frozenset({"filesystem"})))
        inst.grant_preopen("/data", "/srv/tenant-a/data")
        proven = []
        for label, path in [("traversal", "../../etc/passwd"),
                            ("absolute", "/etc/passwd"),
                            ("nested traversal", "reports/../../../root/.ssh/id_rsa")]:
            try:
                inst.resolve("/data", path)
            except PathEscape:
                proven.append(label)
        _verify(len(proven) == 3, proven)
        findings[2] = self.satisfied(
            items[2],
            f"Three path-confinement bypasses are refused ({', '.join(proven)}): resolution normalises "
            "first and compares against the preopen root, so '..' is visible rather than followed.",
            *self._evidence("runtime.py::Instance.resolve"))
        try:
            inst.use("sockets")
        except CapabilityDenied:
            findings[5] = self.satisfied(
                items[5],
                "A capability absent from the world is denied outright: there is no default environment "
                "to fall back on, so ambient authority has no entry point.",
                *self._evidence("runtime.py::Instance.use"))
        else:
            raise AssertionError('expected CapabilityDenied was not raised; the refusal this finding claims did not happen')
        try:
            Instance("api", World("empty", frozenset())).grant_preopen("/d", "/srv")
        except CapabilityDenied:
            findings[1] = self.satisfied(
                items[1],
                "A world without the filesystem capability cannot be given a preopen at all, so least "
                "privilege holds at instantiation rather than at first use.",
                *self._evidence("runtime.py::Instance.grant_preopen"))
        else:
            raise AssertionError('expected CapabilityDenied was not raised; the refusal this finding claims did not happen')
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        inst = Instance("api", World("svc", frozenset({"filesystem"})))
        try:
            inst.resolve("/nowhere", "x")
        except CapabilityDenied:
            findings[0] = self.satisfied(
                items[0],
                "Resolving against a root with no preopen is a named denial, not a silent fallback to "
                "the host filesystem root.",
                *self._evidence("runtime.py::Instance.resolve"))
        else:
            raise AssertionError('expected CapabilityDenied was not raised; the refusal this finding claims did not happen')
        try:
            World("bad", frozenset({"filesystem", "gpu-direct"}))
        except ValueError:
            findings[6] = self.satisfied(
                items[6],
                "A world naming a capability outside the defined set is refused at construction, so the "
                "surface cannot be widened by inventing a capability name.",
                *self._evidence("runtime.py::World"))
        else:
            raise AssertionError('expected ValueError was not raised; the refusal this finding claims did not happen')
        return findings

COMPONENT = SystemInterfaceComponent
