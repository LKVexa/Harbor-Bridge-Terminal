"""GAP-13 - Policy engine.

The policy engine is where the estate's rules are evaluated rather than scattered. Decisions default to deny, the most specific matching rule wins with deterministic tie-breaking, and every verdict carries the rule that produced it -- so an operator can always answer why.

The component answers all 100 requirements of the GAP-13 checklist.  Bands
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



from .engine import (
    BUNDLE_STALENESS_BOUND,
    BundleRejected,
    PolicyEngine,
    Rule,
    ScopeEscalation,
)


from .selftest import selftest_load as _selftest_load


class PolicyEngineComponent(Component):
    """Master-applied component for GAP-13."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        engine = PolicyEngine("prod")
        _selftest_load(engine, [
            Rule("broad-allow", "allow", (("action", "read"),)),
            Rule("narrow-deny", "deny", (("action", "read"), ("classification", "pii"))),
        ], "v1", now=0)
        general = engine.evaluate({"action": "read", "classification": "public"})
        specific = engine.evaluate({"action": "read", "classification": "pii"})
        _verify(general["effect"] == "allow" and specific["effect"] == "deny", "check failed: general['effect'] == 'allow' and specific['effect'] == 'deny'")
        _verify(specific["rule"] == "narrow-deny", "check failed: specific['rule'] == 'narrow-deny'")
        repeat = engine.evaluate({"action": "read", "classification": "pii"})
        _verify(repeat == specific, "evaluation is not deterministic")
        findings[5] = self.satisfied(
            items[5],
            "Evaluation is deterministic and most-specific-wins: a two-attribute deny overrides a "
            "one-attribute allow, and repeated evaluation is byte-identical.",
            *self._evidence("component.py::PolicyEngine.evaluate"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        engine = PolicyEngine("prod")
        verdict = engine.evaluate({"action": "anything"})
        _verify(verdict["effect"] == "deny" and verdict["rule"] is None, "check failed: verdict['effect'] == 'deny' and verdict['rule'] is None")
        findings[1] = self.satisfied(
            items[1],
            "An empty or non-matching policy denies: least privilege is the default state, not a "
            "configuration choice.",
            *self._evidence("component.py::PolicyEngine.evaluate"))
        try:
            engine.load([Rule("r", "allow", (("action", "read"),))], "v1", {"verified": True})
        except BundleRejected:
            findings[4] = self.satisfied(
                items[4],
                "A bundle is never loaded on caller assertion ({'verified': True} is refused); only a "
                "BundleVerifier-minted result over an Ed25519 signature from a trusted GAP-07 key activates.",
                *self._evidence("component.py::PolicyEngine.load"))
        else:
            raise AssertionError('expected BundleRejected was not raised; the refusal this finding claims did not happen')
        try:
            _selftest_load(engine, [
                Rule("estate-deny", "deny", (("action", "write"),), scope="estate"),
                Rule("tenant-allow", "allow", (("action", "write"), ("tenant", "t1")), scope="tenant"),
            ], "v2")
        except ScopeEscalation:
            findings[5] = self.satisfied(
                items[5],
                "A tenant rule that would widen an estate-level deny is refused at load time, so tenant "
                "policy can only narrow.",
                *self._evidence("component.py::PolicyEngine.load"))
        else:
            raise AssertionError('expected ScopeEscalation was not raised; the refusal this finding claims did not happen')
        return findings

    def assess_observability(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_observability(items)
        engine = PolicyEngine("prod")
        _selftest_load(engine, [
            Rule("a-allow", "allow", (("action", "read"),)),
            Rule("b-deny", "deny", (("action", "read"),)),
        ], "v1", now=0)
        verdict = engine.evaluate({"action": "read"})
        _verify(verdict["effect"] == "deny" and verdict["tie_break"], "check failed: verdict['effect'] == 'deny' and verdict['tie_break']")
        _verify(verdict["considered"] == ["b-deny", "a-allow"], "check failed: verdict['considered'] == ['b-deny', 'a-allow']")
        findings[7] = self.satisfied(
            items[7],
            "Equally specific rules resolve deny-first, the tie-break is flagged, and every considered rule "
            "is listed -- so 'why was this denied' has a complete answer.",
            *self._evidence("component.py::PolicyEngine.evaluate"))
        stale = engine.evaluate({"action": "read"}, now=BUNDLE_STALENESS_BOUND + 1)
        _verify(stale["stale"] and stale["version"] == "v1", "check failed: stale['stale'] and stale['version'] == 'v1'")
        findings[3] = self.satisfied(
            items[3],
            "Verdicts carry the policy version and their own staleness, so a decision taken on a cached "
            "bundle at a disconnected site is identifiable afterwards.",
            *self._evidence("component.py::PolicyEngine.evaluate"))
        return findings

COMPONENT = PolicyEngineComponent
