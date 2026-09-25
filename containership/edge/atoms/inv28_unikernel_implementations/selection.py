"""Toolchain selection: typed request, typed result, structured refusal (MC-012, MC-019, MC-022..MC-026,
MC-078..MC-080, MC-094, MC-097..MC-100).

``Selector.select(request, now=...)`` evaluates **every** registered entry against **every**
constraint and records all unmet constraints per candidate (not just the first), so a refusal says
exactly what was missing.  A candidate survives only if it has no remaining codes after approved,
unexpired, scoped waivers are applied to waivable codes.

Determinism: for the same request, registry revision, policy digest, certification snapshot,
advisory snapshot, rollout state and ``now`` the result is byte-identical (``decision_id`` is the
digest of exactly those inputs).  Candidates are ranked by maturity, then certification presence,
then name (casefold), then version (newest first).

Bounds (MC-078): at most ``MAX_CANDIDATES`` are evaluated (the registry cap), at most
``MAX_ELIMINATIONS`` are reported (with a truncation count), request fields are bounded by the
model's token limits.  Deadline/cancellation (MC-079) are checked between candidates and around
every dependency call.  Results are cached (MC-080) by the full input digest; any registry
revision change clears the cache, so a stale answer is impossible by construction.
"""
from __future__ import annotations

import datetime as dt
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass

from .errors import Inv28Error, Reason, RefusalError, ValidationError
from .model import MATURITY, fmt_utc, sha256_hex, text, token, token_set

REQUEST_SCHEMA = "PK_TOOLCHAIN_SELECTION_REQUEST/1"
RESULT_SCHEMA = "PK_TOOLCHAIN_SELECTION/2"
REFUSAL_SCHEMA = "PK_TOOLCHAIN_REFUSAL/1"
MAX_CANDIDATES = 1024
MAX_ELIMINATIONS = 256
CACHE_SIZE = 1024


@dataclass(frozen=True)
class SiteCapabilities:
    """MC-099: what the target site can actually host."""

    site_id: str
    architectures: frozenset
    hypervisors: frozenset = frozenset()
    providers: frozenset = frozenset()

    def __post_init__(self):
        object.__setattr__(self, "site_id", token(self.site_id, "site_id"))
        object.__setattr__(self, "architectures", token_set(self.architectures, "site.architectures"))
        object.__setattr__(self, "hypervisors", token_set(self.hypervisors, "site.hypervisors", allow_empty=True))
        object.__setattr__(self, "providers", token_set(self.providers, "site.providers", allow_empty=True))

    def to_dict(self):
        return {"site_id": self.site_id, "architectures": sorted(self.architectures),
                "hypervisors": sorted(self.hypervisors), "providers": sorted(self.providers)}


