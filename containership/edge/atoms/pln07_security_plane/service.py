"""Production service boundary for PLN-07 (MC-09, MC-10, MC-13, MC-16, MC-39,
MC-45, MC-61).

``SecurityPlaneService`` composes authentication, policy, quota, signing,
trusted time, durable revocation, admission control, quarantine and telemetry
into four operations - ``issue``, ``attenuate``, ``verify``, ``revoke`` - plus
``health`` and ``explain``.  Every operation:

* accepts and returns versioned JSON envelopes (``api_version``),
* authenticates the caller at the boundary (except ``verify``/``health``),
* fails closed with a stable ``code``,
* emits a metric, a structured log line and a hash-chained audit event.

Wire codec: ``encode_grant``/``decode_grant`` serialise a full chain; unknown
major versions are refused, unknown fields inside a known version are refused
(no silent semantic drift).
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Mapping

from . import __version__
from .clock import TrustedClock
from .config import ConfigStore
from .grants import SUPPORTED_GRANT_TYPES, Grant, GrantInvalid, SecurityPlaneError, Verifier
from .identity import AttestationPolicy, Authenticator
from .observability import Telemetry, from_traceparent, span
from .policy import IssuancePolicy, PolicyDenied, QuotaLimiter
from .resilience import Health, Quarantine, TokenBucket
from .revocation import RevocationRegistry
from .signing import KeyStore

API_VERSIONS = ("1",)
MAX_WIRE_CHAIN = 6
_GRANT_FIELDS = {"type", "subject", "tenant", "scope", "not_after", "depth", "issuer", "signature",
                 "environment", "site", "workload", "audience", "issued_at", "not_before", "nonce"}


class UnsupportedVersion(SecurityPlaneError):
    code = "api.unsupported_version"


class Malformed(SecurityPlaneError):
    code = "api.malformed"


# ------------------------------------------------------------------- codec --
def encode_grant(grant: Grant) -> list[dict]:
    chain, link = [], grant
    while link is not None:
        d = {"type": link.grant_type, "subject": link.subject, "tenant": link.tenant,
             "scope": sorted(link.scope), "not_after": link.not_after, "depth": link.depth,
             "issuer": link.issuer, "signature": link.signature}
        if link.grant_type == "PK_GRANT/2":
            for n in ("environment", "site", "workload", "audience", "issued_at", "not_before", "nonce"):
                d[n] = getattr(link, n)
        chain.append(d)
        link = link.parent
    return list(reversed(chain))  # root first


def decode_grant(chain: Any) -> Grant:
    if not isinstance(chain, list) or not 1 <= len(chain) <= MAX_WIRE_CHAIN:
        raise Malformed("grant chain must be a non-empty list within the depth bound")
    parent = None
    for item in chain:
        if not isinstance(item, dict):
            raise Malformed("grant link must be an object")
        t = item.get("type")
        if t not in SUPPORTED_GRANT_TYPES:
            raise UnsupportedVersion("unsupported grant type", details={"type": t,
                                                                         "supported": list(SUPPORTED_GRANT_TYPES)})
        extra = set(item) - _GRANT_FIELDS
        if extra or (t == "PK_GRANT/1" and set(item) & {"environment", "site", "workload", "audience",
                                                         "issued_at", "not_before", "nonce"}):
            raise Malformed("unknown fields for grant type", details={"fields": sorted(extra)})
        kwargs = {k: item.get(k) for k in ("environment", "site", "workload", "audience",
                                            "issued_at", "not_before", "nonce")}
        try:
            parent = Grant(item["subject"], item["tenant"], frozenset(item["scope"]), item["not_after"],
                           parent, item["depth"], item.get("issuer"), item.get("signature"), **kwargs)
        except KeyError as exc:
            raise Malformed("missing grant field", details={"field": str(exc)}) from None
        except (TypeError, ValueError) as exc:
            raise Malformed(str(exc)) from None
        if parent.grant_type != t:
            raise Malformed("declared type does not match fields")
    return parent


def negotiate(requested: Any) -> str:
    """Pick the highest mutually-supported API version or refuse."""
    offered = [requested] if isinstance(requested, str) else list(requested or [])
    common = [v for v in API_VERSIONS if v in offered]
    if not common:
        raise UnsupportedVersion("no mutually supported api_version",
                                 details={"offered": offered, "supported": list(API_VERSIONS)})
    return max(common)


# ----------------------------------------------------------------- service --
@dataclass
class SecurityPlaneService:
    authenticator: Authenticator
    keys: KeyStore
    policy: IssuancePolicy = field(default_factory=IssuancePolicy)
    clock: TrustedClock = field(default_factory=TrustedClock)
    revocations: RevocationRegistry = field(default_factory=RevocationRegistry)
    config: ConfigStore = field(default_factory=ConfigStore)
    attestation: AttestationPolicy = field(default_factory=AttestationPolicy)
    quota: QuotaLimiter | None = None
    telemetry: Telemetry = field(default_factory=Telemetry)
    health_state: Health = field(default_factory=Health)
    quarantine: Quarantine = field(default_factory=Quarantine)
    controller_epoch: int = 1
    _admission: TokenBucket | None = field(default=None, init=False)
    _issued_nonces: set[str] = field(default_factory=set, init=False)

    def __post_init__(self) -> None:
        cfg = self.config.config
        self._admission = TokenBucket(cfg["admission"]["rate_per_second"], cfg["admission"]["burst"])
        if self.quota is None:
            self.quota = QuotaLimiter(default=cfg["tenant_quota_default"])
        self.health_state.set("ready")

    # -- helpers -----------------------------------------------------------------
    def _verifier(self) -> Verifier:
        cfg = self.config.config
        return Verifier(skew=cfg["clock_skew_seconds"], require_signatures=cfg["require_signatures"],
                        signature_verifier=self.keys.grant_verifier(),
                        revocation_source=self.revocations, depth_policy=self.policy.depth_limit,
                        require_v2=cfg["require_v2"])

    def _envelope(self, op: str, ok: bool, code: str, api: str, **data: Any) -> dict:
        return {"api_version": api, "op": op, "ok": ok, "code": code, **data}

    def _run(self, op: str, request: Mapping, body) -> dict:
        from_traceparent(request.get("traceparent"))
        t0 = time.perf_counter_ns()
        api = "?"
        with span(self.telemetry, f"pln07.{op}"):
            try:
                api = negotiate(request.get("api_version"))
                if op not in ("verify", "health"):
                    self._admission.admit()
                result = body(api)
                self.telemetry.metrics.inc("pln07_requests_total", op=op, outcome="ok")
                return result
            except SecurityPlaneError as exc:
                self.telemetry.metrics.inc("pln07_requests_total", op=op, outcome=exc.code)
                self.telemetry.audit.emit(op, "deny", exc.code, detail=str(exc))
                self.telemetry.log("warning", f"{op} refused", code=exc.code)
                return self._envelope(op, False, exc.code, api, error=exc.as_dict())
            except (KeyError, TypeError, ValueError) as exc:
                self.telemetry.metrics.inc("pln07_requests_total", op=op, outcome="api.malformed")
                self.telemetry.audit.emit(op, "deny", "api.malformed", detail=type(exc).__name__)
                return self._envelope(op, False, "api.malformed", api,
                                      error={"code": "api.malformed", "message": str(exc)})
            finally:
                self.telemetry.metrics.observe(f"pln07_{op}_latency", time.perf_counter_ns() - t0)

    # -- operations ----------------------------------------------------------------
    def issue(self, request: Mapping) -> dict:
        def body(api: str) -> dict:
            principal = self.authenticator.authenticate(request["credentials"])
            spec = request["grant"]
            now = self.clock.now()
            self.quarantine.check(tenant=spec["tenant"], subject=spec["subject"], site=spec.get("site"))
            self.attestation.check(principal, spec.get("environment"))
            decision = self.policy.authorize_issue(principal, {**spec, "now": now})
            if not decision.allow:
                raise PolicyDenied(decision.reason, details={"rule": decision.rule, "category": decision.category})
            self.quota.acquire(spec["tenant"])
            nonce = secrets.token_hex(16)
            while nonce in self._issued_nonces:  # pragma: no cover - 128-bit collision
                nonce = secrets.token_hex(16)
            self._issued_nonces.add(nonce)
            grant = Grant(spec["subject"], spec["tenant"], frozenset(spec["scope"]), spec["not_after"],
                          issuer=f"{self.keys.trust_domain}/{principal.subject}",
                          environment=spec.get("environment"), site=spec.get("site"),
                          workload=spec.get("workload"), audience=spec.get("audience"),
                          issued_at=now, not_before=spec.get("not_before", now), nonce=nonce)
            grant = self.keys.sign_grant(grant, now=now)
            self.telemetry.audit.emit("issue", "allow", "grant.issued", grant=grant.fingerprint,
                                      tenant=grant.tenant, actor=principal.subject, rule=decision.rule)
            return self._envelope("issue", True, "grant.issued", api, grant=encode_grant(grant),
                                  grant_id=grant.id, fingerprint=grant.fingerprint)
        return self._run("issue", request, body)

    def attenuate(self, request: Mapping) -> dict:
        def body(api: str) -> dict:
            principal = self.authenticator.authenticate(request["credentials"])
            parent = decode_grant(request["grant"])
            now = self.clock.now()
            self.quarantine.check(tenant=parent.tenant, subject=parent.subject, site=parent.site)
            # holder must present a currently-valid parent that names them
            if principal.subject != parent.subject or principal.tenant != parent.tenant:
                raise PolicyDenied("only the holder may attenuate a grant")
            self._verifier().verify(parent, now, next(iter(sorted(parent.scope))), parent.tenant,
                                    environment=parent.environment, site=parent.site,
                                    workload=parent.workload, audience=parent.audience)
            spec = request.get("attenuation", {})
            child = parent.attenuate(subject=spec.get("subject"), scope=spec.get("scope"),
                                     not_after=spec.get("not_after"), issuer=f"{self.keys.trust_domain}/{principal.subject}",
                                     issued_at=now, nonce=secrets.token_hex(16),
                                     max_depth=self.policy.depth_limit(parent))
            child = self.keys.sign_grant(child, now=now)
            self.telemetry.audit.emit("attenuate", "allow", "grant.attenuated", parent=parent.fingerprint,
                                      grant=child.fingerprint, actor=principal.subject)
            return self._envelope("attenuate", True, "grant.attenuated", api, grant=encode_grant(child),
                                  grant_id=child.id, fingerprint=child.fingerprint)
        return self._run("attenuate", request, body)

    def verify(self, request: Mapping) -> dict:
        def body(api: str) -> dict:
            grant = decode_grant(request["grant"])
            ctx = request["context"]
            self.quarantine.check(tenant=ctx["tenant"], site=ctx.get("site"))
            now = self.clock.now()
            result = self._verifier().verify_detailed(
                grant, now, ctx["capability"], ctx["tenant"], environment=ctx.get("environment"),
                site=ctx.get("site"), workload=ctx.get("workload"), audience=ctx.get("audience"))
            self.telemetry.audit.emit("verify", "allow" if result.verified else "deny", result.code,
                                      grant=result.grant_id, capability=result.capability)
            return self._envelope("verify", result.verified, result.code, api, decision=result.as_dict())
        return self._run("verify", request, body)

    def revoke(self, request: Mapping) -> dict:
        def body(api: str) -> dict:
            principal = self.authenticator.authenticate(request["credentials"])
            grant = decode_grant(request["grant"])
            if principal.tenant != grant.tenant or not ({"revoker", "grant-issuer"} & principal.roles):
                raise PolicyDenied("caller may not revoke this grant")
            now = self.clock.now()
            rec = self.revocations.revoke(
                grant, effective_at=now, epoch=request.get("epoch", self.controller_epoch),
                horizon=self.config.config["revocation_horizon_seconds"],
                reason=str(request.get("reason", "")), actor=principal.subject)
            self.quota.release(grant.tenant)
            self.telemetry.audit.emit("revoke", "allow", "grant.revoked", grant=grant.fingerprint,
                                      actor=principal.subject, seq=rec["seq"])
            return self._envelope("revoke", True, "grant.revoked", api, revocation={
                k: rec[k] for k in ("type", "fingerprint", "grant_id", "effective_at", "horizon", "seq")})
        return self._run("revoke", request, body)

    # -- operator surfaces ----------------------------------------------------------
    def health(self) -> dict:
        h = self.health_state.check()
        return {"component": "PLN-07", "version": __version__, "api_versions": list(API_VERSIONS),
                "grant_types": list(SUPPORTED_GRANT_TYPES), **h,
                "time": self.clock.status(),
                "config": {"version": self.config.active["provenance"]["version"],
                           "digest": self.config.active["provenance"]["digest"]},
                "dependencies": {"keys": self.keys.describe(), "revocation": self.revocations.stats(),
                                 "revocation_chain_ok": self.revocations.verify_chain(),
                                 "audit_chain_ok": self.telemetry.audit.verify()},
                "capabilities": ["issue", "attenuate", "verify", "revoke", "explain"],
                "frozen": self.quarantine.plane_frozen}

    def explain(self, grant_wire: Any, context: Mapping) -> dict:
        """Operator explain view: every link and every check, no secrets."""
        grant = decode_grant(grant_wire)
        now = self.clock.now()
        links, link = [], grant
        while link is not None:
            links.append({"depth": link.depth, "grant_id": link.id, "fingerprint": link.fingerprint,
                          "type": link.grant_type, "subject": link.subject, "tenant": link.tenant,
                          "scope": sorted(link.scope), "not_before": link.not_before,
                          "not_after": link.not_after, "expired": now - self.config.config["clock_skew_seconds"] > link.not_after,
                          "revoked": self.revocations.is_revoked(link),
                          "signature_ok": self.keys.verify(link.signature, link.canonical_payload),
                          "boundary": {n: getattr(link, n) for n in ("environment", "site", "workload", "audience")}})
            link = link.parent
        decision = self._verifier().verify_detailed(grant, now, context["capability"], context["tenant"],
                                                    **{k: context.get(k) for k in ("environment", "site", "workload", "audience")})
        return {"now": now, "decision": decision.as_dict(), "chain": list(reversed(links)),
                "depth_limit": self.policy.depth_limit(grant)}
