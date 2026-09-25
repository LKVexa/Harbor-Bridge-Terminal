"""INV-29 - Hybrid Wasm/unikernel.

The hybrid Wasm/unikernel model puts a Wasm runtime inside a unikernel image: the module gets the component model's portability and the unikernel's hardware-backed boundary at once. The point is defence in depth, so this element refuses a composition where one layer's guarantees silently substitute for the other's.

The component answers all 100 requirements of the INV-29 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build

def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``.

    Bare ``assert`` statements are stripped by the optimiser, which silently turned
    exercised checks into declared-only ones (and, where an assert carried a side
    effect, broke the element outright).  Every check goes through here instead.
    """
    if not condition:
        raise AssertionError(message)



from .model import HostImage, ImportUnsatisfied, LayerMissing, WasmModule, compose
from . import interfaces as _local_ifc


class HybridWasmUnikernelComponent(Component):
    """Master-applied component for INV-29."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        host = HostImage("mirage-host", frozenset({"clock", "net-send", "net-recv"}))
        module = WasmModule("svc", frozenset({"clock", "net-send"}))
        result = compose(module, host)
        _verify(result["layer_count"] == 2 and result["defence_in_depth"], "check failed: result['layer_count'] == 2 and result['defence_in_depth']")
        _verify([l["layer"] for l in result["layers"]] == ["unikernel", "wasm"], "check failed: [l['layer'] for l in result['layers']] == ['unikernel', 'wasm']")
        findings[5] = self.satisfied(
            items[5],
            "Composition records both layers and the distinct guarantee each contributes, so the hybrid "
            "is never described as a single stronger sandbox.",
            *self._evidence("component.py::compose"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        host = HostImage("host", frozenset({"clock"}))
        try:
            compose(WasmModule("svc", frozenset({"clock", "raw-socket"})), host)
        except ImportUnsatisfied:
            findings[2] = self.satisfied(
                items[2],
                "A module importing something the sealed host image does not expose is refused, so imports "
                "cannot be satisfied by an escape hatch beneath the unikernel.",
                *self._evidence("component.py::compose"))
        else:
            raise AssertionError('expected ImportUnsatisfied was not raised; the refusal this finding claims did not happen')
        proven = []
        for label, m, h in [
            ("unikernel layer", WasmModule("a", frozenset()), HostImage("h", frozenset(), sealed=False)),
            ("wasm layer", WasmModule("b", frozenset(), hardened=False), HostImage("h", frozenset())),
        ]:
            try:
                compose(m, h)
            except LayerMissing:
                proven.append(label)
        _verify(len(proven) == 2, 'check failed: len(proven) == 2')
        findings[5] = self.satisfied(
            items[5],
            f"Losing either layer ({', '.join(proven)}) refuses the composition rather than falling back "
            "to the surviving one, so defence in depth cannot quietly become defence in breadth.",
            *self._evidence("component.py::compose"))
        return findings

    def assess_architecture(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_architecture(items)
        findings[6] = self.satisfied(
            items[6],
            "Both layers are mandatory in this tier; a single-layer deployment is a different tier "
            "(INV-27 or INV-44 alone), not a degraded version of this one.",
            *self._evidence("component.py::compose", "contract.py"))
        return findings

    def assess_interfaces(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_interfaces(items)
        inv11 = sibling("INV-11")
        if inv11 is None:
            # 4.3.0: the local typed layer catches signature drift, but INV-11 remains the
            # authority, so without it this stays PARTIAL (never promoted to satisfied).
            clock = _local_ifc.Func("now", (("id", "string"),), ("u64",))
            host_iface = _local_ifc.Interface("wasi:clocks", "0.2.0", frozenset({clock}))
            drifted = _local_ifc.Interface("wasi:clocks", "0.2.1", frozenset(
                {_local_ifc.Func("now", (("id", "string"),), ("u64", "error"))}))
            _verify(_local_ifc.classify(host_iface, drifted)["class"] == _local_ifc.BREAKING,
                    "local typed interface check failed to flag signature drift")
            findings[0] = self.partial(
                items[0],
                "Imports are matched by name and, when typed metadata is supplied, by the local typed "
                "interface layer (interfaces.py), which refuses signature drift; INV-11 is still required "
                "as the authoritative typed-link check.",
                note="INV-11 Interface contract language is not installed here")
            return findings
        clock = inv11.Func("now", (("id", "string"),), ("u64",))
        host_iface = inv11.Interface("wasi:clocks", "0.2.0", frozenset({clock}))
        guest_ok = inv11.Interface("wasi:clocks", "0.2.0", frozenset({clock}))
        drifted = inv11.Interface(
            "wasi:clocks", "0.2.1",
            frozenset({inv11.Func("now", (("id", "string"),), ("u64", "error"))}))
        _verify(inv11.check_link(host_iface, guest_ok)["linked"], "check failed: inv11.check_link(host_iface, guest_ok)['linked']")
        caught = False
        try:
            inv11.check_link(host_iface, drifted)
        except inv11.Incompatible:
            caught = True
        _verify(caught, 'check failed: caught')
        _verify(inv11.classify(host_iface, drifted)["class"] == inv11.BREAKING, "check failed: inv11.classify(host_iface, drifted)['class'] == inv11.BREAKING")
        findings[0] = self.satisfied(
            items[0],
            "compose() matches imports to the host image by name; the INV-11 typed link check covers "
            "what that name match cannot: a guest whose signature matches links, and one that added a "
            "result case the host image cannot produce is refused and classified breaking.",
            *self._evidence("component.py::compose"), "INV-11/check_link")
        return findings

COMPONENT = HybridWasmUnikernelComponent