@dataclass(frozen=True)
class SelectionRequest:
    """MC-023/MC-100: a validated workload-requirements object; the workload never names a toolchain."""

    workload_id: str
    tenant: str
    environment: str
    language: str
    architecture: str
    runtime: str = ""
    devices: frozenset = frozenset()
    features: frozenset = frozenset()
    hypervisor: str = ""
    provider: str = ""
    abi: str = ""
    site: SiteCapabilities | None = None

    def __post_init__(self):
        object.__setattr__(self, "workload_id", text(self.workload_id, "workload_id"))
        object.__setattr__(self, "tenant", text(self.tenant, "tenant"))
        for f in ("environment", "language", "architecture"):
            object.__setattr__(self, f, token(getattr(self, f), f))
        for f in ("runtime", "hypervisor", "provider", "abi"):
            v = getattr(self, f)
            object.__setattr__(self, f, token(v, f) if v else "")
        object.__setattr__(self, "devices", token_set(self.devices, "devices", allow_empty=True))
        object.__setattr__(self, "features", token_set(self.features, "features", allow_empty=True))
        if self.site is not None and not isinstance(self.site, SiteCapabilities):
            raise ValidationError("site must be SiteCapabilities")

    def to_dict(self):
        return {"schema": REQUEST_SCHEMA, "workload_id": self.workload_id, "tenant": self.tenant,
                "environment": self.environment, "language": self.language, "architecture": self.architecture,
                "runtime": self.runtime, "devices": sorted(self.devices), "features": sorted(self.features),
                "hypervisor": self.hypervisor, "provider": self.provider, "abi": self.abi,
                "site": self.site.to_dict() if self.site else None}

    @classmethod
    def from_dict(cls, d: dict) -> SelectionRequest:
        if not isinstance(d, dict):
            raise ValidationError("request must be an object")
        if d.get("schema", REQUEST_SCHEMA) != REQUEST_SCHEMA:
            raise ValidationError(f"request schema must be {REQUEST_SCHEMA}")
        allowed = set(cls.__dataclass_fields__) | {"schema"}
        if set(d) - allowed:
            raise ValidationError(f"unknown request fields {sorted(set(d) - allowed)}")
        missing = {"workload_id", "tenant", "environment", "language", "architecture"} - set(d)
        if missing:
            raise ValidationError(f"missing request fields {sorted(missing)}")
        site = d.get("site")
        try:
            return cls(**{**{k: v for k, v in d.items() if k not in ("schema", "site")},
                          "site": SiteCapabilities(**site) if site else None})
        except TypeError as exc:
            raise ValidationError(f"malformed request: {exc}") from None


@dataclass(frozen=True)
class SelectionResult:
    """MC-024: immutable, schema-bound record of a positive decision."""

    decision_id: str
    toolchain: str
    version: str
    record_digest: str
    artifact_sha256: str
    maturity: str
    certification_id: str
    waivers: tuple
    request_digest: str
    registry_revision: int
    registry_digest: str
    policy_id: str
    policy_revision: int
    policy_digest: str
    certification_snapshot: str
    advisory_snapshot: str
    evaluated_at: str
    eliminated: tuple
    eliminated_truncated: int
    ticket: dict | None = None

    @property
    def ref(self):
        return f"{self.toolchain}@{self.version}"

    def to_dict(self) -> dict:
        return {"schema": RESULT_SCHEMA, "decision_id": self.decision_id, "outcome": "SELECTED",
                "toolchain": self.toolchain, "version": self.version, "record_digest": self.record_digest,
                "artifact_sha256": self.artifact_sha256, "maturity": self.maturity,
                "certification_id": self.certification_id, "waivers": list(self.waivers),
                "request_digest": self.request_digest, "registry_revision": self.registry_revision,
                "registry_digest": self.registry_digest, "policy_id": self.policy_id,
                "policy_revision": self.policy_revision, "policy_digest": self.policy_digest,
                "certification_snapshot": self.certification_snapshot,
                "advisory_snapshot": self.advisory_snapshot, "evaluated_at": self.evaluated_at,
                "eliminated": [dict(e) for e in self.eliminated], "eliminated_truncated": self.eliminated_truncated,
                "ticket": self.ticket}


@dataclass(frozen=True)
class Refusal:
    """MC-026: structured refusal listing every unmet constraint."""

    decision_id: str
    code: str
    summary: str
    unmet: dict                  # reason code -> sorted list of toolchain refs
    eliminated: tuple
    eliminated_truncated: int
    request_digest: str
    registry_revision: int
    policy_id: str
    policy_revision: int
    policy_digest: str
    evaluated_at: str

    def to_dict(self) -> dict:
        return {"schema": REFUSAL_SCHEMA, "decision_id": self.decision_id, "outcome": "REFUSED", "code": self.code,
                "summary": self.summary, "unmet": {k: list(v) for k, v in sorted(self.unmet.items())},
                "eliminated": [dict(e) for e in self.eliminated], "eliminated_truncated": self.eliminated_truncated,
                "request_digest": self.request_digest, "registry_revision": self.registry_revision,
                "policy_id": self.policy_id, "policy_revision": self.policy_revision,
                "policy_digest": self.policy_digest, "evaluated_at": self.evaluated_at}


