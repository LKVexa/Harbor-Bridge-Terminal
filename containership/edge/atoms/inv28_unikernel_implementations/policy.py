"""Versioned, injected selection policy and security waivers (MC-022, MC-038, MC-094).

Production behaviour is not a code constant: it is a ``PK_TOOLCHAIN_POLICY/1`` document with an id,
a monotonically increasing revision and a content digest that every decision records.

MC-094 decision (docs/ADR-0001-production-maturity.md, status PROPOSED pending owner approval):
the shipped default policy admits only ``mature`` toolchains in ``production``; a ``beta``
toolchain is selectable there only through an approved, unexpired, scoped waiver for
``TC_MATURITY_BELOW_POLICY``.  ``experimental`` is never waivable in production.  This is the
stricter of the two readings the v4.2.0 contract allowed, so adopting it cannot let anything
through that was refused before.

Environments must be declared; an environment the policy does not name is refused
(``SEL_POLICY_INVALID``) rather than defaulting to a permissive rule.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from pathlib import Path

from .errors import Reason, ValidationError
from .model import CATALOG_STATUS, MATURITY, fmt_utc, parse_utc, sha256_hex, text, token, token_set

SCHEMA = "PK_TOOLCHAIN_POLICY/1"
SEVERITIES = ("none", "low", "medium", "high", "critical")

#: Codes a waiver may cover.  Everything else (capability mismatch, missing certification or
#: integrity, disabled/EOL) is structurally unwaivable: a waiver cannot make a toolchain able to
#: run a workload it cannot run, nor make an unverified artifact verified.
WAIVABLE = frozenset({Reason.MATURITY_BELOW_POLICY.value, Reason.REVIEW_STALE.value, Reason.ADVISORY_OPEN.value,
                      Reason.SECURITY_RESPONSE_INADEQUATE.value})
SERVICE_WORDS = ("bot", "service", "automation", "pipeline", "claude", "ci")


@dataclass(frozen=True)
class EnvironmentRule:
    min_maturity: str = "mature"
    require_security_contact: bool = True
    min_response_sla_hours: int = 0          # 0 = any declared SLA (or none) accepted
    require_review: bool = True
    accept_conditional_review: bool = False
    allow_deprecated: bool = False
    require_certification: bool = True
    require_integrity: bool = True
    advisory_block_severity: str = "high"    # open advisory at/above this severity eliminates
    allowed_catalog_status: frozenset = frozenset({"supported"})
    require_advisory_feed: bool = True       # a missing/stale advisory feed refuses (no news != good news)
    production: bool = True

    def __post_init__(self):
        if self.min_maturity not in MATURITY:
            raise ValidationError(f"min_maturity must be one of {MATURITY}", code=Reason.POLICY_INVALID)
        for f in ("require_security_contact", "require_review", "accept_conditional_review", "allow_deprecated",
                  "require_certification", "require_integrity", "require_advisory_feed", "production"):
            if type(getattr(self, f)) is not bool:
                raise ValidationError(f"{f} must be bool", code=Reason.POLICY_INVALID)
        if type(self.min_response_sla_hours) is not int or self.min_response_sla_hours < 0:
            raise ValidationError("min_response_sla_hours must be a non-negative int", code=Reason.POLICY_INVALID)
        if self.advisory_block_severity not in SEVERITIES:
            raise ValidationError(f"advisory_block_severity must be one of {SEVERITIES}", code=Reason.POLICY_INVALID)
        acs = frozenset(self.allowed_catalog_status)
        if not acs or not acs <= set(CATALOG_STATUS):
            raise ValidationError("allowed_catalog_status invalid", code=Reason.POLICY_INVALID)
        object.__setattr__(self, "allowed_catalog_status", acs)
        # Fail-closed floor: a rule marked production may not switch off the core production gates.
        if self.production and (self.min_maturity == "experimental" or not self.require_security_contact
                                or not self.require_review or not self.require_certification
                                or not self.require_integrity or not self.require_advisory_feed):
            raise ValidationError("a production rule may not admit experimental toolchains or disable the "
                                  "security-contact, review, certification, integrity or advisory-feed gates",
                                  code=Reason.POLICY_INVALID)

    def to_dict(self) -> dict:
        return {"min_maturity": self.min_maturity, "require_security_contact": self.require_security_contact,
                "min_response_sla_hours": self.min_response_sla_hours, "require_review": self.require_review,
                "accept_conditional_review": self.accept_conditional_review,
                "allow_deprecated": self.allow_deprecated, "require_certification": self.require_certification,
                "require_integrity": self.require_integrity, "advisory_block_severity": self.advisory_block_severity,
                "allowed_catalog_status": sorted(self.allowed_catalog_status),
                "require_advisory_feed": self.require_advisory_feed, "production": self.production}


@dataclass(frozen=True)
class Waiver:
    """MC-038: a scoped, owned, approved, expiring exception."""

    id: str
    toolchain_ref: str               # exact name@version
    codes: frozenset
    environments: frozenset
    owner: str
    approver: str
    reason: str
    expires: str                     # RFC 3339 UTC
    status: str = "approved"         # proposed | approved | revoked

    def __post_init__(self):
        object.__setattr__(self, "id", text(self.id, "waiver.id"))
        object.__setattr__(self, "toolchain_ref", text(self.toolchain_ref, "waiver.toolchain_ref"))
        if "@" not in self.toolchain_ref:
            raise ValidationError("waiver.toolchain_ref must be an exact name@version", code=Reason.POLICY_INVALID)
        codes = frozenset(self.codes)
        if not codes or not codes <= WAIVABLE:
            raise ValidationError(f"waiver {self.id}: only {sorted(WAIVABLE)} are waivable", code=Reason.POLICY_INVALID)
        object.__setattr__(self, "codes", codes)
        object.__setattr__(self, "environments", token_set(self.environments, "waiver.environments"))
        object.__setattr__(self, "owner", text(self.owner, "waiver.owner"))
        object.__setattr__(self, "approver", self.approver.strip() if isinstance(self.approver, str) else "")
        object.__setattr__(self, "reason", text(self.reason, "waiver.reason"))
        object.__setattr__(self, "expires", fmt_utc(parse_utc(self.expires, "waiver.expires")))
        if self.status not in ("proposed", "approved", "revoked"):
            raise ValidationError("waiver.status invalid", code=Reason.POLICY_INVALID)

    def approver_ok(self) -> bool:
        a = self.approver.lower()
        return bool(a) and a != self.owner.lower() and not any(w in a.replace("-", " ").split() for w in SERVICE_WORDS)

    def active(self, now: dt.datetime) -> bool:
        return self.status == "approved" and self.approver_ok() and now <= parse_utc(self.expires, "expires")

    def covers(self, ref: str, environment: str, code: str, now: dt.datetime) -> bool:
        return self.active(now) and ref == self.toolchain_ref and environment in self.environments and code in self.codes

    def to_dict(self) -> dict:
        return {"id": self.id, "toolchain_ref": self.toolchain_ref, "codes": sorted(self.codes),
                "environments": sorted(self.environments), "owner": self.owner, "approver": self.approver,
                "reason": self.reason, "expires": self.expires, "status": self.status}


@dataclass(frozen=True)
class SitePolicy:
    deny_toolchains: frozenset = frozenset()     # names (casefolded)
    allow_toolchains: frozenset = frozenset()    # empty = no allow-list

    def to_dict(self):
        return {"deny_toolchains": sorted(self.deny_toolchains), "allow_toolchains": sorted(self.allow_toolchains)}


@dataclass(frozen=True)
class SelectionPolicy:
    policy_id: str
    revision: int
    environments: dict                 # env -> EnvironmentRule
    sites: dict = field(default_factory=dict)       # site_id -> SitePolicy
    waivers: tuple = ()

    def __post_init__(self):
        object.__setattr__(self, "policy_id", text(self.policy_id, "policy_id"))
        if type(self.revision) is not int or self.revision < 1:
            raise ValidationError("policy revision must be a positive int", code=Reason.POLICY_INVALID)
        if not self.environments:
            raise ValidationError("policy declares no environments", code=Reason.POLICY_INVALID)
        envs = {}
        for k, v in self.environments.items():
            if not isinstance(v, EnvironmentRule):
                raise ValidationError("environment rules must be EnvironmentRule", code=Reason.POLICY_INVALID)
            envs[token(k, "environment")] = v
        object.__setattr__(self, "environments", envs)
        ids = [w.id for w in self.waivers]
        if len(set(ids)) != len(ids):
            raise ValidationError("duplicate waiver ids", code=Reason.POLICY_INVALID)

    def rule(self, environment: str) -> EnvironmentRule:
        try:
            return self.environments[environment]
        except KeyError:
            raise ValidationError(f"environment {environment!r} is not declared by policy "
                                  f"{self.policy_id} r{self.revision}", code=Reason.POLICY_INVALID) from None

    def waiver_for(self, ref: str, environment: str, code: str, now: dt.datetime):
        for w in sorted(self.waivers, key=lambda w: w.id):
            if w.covers(ref, environment, code, now):
                return w
        return None

    def to_dict(self) -> dict:
        return {"schema": SCHEMA, "policy_id": self.policy_id, "revision": self.revision,
                "environments": {k: v.to_dict() for k, v in sorted(self.environments.items())},
                "sites": {k: v.to_dict() for k, v in sorted(self.sites.items())},
                "waivers": [w.to_dict() for w in sorted(self.waivers, key=lambda w: w.id)]}

    @property
    def digest(self) -> str:
        return sha256_hex(self.to_dict())

    @classmethod
    def from_dict(cls, d: dict) -> SelectionPolicy:
        if not isinstance(d, dict) or d.get("schema") != SCHEMA:
            raise ValidationError(f"policy schema must be {SCHEMA}", code=Reason.POLICY_INVALID)
        try:
            envs = {k: EnvironmentRule(**{**v, "allowed_catalog_status": frozenset(v.get("allowed_catalog_status", ["supported"]))})
                    for k, v in d["environments"].items()}
            sites = {k: SitePolicy(frozenset(x.casefold() for x in v.get("deny_toolchains", [])),
                                   frozenset(x.casefold() for x in v.get("allow_toolchains", [])))
                     for k, v in d.get("sites", {}).items()}
            waivers = tuple(Waiver(**{**w, "codes": frozenset(w["codes"]), "environments": frozenset(w["environments"])})
                            for w in d.get("waivers", []))
            return cls(d["policy_id"], d["revision"], envs, sites, waivers)
        except (KeyError, TypeError) as exc:
            raise ValidationError(f"malformed policy: {exc}", code=Reason.POLICY_INVALID) from None

    @classmethod
    def load(cls, path) -> SelectionPolicy:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def default_policy() -> SelectionPolicy:
    """The shipped policy (config/policy.default.json mirrors it; a test pins the two together)."""
    dev = EnvironmentRule(min_maturity="experimental", require_security_contact=False, require_review=False,
                          allow_deprecated=True, require_certification=False, require_integrity=False,
                          advisory_block_severity="critical", require_advisory_feed=False,
                          allowed_catalog_status=frozenset({"supported", "example"}), production=False)
    staging = EnvironmentRule(min_maturity="beta", require_security_contact=True, require_review=True,
                              accept_conditional_review=True, allow_deprecated=True, require_certification=False,
                              require_integrity=True, advisory_block_severity="high", require_advisory_feed=False,
                              allowed_catalog_status=frozenset({"supported", "example"}), production=False)
    prod = EnvironmentRule()  # the fail-closed defaults above
    return SelectionPolicy("inv28-default", 1, {"dev": dev, "test": dev, "staging": staging, "production": prod})
