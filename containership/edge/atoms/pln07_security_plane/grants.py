"""Security-plane capability grant primitives.

This module intentionally has no ``pk_core`` dependency so the security-critical
invariants can be unit-tested even when the orchestration framework is absent.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Iterable

MAX_DELEGATION_DEPTH = 5
MAX_SCOPE_ITEMS = 256
MAX_ATOM_LENGTH = 256
_ID_RE = re.compile(r"^[0-9a-f]{16}$")
_FP_RE = re.compile(r"^[0-9a-f]{64}$")

#: Wire/schema versions this build understands.  ``PK_GRANT/1`` is the 4.x body;
#: ``PK_GRANT/2`` adds boundary, replay and issuance-instance fields (MC-11/13/16).
SUPPORTED_GRANT_TYPES = ("PK_GRANT/1", "PK_GRANT/2")
_V2_FIELDS = ("environment", "site", "workload", "audience", "issued_at", "not_before", "nonce")


class SecurityPlaneError(PermissionError):
    """Base class for machine-readable security-plane failures."""

    code = "security_plane.error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = dict(details or {})

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "details": dict(self.details)}


class Widening(SecurityPlaneError):
    """Raised when a derived grant requests authority its parent does not hold."""

    code = "grant.widening"


class GrantInvalid(SecurityPlaneError):
    """Raised when a grant or grant chain fails validation or verification."""

    code = "grant.invalid"

    def __init__(
        self,
        message: str,
        *,
        reason: str = "invalid",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, details=details)
        self.reason = reason
        self.code = f"grant.{reason}"


def _text_atom(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if value != value.strip() or not value:
        raise ValueError(f"{name} must be non-empty and must not have surrounding whitespace")
    if len(value) > MAX_ATOM_LENGTH:
        raise ValueError(f"{name} exceeds {MAX_ATOM_LENGTH} characters")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError(f"{name} contains a control character")
    return value


def _nonnegative_int(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def _scope(value: Iterable[str] | frozenset[str]) -> frozenset[str]:
    if isinstance(value, (str, bytes)):
        raise TypeError("scope must be an iterable of capability strings, not a string")
    try:
        normalized = frozenset(_text_atom("capability", item) for item in value)
    except TypeError:
        raise TypeError("scope must be an iterable of capability strings") from None
    if len(normalized) > MAX_SCOPE_ITEMS:
        raise ValueError(f"scope exceeds {MAX_SCOPE_ITEMS} capabilities")
    return normalized


@dataclass(frozen=True, slots=True)
class Grant:
    """A tenant-bound, scoped, expiring capability grant.

    ``id`` remains the 16-hex compatibility identifier used by the 4.x series.
    ``fingerprint`` exposes the full SHA-256 digest for collision-resistant audit
    correlation.  Every child is bound to its parent identifier.
    """

    subject: str
    tenant: str
    scope: frozenset[str]
    not_after: int
    parent: "Grant | None" = None
    depth: int = 0
    issuer: str | None = None
    signature: Any = field(default=None, repr=False, compare=False)
    # --- PK_GRANT/2 fields (all optional; absent == 4.x semantics) -----------
    environment: str | None = None
    site: str | None = None
    workload: str | None = None
    audience: str | None = None
    issued_at: int | None = None
    not_before: int | None = None
    nonce: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject", _text_atom("subject", self.subject))
        object.__setattr__(self, "tenant", _text_atom("tenant", self.tenant))
        object.__setattr__(self, "scope", _scope(self.scope))
        object.__setattr__(self, "not_after", _nonnegative_int("not_after", self.not_after))
        object.__setattr__(self, "depth", _nonnegative_int("depth", self.depth))
        if self.issuer is not None:
            object.__setattr__(self, "issuer", _text_atom("issuer", self.issuer))
        for name in ("environment", "site", "workload", "audience", "nonce"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _text_atom(name, value))
        for name in ("issued_at", "not_before"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _nonnegative_int(name, value))
        if self.not_before is not None and self.not_before > self.not_after:
            raise GrantInvalid("not_before is later than not_after", reason="window")
        if self.issued_at is not None and self.issued_at > self.not_after:
            raise GrantInvalid("issued_at is later than not_after", reason="window")

        if self.parent is not None and not isinstance(self.parent, Grant):
            raise TypeError("parent must be a Grant or None")
        expected_depth = 0 if self.parent is None else self.parent.depth + 1
        if self.depth != expected_depth:
            raise GrantInvalid(
                f"delegation depth {self.depth} does not match expected depth {expected_depth}",
                reason="depth",
                details={"expected": expected_depth, "actual": self.depth},
            )
        if self.depth > MAX_DELEGATION_DEPTH:
            raise GrantInvalid(
                f"delegation depth {self.depth} exceeds {MAX_DELEGATION_DEPTH}",
                reason="depth",
            )
        if self.parent is not None:
            if self.tenant != self.parent.tenant:
                raise Widening("a child grant cannot cross tenant boundaries")
            if not self.scope <= self.parent.scope:
                raise Widening(
                    f"scope {sorted(self.scope - self.parent.scope)} exceeds the parent grant"
                )
            if self.not_after > self.parent.not_after:
                raise Widening(
                    f"expiry {self.not_after} is later than the parent grant's {self.parent.not_after}"
                )
            # Boundary fields are sticky: once a parent pins a boundary, a child
            # may not drop or change it (MC-11).
            for name in ("environment", "site", "workload", "audience"):
                pv = getattr(self.parent, name)
                if pv is not None and getattr(self, name) != pv:
                    raise Widening(f"a child grant cannot change or drop the parent's {name} boundary")
            if (
                self.parent.not_before is not None
                and (self.not_before is None or self.not_before < self.parent.not_before)
            ):
                raise Widening("a child grant cannot become valid before its parent")

    @property
    def grant_type(self) -> str:
        return "PK_GRANT/2" if any(getattr(self, n) is not None for n in _V2_FIELDS) else "PK_GRANT/1"

    def _payload(self, parent_id: str | None) -> bytes:
        body = {
            "depth": self.depth,
            "issuer": self.issuer,
            "not_after": self.not_after,
            "parent_id": parent_id,
            "scope": sorted(self.scope),
            "subject": self.subject,
            "tenant": self.tenant,
            "type": "PK_GRANT/1",
        }
        if self.grant_type == "PK_GRANT/2":
            body["type"] = "PK_GRANT/2"
            body["parent_fingerprint"] = self.parent.fingerprint if self.parent is not None else None
            for name in _V2_FIELDS:
                body[name] = getattr(self, name)
        return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def _legacy_digest(self, seen: set[int]) -> str:
        """Compute the 4.x identifier digest while detecting malicious cycles."""
        marker = id(self)
        if marker in seen:
            raise GrantInvalid("cycle detected in grant chain", reason="cycle")
        seen.add(marker)
        try:
            parent_id = self.parent._legacy_digest(seen)[:16] if self.parent is not None else ""
            seed = (
                f"{self.subject}|{self.tenant}|{sorted(self.scope)}|"
                f"{self.not_after}|{self.depth}|{parent_id}"
            )
            return hashlib.sha256(seed.encode("utf-8")).hexdigest()
        finally:
            seen.remove(marker)

    @property
    def id(self) -> str:
        """Stable 4.x grant identifier used by existing revocation records."""
        return self._legacy_digest(set())[:16]

    @property
    def canonical_payload(self) -> bytes:
        """Canonical, signature-ready representation of this grant body."""
        parent_id = self.parent.id if self.parent is not None else None
        return self._payload(parent_id)

    @property
    def fingerprint(self) -> str:
        """Full SHA-256 fingerprint of the canonical grant body for audit correlation."""
        return hashlib.sha256(self.canonical_payload).hexdigest()

    def signed(self, signature: Any) -> "Grant":
        """Return an immutable copy carrying a signature over ``canonical_payload``."""
        if signature is None:
            raise ValueError("signature must not be None")
        return replace(self, signature=signature)

    def attenuate(
        self,
        *,
        subject: str | None = None,
        scope: Iterable[str] | None = None,
        not_after: int | None = None,
        issuer: str | None = None,
        signature: Any = None,
        not_before: int | None = None,
        nonce: str | None = None,
        issued_at: int | None = None,
        max_depth: int | None = None,
    ) -> "Grant":
        """Derive a same-or-narrower grant; widening in any dimension is refused.

        A no-op attenuation is rejected.  Delegating to a different subject counts
        as a meaningful derivation even when scope and expiry remain unchanged.
        """
        new_subject = self.subject if subject is None else _text_atom("subject", subject)
        new_scope = self.scope if scope is None else _scope(scope)
        if not new_scope <= self.scope:
            raise Widening(f"scope {sorted(new_scope - self.scope)} exceeds the held grant")
        new_expiry = self.not_after if not_after is None else _nonnegative_int("not_after", not_after)
        if new_expiry > self.not_after:
            raise Widening(f"expiry {new_expiry} is later than the held grant's {self.not_after}")
        limit = MAX_DELEGATION_DEPTH if max_depth is None else min(
            MAX_DELEGATION_DEPTH, _nonnegative_int("max_depth", max_depth)
        )
        if self.depth + 1 > limit:
            raise GrantInvalid(
                f"delegation depth {self.depth + 1} exceeds {limit}",
                reason="depth",
            )
        new_nb = self.not_before if not_before is None else _nonnegative_int("not_before", not_before)
        if new_subject == self.subject and new_scope == self.scope and new_expiry == self.not_after:
            raise GrantInvalid("attenuation must change subject, scope, or expiry", reason="noop")
        return Grant(
            new_subject,
            self.tenant,
            new_scope,
            new_expiry,
            self,
            self.depth + 1,
            issuer,
            signature,
            environment=self.environment,
            site=self.site,
            workload=self.workload,
            audience=self.audience,
            issued_at=issued_at,
            not_before=new_nb,
            nonce=nonce,
        )


SignatureVerifier = Callable[[Grant], bool]


@dataclass(frozen=True, slots=True)
class VerificationResult:
    verified: bool
    code: str
    reason: str
    grant_id: str
    capability: str
    tenant: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "type": "PK_GRANT_VERIFICATION/1",
            "verified": self.verified,
            "code": self.code,
            "reason": self.reason,
            "grant_id": self.grant_id,
            "capability": self.capability,
            "tenant": self.tenant,
        }


@dataclass(slots=True)
class Verifier:
    """Verify an entire grant chain at a logical point in time."""

    revoked: set[str] = field(default_factory=set)
    skew: int = 0
    require_signatures: bool = False
    signature_verifier: SignatureVerifier | None = None
    #: Optional live revocation source (e.g. ``revocation.RevocationRegistry``);
    #: must expose ``is_revoked(grant) -> bool``.  Consulted for every link.
    revocation_source: Any = None
    #: Optional depth policy ``(grant) -> int`` returning the maximum depth allowed
    #: for that grant's tenant/capability/environment (MC-15).
    depth_policy: Callable[[Grant], int] | None = None
    #: Refuse PK_GRANT/1 bodies (no boundary/replay fields) once migrated (MC-16).
    require_v2: bool = False

    def __post_init__(self) -> None:
        self.skew = _nonnegative_int("skew", self.skew)
        normalized: set[str] = set()
        for grant_id in self.revoked:
            grant_id = _text_atom("revoked grant id", grant_id).lower()
            if not (_ID_RE.fullmatch(grant_id) or _FP_RE.fullmatch(grant_id)):
                raise ValueError(
                    "revoked ids must be 16-hex legacy ids or 64-hex full fingerprints"
                )
            normalized.add(grant_id)
        self.revoked = normalized
        if self.require_signatures and self.signature_verifier is None:
            raise ValueError("signature_verifier is required when require_signatures=True")

    def _verify_signature(self, grant: Grant) -> None:
        if not self.require_signatures:
            return
        if grant.signature is None:
            raise GrantInvalid(f"grant {grant.id} is unsigned", reason="unsigned")
        try:
            verified = bool(self.signature_verifier(grant))  # type: ignore[misc]
        except Exception as exc:  # verifier adapters are outside this trust boundary
            raise GrantInvalid(
                f"signature verification failed for grant {grant.id}",
                reason="signature",
                details={"verifier_error": type(exc).__name__},
            ) from exc
        if not verified:
            raise GrantInvalid(f"signature verification failed for grant {grant.id}", reason="signature")

    def verify(
        self,
        grant: Grant,
        now: int,
        capability: str,
        tenant: str,
        *,
        environment: str | None = None,
        site: str | None = None,
        workload: str | None = None,
        audience: str | None = None,
    ) -> bool:
        now = _nonnegative_int("now", now)
        capability = _text_atom("capability", capability)
        tenant = _text_atom("tenant", tenant)
        if not isinstance(grant, Grant):
            raise TypeError("grant must be a Grant")
        expected = {"environment": environment, "site": site, "workload": workload, "audience": audience}
        if self.require_v2 and grant.grant_type != "PK_GRANT/2":
            raise GrantInvalid("PK_GRANT/1 bodies are no longer accepted", reason="version")

        seen_objects: set[int] = set()
        link: Grant | None = grant
        while link is not None:
            marker = id(link)
            if marker in seen_objects:
                raise GrantInvalid("cycle detected in grant chain", reason="cycle")
            seen_objects.add(marker)

            if link.depth > MAX_DELEGATION_DEPTH or len(seen_objects) > MAX_DELEGATION_DEPTH + 1:
                raise GrantInvalid("grant chain exceeds maximum delegation depth", reason="depth")
            if link.id in self.revoked or link.fingerprint in self.revoked:
                raise GrantInvalid(f"grant {link.id} is revoked", reason="revoked")
            if self.revocation_source is not None:
                try:
                    hit = bool(self.revocation_source.is_revoked(link))
                except Exception as exc:  # fail closed: unknown revocation state
                    raise GrantInvalid(
                        "revocation state unavailable", reason="revocation_unavailable",
                        details={"error": type(exc).__name__},
                    ) from exc
                if hit:
                    raise GrantInvalid(f"grant {link.id} is revoked", reason="revoked")
            if link.not_before is not None and now + self.skew < link.not_before:
                raise GrantInvalid(f"grant {link.id} is not yet valid", reason="not_yet_valid")
            if now - self.skew > link.not_after:
                raise GrantInvalid(
                    f"grant {link.id} expired at {link.not_after}",
                    reason="expired",
                    details={"not_after": link.not_after, "now": now, "skew": self.skew},
                )
            if link.tenant != tenant:
                raise GrantInvalid("grant chain crosses a tenant boundary", reason="tenant")
            for name, want in expected.items():
                have = getattr(link, name)
                if have is not None and want != have:
                    raise GrantInvalid(f"grant chain is bound to a different {name}", reason=name)
            self._verify_signature(link)

            expected_depth = 0 if link.parent is None else link.parent.depth + 1
            if link.depth != expected_depth:
                raise GrantInvalid(
                    f"grant {link.id} has an inconsistent delegation depth",
                    reason="depth",
                )
            if link.parent is not None:
                if link.tenant != link.parent.tenant:
                    raise GrantInvalid(f"grant {link.id} crosses tenant boundaries", reason="tenant")
                if not link.scope <= link.parent.scope:
                    raise GrantInvalid(f"grant {link.id} widens its parent", reason="widening")
                if link.not_after > link.parent.not_after:
                    raise GrantInvalid(f"grant {link.id} outlives its parent", reason="expiry_widening")
            link = link.parent

        if self.depth_policy is not None:
            try:
                limit = int(self.depth_policy(grant))
            except Exception as exc:
                raise GrantInvalid("delegation policy unavailable", reason="policy_unavailable") from exc
            if grant.depth > limit:
                raise GrantInvalid(f"delegation depth {grant.depth} exceeds policy limit {limit}", reason="depth")
        if capability not in grant.scope:
            raise GrantInvalid(
                f"capability {capability!r} is outside the grant scope",
                reason="capability",
            )
        return True

    def verify_detailed(self, grant: Grant, now: int, capability: str, tenant: str, **boundary: Any) -> VerificationResult:
        """Return a machine-readable decision without suppressing verification logic."""
        try:
            self.verify(grant, now=now, capability=capability, tenant=tenant, **boundary)
        except GrantInvalid as exc:
            try:
                grant_id = grant.id
            except GrantInvalid:
                grant_id = "invalid-chain"
            return VerificationResult(False, exc.code, str(exc), grant_id, capability, tenant)
        except (TypeError, ValueError) as exc:
            return VerificationResult(False, "grant.malformed", str(exc), "invalid-input", str(capability), str(tenant))
        return VerificationResult(True, "grant.valid", "verified", grant.id, capability, tenant)
