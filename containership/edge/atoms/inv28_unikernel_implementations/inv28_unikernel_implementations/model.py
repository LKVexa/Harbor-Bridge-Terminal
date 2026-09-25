"""PK_TOOLCHAIN/2 register-entry model (MC-009..MC-021, MC-095, MC-096).

A :class:`ToolchainRecord` is immutable, normalised on construction and fails closed on anything
malformed, ambiguous or unknown.  Its identity is ``name@version`` and its content digest is the
SHA-256 of its canonical JSON (sorted keys, no whitespace, UTF-8) - the same bytes the registry
signs and the selection ticket binds (MC-021, MC-098).

Review freshness uses real UTC timestamps with reviewer/evidence provenance (MC-017, MC-096) and a
per-toolchain interval (MC-018).  The v1 logical-tick model survives only in the deprecated
``component.Toolchain`` compatibility shim (docs/MIGRATION.md).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from dataclasses import dataclass
from functools import cached_property

from .errors import ValidationError

SCHEMA = "PK_TOOLCHAIN/2"
MATURITY = ("experimental", "beta", "mature")
LIFECYCLE = ("candidate", "active", "deprecated", "eol", "retired", "quarantined", "disabled")
#: lifecycle states that may ever be selected (deprecated only outside production, see policy)
SELECTABLE_LIFECYCLE = ("active", "deprecated")
REVIEW_RESULTS = ("approved", "conditional", "rejected")
CATALOG_STATUS = ("supported", "example", "unregistered")

# Resource bounds (MC-078): every string and collection is bounded so a hostile register entry or
# request cannot cause unbounded work or unbounded output.
MAX_TOKEN_LEN = 64
MAX_SET_SIZE = 64
MAX_TEXT_LEN = 512
MAX_LIMITATIONS = 32

_TOKEN = re.compile(r"^[a-z0-9][a-z0-9._+\-/]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_VERSION = re.compile(r"^[0-9A-Za-z][0-9A-Za-z.+\-_]{0,63}$")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-]{0,63}$")


def canonical(obj) -> bytes:
    """Deterministic serialisation used for every digest/signature in INV-28."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(obj) -> str:
    return hashlib.sha256(obj if isinstance(obj, bytes) else canonical(obj)).hexdigest()


