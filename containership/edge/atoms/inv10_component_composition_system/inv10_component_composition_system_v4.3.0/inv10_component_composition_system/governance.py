"""MC-11..MC-14: context boundaries, link authorization, provenance, externals.

* :class:`CompositionContext` carries tenant/workload/environment/site identity.
* :class:`LinkPolicy` decides whether consumer -> provider bindings are allowed.
* :class:`ProvenanceVerifier` checks artifact digest, signature and approved version.
* :class:`EnvironmentResolver` proves each declared external exists in the
  target environment with a compatible version and trust level.
All are fail-closed: absence of a rule is denial.
"""
from __future__ import annotations

import fnmatch
import hashlib
import hmac
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from .composition import Unit
from .errors import BoundaryViolation, ExternalUnavailable, PolicyRejected, ProvenanceRejected

_CTX = re.compile(r"^[a-z0-9][a-z0-9._\-]{0,127}$")


@dataclass(frozen=True)
class CompositionContext:
    tenant: str
    workload: str
    environment: str
    site: str = "any"

    def __post_init__(self) -> None:
        for k in ("tenant", "workload", "environment", "site"):
            if not _CTX.match(getattr(self, k)):
                raise BoundaryViolation(f"invalid context {k}", field=k)

    def as_dict(self) -> dict[str, str]:
        return {"tenant": self.tenant, "workload": self.workload,
                "environment": self.environment, "site": self.site}


def enforce_tenant_boundary(ctx: CompositionContext, unit_tenants: Mapping[str, str]) -> None:
    """Compositions do not link across tenants (contract boundary)."""
    for unit, tenant in sorted(unit_tenants.items()):
        if tenant != ctx.tenant and tenant != "shared":
            raise BoundaryViolation("unit belongs to another tenant", unit=unit,
                                    unit_tenant=tenant, tenant=ctx.tenant)


@dataclass(frozen=True)
class LinkRule:
    consumer: str  # glob over component names
    interface: str  # glob over interface identifiers
    provider: str = "*"  # glob over provider names, or "<external>"
    tenants: tuple[str, ...] = ("*",)
    effect: str = "allow"  # allow | deny


@dataclass
class LinkPolicy:
    """Ordered capability policy; deny rules win; default deny."""

    rules: list[LinkRule] = field(default_factory=list)
    version: str = "0"

    def decide(self, ctx: CompositionContext, binding: Mapping[str, Any]) -> dict[str, Any]:
        provider = binding.get("provider", "<external>")
        matched = [r for r in self.rules
                   if fnmatch.fnmatchcase(binding["consumer"], r.consumer)
                   and fnmatch.fnmatchcase(binding["interface"], r.interface)
                   and fnmatch.fnmatchcase(provider, r.provider)
                   and any(fnmatch.fnmatchcase(ctx.tenant, t) for t in r.tenants)]
        if any(r.effect == "deny" for r in matched):
            return {"allowed": False, "reason": "explicit-deny", "binding": dict(binding)}
        if any(r.effect == "allow" for r in matched):
            return {"allowed": True, "reason": "allow", "binding": dict(binding)}
        return {"allowed": False, "reason": "default-deny", "binding": dict(binding)}

    def enforce(self, ctx: CompositionContext, bindings: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        decisions = [self.decide(ctx, b) for b in bindings]
        denied = [d for d in decisions if not d["allowed"]]
        if denied:
            raise PolicyRejected("link policy denied binding(s)", policy_version=self.version,
                                 denied=[{**d["binding"], "reason": d["reason"]} for d in denied])
        return decisions


@dataclass(frozen=True)
class ArtifactRecord:
    unit: str
    version: str
    digest: str  # sha256 hex
    signature: str  # hex HMAC-SHA256 over "unit\nversion\ndigest"
    key_id: str


class ProvenanceVerifier:
    """Verifies digest, signature (via a key provider) and approved versions.

    Signatures use HMAC-SHA256 because the package is stdlib-only; production
    deployments should plug an asymmetric verifier (e.g. Sigstore/ed25519) with
    the same ``verify`` signature.
    """

    def __init__(self, keys: Any, approved: Mapping[str, set[str]]) -> None:
        self.keys = keys
        self.approved = {k: set(v) for k, v in approved.items()}

    @staticmethod
    def message(unit: str, version: str, digest: str) -> bytes:
        return f"{unit}\n{version}\n{digest}".encode()

    def verify(self, record: ArtifactRecord, artifact: bytes | None = None) -> None:
        if artifact is not None and hashlib.sha256(artifact).hexdigest() != record.digest:
            raise ProvenanceRejected("artifact digest mismatch", unit=record.unit)
        if record.version not in self.approved.get(record.unit, set()):
            raise ProvenanceRejected("version not approved", unit=record.unit, version=record.version)
        key = self.keys.verification_key(record.key_id)
        expected = hmac.new(key, self.message(record.unit, record.version, record.digest), "sha256").hexdigest()
        if not hmac.compare_digest(expected, record.signature):
            raise ProvenanceRejected("signature invalid", unit=record.unit, key_id=record.key_id)

    def verify_all(self, units: Iterable[Unit], records: Mapping[str, ArtifactRecord]) -> None:
        for u in units:
            if u.name not in records:
                raise ProvenanceRejected("no provenance record", unit=u.name)
            self.verify(records[u.name])


@dataclass(frozen=True)
class EnvironmentOffer:
    interface: str
    trust: str = "platform"  # platform | vendor | tenant
    capabilities: tuple[str, ...] = ()


class EnvironmentResolver:
    """Proves declared externals are actually supplied by an environment."""

    TRUST_ORDER = {"tenant": 0, "vendor": 1, "platform": 2}

    def __init__(self, offers: Mapping[str, Iterable[EnvironmentOffer]], interface_resolver: Any = None) -> None:
        self.offers = {env: list(v) for env, v in offers.items()}
        self.iface = interface_resolver

    def resolve(self, ctx: CompositionContext, externals: Iterable[str], *, min_trust: str = "vendor") -> dict[str, str]:
        offered = self.offers.get(ctx.environment)
        if offered is None:
            raise ExternalUnavailable("environment unknown to resolver", environment=ctx.environment)
        out: dict[str, str] = {}
        for ext in sorted(externals):
            cands = [o for o in offered if o.interface == ext or
                     (self.iface is not None and self.iface.compatible(ext, o.interface))]
            cands = [o for o in cands if self.TRUST_ORDER[o.trust] >= self.TRUST_ORDER[min_trust]]
            if not cands:
                raise ExternalUnavailable("external import not available in environment",
                                          interface=ext, environment=ctx.environment)
            out[ext] = sorted(cands, key=lambda o: o.interface)[-1].interface
        return out
