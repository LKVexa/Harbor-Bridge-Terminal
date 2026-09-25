"""PLN-07 - Security plane.

The security plane replaces ambient trust with explicit, attenuable capabilities. Nothing in the estate holds authority it was not granted; every grant names its holder, its scope, and its expiry, and any holder may attenuate a grant but never widen one.

The component answers all 100 requirements of the PLN-07 checklist.  Bands
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



from .grants import Grant, GrantInvalid, MAX_DELEGATION_DEPTH, Verifier, Widening


class SecurityPlaneComponent(Component):
    """Master-applied component for PLN-07."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        root = Grant("controller", "t1", frozenset({"state", "messaging", "invoke"}), not_after=100)
        narrowed = root.attenuate(subject="worker", scope={"state"}, not_after=50)
        _verify(narrowed.scope == frozenset({"state"}) and narrowed.depth == 1, "check failed: narrowed.scope == frozenset({'state'}) and narrowed.depth == 1")
        verifier = Verifier()
        _verify(verifier.verify(narrowed, now=10, capability="state", tenant="t1"), "check failed: verifier.verify(narrowed, now=10, capability='state', tenant='t1')")
        findings[5] = self.satisfied(
            items[5],
            f"Issuance and attenuation are deterministic: root {root.id} -> attenuated {narrowed.id} "
            "at depth 1 with a strictly smaller scope and earlier expiry.",
            *self._evidence("component.py::Grant"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        root = Grant("controller", "t1", frozenset({"state"}), not_after=100)
        proven = []
        try:
            root.attenuate(scope={"state", "secrets"})
        except Widening:
            proven.append("scope widening")
        try:
            root.attenuate(not_after=200)
        except Widening:
            proven.append("expiry extension")
        _verify(len(proven) == 2, 'check failed: len(proven) == 2')
        findings[1] = self.satisfied(
            items[1],
            f"Attenuation is one-way: {' and '.join(proven)} both refused.",
            *self._evidence("component.py::Grant.attenuate"))

        verifier = Verifier()
        try:
            verifier.verify(root, now=101, capability="state", tenant="t1")
        except GrantInvalid:
            findings[3] = self.satisfied(
                items[3], "An expired grant is refused at verification.",
                *self._evidence("component.py::Verifier.verify"))
        else:
            raise AssertionError('expected GrantInvalid was not raised; the refusal this finding claims did not happen')
        revoking = Verifier(revoked={root.id})
        child = root.attenuate(subject="worker")
        try:
            revoking.verify(child, now=10, capability="state", tenant="t1")
        except GrantInvalid:
            findings[4] = self.satisfied(
                items[4], "Revoking a parent invalidates every grant derived from it.",
                *self._evidence("component.py::Verifier.verify"))
        else:
            raise AssertionError('expected GrantInvalid was not raised; the refusal this finding claims did not happen')
        try:
            verifier.verify(root, now=10, capability="state", tenant="t2")
        except GrantInvalid:
            findings[5] = self.satisfied(
                items[5], "A grant cannot be used against a tenant other than the one it names.",
                *self._evidence("component.py::Verifier.verify"))
        else:
            raise AssertionError('expected GrantInvalid was not raised; the refusal this finding claims did not happen')
        gap07 = sibling("GAP-07")
        if gap07 is None:
            from .signing import AlgorithmPolicy, KeyStore
            store = KeyStore("prod", AlgorithmPolicy(frozenset({"Ed25519", "HMAC-SHA256"})))
            store.generate("HMAC-SHA256")
            grant = store.sign_grant(Grant("worker", "t1", frozenset({"state"}), not_after=100, issuer="authority"))
            signed_verifier = Verifier(require_signatures=True, signature_verifier=store.grant_verifier())
            _verify(signed_verifier.verify(grant, now=10, capability="state", tenant="t1"), "signed grant did not verify")
            from dataclasses import replace
            try:
                signed_verifier.verify(replace(grant, scope=frozenset({"state", "secrets"})), now=10,
                                       capability="state", tenant="t1")
                forged = True
            except GrantInvalid:
                forged = False
            _verify(not forged, "a widened grant body verified against the original signature")
            findings[8] = self.partial(
                items[8], "Grants are signed and verified by the in-package reference KeyStore "
                "(signing.py); editing a signed body invalidates it.",
                note="Production trust root must come from GAP-07/HSM; not installed here")
        else:
            store = gap07.TrustStore("prod")
            store.add("authority", "authority", b"grant-key")
            unsigned = Grant("worker", "t1", frozenset({"state"}), not_after=100, issuer="authority")
            signature = store.sign("authority", unsigned.canonical_payload)
            grant = unsigned.signed(signature)

            def _signature_verifier(candidate):
                return store.verify(candidate.signature, candidate.canonical_payload, "grant")["verified"]

            signed_verifier = Verifier(require_signatures=True, signature_verifier=_signature_verifier)
            _verify(signed_verifier.verify(grant, now=10, capability="state", tenant="t1"),
                    "signed grant did not verify")
            from dataclasses import replace
            widened = replace(grant, scope=frozenset({"state", "secrets"}))
            try:
                signed_verifier.verify(widened, now=10, capability="state", tenant="t1")
                forged = True
            except GrantInvalid:
                forged = False
            _verify(not forged, "a widened grant body verified against the original signature")
            findings[8] = self.satisfied(
                items[8],
                "Grants are signed through GAP-07 and Verifier checks the signature-bound canonical grant "
                "body before accepting it; editing the scope after issue invalidates verification.",
                *self._evidence("grants.py::Grant.canonical_payload"), "GAP-07/TrustStore.verify")
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        grant = Grant("a", "t1", frozenset({"state"}), not_after=100)
        for depth in range(MAX_DELEGATION_DEPTH):
            grant = grant.attenuate(subject=f"delegated-{depth + 1}")
        try:
            grant.attenuate(subject="too-deep")
        except GrantInvalid:
            findings[6] = self.satisfied(
                items[6],
                f"Delegation depth is capped at {MAX_DELEGATION_DEPTH}, bounding blast radius of a "
                "compromised holder.",
                *self._evidence("component.py::Grant.attenuate"))
        else:
            raise AssertionError('expected GrantInvalid was not raised; the refusal this finding claims did not happen')
        gap04 = sibling("GAP-04")
        if gap04 is None:
            from .revocation import RevocationRegistry
            reg = RevocationRegistry()
            victim = Grant("worker", "t1", frozenset({"state"}), not_after=100)
            rec = reg.revoke(victim, effective_at=10, horizon=5, epoch=1)
            _verify(reg.horizon_breached(["dub"], now=16) == ["dub"], "horizon breach not detected")
            reg.acknowledge("dub", rec["seq"], epoch=1)
            _verify(reg.horizon_breached(["dub"], now=16) == [], "ack not honoured")
            findings[3] = self.partial(
                items[3], "Revocations are durable, hash-chained, acknowledged per site and horizon "
                "breaches are detected for quarantine (revocation.py).",
                note="GAP-04 site autonomy controller not installed; transport between sites is external")
        else:
            controller = gap04.AutonomyController("dub", granted_at=0, lease_ticks=60)
            controller.partition(0)
            _verify(controller.tier(61) == "expired", "check failed: controller.tier(61) == 'expired'")
            short = Grant("worker", "t1", frozenset({"state"}), not_after=60)
            verifier = Verifier()
            try:
                verifier.verify(short, now=61, capability="state", tenant="t1")
                survived = True
            except GrantInvalid:
                survived = False
            _verify(not survived, "a grant outlived the site's autonomy lease")
            findings[3] = self.satisfied(
                items[3],
                "The revocation horizon is the grant lifetime: a partitioned site's GAP-04 autonomy lease "
                "and the grants issued to it expire together, so an unseen revocation cannot outlive its "
                "window rather than propagating instantly.",
                *self._evidence("component.py::Verifier.verify"), "GAP-04/AutonomyController")
        return findings

COMPONENT = SecurityPlaneComponent
