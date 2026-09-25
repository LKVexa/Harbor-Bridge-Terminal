"""GAP-07 - Artifact provenance/signing production-component adapter."""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .core import (
    AuditLedger,
    InMemoryKeyProvider,
    ProvenanceInvalid,
    SignatureInvalid,
    SignerUntrusted,
    TrustStore,
    Unsigned,
    digest,
    provenance,
    verify_provenance,
)


def _verify(condition, message="behavioural check failed"):
    """Fail behavioural checks even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class ArtifactProvenanceSigningComponent(Component):
    """Master-applied component for GAP-07."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    @staticmethod
    def _store(environment: str = "prod") -> TrustStore:
        keys = InMemoryKeyProvider({
            "release-k1": b"release-reference-key-0001",
            "release-k2": b"release-reference-key-0002",
            "policy-k1": b"policy-reference-key-000001",
            "data-k1": b"data-reference-key-00000001",
        })
        return TrustStore(environment, keys, audit=AuditLedger())

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        store = self._store()
        store.add("release-bot", "release", "release-k1")
        payload = b"executable-bytes"
        sig = store.sign("release-bot", payload, "code", now=100)
        result = store.verify(sig, payload, "code", now=101)
        _verify(result["verified"] and result["digest"] == digest(payload))

        chain = provenance([("source", b"src"), ("build", b"obj"), ("package", payload)])
        checked = verify_provenance(chain, [b"src", b"obj", payload])
        _verify(checked["verified"] and checked["head"] == chain["head"])
        _verify(chain["links"][1]["previous"] == chain["links"][0]["link_digest"])
        findings[5] = self.satisfied(
            items[5],
            "PK_SIGNATURE/2 binds signer, environment, artifact kind, key id, digest and issuance time; "
            "PK_PROVENANCE/2 hash-chains each step's metadata and artifact digest.",
            *self._evidence("core.py::TrustStore.verify", "core.py::provenance", "core.py::verify_provenance"),
        )
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        store = self._store()
        store.add("release-bot", "release", "release-k1")
        store.add("data-bot", "data", "data-k1")
        payload = b"executable-bytes"
        sig = store.sign("release-bot", payload, "code", now=100)

        proven = []
        refusal_cases = [
            (lambda: store.verify(sig, b"substituted-bytes", "code", now=101), SignatureInvalid, "byte substitution"),
            (lambda: store.verify(None, payload, "code", now=101), Unsigned, "signature stripping"),
            (lambda: store.sign("data-bot", payload, "code", now=100), SignerUntrusted, "role confusion"),
            (lambda: store.verify(sig, payload, "bundle", now=101), SignatureInvalid, "cross-kind replay"),
        ]
        for action, expected, label in refusal_cases:
            try:
                action()
            except expected:
                proven.append(label)
            else:
                raise AssertionError(f"expected {expected.__name__}: {label}")
        _verify(len(proven) == len(refusal_cases), proven)
        findings[4] = self.satisfied(
            items[4],
            "Digest, role, artifact-kind, environment and key-id binding refuse: " + ", ".join(proven) + ".",
            *self._evidence("core.py::TrustStore.sign", "core.py::TrustStore.verify"),
        )

        store.revoke("release-bot", now=102)
        try:
            store.verify(sig, payload, "code", now=103)
        except SignerUntrusted:
            findings[3] = self.satisfied(
                items[3],
                "A locally revoked signer is refused immediately, including for artifacts signed before revocation.",
                *self._evidence("core.py::TrustStore.role_of", "core.py::TrustStore.revoke"),
            )
        else:
            raise AssertionError("expected SignerUntrusted after revocation")

        _verify(store.audit is not None and store.audit.verify())
        findings[8] = self.satisfied(
            items[8],
            "Security-sensitive trust, sign, verify and refusal events are emitted to a local hash-chained audit ledger. "
            "External durable anchoring remains an integration responsibility.",
            *self._evidence("core.py::AuditLedger", "core.py::TrustStore._event"),
        )
        findings[9] = self.partial(
            items[9],
            "Deterministic tests cover substitution, stripping, role confusion, cross-kind replay, cross-environment replay, "
            "malformed signatures, revocation and provenance tampering; production fuzzing/resource-exhaustion campaigns are not bundled.",
            note="requires CI fuzz/soak infrastructure outside this component package",
        )
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        keys = InMemoryKeyProvider({"policy-k1": b"policy-reference-key-000001"})
        store = TrustStore("prod", keys)
        store.add("bot", "policy", "policy-k1")
        good = store.sign("bot", b"policy-bytes", "policy", now=10)
        for payload, kind, expected in [
            (b"policy-bytes", "policy", None),
            (b"tampered", "policy", SignatureInvalid),
            (b"policy-bytes", "code", SignatureInvalid),
        ]:
            try:
                store.verify(good, payload, kind, now=11)
            except PermissionError as exc:
                _verify(expected is not None and isinstance(exc, expected), f"{kind}: got {type(exc).__name__}")
            else:
                _verify(expected is None, f"{kind}: expected {expected} was not raised")
        findings[0] = self.satisfied(
            items[0],
            "Verification refusals expose stable exception classes and machine-readable error codes; malformed or replayed inputs fail closed.",
            *self._evidence("core.py::VerificationError", "core.py::TrustStore.verify"),
        )
        return findings


COMPONENT = ArtifactProvenanceSigningComponent
