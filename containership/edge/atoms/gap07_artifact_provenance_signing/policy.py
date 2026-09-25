"""GAP-13 policy-engine adapter (v6): signed bundles, deterministic evaluation.

``PK_POLICY_BUNDLE/1`` (signed ``policy-bundle`` config) holds prioritised
rules matched on (tenant, environment, kind).  Evaluation is deterministic:

1. collect rules whose ``match`` fields equal the query (``"*"`` = any);
2. none -> ``POLICY_NO_MATCH`` (deny);
3. highest priority wins; >1 rule at that priority with different effects or
   requirements -> ``POLICY_CONFLICT`` (deny);
4. ``deny`` effect -> ``POLICY_DENY``;
5. every requirement of the ``allow`` rule is checked against *verified*
   facts; any unmet requirement denies with its own code unless a signed,
   scoped, unexpired, two-approver waiver covers exactly that control.

Unknown fields, versions or enum values in a bundle are rejected at
activation, so nothing is silently ignored.  The decision records the bundle
digest/version and a trace of the rule and each requirement outcome.
"""
from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from . import algorithms as algs
from .canonical import canonical_bytes, exact_fields
from .errors import GapError, fail
from .store import AuthorityKey, verify_config

BUNDLE_SCHEMA = "PK_POLICY_BUNDLE/1"
DECISION_SCHEMA = "PK_POLICY_DECISION/1"
ADAPTER_VERSION = 1
MAX_RULES = 512
WAIVABLE = frozenset({"sbom", "transparency", "attestation_freshness", "signature_age", "vulnerability"})
_REQ_KEYS = {"roles", "identities", "algorithms", "kids", "threshold", "max_signature_age_s", "attestations",
             "transparency", "max_checkpoint_age_s", "sbom", "min_strength"}


def _validate_rule(r: Mapping[str, Any]) -> dict[str, Any]:
    r = exact_fields(r, {"rule_id", "priority", "match", "effect", "require"}, what="policy rule")
    m = exact_fields(r["match"], {"tenant", "environment", "kind"}, what="rule match")
    if r["effect"] not in ("allow", "deny"):
        raise fail("POLICY_INVALID", "rule effect must be allow|deny", rule_id=str(r["rule_id"])[:64])
    if isinstance(r["priority"], bool) or not isinstance(r["priority"], int) or not 0 <= r["priority"] <= 10_000:
        raise fail("POLICY_INVALID", "rule priority invalid")
    req = dict(r["require"])
    unknown = set(req) - _REQ_KEYS
    if unknown:
        raise fail("POLICY_INVALID", "unknown requirement fields (adapter version skew?)", fields=sorted(unknown))
    if r["effect"] == "allow":
        if int(req.get("threshold", 1)) < 1:
            raise fail("POLICY_INVALID", "allow rules require threshold >= 1")
        for a in req.get("algorithms", []):
            algs.get(a)
        for att in req.get("attestations", []):
            exact_fields(att, {"predicate_type"}, {"builder_ids", "build_types", "external_parameter_keys", "max_age_s", "threshold"}, what="attestation requirement")
        if "sbom" in req:
            exact_fields(req["sbom"], {"required"}, {"deny_packages", "max_severity", "formats"}, what="sbom requirement")
    return {**r, "match": dict(m), "require": req}


@dataclass(frozen=True)
class PolicyBundle:
    bundle_id: str
    version: int
    issued_at: int
    expires: int
    tenant: str
    rules: tuple[Mapping[str, Any], ...]
    digest: str

    @classmethod
    def from_signed(cls, doc: Mapping[str, Any], authorities: Mapping[str, AuthorityKey], *, now: int) -> "PolicyBundle":
        body = verify_config(doc, authorities, expect_type="policy-bundle")
        b = exact_fields(body, {"schema", "adapter_version", "bundle_id", "version", "issued_at", "expires", "tenant", "rules"}, what="policy bundle")
        if b["schema"] != BUNDLE_SCHEMA or b["adapter_version"] != ADAPTER_VERSION:
            raise fail("POLICY_INVALID", "policy bundle schema/adapter version incompatible", adapter_version=b.get("adapter_version"))
        if not isinstance(b["rules"], list) or not 0 < len(b["rules"]) <= MAX_RULES:
            raise fail("POLICY_INVALID", "policy bundle rule count invalid")
        if now > b["expires"]:
            raise fail("POLICY_INVALID", "policy bundle expired", expires=b["expires"])
        rules = tuple(_validate_rule(r) for r in b["rules"])
        ids = [r["rule_id"] for r in rules]
        if len(set(ids)) != len(ids):
            raise fail("POLICY_INVALID", "duplicate rule ids")
        return cls(b["bundle_id"], b["version"], b["issued_at"], b["expires"], b["tenant"], rules,
                   hashlib.sha256(canonical_bytes(body)).hexdigest())


