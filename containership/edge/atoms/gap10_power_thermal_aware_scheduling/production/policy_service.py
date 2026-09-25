"""Components 05 and 06 - atomic policy distribution/activation service and
policy authorization/signature verification.

A policy revision is immutable and content-addressed
(``rev-<sha256[:16]>``). Activation is a single atomic pointer swap per
scope (``site/environment``), with staged activation (``cohort`` list) and
one-step rollback to the previous revision.

Authorization: every bundle must be signed by an identity holding
``policy.author`` for the scope. A bundle that *relaxes* any safety limit
relative to the active revision (higher thresholds, higher ceilings, lower
reserve, longer freshness window) additionally needs a signature from a
*different* identity holding ``policy.approve-relax`` (two-person rule).
"""
from __future__ import annotations

import hashlib
import threading
from dataclasses import asdict, dataclass, field, fields

from ..model import PolicyError, PowerThermalPolicy
from .errors import ErrorCode, Gap10Error
from .keys import KeyRing, canonical

# direction in which a larger value is *less* restrictive
RELAX_IF_HIGHER = {"elevated_c", "critical_c", "emergency_c", "power_elevated_ratio", "power_critical_ratio",
                   "power_emergency_ratio", "max_sensor_age_seconds", "max_future_skew_seconds",
                   "nominal_ceiling", "elevated_ceiling", "critical_ceiling", "max_valid_temperature_c"}
RELAX_IF_LOWER = {"battery_reserve", "recovery_margin_c", "power_recovery_margin", "battery_recovery_margin",
                  "min_valid_temperature_c"}


def policy_to_dict(p: PowerThermalPolicy) -> dict:
    return {f.name: getattr(p, f.name) for f in fields(p)}


def relaxations(old: PowerThermalPolicy | None, new: PowerThermalPolicy) -> list[str]:
    if old is None:
        base = PowerThermalPolicy()
        old = base
    out = []
    for name in RELAX_IF_HIGHER:
        if getattr(new, name) > getattr(old, name):
            out.append(name)
    for name in RELAX_IF_LOWER:
        if getattr(new, name) < getattr(old, name):
            out.append(name)
    return sorted(out)


@dataclass(frozen=True)
class PolicyRevision:
    revision_id: str
    scope: str
    policy: PowerThermalPolicy
    author: str
    approver: str | None
    created_at: float
    parent: str | None
    provenance: dict

    def to_dict(self) -> dict:
        d = asdict(self)
        d["policy"] = policy_to_dict(self.policy)
        return d


