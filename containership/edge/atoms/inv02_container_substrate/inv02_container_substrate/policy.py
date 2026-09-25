"""MC32 / MC29 / MC49 / MC77 — admission policy engine, tenant isolation, decision
explanation and the exception/waiver registry.

The engine evaluates an ordered list of pure rule functions against an admission
``Request``.  Every rule contributes an explained outcome; the decision is DENY if any
rule denies (fail closed), and a rule that raises is treated as DENY with its error.
Decisions carry the policy bundle version and digest so they are reproducible.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Callable

from .registry import ValidationError
from .trust import ScanState


@dataclass(frozen=True)
class Request:
    tenant: str
    workload_class: str
    environment: str
    reference: str
    digest: str | None
    signed_by: tuple[str, ...] = ()
    provenance_builder: str | None = None
    scan_state: ScanState = ScanState.UNSCANNED
    open_vulns: tuple[str, ...] = ()
    runtime: dict = field(default_factory=dict)  # privileged, capabilities, host_network, devices...
    quarantined: bool = False


@dataclass(frozen=True)
class Outcome:
    rule: str
    allow: bool
    reason: str
    waiver: str | None = None


@dataclass(frozen=True)
class Decision:
    allow: bool
    outcomes: tuple[Outcome, ...]
    policy_version: str
    policy_digest: str

    def explain(self) -> dict:
        """MC49 — machine-readable explanation of a decision."""
        return {"allow": self.allow, "policy_version": self.policy_version, "policy_digest": self.policy_digest,
                "denied_by": [o.rule for o in self.outcomes if not o.allow],
                "outcomes": [o.__dict__ for o in self.outcomes]}


# --- MC77 waiver registry -------------------------------------------------------------
@dataclass(frozen=True)
class Waiver:
    waiver_id: str
    rule: str
    scope_tenant: str
    scope_digest: str | None
    owner: str
    approver: str
    justification: str
    compensating_control: str
    expires_at: float
    closure_issue: str

    def __post_init__(self):
        for f in ("waiver_id", "rule", "owner", "approver", "justification", "compensating_control", "closure_issue"):
            if not str(getattr(self, f)).strip():
                raise ValidationError(f"waiver.{f} is required")
        if self.owner == self.approver:
            raise ValidationError("waiver approver must differ from owner")


class WaiverRegistry:
    def __init__(self, waivers: list[Waiver] | None = None) -> None:
        self._w: dict[str, Waiver] = {}
        for w in waivers or []:
            self.add(w)

    def add(self, w: Waiver) -> None:
        if w.waiver_id in self._w:
            raise ValidationError("duplicate waiver id")
        self._w[w.waiver_id] = w

    def find(self, rule: str, req: Request, now: float) -> Waiver | None:
        for w in self._w.values():
            if w.rule == rule and w.scope_tenant == req.tenant and now < w.expires_at \
                    and (w.scope_digest is None or w.scope_digest == req.digest):
                return w
        return None

    def expired(self, now: float) -> list[str]:
        return sorted(w.waiver_id for w in self._w.values() if now >= w.expires_at)

    @classmethod
    def load(cls, path: str) -> "WaiverRegistry":
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return cls([Waiver(**w) for w in data.get("waivers", [])])


Rule = Callable[[Request, dict], tuple[bool, str]]


class PolicyEngine:
    def __init__(self, bundle: dict, rules: dict[str, Rule] | None = None,
                 waivers: WaiverRegistry | None = None) -> None:
        if not isinstance(bundle.get("version"), str):
            raise ValidationError("policy bundle requires a version")
        self.bundle = bundle
        self.digest = "sha256:" + hashlib.sha256(json.dumps(bundle, sort_keys=True).encode()).hexdigest()
        self.rules = rules if rules is not None else dict(DEFAULT_RULES)
        self.waivers = waivers or WaiverRegistry()

    def evaluate(self, req: Request, now: float) -> Decision:
        outcomes = []
        for name, fn in self.rules.items():
            try:
                ok, why = fn(req, self.bundle)
            except Exception as exc:  # fail closed
                ok, why = False, f"rule error: {type(exc).__name__}: {exc}"
            waiver = None
            if not ok and name not in self.bundle.get("unwaivable", []):
                w = self.waivers.find(name, req, now)
                if w:
                    ok, waiver = True, w.waiver_id
            outcomes.append(Outcome(name, ok, why, waiver))
        return Decision(all(o.allow for o in outcomes), tuple(outcomes), self.bundle["version"], self.digest)


# --- default rules -----------------------------------------------------------------
def _env_protected(req, b):
    return req.environment.strip().lower() in set(b.get("protected_environments", ["prod", "production"]))


def rule_digest_pinned(req, b):
    if _env_protected(req, b) and not req.digest:
        return False, "protected environment requires a digest reference"
    return True, "reference pinned or environment unprotected"


def rule_not_quarantined(req, b):
    return (not req.quarantined), ("content quarantined" if req.quarantined else "not quarantined")


def rule_signed(req, b):
    need = b.get("require_signature", {}).get(req.environment, b.get("require_signature", {}).get("*", False))
    if not need:
        return True, "signature not required"
    trusted = set(b.get("trusted_signers", []))
    ok = bool(trusted & set(req.signed_by))
    return ok, "signed by trusted key" if ok else "no trusted signature"


def rule_provenance(req, b):
    allowed = b.get("allowed_builders")
    if not allowed or not _env_protected(req, b):
        return True, "provenance not required"
    return (req.provenance_builder in allowed), f"builder={req.provenance_builder!r}"


def rule_vulnerabilities(req, b):
    acceptable = {ScanState.CLEAN, ScanState.EXCEPTION_APPROVED}
    if not _env_protected(req, b):
        acceptable |= {ScanState.VULNERABLE, ScanState.SCAN_STALE}
    ok = req.scan_state in acceptable
    return ok, f"scan_state={req.scan_state.value}" + (f" open={list(req.open_vulns)}" if req.open_vulns else "")


def rule_tenant_isolation(req, b):
    """MC29 — a workload class must be permitted for the tenant, and privileged runtime
    features require an explicit per-class grant."""
    classes = b.get("tenants", {}).get(req.tenant, {}).get("workload_classes")
    if classes is None:
        return False, f"unknown tenant {req.tenant!r}"
    if req.workload_class not in classes:
        return False, f"workload class {req.workload_class!r} not permitted for tenant"
    grants = set(b.get("workload_classes", {}).get(req.workload_class, {}).get("grants", []))
    asked = {k for k in ("privileged", "host_network", "host_pid", "host_ipc") if req.runtime.get(k)}
    asked |= {f"cap:{c}" for c in req.runtime.get("capabilities", [])}
    asked |= {f"device:{d}" for d in req.runtime.get("devices", [])}
    missing = sorted(asked - grants)
    return (not missing), ("runtime grants ok" if not missing else f"ungranted: {missing}")


DEFAULT_RULES: dict[str, Rule] = {
    "digest-pinned": rule_digest_pinned,
    "not-quarantined": rule_not_quarantined,
    "signed": rule_signed,
    "provenance": rule_provenance,
    "vulnerabilities": rule_vulnerabilities,
    "tenant-isolation": rule_tenant_isolation,
}
