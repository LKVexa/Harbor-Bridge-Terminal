"""GAP-09 - Unified observability master-applied component.

The pk_core-facing assessment layer delegates data-plane behavior to
``runtime.py``.  Security findings exercise the verified submission path rather
than trusting caller-supplied booleans.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .runtime import (
    STALENESS_BOUND,
    CrossTenantQuery,
    HMACFixtureVerifier,
    ReporterAuthority,
    ReporterUntrusted,
    Sample,
    ScopeViolation,
    SignalStore,
)


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioral check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


_FIXTURE_KEY = b"gap09-conformance-only-key"


def _fixture() -> tuple[SignalStore, HMACFixtureVerifier]:
    authority = ReporterAuthority(
        reporter="n1",
        attested_level="hardware",
        tenants=frozenset({"t1"}),
        environments=frozenset({"prod"}),
        sites=frozenset({"dub"}),
        workloads=frozenset({"w1"}),
    )
    verifier = HMACFixtureVerifier(
        keys={("n1", "k1"): _FIXTURE_KEY},
        authorities={"n1": authority},
    )
    return SignalStore(trust_verifier=verifier), verifier


def _submit(
    store: SignalStore,
    verifier: HMACFixtureVerifier,
    reporter: str,
    samples: list[Sample],
    *,
    now: int,
    submission_id: str,
    key: bytes = _FIXTURE_KEY,
) -> int:
    payload = store.canonical_submission_payload(
        reporter=reporter,
        submission_id=submission_id,
        issued_at=now,
        samples=samples,
    )
    signature = verifier.sign(key, payload)
    return store.submit_verified(
        reporter,
        samples,
        submission_id=submission_id,
        issued_at=now,
        signature=signature,
        attestation={"key_id": "k1"},
        now=now,
    )


class UnifiedObservabilityComponent(Component):
    """Master-applied component for GAP-09."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        # Implementation & Configuration index 3 == checklist C034:
        # validate configuration before activation and fail closed.
        try:
            SignalStore(staleness_bound=0)
        except ValueError:
            findings[3] = self.satisfied(
                items[3],
                "Invalid security/operational bounds are rejected during store construction before activation.",
                *self._evidence("runtime.py::SignalStore.__post_init__"),
            )
        else:
            raise AssertionError("invalid configuration did not fail closed")
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        store, verifier = _fixture()
        valid = Sample("demand", 1.0, "t1", "prod", "dub", "w1", at=0)

        # Security index 1 == C042: least privilege.
        over_scoped = Sample("demand", 1.0, "t2", "prod", "dub", "w1", at=0)
        try:
            _submit(store, verifier, "n1", [over_scoped], now=0, submission_id="sec-scope")
        except ScopeViolation:
            findings[1] = self.satisfied(
                items[1],
                "A verified reporter is still limited to its explicit tenant/environment/site/workload capability scope.",
                *self._evidence("runtime.py::SignalStore._authorize"),
            )
        else:
            raise AssertionError("expected ScopeViolation for over-scoped reporter")

        # Security index 3 == C044: authenticate nodes/peers before trust.
        rogue_payload = store.canonical_submission_payload(
            reporter="rogue", submission_id="sec-rogue", issued_at=0, samples=[valid]
        )
        try:
            store.submit_verified(
                "rogue",
                [valid],
                submission_id="sec-rogue",
                issued_at=0,
                signature=verifier.sign(_FIXTURE_KEY, rogue_payload),
                attestation={"key_id": "k1"},
                now=0,
            )
        except ReporterUntrusted:
            findings[3] = self.satisfied(
                items[3],
                "A reporter without a verified authority/key binding cannot inject signals.",
                *self._evidence("runtime.py::SignalStore.submit_verified"),
            )
        else:
            raise AssertionError("expected ReporterUntrusted for unapproved reporter")

        # Security index 4 == C045: verify signatures/provenance before trust.
        try:
            store.submit_verified(
                "n1",
                [valid],
                submission_id="sec-badsig",
                issued_at=0,
                signature="00",
                attestation={"key_id": "k1"},
                now=0,
            )
        except ReporterUntrusted:
            findings[4] = self.satisfied(
                items[4],
                "A submission with an invalid signature is refused even for an approved reporter.",
                *self._evidence("runtime.py::HMACFixtureVerifier.verify"),
            )
        else:
            raise AssertionError("expected ReporterUntrusted for invalid signature")

        # Security index 5 == C046: tenant/workload isolation.
        _submit(store, verifier, "n1", [valid], now=0, submission_id="sec-ok")
        try:
            store.read(
                caller_tenant="t2",
                tenant="t1",
                environment="prod",
                site="dub",
                workload="w1",
                signal="demand",
                now=1,
            )
        except CrossTenantQuery:
            findings[5] = self.satisfied(
                items[5],
                "A query naming another tenant is refused at the read boundary.",
                *self._evidence("runtime.py::SignalStore.read"),
            )
        else:
            raise AssertionError("expected CrossTenantQuery")
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        store, verifier = _fixture()
        _submit(
            store,
            verifier,
            "n1",
            [Sample("cpu", 1.0, "t1", "prod", "dub", "w1", at=0)],
            now=0,
            submission_id="res-1",
        )
        fresh = store.read(
            caller_tenant="t1", tenant="t1", environment="prod", site="dub",
            workload="w1", signal="cpu", now=1,
        )
        old = store.read(
            caller_tenant="t1", tenant="t1", environment="prod", site="dub",
            workload="w1", signal="cpu", now=STALENESS_BOUND + 5,
        )
        _verify(not fresh["stale"] and old["stale"] and old["value"] == 1.0)
        _verify(store.silent_reporters(["n1", "n2"], now=0) == ["n2"])
        _verify(store.silent_reporters(["n1"], now=STALENESS_BOUND + 5) == ["n1"])

        # Resilience index 1 == C052: health/stall detection thresholds.
        findings[1] = self.satisfied(
            items[1],
            "Configured staleness and reporter-silence thresholds distinguish fresh, stale and silent telemetry sources.",
            *self._evidence("runtime.py::SignalStore.read"),
            *self._evidence("runtime.py::SignalStore.silent_reporters"),
        )
        return findings


COMPONENT = UnifiedObservabilityComponent