class PolicyStore:
    """Holds the active bundle; monotonic versions; fail-closed when absent/expired."""

    def __init__(self, authorities: Mapping[str, AuthorityKey], *, audit: Any = None):
        self._auth = dict(authorities)
        self._lock = threading.Lock()
        self._active: PolicyBundle | None = None
        self._audit = audit

    def activate(self, doc: Mapping[str, Any], *, now: int, actor: str) -> PolicyBundle:
        b = PolicyBundle.from_signed(doc, self._auth, now=now)
        with self._lock:
            if self._active is not None and b.version <= self._active.version:
                raise fail("POLICY_INVALID", "policy version must increase", active=self._active.version, offered=b.version)
            self._active = b
        if self._audit is not None:
            self._audit.append("policy.activate", {"bundle_id": b.bundle_id, "version": b.version, "digest": b.digest, "actor": actor})
        return b

    def current(self, now: int) -> PolicyBundle:
        b = self._active
        if b is None:
            raise fail("POLICY_UNAVAILABLE", "no active policy bundle")
        if now > b.expires:
            raise fail("POLICY_UNAVAILABLE", "active policy bundle expired", expires=b.expires)
        return b


def verify_waiver(doc: Mapping[str, Any], authorities: Mapping[str, AuthorityKey], *, now: int, digest: str, tenant: str, environment: str) -> dict[str, Any]:
    body = verify_config(doc, authorities, expect_type="waiver")
    w = exact_fields(body, {"schema", "waiver_id", "owner", "justification", "controls", "digest", "tenant", "environment",
                            "issued_at", "expires", "approvers", "compensating_controls"}, what="waiver")
    if w["schema"] != "PK_WAIVER/1":
        raise fail("EXCEPTION_INVALID", "unsupported waiver schema")
    if not set(w["controls"]) <= WAIVABLE or not w["controls"]:
        raise fail("EXCEPTION_INVALID", "waiver names non-waivable controls", controls=sorted(set(w["controls"]) - WAIVABLE))
    if w["digest"] != digest or w["tenant"] != tenant or w["environment"] != environment:
        raise fail("EXCEPTION_INVALID", "waiver scope does not cover this artifact/namespace")
    if not w["issued_at"] <= now <= w["expires"] or w["expires"] - w["issued_at"] > 30 * 86400:
        raise fail("EXCEPTION_INVALID", "waiver not currently valid or exceeds 30-day maximum")
    if len(set(w["approvers"])) < 2 or w["owner"] in w["approvers"]:
        raise fail("EXCEPTION_INVALID", "waiver needs two approvers distinct from its owner")
    return dict(w)