def token(value, what: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{what} entries must be strings", field=what)
    v = value.strip().lower()
    if not v or len(v) > MAX_TOKEN_LEN or not _TOKEN.match(v):
        raise ValidationError(f"{what}: malformed token {value!r}", field=what)
    return v


def token_set(value, what: str, *, allow_empty: bool = False) -> frozenset:
    if isinstance(value, (str, bytes)) or not isinstance(value, (set, frozenset, list, tuple)):
        raise ValidationError(f"{what} must be a collection of tokens, not {type(value).__name__}", field=what)
    if len(value) > MAX_SET_SIZE:
        raise ValidationError(f"{what}: more than {MAX_SET_SIZE} entries", field=what)
    out = frozenset(token(v, what) for v in value)
    if len(out) != len(value):
        raise ValidationError(f"{what}: duplicate entries after normalisation", field=what)
    if not out and not allow_empty:
        raise ValidationError(f"{what} must not be empty", field=what)
    return out


def text(value, what: str, *, optional: bool = False) -> str:
    if value is None and optional:
        return ""
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_TEXT_LEN:
        raise ValidationError(f"{what} must be a non-empty string of at most {MAX_TEXT_LEN} chars", field=what)
    return value.strip()


def parse_utc(value, what: str) -> dt.datetime:
    """Strict RFC 3339 UTC timestamp ('Z' or +00:00).  Naive or non-UTC times are refused."""
    if isinstance(value, dt.datetime):
        ts = value
    elif isinstance(value, str):
        try:
            ts = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            raise ValidationError(f"{what}: not an ISO-8601 timestamp: {value!r}", field=what) from None
    else:
        raise ValidationError(f"{what}: timestamp required", field=what)
    if ts.tzinfo is None or ts.utcoffset() != dt.timedelta(0):
        raise ValidationError(f"{what}: timestamp must be UTC", field=what)
    return ts.astimezone(dt.timezone.utc)


def fmt_utc(ts: dt.datetime) -> str:
    return ts.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(value, what: str, *, optional=False) -> str:
    if (value is None or value == "") and optional:
        return ""
    if not isinstance(value, str) or not _SHA256.match(value):
        raise ValidationError(f"{what} must be a lowercase hex SHA-256", field=what)
    return value


@dataclass(frozen=True)
class SecurityResponse:
    """MC-016: more than a boolean - who to tell, where advisories appear, how fast they respond."""

    contact_ref: str = ""            # e.g. "mailto:security@example.org" or a SECURITY.md URL
    advisory_feed: str = ""          # URL/identifier of the upstream advisory feed
    disclosure_policy_ref: str = ""
    response_sla_hours: int = 0      # 0 = no declared SLA

    def __post_init__(self):
        for f in ("contact_ref", "advisory_feed", "disclosure_policy_ref"):
            v = getattr(self, f)
            if not isinstance(v, str) or len(v) > MAX_TEXT_LEN:
                raise ValidationError(f"security.{f} must be a string", field=f)
            object.__setattr__(self, f, v.strip())
        if type(self.response_sla_hours) is not int or not 0 <= self.response_sla_hours <= 24 * 365:
            raise ValidationError("security.response_sla_hours must be an int in [0, 8760]")

    @property
    def has_contact(self) -> bool:
        return bool(self.contact_ref)

    def to_dict(self) -> dict:
        return {"contact_ref": self.contact_ref, "advisory_feed": self.advisory_feed,
                "disclosure_policy_ref": self.disclosure_policy_ref, "response_sla_hours": self.response_sla_hours}


@dataclass(frozen=True)
class ReviewRecord:
    """MC-017/MC-018/MC-096: a security review with provenance and its own validity interval."""

    reviewer: str
    reviewed_at: str                  # RFC 3339 UTC
    result: str                       # approved | conditional | rejected
    evidence_uri: str
    evidence_sha256: str
    interval_days: int = 180

    def __post_init__(self):
        object.__setattr__(self, "reviewer", text(self.reviewer, "review.reviewer"))
        object.__setattr__(self, "reviewed_at", fmt_utc(parse_utc(self.reviewed_at, "review.reviewed_at")))
        r = self.result.strip().lower() if isinstance(self.result, str) else ""
        if r not in REVIEW_RESULTS:
            raise ValidationError(f"review.result must be one of {REVIEW_RESULTS}")
        object.__setattr__(self, "result", r)
        object.__setattr__(self, "evidence_uri", text(self.evidence_uri, "review.evidence_uri"))
        object.__setattr__(self, "evidence_sha256", _sha(self.evidence_sha256, "review.evidence_sha256"))
        if type(self.interval_days) is not int or not 1 <= self.interval_days <= 730:
            raise ValidationError("review.interval_days must be an int in [1, 730]")

    def expires_at(self) -> dt.datetime:
        return self._expires

    @cached_property
    def _expires(self) -> dt.datetime:
        return parse_utc(self.reviewed_at, "reviewed_at") + dt.timedelta(days=self.interval_days)

    def stale(self, now: dt.datetime) -> bool:
        return now > self.expires_at()

    def to_dict(self) -> dict:
        return {"reviewer": self.reviewer, "reviewed_at": self.reviewed_at, "result": self.result,
                "evidence_uri": self.evidence_uri, "evidence_sha256": self.evidence_sha256,
                "interval_days": self.interval_days}


@dataclass(frozen=True)
class Limitation:
    """MC-019: a structured limitation evaluated against the request, not just prose.

    ``excludes_features`` - the toolchain cannot serve a workload that needs any of these features.
    ``excludes_environments`` - never selectable in these environments.
    """

    code: str
    description: str
    excludes_features: frozenset = frozenset()
    excludes_environments: frozenset = frozenset()

    def __post_init__(self):
        object.__setattr__(self, "code", token(self.code, "limitation.code"))
        object.__setattr__(self, "description", text(self.description, "limitation.description"))
        object.__setattr__(self, "excludes_features",
                           token_set(self.excludes_features, "limitation.excludes_features", allow_empty=True))
        object.__setattr__(self, "excludes_environments",
                           token_set(self.excludes_environments, "limitation.excludes_environments", allow_empty=True))

    def to_dict(self) -> dict:
        return {"code": self.code, "description": self.description,
                "excludes_features": sorted(self.excludes_features),
                "excludes_environments": sorted(self.excludes_environments)}


@dataclass(frozen=True)
class IntegrityIdentity:
    """MC-021: immutable identity of the toolchain release the selection is bound to."""

    source_uri: str
    artifact_sha256: str
    signer: str = ""
    sbom_sha256: str = ""
    provenance_uri: str = ""

    def __post_init__(self):
        object.__setattr__(self, "source_uri", text(self.source_uri, "integrity.source_uri"))
        object.__setattr__(self, "artifact_sha256", _sha(self.artifact_sha256, "integrity.artifact_sha256"))
        object.__setattr__(self, "sbom_sha256", _sha(self.sbom_sha256, "integrity.sbom_sha256", optional=True))
        for f in ("signer", "provenance_uri"):
            v = getattr(self, f)
            if not isinstance(v, str) or len(v) > MAX_TEXT_LEN:
                raise ValidationError(f"integrity.{f} must be a string")
            object.__setattr__(self, f, v.strip())

    def to_dict(self) -> dict:
        return {"source_uri": self.source_uri, "artifact_sha256": self.artifact_sha256, "signer": self.signer,
                "sbom_sha256": self.sbom_sha256, "provenance_uri": self.provenance_uri}


@dataclass(frozen=True)
class ToolchainRecord:
    """One registered unikernel toolchain release (PK_TOOLCHAIN/2)."""

    name: str
    version: str
    languages: frozenset
    runtimes: frozenset
    architectures: frozenset
    devices: frozenset
    features: frozenset
    hypervisors: frozenset
    providers: frozenset
    abis: frozenset
    maturity: str
    security: SecurityResponse
    review: ReviewRecord | None = None
    limitations: tuple = ()
    lifecycle: str = "candidate"
    eol_date: str = ""
    integrity: IntegrityIdentity | None = None
    catalog_status: str = "example"
    owner: str = "inv28-register-owner"
    notes: str = ""

    def __post_init__(self):
        if not isinstance(self.name, str) or not _NAME.match(self.name.strip()):
            raise ValidationError(f"name must match {_NAME.pattern}", field="name")
        object.__setattr__(self, "name", self.name.strip())
        if not isinstance(self.version, str) or not _VERSION.match(self.version.strip()):
            raise ValidationError("version must be a pinned release string (no ranges/wildcards)", field="version")
        if any(c in self.version for c in "*^~<>= "):
            raise ValidationError("version must be exact, not a range", field="version")
        object.__setattr__(self, "version", self.version.strip())
        for f in ("languages", "architectures"):
            object.__setattr__(self, f, token_set(getattr(self, f), f))
        for f in ("runtimes", "devices", "features", "hypervisors", "providers", "abis"):
            object.__setattr__(self, f, token_set(getattr(self, f), f, allow_empty=True))
        m = self.maturity.strip().lower() if isinstance(self.maturity, str) else ""
        if m not in MATURITY:
            raise ValidationError(f"unknown maturity {self.maturity!r}", field="maturity")
        object.__setattr__(self, "maturity", m)
        if not isinstance(self.security, SecurityResponse):
            raise ValidationError("security must be a SecurityResponse", field="security")
        if self.review is not None and not isinstance(self.review, ReviewRecord):
            raise ValidationError("review must be a ReviewRecord or None", field="review")
        if not isinstance(self.limitations, (tuple, list)) or len(self.limitations) > MAX_LIMITATIONS \
                or any(not isinstance(x, Limitation) for x in self.limitations):
            raise ValidationError("limitations must be a sequence of Limitation", field="limitations")
        codes = [x.code for x in self.limitations]
        if len(set(codes)) != len(codes):
            raise ValidationError("duplicate limitation codes", field="limitations")
        object.__setattr__(self, "limitations", tuple(sorted(self.limitations, key=lambda x: x.code)))
        lc = self.lifecycle.strip().lower() if isinstance(self.lifecycle, str) else ""
        if lc not in LIFECYCLE:
            raise ValidationError(f"unknown lifecycle {self.lifecycle!r}", field="lifecycle")
        object.__setattr__(self, "lifecycle", lc)
        if self.eol_date:
            try:
                dt.date.fromisoformat(self.eol_date)
            except (TypeError, ValueError):
                raise ValidationError("eol_date must be YYYY-MM-DD", field="eol_date") from None
        if self.integrity is not None and not isinstance(self.integrity, IntegrityIdentity):
            raise ValidationError("integrity must be an IntegrityIdentity or None", field="integrity")
        cs = self.catalog_status.strip().lower() if isinstance(self.catalog_status, str) else ""
        if cs not in CATALOG_STATUS:
            raise ValidationError(f"catalog_status must be one of {CATALOG_STATUS}", field="catalog_status")
        object.__setattr__(self, "catalog_status", cs)
        object.__setattr__(self, "owner", text(self.owner, "owner"))
        if not isinstance(self.notes, str) or len(self.notes) > MAX_TEXT_LEN:
            raise ValidationError("notes must be a string", field="notes")

    # -- identity -------------------------------------------------------------------------------
    @property
    def key(self) -> str:
        return f"{self.name.casefold()}@{self.version}"

    @property
    def ref(self) -> str:
        return f"{self.name}@{self.version}"

    @cached_property
    def digest(self) -> str:
        """Memoised: the record is immutable, so its canonical digest never changes."""
        return sha256_hex(self.to_dict())

    # -- helpers --------------------------------------------------------------------------------
    def eol_passed(self, now: dt.datetime) -> bool:
        return bool(self.eol_date) and now.date() > self._eol

    @cached_property
    def _eol(self) -> dt.date:
        return dt.date.fromisoformat(self.eol_date)

    def replace(self, **changes) -> ToolchainRecord:
        d = self.to_dict()
        d.update({k: v for k, v in changes.items()})
        return ToolchainRecord.from_dict(d)

    # -- serialisation --------------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "schema": SCHEMA, "name": self.name, "version": self.version,
            "languages": sorted(self.languages), "runtimes": sorted(self.runtimes),
            "architectures": sorted(self.architectures), "devices": sorted(self.devices),
            "features": sorted(self.features), "hypervisors": sorted(self.hypervisors),
            "providers": sorted(self.providers), "abis": sorted(self.abis),
            "maturity": self.maturity, "security": self.security.to_dict(),
            "review": self.review.to_dict() if self.review else None,
            "limitations": [x.to_dict() for x in self.limitations],
            "lifecycle": self.lifecycle, "eol_date": self.eol_date,
            "integrity": self.integrity.to_dict() if self.integrity else None,
            "catalog_status": self.catalog_status, "owner": self.owner, "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ToolchainRecord:
        if not isinstance(d, dict):
            raise ValidationError("toolchain record must be an object")
        allowed = set(cls.__dataclass_fields__) | {"schema"}
        unknown = set(d) - allowed
        if unknown:
            raise ValidationError(f"unknown fields {sorted(unknown)}", field="record")
        if d.get("schema", SCHEMA) != SCHEMA:
            raise ValidationError(f"unsupported schema {d.get('schema')!r}; expected {SCHEMA}", field="schema")
        req = {"name", "version", "languages", "architectures", "maturity", "security"}
        missing = req - set(d)
        if missing:
            raise ValidationError(f"missing fields {sorted(missing)}", field="record")
        sec = d["security"]
        if not isinstance(sec, dict):
            raise ValidationError("security must be an object")
        rev = d.get("review")
        integ = d.get("integrity")
        try:
            return cls(
                name=d["name"], version=d["version"], languages=d["languages"],
                runtimes=d.get("runtimes", []), architectures=d["architectures"],
                devices=d.get("devices", []), features=d.get("features", []),
                hypervisors=d.get("hypervisors", []), providers=d.get("providers", []),
                abis=d.get("abis", []), maturity=d["maturity"],
                security=SecurityResponse(**sec),
                review=ReviewRecord(**rev) if rev is not None else None,
                limitations=tuple(Limitation(**x) for x in d.get("limitations", [])),
                lifecycle=d.get("lifecycle", "candidate"), eol_date=d.get("eol_date", ""),
                integrity=IntegrityIdentity(**integ) if integ is not None else None,
                catalog_status=d.get("catalog_status", "example"),
                owner=d.get("owner", "inv28-register-owner"), notes=d.get("notes", ""),
            )
        except TypeError as exc:  # unknown nested keys
            raise ValidationError(f"malformed nested object: {exc}") from None