@dataclass
class PolicyService:
    keyring: KeyRing
    audit: object = None
    revisions: dict[str, PolicyRevision] = field(default_factory=dict)
    active: dict[str, str] = field(default_factory=dict)          # scope -> revision
    previous: dict[str, list[str]] = field(default_factory=dict)  # scope -> history stack
    staged: dict[str, tuple[str, frozenset]] = field(default_factory=dict)  # scope -> (rev, cohort nodes)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _audit(self, kind, actor, at, **d):
        if self.audit is not None:
            self.audit.append(kind, actor, at, **d)

    def submit(self, bundle: dict, *, now: float) -> PolicyRevision:
        """bundle = {scope, policy:{...}, parent, author_key, author_sig, approver_key?, approver_sig?}"""
        scope = bundle.get("scope")
        if not isinstance(scope, str) or "/" not in scope:
            raise Gap10Error(ErrorCode.POLICY_INVALID, "scope must be 'site/environment'")
        body = {"scope": scope, "policy": bundle.get("policy"), "parent": bundle.get("parent")}
        try:
            author = self.keyring.verify(bundle.get("author_key", ""), "policy.author", scope, body,
                                         bundle.get("author_sig", ""), now=now)
        except Gap10Error as e:
            self._audit("policy.rejected", str(bundle.get("author_key")), now, scope=scope, code=e.code.value)
            self._audit("security.failure", str(bundle.get("author_key")), now, what="policy signature", code=e.code.value)
            code = ErrorCode.POLICY_UNSIGNED if e.code in (ErrorCode.KEY_UNKNOWN, ErrorCode.TELEMETRY_BAD_SIGNATURE) else ErrorCode.POLICY_UNAUTHORIZED
            raise Gap10Error(code, e.message) from e
        try:
            policy = PowerThermalPolicy(**body["policy"])
        except (TypeError, PolicyError) as e:
            self._audit("policy.rejected", author, now, scope=scope, code=ErrorCode.POLICY_INVALID.value)
            raise Gap10Error(ErrorCode.POLICY_INVALID, str(e)) from e
        with self._lock:
            current = self.active.get(scope)
            if body["parent"] != current:
                raise Gap10Error(ErrorCode.POLICY_REVISION_CONFLICT, f"parent {body['parent']} != active {current}")
            relaxed = relaxations(self.revisions[current].policy if current else None, policy)
            approver = None
            if relaxed:
                try:
                    approver = self.keyring.verify(bundle.get("approver_key", ""), "policy.approve-relax", scope, body,
                                                   bundle.get("approver_sig", ""), now=now)
                except Gap10Error as e:
                    self._audit("policy.rejected", author, now, scope=scope, relaxed=",".join(relaxed), code=ErrorCode.POLICY_UNAUTHORIZED.value)
                    raise Gap10Error(ErrorCode.POLICY_UNAUTHORIZED, f"relaxes {relaxed}; second-party approval required") from e
                if approver == author:
                    raise Gap10Error(ErrorCode.POLICY_UNAUTHORIZED, "approver must differ from author")
            rev_id = "rev-" + hashlib.sha256(canonical(body)).hexdigest()[:16]
            rev = PolicyRevision(rev_id, scope, policy, author, approver, now, current,
                                 {"author_key": bundle.get("author_key"), "relaxed": relaxed,
                                  "content_sha256": hashlib.sha256(canonical(body)).hexdigest()})
            self.revisions.setdefault(rev_id, rev)
            self._audit("policy.proposed", author, now, scope=scope, revision=rev_id, relaxed=",".join(relaxed))
            return self.revisions[rev_id]

    def stage(self, scope: str, revision_id: str, cohort: set[str], *, actor: str, now: float) -> None:
        if revision_id not in self.revisions or self.revisions[revision_id].scope != scope:
            raise Gap10Error(ErrorCode.POLICY_UNKNOWN_REVISION, revision_id)
        with self._lock:
            self.staged[scope] = (revision_id, frozenset(cohort))
        self._audit("policy.activated", actor, now, scope=scope, revision=revision_id, stage="canary", cohort=len(cohort))

    def activate(self, scope: str, revision_id: str, *, actor: str, now: float) -> None:
        if revision_id not in self.revisions or self.revisions[revision_id].scope != scope:
            raise Gap10Error(ErrorCode.POLICY_UNKNOWN_REVISION, revision_id)
        with self._lock:
            cur = self.active.get(scope)
            rev = self.revisions[revision_id]
            if cur != revision_id and rev.parent != cur:
                # compare-and-swap: a revision may only replace the revision it was authored against
                raise Gap10Error(ErrorCode.POLICY_REVISION_CONFLICT, f"{revision_id} parent {rev.parent} != active {cur}")
            if cur is not None and cur != revision_id:
                self.previous.setdefault(scope, []).append(cur)
            self.active[scope] = revision_id
            self.staged.pop(scope, None)
        self._audit("policy.activated", actor, now, scope=scope, revision=revision_id, stage="full")

    def rollback(self, scope: str, *, actor: str, now: float) -> str:
        with self._lock:
            self.staged.pop(scope, None)
            hist = self.previous.get(scope) or []
            if not hist:
                raise Gap10Error(ErrorCode.POLICY_UNKNOWN_REVISION, f"no previous revision for {scope}")
            rev = hist.pop()
            self.active[scope] = rev
        self._audit("policy.rolled_back", actor, now, scope=scope, revision=rev)
        return rev

    def effective(self, scope: str, node: str) -> PolicyRevision | None:
        """Revision for a node: staged canary revision if node is in the cohort."""
        with self._lock:
            st = self.staged.get(scope)
            if st and node in st[1]:
                return self.revisions[st[0]]
            rid = self.active.get(scope)
            return self.revisions[rid] if rid else None


def sign_bundle(keyring: KeyRing, scope: str, policy: dict, parent: str | None, author_key: str,
                approver_key: str | None = None) -> dict:
    body = {"scope": scope, "policy": policy, "parent": parent}
    b = dict(body, author_key=author_key, author_sig=keyring.sign(author_key, "policy.author", scope, body))
    if approver_key:
        b["approver_key"] = approver_key
        b["approver_sig"] = keyring.sign(approver_key, "policy.approve-relax", scope, body)
    return b