_SEV = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def evaluate(bundle: PolicyBundle, facts: Mapping[str, Any], *, waivers: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """Pure function: (bundle, verified facts, verified waivers) -> decision."""
    q = facts
    trace: list[dict[str, Any]] = []
    matches = [r for r in bundle.rules if all(r["match"][k] in ("*", q[k]) for k in ("tenant", "environment", "kind"))]

    def decide(allow: bool, code: str, rule_id: str | None, **extra: Any) -> dict[str, Any]:
        return {"schema": DECISION_SCHEMA, "allow": allow, "reason_code": code, "rule_id": rule_id, "bundle_id": bundle.bundle_id,
                "bundle_version": bundle.version, "bundle_digest": bundle.digest, "trace": trace, "adapter_version": ADAPTER_VERSION, **extra}

    if not matches:
        return decide(False, "POLICY_NO_MATCH", None)
    top = max(r["priority"] for r in matches)
    winners = [r for r in matches if r["priority"] == top]
    if len({canonical_bytes({"e": r["effect"], "q": r["require"]}) for r in winners}) > 1:
        return decide(False, "POLICY_CONFLICT", None, conflicting=sorted(r["rule_id"] for r in winners))
    rule = winners[0]
    if rule["effect"] == "deny":
        return decide(False, "POLICY_DENY", rule["rule_id"])
    req = rule["require"]
    waived: set[str] = set()
    for w in waivers:
        waived |= set(w["controls"])
    applied: list[str] = []

    def check(control: str, ok: bool, code: str, waivable: bool = False) -> str | None:
        trace.append({"control": control, "ok": ok})
        if ok:
            return None
        if waivable and control in waived:
            applied.append(control)
            trace[-1]["waived"] = True
            return None
        return code

    sigs = [s for s in q.get("signatures", []) if s.get("verified")]
    def sig_ok(s: Mapping[str, Any]) -> bool:
        return ((not req.get("roles") or set(s["roles"]) & set(req["roles"]))
                and (not req.get("identities") or s["signer"] in req["identities"])
                and (not req.get("algorithms") or s["alg"] in req["algorithms"])
                and (not req.get("kids") or s["kid"] in req["kids"])
                and algs.REGISTRY[s["alg"]].strength >= int(req.get("min_strength", 128))
                and s.get("profile") == algs.PROFILE_PRODUCTION)
    good = [s for s in sigs if sig_ok(s)]
    distinct = {s["signer"] for s in good}
    need = int(req.get("threshold", 1))
    code = check("signature", bool(good), "SIGNER_UNTRUSTED" if sigs else "UNSIGNED")
    if code:
        return decide(False, code, rule["rule_id"])
    code = check("threshold", len(distinct) >= need, "THRESHOLD_UNMET")
    if code:
        return decide(False, code, rule["rule_id"], have=len(distinct), need=need)
    if "max_signature_age_s" in req:
        newest = max(s["issued_at"] for s in good)
        code = check("signature_age", q["now"] - newest <= req["max_signature_age_s"], "SIGNATURE_EXPIRED", True)
        if code:
            return decide(False, code, rule["rule_id"])
    for att_req in req.get("attestations", []):
        atts = [a for a in q.get("attestations", []) if a["predicate_type"] == att_req["predicate_type"]]
        ok = bool(atts) and all(
            (not att_req.get("builder_ids") or a.get("builder_id") in att_req["builder_ids"])
            and (not att_req.get("build_types") or a.get("build_type") in att_req["build_types"]) for a in atts)
        code = check(f"attestation:{att_req['predicate_type']}", ok, "ATTESTATION_BUILDER" if atts else "ATTESTATION_PREDICATE")
        if code:
            return decide(False, code, rule["rule_id"])
    if req.get("transparency"):
        code = check("transparency", bool(q.get("transparency")), "TLOG_REQUIRED", True)
        if code:
            return decide(False, code, rule["rule_id"])
    sreq = req.get("sbom")
    if sreq and sreq.get("required"):
        sb = q.get("sbom")
        code = check("sbom", sb is not None, "SBOM_INVALID", True)
        if code:
            return decide(False, code, rule["rule_id"])
        if sb is not None:
            from .sbom import normalize_purl
            bad = sorted(set(sb.get("packages", [])) & {normalize_purl(p) for p in sreq.get("deny_packages", [])})
            code = check("sbom_packages", not bad, "SBOM_POLICY")
            if code:
                return decide(False, code, rule["rule_id"], denied_packages=bad[:16])
            maxsev = _SEV[sreq.get("max_severity", "critical")]
            sevs = sb.get("open_vulnerability_severities")
            worst = 4 if sevs is None else max((_SEV.get(v, 4) for v in sevs), default=0)  # unknown state counts as critical
            code = check("vulnerability", worst <= maxsev, "SBOM_POLICY", True)
            if code:
                return decide(False, code, rule["rule_id"])
    return decide(True, "ALLOW", rule["rule_id"], waivers_applied=sorted(set(applied)),
                  waiver_ids=sorted(w["waiver_id"] for w in waivers if set(w["controls"]) & set(applied)))
