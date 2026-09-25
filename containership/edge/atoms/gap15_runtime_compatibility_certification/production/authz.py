"""Authorization / capability policy (component 08).

ABAC with default deny and deny-overrides. A signed, versioned
``PolicyBundle`` holds rules of the form (effect, action, principal types,
partition pattern, conditions). Every entry point calls ``authorize()`` and the
result records the exact policy revision (MC-08-04, MC-08-07). High-impact
actions require separation of duties (a distinct second approver)
(MC-08-05). Break-glass is honoured only for a named set of actions with an
incident reference and is always audited (MC-08-08).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .authn import Principal
from .canonical import digest

ACTIONS = {
    "evidence.submit", "evidence.read", "matrix.read", "certify", "lifecycle.mutate", "lifecycle.reactivate",
    "revocation.create", "revocation.reverse", "quarantine.create", "quarantine.release", "policy.update",
    "truststore.update", "backup.run", "restore.run", "admin.diagnostics", "explain.read", "audit.read",
    "waiver.request", "waiver.approve", "admission.decide", "scheduler.control", "conflict.resolve",
    "gate.approve", "emergency.disable",
}
SOD_ACTIONS = {"lifecycle.reactivate", "truststore.update", "revocation.reverse", "quarantine.release",
               "policy.update", "gate.approve", "waiver.approve"}
BREAKGLASS_ACTIONS = {"revocation.create", "quarantine.create", "emergency.disable", "admin.diagnostics"}


class AuthzError(PermissionError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


@dataclass(frozen=True)
class Rule:
    rule_id: str
    effect: str  # allow | deny
    actions: frozenset
    ptypes: frozenset
    partitions: frozenset = frozenset({"*"})  # exact keys or "tenant/env/*" style prefixes
    subjects: frozenset = frozenset({"*"})


@dataclass
class PolicyBundle:
    revision: str
    rules: list = field(default_factory=list)

    def validate(self) -> list:
        """Static checks: unknown actions, wildcard actions, equal-scope allow/deny contradictions (MC-08-09, MC-23-05)."""
        problems = []
        ids = set()
        for r in self.rules:
            if r.rule_id in ids:
                problems.append(f"duplicate rule id {r.rule_id}")
            ids.add(r.rule_id)
            if r.effect not in ("allow", "deny"):
                problems.append(f"{r.rule_id}: bad effect")
            unknown = set(r.actions) - ACTIONS
            if unknown:
                problems.append(f"{r.rule_id}: unknown actions {sorted(unknown)}")
            if "*" in r.actions:
                problems.append(f"{r.rule_id}: wildcard action is prohibited")
            if r.effect == "allow" and "*" in r.partitions and set(r.actions) & SOD_ACTIONS:
                problems.append(f"{r.rule_id}: estate-wide allow on a separation-of-duties action")
        return problems

    def digest(self) -> str:
        return digest({"revision": self.revision, "rules": [
            [r.rule_id, r.effect, sorted(r.actions), sorted(r.ptypes), sorted(r.partitions), sorted(r.subjects)]
            for r in self.rules]})


def _partition_match(patterns: frozenset, partition: str) -> bool:
    for p in patterns:
        if p == "*" or p == partition or (p.endswith("/*") and partition.startswith(p[:-1])):
            return True
    return False


@dataclass(frozen=True)
class Decision:
    allowed: bool
    code: str
    matched: tuple
    policy_revision: str
    policy_digest: str

    def as_dict(self) -> dict:
        return dict(allowed=self.allowed, code=self.code, matched=list(self.matched),
                    policy_revision=self.policy_revision, policy_digest=self.policy_digest)


class Authorizer:
    def __init__(self, bundle: PolicyBundle) -> None:
        problems = bundle.validate()
        if problems:
            raise AuthzError("E_POLICY_INVALID", "; ".join(problems))
        self.bundle = bundle
        self._digest = bundle.digest()
        self.history = [bundle]

    def activate(self, bundle: PolicyBundle, *, trust=None, signature: Optional[dict] = None) -> None:
        if trust is not None and not verify_bundle(trust, signature, bundle):
            raise AuthzError("E_POLICY_SIGNATURE", "policy bundle signature missing or invalid")
        problems = bundle.validate()
        if problems:
            raise AuthzError("E_POLICY_INVALID", "; ".join(problems))
        self.bundle, self._digest = bundle, bundle.digest()
        self.history.append(bundle)

    def rollback(self) -> None:
        if len(self.history) < 2:
            raise AuthzError("E_POLICY_ROLLBACK", "no previous revision")
        self.history.pop()
        self.bundle = self.history[-1]
        self._digest = self.bundle.digest()

    def decide(self, principal: Principal, action: str, partition: str, *, second_approver: Optional[Principal] = None,
               _as_approver: bool = False) -> Decision:
        rev, dg = self.bundle.revision, self._digest
        if action not in ACTIONS:
            return Decision(False, "E_AUTHZ_UNKNOWN_ACTION", (), rev, dg)
        # the token itself must carry the partition (token scoping) — horizontal escape guard
        if not _partition_match(principal.partitions, partition):
            return Decision(False, "E_AUTHZ_PARTITION", (), rev, dg)
        if principal.ptype == "breakglass":
            if action not in BREAKGLASS_ACTIONS:
                return Decision(False, "E_AUTHZ_BREAKGLASS_SCOPE", (), rev, dg)
            return Decision(True, "OK_BREAKGLASS", ("breakglass",), rev, dg)
        if action not in principal.scopes:
            return Decision(False, "E_AUTHZ_SCOPE", (), rev, dg)
        matched_allow, matched_deny = [], []
        for r in self.bundle.rules:
            if action in r.actions and principal.ptype in r.ptypes and _partition_match(r.partitions, partition) \
                    and ("*" in r.subjects or principal.subject in r.subjects):
                (matched_allow if r.effect == "allow" else matched_deny).append(r.rule_id)
        if matched_deny:
            return Decision(False, "E_AUTHZ_DENIED", tuple(matched_deny), rev, dg)
        if not matched_allow:
            return Decision(False, "E_AUTHZ_DEFAULT_DENY", (), rev, dg)
        if action in SOD_ACTIONS and not _as_approver:
            if second_approver is None or second_approver.subject == principal.subject:
                return Decision(False, "E_AUTHZ_SOD", tuple(matched_allow), rev, dg)
            second = self.decide(second_approver, action, partition, _as_approver=True)
            if not second.allowed:
                return Decision(False, "E_AUTHZ_SOD_APPROVER", tuple(matched_allow), rev, dg)
        return Decision(True, "OK", tuple(matched_allow), rev, dg)

    def authorize(self, principal: Principal, action: str, partition: str, **kw) -> Decision:
        d = self.decide(principal, action, partition, **kw)
        if not d.allowed:
            raise AuthzError(d.code, action)
        return d


def sign_bundle(provider, key_id: str, bundle, *, signed_at: int, kind: str = "authz-policy") -> dict:
    """Sign a policy bundle's digest (authz or precedence policy) — MC-08-07 / MC-23-06."""
    from .signing import sign_payload
    return sign_payload(provider, key_id, message_type=kind, environment="policy",
                        payload={"revision": bundle.revision, "digest": bundle.digest()}, signed_at=signed_at)


def verify_bundle(trust, signature: dict, bundle, *, kind: str = "authz-policy") -> bool:
    from .signing import verify_payload
    return verify_payload(trust, signature, message_type=kind, environment="policy",
                          payload={"revision": bundle.revision, "digest": bundle.digest()},
                          required_scope="policy:sign").ok


def coverage_report(bundle: PolicyBundle) -> dict:
    """Which actions have any allow rule (privilege-expansion / coverage test input)."""
    allowed = {a for r in bundle.rules if r.effect == "allow" for a in r.actions}
    return {"actions": sorted(ACTIONS), "allowed": sorted(allowed), "never_allowed": sorted(ACTIONS - allowed)}
