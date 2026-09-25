"""INV-72 - Accelerated workload requirement.

An accelerated workload requirement is how a job says what hardware it actually needs: which accelerator class, how much device memory, how many devices, and whether they must share a fast interconnect. Matching is strict on what matters -- a job needing 80 GB is never placed on a 40 GB part -- and device sharing is allowed only when the tenant's isolation class permits partitioning.

The pk_core integration exposes assessments for the INV-72 checklist. Bands
whose defaults would merely restate the contract are overridden below so selected
findings are backed by exercised element behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import build
from .metadata import ELEMENT_ID, ELEMENT_NAME

def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``.

    Bare ``assert`` statements are stripped by the optimiser, which silently turned
    exercised checks into declared-only ones (and, where an assert carried a side
    effect, broke the element outright).  Every check goes through here instead.
    """
    if not condition:
        raise AssertionError(message)



from .matcher import Device, match


class AcceleratedWorkloadRequirementComponent(Component):
    """Master-applied component for INV-72."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def _fleet(self):
        return [Device("a0", "gpu-large", 80, "n1", "nvl-1"), Device("a1", "gpu-large", 80, "n1", "nvl-1"),
                Device("b0", "gpu-large", 80, "n2", "pcie"), Device("c0", "gpu-large", 40, "n3", "pcie"),
                Device("p0", "gpu-large", 80, "n4", "pcie", partition_of="gpu-n4")]

    def assess_testing(self, items: list[ChecklistItem]) -> list[Finding]:
        # v4.2.0 bound this exercised check to implementation[0] = C031 (pin approved technology), which it
        # does not evidence; it evidences C081 (deterministic unit-level logic).
        findings = super().assess_testing(items)
        fleet = self._fleet()
        pair, _ = match({"class": "gpu-large", "mem_gb": 80, "count": 2, "interconnect": True,
                         "tenant": "t1", "isolation": "dedicated"}, fleet)
        big, why = match({"class": "gpu-large", "mem_gb": 120, "tenant": "t1"}, fleet)
        _verify(pair == ["a0", "a1"] and big is None and "80 GB < 120 GB" in why[0], "check failed: pair == ['a0', 'a1'] and big is None and ('80 GB < 120 GB' in why[0])")
        findings[0] = self.satisfied(
            items[0],
            "A two-device job needing a shared interconnect gets the two 80 GB parts on one link group, "
            "and a job needing more memory than any part has is refused with the gap stated rather than "
            "placed to fail mid-run.",
            *self._evidence("matcher.py::match"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        part = [Device("p0", "gpu-large", 80, "n4", "pcie", partition_of="gpu-n4")]
        got, _ = match({"class": "gpu-large", "mem_gb": 20, "tenant": "t1", "isolation": "shared"}, part)
        other, why = match({"class": "gpu-large", "mem_gb": 20, "tenant": "t2", "isolation": "shared"}, part)
        ded, why2 = match({"class": "gpu-large", "mem_gb": 20, "tenant": "t1", "isolation": "dedicated"},
                          [Device("p1", "gpu-large", 80, "n4", "pcie", partition_of="gpu-n4")])
        _verify(got == ["p0"] and other is None and ded is None, "check failed: got == ['p0'] and other is None and (ded is None)")
        # v4.2.0 bound this to security[0] = C041 (threat model); it evidences C046 (tenant isolation).
        findings[5] = self.satisfied(
            items[5],
            "Partitioned devices are shared only within the rules: a slice taken by one tenant is refused "
            "to a second tenant, and a job requiring dedicated isolation is never given a slice at all.",
            *self._evidence("matcher.py::match"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        import tempfile, os
        from .state import ReservationStore
        from .errors import AccelError
        with tempfile.TemporaryDirectory() as td:
            j = os.path.join(td, "j.jsonl")
            s = ReservationStore(journal_path=j, fsync=False)
            r, _ = s.reserve({"class": "gpu-large", "mem_gb": 80, "tenant": "t1"}, self._fleet())
            with open(j, "a") as f:
                f.write('{"torn')
            back = ReservationStore.recover(j)
            back.advance_fence(2)
            try:
                back.reserve({"class": "gpu-large", "mem_gb": 80, "tenant": "t2"}, self._fleet(), fence=1)
                stale_refused = False
            except AccelError as e:
                stale_refused = e.code == "ACCEL_STALE_FENCE"
        _verify([x.reservation_id for x in back.active()] == [r.reservation_id] and back.recovery_report["torn_tail"]
                and stale_refused, "check failed: journal recovery / fencing")
        findings[6] = self.satisfied(
            items[6],
            "Recovery replays the write-ahead journal (a torn final record is truncated, earlier corruption is "
            "refused) and a stale controller's write is refused by fencing.",
            *self._evidence("state.py::ReservationStore.recover", "state.py::ReservationStore._check_fence"))
        return findings

    def assess_observability(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_observability(items)
        from .telemetry import Metrics
        m = Metrics()
        m.inc("accel_refused_total", reason="ACCEL_INSUFFICIENT_MEMORY")
        m.observe("accel_decision_latency_ms", 0.4)
        text = m.render()
        _verify("accel_refused_total" in text and "accel_decision_latency_ms_bucket" in text,
                "check failed: metrics exposition")
        findings[1] = self.satisfied(
            items[1], "Rate, error, latency and saturation metrics are emitted and exposed in Prometheus text form.",
            *self._evidence("telemetry.py::Metrics.render"))
        return findings

    def assess_interfaces(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_interfaces(items)
        from .schema_check import check
        ok = check({"class": "gpu-large", "mem_gb": 80, "tenant": "t1"}, "PK_ACCEL_REQ-1") == []
        bad = check({"class": "gpu-large", "mem_gb": True, "tenant": "t1", "x": 1}, "PK_ACCEL_REQ-1")
        _verify(ok and len(bad) >= 2, "check failed: request schema")
        findings[1] = self.satisfied(
            items[1], "Requests are validated against the versioned PK_ACCEL_REQ/1 schema; unknown fields and "
            "booleans-as-numbers are rejected.", *self._evidence("schema_check.py::check", "schemas/"))
        return findings


# Findings backed by exercised behaviour rather than restated contract declarations.  pk_core's default
# handlers derive the other findings from the contract (some unconditionally), so a pk_core GO is a
# declaration-conformance verdict, not implementation evidence - see evidence/PK_GATE_RESULTS.json.
EXERCISED_BANDS = ("testing[0]=C081", "security[5]=C046", "resilience[6]=C057", "observability[1]=C072",
                   "interfaces[1]=C022")

COMPONENT = AcceleratedWorkloadRequirementComponent
