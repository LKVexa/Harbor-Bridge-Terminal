"""MC-005 -- authorization policy enforcement point (deny by default).

Rules are declarative data: ``{"id", "tenant", "workload" (glob), "world",
"capabilities", "preopens": {logical: {"host_root", "rights"}}}``.  A request
is allowed only if a rule for *that tenant* matches the workload and covers
every requested capability and preopen; host roots must lie under the tenant's
registered roots so preopens never span tenants.  Every decision returns a
machine-readable reason list and the policy digest it was made under.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .errors import ErrorCode, Inv13Error


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reasons: tuple[str, ...]
    rule_id: str | None
    policy_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {"allowed": self.allowed, "reasons": list(self.reasons),
                "rule_id": self.rule_id, "policy_digest": self.policy_digest}


def _within(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip("/") + "/")


class PolicyEngine:
    def __init__(self, document: dict[str, Any]) -> None:
        self._validate(document)
        self.document = json.loads(json.dumps(document))  # deep, detached copy
        self.digest = hashlib.sha256(json.dumps(self.document, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def _validate(doc: Any) -> None:
        if not isinstance(doc, dict) or doc.get("schema") != "INV13_POLICY/1":
            raise Inv13Error(ErrorCode.INVALID_ARGUMENT, "schema")
        tenants = doc.get("tenants")
        if not isinstance(tenants, dict):
            raise Inv13Error(ErrorCode.INVALID_ARGUMENT, "tenants")
        ids = set()
        for t, spec in tenants.items():
            roots = spec.get("host_roots", [])
            for r in roots:
                if not isinstance(r, str) or not r.startswith("/"):
                    raise Inv13Error(ErrorCode.INVALID_ARGUMENT, "host_roots")
            for rule in spec.get("rules", []):
                if rule.get("id") in ids or not rule.get("id"):
                    raise Inv13Error(ErrorCode.INVALID_ARGUMENT, "rule id")
                ids.add(rule["id"])
                for lp, p in rule.get("preopens", {}).items():
                    if not any(_within(p.get("host_root", ""), r) for r in roots):
                        raise Inv13Error(ErrorCode.INVALID_ARGUMENT, f"rule {rule['id']} preopen outside tenant roots")
        # cross-tenant overlap of host roots is forbidden
        all_roots = [(t, r) for t, s in tenants.items() for r in s.get("host_roots", [])]
        for i, (t1, r1) in enumerate(all_roots):
            for t2, r2 in all_roots[i + 1:]:
                if t1 != t2 and (_within(r1, r2) or _within(r2, r1)):
                    raise Inv13Error(ErrorCode.INVALID_ARGUMENT, f"tenant roots overlap: {t1}/{t2}")

    def decide(self, *, tenant: str, workload: str, world: str, capabilities: set[str],
               preopens: dict[str, str] | None = None, rights: dict[str, set[str]] | None = None) -> Decision:
        preopens = preopens or {}
        rights = rights or {}
        spec = self.document["tenants"].get(tenant)
        if spec is None:
            return Decision(False, ("unknown-tenant",), None, self.digest)
        reasons: list[str] = []
        for rule in spec.get("rules", []):
            if not fnmatch.fnmatchcase(workload, rule.get("workload", "")) or rule.get("world") != world:
                continue
            missing = sorted(set(capabilities) - set(rule.get("capabilities", [])))
            bad = []
            for lp, hr in preopens.items():
                allowed = rule.get("preopens", {}).get(lp)
                if allowed is None or not _within(hr, allowed["host_root"]):
                    bad.append(f"preopen-not-allowed:{lp}")
                elif not set(rights.get(lp, {"read"})) <= set(allowed.get("rights", [])):
                    bad.append(f"rights-exceed:{lp}")
            if not missing and not bad:
                return Decision(True, ("rule-match",), rule["id"], self.digest)
            reasons += [f"capability-not-allowed:{c}" for c in missing] + bad
        return Decision(False, tuple(reasons) or ("no-matching-rule",), None, self.digest)

    def enforce(self, **kw: Any) -> Decision:
        d = self.decide(**kw)
        if not d.allowed:
            raise Inv13Error(ErrorCode.POLICY_DENIED, d.to_dict())
        return d