def version_key(v: str):
    parts = []
    for chunk in v.replace("-", ".").replace("+", ".").split("."):
        parts.append((0, int(chunk), "") if chunk.isdigit() else (1, 0, chunk))
    return tuple(parts)


class Selector:
    def __init__(self, registry, policy, *, certifications=None, advisories=None, rollout=None, binder=None,
                 metrics=None, logger=None, audit=None):
        self.registry = registry
        self._policy = policy
        self._policy_digest = policy.digest
        self.certifications = certifications
        self.advisories = advisories
        self.rollout = rollout
        self.binder = binder
        self.metrics = metrics
        self.logger = logger
        self.audit = audit
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self.cache_hits = 0
        registry.on_change(lambda _rev: self.invalidate())

    # -- policy management (versioned, MC-022) ---------------------------------------------------
    @property
    def policy(self):
        return self._policy

    def set_policy(self, policy) -> None:
        if policy.policy_id == self._policy.policy_id and policy.revision <= self._policy.revision:
            raise ValidationError("policy revision must increase", code=Reason.POLICY_INVALID)
        self._policy, self._policy_digest = policy, policy.digest
        self.invalidate()

    def invalidate(self) -> None:
        with self._lock:
            self._cache.clear()

    # -- main entry ------------------------------------------------------------------------------
    def select(self, request: SelectionRequest, *, now: dt.datetime, deadline: float | None = None,
               cancel: threading.Event | None = None, trace=None) -> SelectionResult:
        """Return a SelectionResult or raise RefusalError (structured) / Inv28Error (request-level)."""
        t0 = time.perf_counter()
        if not isinstance(request, SelectionRequest):
            raise ValidationError("select takes a SelectionRequest")
        if not isinstance(now, dt.datetime) or now.tzinfo is None or now.utcoffset() != dt.timedelta(0):
            raise ValidationError("now must be a timezone-aware UTC datetime from a trusted clock",
                                  code=Reason.CLOCK_UNTRUSTED)
        env = request.environment
        try:
            rule = self._policy.rule(env)
            key, decision_id = self._cache_key(request, now)
            with self._lock:
                hit = self._cache.get(key)
                if hit is not None:
                    self._cache.move_to_end(key)
                    self.cache_hits += 1
            if hit is not None:
                outcome = hit
            else:
                outcome = self._evaluate(request, rule, now, decision_id, deadline, cancel)
                with self._lock:
                    self._cache[key] = outcome
                    while len(self._cache) > CACHE_SIZE:
                        self._cache.popitem(last=False)
        except Inv28Error as exc:
            self._observe_refusal(request, exc.code.value, None, t0, trace)
            raise
        if isinstance(outcome, Refusal):
            self._observe_refusal(request, outcome.code, outcome, t0, trace)
            raise RefusalError(outcome)
        result = outcome
        if self.binder is not None:
            result = _with_ticket(result, self.binder.issue(result, now))
        self._observe_selection(request, result, t0, trace)
        return result

    # -- evaluation ------------------------------------------------------------------------------
    def _cache_key(self, request, now) -> tuple:
        """(cache key, decision id).  The decision id is the digest of every decision input and is
        therefore identical across processes; the cache key additionally pins this registry object."""
        did = sha256_hex({
            "request": request.to_dict(), "registry": self.registry.digest,
            "policy": self._policy_digest,
            "certs": self.certifications.digest if self.certifications is not None else None,
            "advisories": self.advisories.digest if self.advisories is not None else None,
            "rollout": self.rollout.digest if self.rollout is not None else None,
            "now": fmt_utc(now) + f".{now.microsecond:06d}"})
        return sha256_hex([id(self.registry), self.registry.revision, did]), did

    def _check_deadline(self, deadline, cancel):
        if cancel is not None and cancel.is_set():
            raise Inv28Error(Reason.CANCELLED, "selection cancelled")
        if deadline is not None and time.monotonic() > deadline:
            raise Inv28Error(Reason.DEADLINE_EXCEEDED, "selection deadline exceeded")

    def _evaluate(self, req: SelectionRequest, rule, now, decision_id, deadline, cancel):
        pol = self._policy
        env = req.environment
        # Request-level dependency checks: fail closed rather than decide on missing inputs.
        if rule.require_certification and self.certifications is None:
            raise Inv28Error(Reason.DEPENDENCY_UNAVAILABLE, "GAP-15 certification store not configured")
        if rule.require_certification:
            self._check_deadline(deadline, cancel)
            self.certifications.refresh()
            self._check_deadline(deadline, cancel)
        if rule.require_advisory_feed and (self.advisories is None or self.advisories.stale(now)):
            raise Inv28Error(Reason.DEPENDENCY_UNAVAILABLE, "advisory feed missing or stale")
        if req.site is not None and req.architecture not in req.site.architectures:
            raise Inv28Error(Reason.SITE_ARCH_UNSUPPORTED,
                             f"site {req.site.site_id} does not host {req.architecture}")
        site_pol = pol.sites.get(req.site.site_id) if req.site else None
        entries = self.registry.entries
        if len(entries) > MAX_CANDIDATES:
            raise Inv28Error(Reason.LIMIT_EXCEEDED, "registry exceeds selection candidate bound")
        survivors, eliminated = [], []
        for rec in entries:
            self._check_deadline(deadline, cancel)
            codes = self._codes(rec, req, rule, now, site_pol)
            cert = None
            if rule.require_certification and rec.integrity is not None:
                cert = self.certifications.lookup(
                    ref=rec.ref, artifact_sha256=rec.integrity.artifact_sha256, architecture=req.architecture,
                    runtime=req.runtime, hypervisor=req.hypervisor, now=now)
                if cert is None:
                    codes.append(Reason.NOT_CERTIFIED.value)
            elif rule.require_certification:
                codes.append(Reason.NOT_CERTIFIED.value)
            elif self.certifications is not None and rec.integrity is not None:
                cert = self.certifications.lookup(
                    ref=rec.ref, artifact_sha256=rec.integrity.artifact_sha256, architecture=req.architecture,
                    runtime=req.runtime, hypervisor=req.hypervisor, now=now)
            waived = []
            remaining = []
            for c in dict.fromkeys(codes):
                w = None
                if not (c == Reason.MATURITY_BELOW_POLICY.value and rule.production and rec.maturity == "experimental"):
                    w = pol.waiver_for(rec.ref, env, c, now)
                if w is not None:
                    waived.append(w.id)
                else:
                    remaining.append(c)
            if remaining:
                eliminated.append({"toolchain": rec.ref, "codes": sorted(remaining)})
            else:
                survivors.append((rec, cert, tuple(sorted(set(waived)))))
        truncated = max(0, len(eliminated) - MAX_ELIMINATIONS)
        elim = tuple(eliminated[:MAX_ELIMINATIONS])
        common = dict(request_digest=sha256_hex(req.to_dict()), registry_revision=self.registry.revision,
                      policy_id=pol.policy_id, policy_revision=pol.revision, policy_digest=self._policy_digest,
                      evaluated_at=fmt_utc(now))
        if not survivors:
            unmet: dict = {}
            for e in eliminated:
                for c in e["codes"]:
                    unmet.setdefault(c, []).append(e["toolchain"])
            return Refusal(decision_id=decision_id, code=Reason.NO_SUITABLE_TOOLCHAIN.value,
                           summary=(f"no registered toolchain meets language={req.language} arch={req.architecture} "
                                    f"env={env}" + (f" site={req.site.site_id}" if req.site else "")),
                           unmet={k: tuple(sorted(v)) for k, v in unmet.items()}, eliminated=elim,
                           eliminated_truncated=truncated, **common)
        survivors.sort(key=lambda s: (-MATURITY.index(s[0].maturity), s[1] is None, s[0].name.casefold(),
                                      tuple(_neg(version_key(s[0].version)))))
        rec, cert, chosen_waivers = survivors[0]
        return SelectionResult(
            decision_id=decision_id, toolchain=rec.name, version=rec.version, record_digest=rec.digest,
            artifact_sha256=rec.integrity.artifact_sha256 if rec.integrity else "", maturity=rec.maturity,
            certification_id=cert.cert_id if cert else "", waivers=chosen_waivers,
            registry_digest=self.registry.digest,
            certification_snapshot=self.certifications.digest if self.certifications is not None else "",
            advisory_snapshot=self.advisories.digest if self.advisories is not None else "",
            eliminated=elim, eliminated_truncated=truncated, **common)

    def _codes(self, rec, req, rule, now, site_pol) -> list:
        R, codes = Reason, []
        # lifecycle / catalog / site policy
        if rec.lifecycle == "disabled":
            codes.append(R.DISABLED.value)
        elif rec.lifecycle == "eol" or rec.eol_passed(now):
            codes.append(R.EOL.value)
        elif rec.lifecycle not in ("active", "deprecated") or (rec.lifecycle == "deprecated" and not rule.allow_deprecated):
            codes.append(R.LIFECYCLE_NOT_SELECTABLE.value)
        if rec.catalog_status not in rule.allowed_catalog_status:
            codes.append(R.POLICY_DENIED.value)
        if site_pol is not None:
            n = rec.name.casefold()
            if n in site_pol.deny_toolchains or (site_pol.allow_toolchains and n not in site_pol.allow_toolchains):
                codes.append(R.POLICY_DENIED.value)
        # capabilities (MC-010..MC-015, MC-100)
        if req.language not in rec.languages:
            codes.append(R.LANGUAGE_UNSUPPORTED.value)
        if req.runtime and req.runtime not in rec.runtimes:
            codes.append(R.RUNTIME_UNSUPPORTED.value)
        if req.architecture not in rec.architectures:
            codes.append(R.ARCH_UNSUPPORTED.value)
        if not req.devices <= rec.devices:
            codes.append(R.DEVICE_UNSUPPORTED.value)
        if not req.features <= rec.features:
            codes.append(R.FEATURE_UNSUPPORTED.value)
        if req.hypervisor and req.hypervisor not in rec.hypervisors:
            codes.append(R.HYPERVISOR_UNSUPPORTED.value)
        if req.provider and req.provider not in rec.providers:
            codes.append(R.PROVIDER_UNSUPPORTED.value)
        if req.abi and req.abi not in rec.abis:
            codes.append(R.ABI_UNSUPPORTED.value)
        # limitations (MC-019)
        for lim in rec.limitations:
            if (lim.excludes_features & req.features) or req.environment in lim.excludes_environments:
                codes.append(R.LIMITATION_CONFLICT.value)
                break
        # site capabilities (MC-099)
        if req.site is not None:
            hv = rec.hypervisors & req.site.hypervisors if req.site.hypervisors else rec.hypervisors
            if req.site.hypervisors and (not hv or (req.hypervisor and req.hypervisor not in hv)):
                codes.append(R.SITE_HYPERVISOR_UNSUPPORTED.value)
            if req.site.providers and not (rec.providers & req.site.providers):
                codes.append(R.PROVIDER_UNSUPPORTED.value)
        # maturity (MC-094) and security posture (MC-016..MC-018)
        if MATURITY.index(rec.maturity) < MATURITY.index(rule.min_maturity):
            codes.append(R.MATURITY_BELOW_POLICY.value)
        if rule.require_security_contact and not rec.security.has_contact:
            codes.append(R.NO_SECURITY_CONTACT.value)
        if rule.min_response_sla_hours and not (0 < rec.security.response_sla_hours <= rule.min_response_sla_hours):
            codes.append(R.SECURITY_RESPONSE_INADEQUATE.value)
        if rule.require_review:
            if rec.review is None:
                codes.append(R.REVIEW_MISSING.value)
            elif rec.review.result == "rejected" or (rec.review.result == "conditional" and not rule.accept_conditional_review):
                codes.append(R.REVIEW_REJECTED.value)
            elif rec.review.stale(now):
                codes.append(R.REVIEW_STALE.value)
        if rule.require_integrity and rec.integrity is None:
            codes.append(R.INTEGRITY_MISSING.value)
        if self.advisories is not None and self.advisories.open_for(rec.name, rec.version, rule.advisory_block_severity):
            codes.append(R.ADVISORY_OPEN.value)
        if self.rollout is not None and not self.rollout.admits(rec.ref, req):
            codes.append(R.NOT_IN_ROLLOUT.value)
        return codes

    # -- observability -----------------------------------------------------------------------------
    def _observe_selection(self, req, result, t0, trace):
        ms = (time.perf_counter() - t0) * 1000
        if self.metrics:
            self.metrics.inc("inv28_selections_total", toolchain=result.toolchain, environment=req.environment)
            self.metrics.observe("inv28_selection_latency_ms", ms, environment=req.environment)
            counts: dict = {}
            for e in result.eliminated:
                for c in e["codes"]:
                    counts[c] = counts.get(c, 0) + 1
            self.metrics.inc_many("inv28_candidate_eliminations_total", "code", counts)
        if self.audit is not None:
            self.audit.append("selection", {"decision_id": result.decision_id, "outcome": "SELECTED",
                                            "toolchain": result.ref, "record_digest": result.record_digest,
                                            "request": req.to_dict(), "policy_digest": result.policy_digest,
                                            "registry_revision": result.registry_revision,
                                            "certification_id": result.certification_id,
                                            "waivers": list(result.waivers), "eliminated": list(result.eliminated)})
        if self.logger:
            self.logger.log("info", "toolchain.selected", operation_id=result.decision_id[:16], trace=trace,
                            tenant=req.tenant, workload_id=req.workload_id, toolchain=result.ref,
                            environment=req.environment, latency_ms=round(ms, 3))

    def _observe_refusal(self, req, code, refusal, t0, trace):
        ms = (time.perf_counter() - t0) * 1000
        if self.metrics:
            self.metrics.inc("inv28_selection_refusals_total", code=code, environment=req.environment)
            self.metrics.observe("inv28_selection_latency_ms", ms, environment=req.environment)
            if code == Reason.DEPENDENCY_UNAVAILABLE.value:
                self.metrics.inc("inv28_dependency_errors_total", dependency="gap15-or-advisory")
        if self.audit is not None:
            self.audit.append("refusal", {"decision_id": refusal.decision_id if refusal else "", "outcome": "REFUSED",
                                          "code": code, "request": req.to_dict(),
                                          "unmet": {k: list(v) for k, v in (refusal.unmet.items() if refusal else [])},
                                          "policy_digest": self._policy_digest,
                                          "registry_revision": self.registry.revision})
        if self.logger:
            self.logger.log("warning", "toolchain.refused", operation_id=(refusal.decision_id[:16] if refusal else ""),
                            trace=trace, tenant=req.tenant, workload_id=req.workload_id, code=code,
                            environment=req.environment, latency_ms=round(ms, 3))


def _neg(vk):
    # newest version first: invert numeric parts, keep deterministic ordering for text parts
    return [(a, -b, "".join(chr(0x10FFFF - ord(ch)) for ch in c)) for a, b, c in vk]


def _with_ticket(result: SelectionResult, ticket: dict) -> SelectionResult:
    d = dict(result.__dict__)
    d["ticket"] = ticket
    return SelectionResult(**d)
