"""GAP-02 - Hardware capability discovery.

Hardware capability discovery is what makes the rest of the estate honest about heterogeneity. It reports only what it has actually probed, distinguishes a capability that is absent from one it could not test, and never lets a node advertise more than it proved.

The component answers all 100 requirements of the GAP-02 checklist.  Bands
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


from .capabilities import (
    ABSENT,
    FRESHNESS_BOUND,
    PRESENT,
    UNPROBED,
    CapabilityReport,
    ProbeSchedule,
    ProbeUnavailable,
    ReportStale,
    probe,
)


class HardwareCapabilityDiscoveryComponent(Component):
    """Master-applied component for GAP-02."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        report = CapabilityReport("n1")
        _verify(probe(report, "sev-snp", lambda: True, 0) == PRESENT, "check failed: probe(report, 'sev-snp', lambda: True, 0) == PRESENT")
        _verify(probe(report, "sgx", lambda: False, 0) == ABSENT, "check failed: probe(report, 'sgx', lambda: False, 0) == ABSENT")
        def unavailable():
            raise ProbeUnavailable("no /dev access in this container")
        _verify(probe(report, "tdx", unavailable, 0) == UNPROBED, "check failed: probe(report, 'tdx', unavailable, 0) == UNPROBED")
        _verify(report.present() == {"sev-snp"}, "check failed: report.present() == {'sev-snp'}")
        view = report.for_consumer(now=1)
        _verify(view["unprobed"] == ["tdx"] and "tdx" not in view["present"], "check failed: view['unprobed'] == ['tdx'] and 'tdx' not in view['present']")
        findings[5] = self.satisfied(
            items[5],
            "Probing is deterministic and three-valued: present, absent and unprobed are distinct, and "
            "only the probed-present set reaches consumers.",
            *self._evidence("component.py::probe"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        report = CapabilityReport("n1")
        def unavailable():
            raise ProbeUnavailable("blocked")
        probe(report, "microvm", unavailable, 0)
        _verify("microvm" not in report.for_consumer(now=1)["present"], "check failed: 'microvm' not in report.for_consumer(now=1)['present']")
        findings[0] = self.satisfied(
            items[0],
            "A node cannot over-report: a capability that could not be probed is published as unprobed and "
            "is invisible to the placement filter.",
            *self._evidence("component.py::CapabilityReport.present"))
        gap06, gap07 = sibling("GAP-06"), sibling("GAP-07")
        if gap06 is None or gap07 is None:
            missing = [n for n, m in (("GAP-06", gap06), ("GAP-07", gap07)) if m is None]
            findings[4] = self.partial(
                items[4], "Reports are structurally consistent but not signed by the node identity.",
                note=f"not installed here: {', '.join(missing)}")
        else:
            attestor = gap06.Attestor("prod", accepted={"m-fw-1"})
            attestor.attest(gap06.Evidence("n1", ("m-fw-1",), attestor.challenge("n1", 0), hardware_rooted=True), now=0)
            _verify(attestor.level_of("n1", 0) == "hardware", "check failed: attestor.level_of('n1', 0) == 'hardware'")
            store = gap07.TrustStore("prod")
            store.add("n1", "authority", b"node-key")
            report = CapabilityReport("n1")
            probe(report, "sev-snp", lambda: True, 0)
            body = report.canonical_bytes(now=1)
            signature = store.sign("n1", body)
            _verify(store.verify(signature, body, "attestation")["verified"], "check failed: store.verify(signature, body, 'attestation')['verified']")
            tampered = body.replace(b"sev-snp", b"sev-snp-plus")
            try:
                store.verify(signature, tampered, "attestation")
                forged = True
            except gap07.SignatureInvalid:
                forged = False
            _verify(not forged, "an edited capability report verified")
            findings[4] = self.satisfied(
                items[4],
                "The report is signed by a GAP-06-attested node identity through GAP-07 and bound to its "
                "digest, so a node cannot edit its capability list after publication.",
                *self._evidence("component.py::CapabilityReport.for_consumer"),
                "GAP-06/Attestor", "GAP-07/TrustStore")
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        report = CapabilityReport("n1")
        probe(report, "sev-snp", lambda: True, 0)
        try:
            report.for_consumer(now=FRESHNESS_BOUND + 1)
        except ReportStale:
            findings[0] = self.satisfied(
                items[0],
                f"A report older than {FRESHNESS_BOUND} ticks is refused at the consumer boundary rather "
                "than silently trusted.",
                *self._evidence("component.py::CapabilityReport.for_consumer"))
        else:
            raise AssertionError('expected ReportStale was not raised; the refusal this finding claims did not happen')
        probe(report, "sev-snp", lambda: False, 10)
        _verify(report.state("sev-snp") == ABSENT, "check failed: report.state('sev-snp') == ABSENT")
        schedule = ProbeSchedule(("sev-snp", "tdx"), interval=FRESHNESS_BOUND)
        _verify(schedule.due(report, now=10) == ["tdx"], "newly declared capability was not scheduled")
        _verify("sev-snp" in schedule.due(report, now=10 + FRESHNESS_BOUND), "stale capability was not scheduled")
        findings[1] = self.satisfied(
            items[1],
            "Hardware that disappears between probes flips to absent on the next sweep, so a capability "
            "downgrade is visible rather than sticky.",
            *self._evidence("component.py::probe"))
        return findings

COMPONENT = HardwareCapabilityDiscoveryComponent
