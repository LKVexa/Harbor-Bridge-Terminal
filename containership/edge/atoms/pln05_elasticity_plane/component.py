"""PLN-05 - Elasticity plane.

The elasticity plane decides how much capacity exists, including the scale-to-zero case that container orchestration handles badly. It converts observed demand into a capacity target with explicit hysteresis, so the estate does not oscillate.

The component maps the PLN-05 checklist into the shared ``pk_core`` assessment
framework.  Custom findings below are used only where this repository contains
concrete behavioural evidence; repository-level gaps remain visible in the
post-hardening audit report.
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



from .controller import ElasticityController, Limits


class ElasticityPlaneComponent(Component):
    """Master-applied component for PLN-05."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        c = ElasticityController(Limits(floor=0, ceiling=8, grace_samples=3), current=4)
        _verify(c.observe(0.9)[0] == 8, 'check failed: c.observe(0.9)[0] == 8')
        held = [c.observe(0.05) for _ in range(2)]
        _verify(all(t == 8 for t, _ in held), "scale-down acted before the grace period")
        _verify(c.observe(0.05)[0] == 4, "scale-down did not act after the grace period")
        # C034: configuration validation must fail closed.
        try:
            Limits(floor=5, ceiling=1)
        except ValueError:
            findings[3] = self.satisfied(
                items[3],
                f"Typed limits reject inconsistent configuration; the controller also exercised "
                f"{c.suppressed} hysteresis hold(s) before scale-down.",
                *self._evidence("controller.py::Limits"),
                *self._evidence("controller.py::ElasticityController.observe"))
        else:
            raise AssertionError("expected inconsistent limits to fail closed")
        return findings

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        c = ElasticityController(Limits(floor=0, ceiling=5), current=3)
        _verify(c.observe(0.99)[0] == 5, 'check failed: c.observe(0.99)[0] == 5')
        samples = 0
        while c.current > 0 and samples < 40:
            target, _ = c.observe(0.0)
            _verify(0 <= target <= 5, "target escaped the declared envelope")
            samples += 1
        _verify(c.current == 0, "scale-to-zero never reached with floor=0")
        # C069: the controller defines a bounded capacity model and saturation thresholds.
        findings[8] = self.satisfied(
            items[8],
            f"Capacity targets stayed inside the declared model across a full step-down to zero "
            f"({samples} samples, {c.suppressed} suppressed by hysteresis).",
            *self._evidence("controller.py::ElasticityController.observe"))
        # C061 asks for a full reproducible performance baseline.  A sibling
        # snapshot implementation can provide one startup datapoint, but that is
        # intentionally not overstated as complete performance certification.
        inv26 = sibling("INV-26")
        if inv26 is None:
            findings[0] = self.partial(
                items[0],
                "No reproducible cold-start baseline can be produced by this repository alone.",
                note="INV-26 MicroVM snapshotting is not installed here")
        else:
            store = inv26.SnapshotStore()
            devices = {"virtio-net", "virtio-block"}
            store.capture(name="warm-pool", tenant="t1", workload="w1",
                          devices=devices, memory_mib=256)
            restore = store.restore("warm-pool", tenant="t1", devices=devices, elapsed_ms=4)
            _verify(restore["within_budget"] and not restore["cold"], "snapshot restore missed its declared budget")
            findings[0] = self.partial(
                items[0],
                f"A reproducible snapshot-restore datapoint is available ({restore['restore_ms']}ms against "
                f"a {restore['budget_ms']}ms budget), but full latency/throughput/startup/CPU/memory/storage/"
                "network/power baselines are not implemented in this package.",
                *self._evidence("controller.py::ElasticityController.observe"),
                "INV-26/SnapshotStore.restore")
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        c = ElasticityController(Limits(floor=2, ceiling=10), current=10)
        c.lower_ceiling(4)
        target, _ = c.observe(0.99)
        _verify(target == 4, "externally lowered ceiling was not honoured")
        findings[0] = self.partial(
            items[0],
            "The contract names key elasticity threats and the ceiling-bypass mitigation is exercised, but the "
            "repository does not contain a complete tenant/supply-chain/control-plane threat model.",
            *self._evidence("controller.py::ElasticityController.lower_ceiling"))
        gap09 = sibling("GAP-09")
        if gap09 is None:
            findings[3] = self.partial(
                items[3], "This plane trusts its demand input; signal authentication is not available.",
                note="GAP-09 Unified observability is not installed here")
        else:
            store = gap09.SignalStore()
            sample = gap09.Sample("demand", 0.99, "t1", "dub", "w1", at=0)
            try:
                store.submit("rogue", [sample], attested_level="untrusted", signed=True, now=0)
                forged = True
            except gap09.ReporterUntrusted:
                forged = False
            _verify(not forged, "an unattested reporter injected a demand sample")
            store.submit("n1", [sample], attested_level="hardware", signed=True, now=0)
            reading = store.read(caller_tenant="t1", tenant="t1", site="dub", workload="w1",
                                 signal="demand", now=1)
            controller = ElasticityController(Limits(floor=0, ceiling=8), current=2)
            target, reason = controller.observe(reading["value"])
            _verify(target > 2 and reason == "scale-up", "check failed: target > 2 and reason == 'scale-up'")
            findings[3] = self.partial(
                items[3],
                "GAP-09 authenticates the demand reporter used by this controller, but PLN-05 still lacks "
                "repository-local authentication requirements/tests for every node, peer, artifact, provider, "
                "and control-plane actor boundary.",
                *self._evidence("controller.py::ElasticityController.observe"), "GAP-09/SignalStore")
        return findings

COMPONENT = ElasticityPlaneComponent
