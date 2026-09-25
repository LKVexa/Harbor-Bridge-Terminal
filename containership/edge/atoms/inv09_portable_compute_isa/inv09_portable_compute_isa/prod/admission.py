"""M04 declared-capability binding, M10 execution admission gate, M11 TOCTOU
protection, M33 health/readiness.

Flow (the only path by which a module reaches an engine):

    bytes --snapshot--> digest (M07) --> cache? (M09)
          --> decode+typecheck+features (M01-M03, byte-derived only)
          --> host-import classification (M17/M18)
          --> declared-capability binding (M04) + profile policy (M22)
          --> engine capability check (M06)
          --> signed attestation (M08)
    admit(bytes, attestation) --> AdmissionTicket (immutable snapshot + digest)
    execute(ticket, runner)   --> re-hash snapshot, re-check epoch, run

Any exception on this path is a refusal.  There is no "skip validation" flag.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional

from . import VALIDATOR_ID, VALIDATOR_VERSION
from .attest import Attestation, Signer, Verifier, issue, verify
from .cache import ValidationCache
from .digest import digests_equal, module_digest
from .errors import Code, InvalidModule
from .hostimports import HostContract, default_contract
from .limits import DEFAULT_LIMITS, Limits
from .registry import PolicyBundle, canonical_json, default_bundle
from .telemetry import AuditStream, Metrics, get_logger, new_span_id, parse_traceparent
from .typecheck import validate_module

MANIFEST_SCHEMA = "PK_CAPABILITY_MANIFEST/1"


@dataclass(frozen=True)
class CapabilityManifest:
    """M04: the *declared* capability set, bound to one module digest.

    Declarations are requests, never facts: byte-derived features must be a
    subset of the declaration, and the declaration must fit the profile.
    """
    module_digest: str
    declared_features: frozenset[str]

    @staticmethod
    def parse(raw: bytes | str) -> "CapabilityManifest":
        try:
            d = json.loads(raw)
        except ValueError:
            raise InvalidModule(Code.BINDING_MISMATCH, "manifest is not JSON") from None
        if not isinstance(d, dict) or set(d) != {"schema", "module_digest", "declared_features"} \
                or d["schema"] != MANIFEST_SCHEMA:
            raise InvalidModule(Code.BINDING_MISMATCH, "manifest schema/fields invalid")
        f = d["declared_features"]
        if not isinstance(f, list) or not all(isinstance(x, str) for x in f) or len(f) > 64:
            raise InvalidModule(Code.BINDING_MISMATCH, "declared_features must be a list of strings")
        return CapabilityManifest(d["module_digest"], frozenset(f))

    def digest(self) -> str:
        return module_digest(canonical_json({"schema": MANIFEST_SCHEMA, "module_digest": self.module_digest,
                                             "declared_features": sorted(self.declared_features)}))


@dataclass(frozen=True)
class AdmissionTicket:
    module_digest: str
    profile: str
    engine: str
    epoch: int
    attestation: Attestation
    _bytes: bytes = field(repr=False)

    @property
    def module_bytes(self) -> bytes:
        return self._bytes


class Gate:
    def __init__(self, *, signer: Signer, verifier: Verifier, bundle: PolicyBundle | None = None,
                 host_contract: HostContract | None = None, limits: Limits = DEFAULT_LIMITS,
                 cache: ValidationCache | None = None, audit: AuditStream | None = None,
                 attestation_ttl: float = 3600.0, clock=time.time):
        self._lock = threading.Lock()
        self.signer, self.verifier, self.limits = signer, verifier, limits
        self.cache = cache if cache is not None else ValidationCache()
        self.audit = audit if audit is not None else AuditStream()
        self.ttl, self.clock = attestation_ttl, clock
        self.log = get_logger()
        self._activate(bundle if bundle is not None else default_bundle(), host_contract)

    # ---------------------------------------------------- M43 activation
    def _activate(self, bundle: PolicyBundle, contract: HostContract | None) -> None:
        contract = contract if contract is not None else default_contract(bundle.known_features)
        with self._lock:
            self.bundle, self.contract = bundle, contract
            self.metrics = Metrics(bundle.profiles)
            self.cache.bump_epoch()
        self.audit.emit("config.activated", bundle_revision=bundle.revision, epoch=bundle.epoch,
                        host_contract_revision=contract.revision, limits_revision=self.limits.revision())

    def activate(self, bundle: PolicyBundle, contract: HostContract | None = None) -> None:
        """Atomically swap policy.  Epochs must strictly increase (anti-rollback)."""
        if bundle.epoch <= self.bundle.epoch:
            self.audit.emit("config.rejected", reason="non-increasing epoch", epoch=bundle.epoch)
            raise InvalidModule(Code.STALE_CONFIGURATION,
                                f"bundle epoch {bundle.epoch} <= active {self.bundle.epoch}")
        self._activate(bundle, contract)

    def health(self) -> dict[str, Any]:
        """M33 readiness: ready only if policy is loaded and a self-test passes."""
        checks = {"bundle_loaded": bool(self.bundle.profiles), "signer": True, "self_test": False}
        try:
            self._self_test()
            checks["self_test"] = True
        except Exception as exc:  # noqa: BLE001
            checks["self_test_error"] = type(exc).__name__
        ready = all(v for k, v in checks.items() if isinstance(v, bool))
        return {"schema": "PK_HEALTH/1", "status": "ready" if ready else "degraded", "checks": checks,
                "bundle_revision": self.bundle.revision, "epoch": self.bundle.epoch,
                "validator": f"{VALIDATOR_ID}/{VALIDATOR_VERSION}"}

    def _self_test(self) -> None:
        empty = b"\x00asm\x01\x00\x00\x00"
        validate_module(empty, self.limits)
        try:
            validate_module(b"\x00asm\x02\x00\x00\x00", self.limits)
        except InvalidModule:
            return
        raise RuntimeError("self-test: bad version accepted")

    # ---------------------------------------------------- validation
    def validate(self, data: bytes, *, profile: str, engine: str,
                 manifest: CapabilityManifest | None = None,
                 traceparent: str | None = None) -> dict[str, Any]:
        """Validate raw bytes; returns a verdict dict.  ``outcome`` is
        ``accept`` (with a signed ``attestation``) or ``reject``/``refuse``/``error``."""
        t0 = time.perf_counter()
        trace_id, parent = parse_traceparent(traceparent)
        span = new_span_id()
        snap = bytes(data)  # M11: private immutable snapshot; caller mutations cannot reach us
        digest = module_digest(snap)
        bundle, contract = self.bundle, self.contract  # consistent view for this request
        base = {"schema": "PK_MODULE_VALIDATION/2", "module_digest": digest, "profile": profile,
                "engine": engine, "bundle_revision": bundle.revision, "epoch": bundle.epoch,
                "validator": f"{VALIDATOR_ID}/{VALIDATOR_VERSION}", "trace_id": trace_id, "span_id": span}
        key = self.cache.key(d=digest, p=profile, b=bundle.revision, h=contract.revision, e=engine,
                             v=VALIDATOR_VERSION, l=self.limits.revision(),
                             m=manifest.digest() if manifest else None)
        cached = self.cache.get(key)
        if cached is not None:
            verdict = dict(cached, **{k: base[k] for k in ("trace_id", "span_id")})
            if verdict["outcome"] == "accept":  # never replay an old attestation: re-issue
                verdict["attestation"] = self._issue(verdict, bundle, contract).to_json()
            self.metrics.inc("validations_total", outcome=verdict["outcome"], profile=profile, cache="hit",
                             code=(verdict.get("failure") or {}).get("code", "OK"))
            return verdict
        try:
            verdict = self._validate_uncached(snap, digest, profile, engine, manifest, bundle, contract, base)
        except InvalidModule as exc:
            outcome = "error" if not exc.deterministic else (
                "refuse" if exc.code in (Code.FEATURE_REFUSED, Code.HOST_IMPORT_REFUSED,
                                         Code.ENGINE_UNSUPPORTED, Code.BINDING_MISMATCH) else "reject")
            verdict = dict(base, outcome=outcome, valid=False, failure=exc.to_dict())
            if exc.deterministic:
                self.cache.put(key, {k: v for k, v in verdict.items() if k not in ("trace_id", "span_id")})
            self.audit.emit("validation." + outcome, module_digest=digest, profile=profile,
                            code=exc.code.value, trace_id=trace_id)
            self.log.info("refused", extra={"fields": {"module_digest": digest, "code": exc.code.value,
                                                        "trace_id": trace_id}})
        else:
            self.cache.put(key, {k: v for k, v in verdict.items()
                                 if k not in ("trace_id", "span_id", "attestation")})
            self.audit.emit("validation.accept", module_digest=digest, profile=profile, trace_id=trace_id)
        ms = (time.perf_counter() - t0) * 1000
        code = (verdict.get("failure") or {}).get("code", "OK")
        self.metrics.inc("validations_total", outcome=verdict["outcome"], profile=profile, cache="miss", code=code)
        self.metrics.observe_ms(ms, profile=profile)
        return verdict

    def _validate_uncached(self, snap, digest, profile, engine, manifest, bundle, contract, base):
        prof = bundle.profiles.get(profile)
        if prof is None:
            raise InvalidModule(Code.FEATURE_REFUSED, f"unknown profile {profile!r}")
        eng = bundle.engines.get(engine)
        if eng is None or eng.status == "revoked":
            raise InvalidModule(Code.ENGINE_UNSUPPORTED, f"engine {engine!r} unknown or revoked")
        _, facts = validate_module(snap, self.limits)
        classes, implied = contract.classify(facts.imports)
        used = set(facts.features) | set(implied)
        unknown = used - bundle.known_features
        if unknown:
            raise InvalidModule(Code.FEATURE_REFUSED, f"unregistered features {sorted(unknown)}")
        # M04 binding: declarations may only widen what is requested, never hide what is used
        if manifest is not None:
            if not digests_equal(manifest.module_digest, digest):
                raise InvalidModule(Code.BINDING_MISMATCH, "manifest is bound to a different module digest")
            if manifest.declared_features - bundle.known_features:
                raise InvalidModule(Code.BINDING_MISMATCH, "manifest declares unregistered features")
            undeclared = used - manifest.declared_features
            if undeclared:
                raise InvalidModule(Code.BINDING_MISMATCH, f"bytes use undeclared features {sorted(undeclared)}")
            declared = set(manifest.declared_features)
        else:
            declared = set(used)
        outside = (used | declared) - prof.features
        if outside:
            raise InvalidModule(Code.FEATURE_REFUSED,
                                f"features outside profile {profile!r}: {sorted(outside)}")
        bad_cls = classes - prof.allowed_import_classes
        if bad_cls:
            raise InvalidModule(Code.HOST_IMPORT_REFUSED, f"import classes {sorted(bad_cls)} not allowed")
        if used - eng.features:
            raise InvalidModule(Code.ENGINE_UNSUPPORTED, f"engine lacks {sorted(used - eng.features)}")
        if prof.require_nan_canonicalization and facts.uses_float and not eng.nan_canonicalization:
            raise InvalidModule(Code.ENGINE_UNSUPPORTED, "deterministic profile needs NaN canonicalisation")
        deterministic = all(bundle.features[f].deterministic for f in used) and "nondeterministic" not in classes
        verdict = dict(base, outcome="accept", valid=True, used=sorted(used),
                       declared_unused=sorted(declared - used), deterministic=deterministic,
                       uses_float=facts.uses_float, import_classes=sorted(classes),
                       feature_evidence=[list(e) for e in facts.evidence],
                       instruction_count=facts.instruction_count, size_bytes=facts.size_bytes)
        verdict["attestation"] = self._issue(verdict, bundle, contract).to_json()
        return verdict

    def _issue(self, verdict, bundle, contract) -> Attestation:
        return issue(self.signer, ttl=self.ttl, clock=self.clock,
                     module_digest=verdict["module_digest"], profile=verdict["profile"],
                     bundle_revision=bundle.revision, epoch=bundle.epoch,
                     host_contract_revision=contract.revision, engine=verdict["engine"],
                     validator=f"{VALIDATOR_ID}/{VALIDATOR_VERSION}", limits_revision=self.limits.revision(),
                     verdict="accept", features=verdict["used"], deterministic=verdict["deterministic"])

    # ---------------------------------------------------- M10 / M11
    def admit(self, data: bytes, attestation_json: str, *, profile: str, engine: str) -> AdmissionTicket:
        snap = bytes(data)
        digest = module_digest(snap)
        try:
            env = json.loads(attestation_json)
            att = Attestation(env["payload"].encode("ascii"), env["signature"])
        except (ValueError, KeyError, TypeError, AttributeError):
            self.audit.emit("admission.refused", module_digest=digest, code="ATTESTATION_INVALID")
            raise InvalidModule(Code.ATTESTATION_INVALID, "attestation envelope malformed") from None
        try:
            verify(att, self.verifier, expect={
                "module_digest": digest, "profile": profile, "engine": engine,
                "bundle_revision": self.bundle.revision, "epoch": self.bundle.epoch,
                "host_contract_revision": self.contract.revision,
                "validator": f"{VALIDATOR_ID}/{VALIDATOR_VERSION}",
                "limits_revision": self.limits.revision(), "verdict": "accept"})
        except InvalidModule as exc:
            self.audit.emit("admission.refused", module_digest=digest, code=exc.code.value)
            raise
        self.audit.emit("admission.granted", module_digest=digest, profile=profile, engine=engine)
        return AdmissionTicket(digest, profile, engine, self.bundle.epoch, att, snap)

    def execute(self, ticket: AdmissionTicket, runner: Callable[[bytes], Any]) -> Any:
        """Hand the *attested* bytes to the engine.  Re-checks identity and epoch
        at the point of use (TOCTOU) - the runner never sees caller-owned buffers."""
        if not isinstance(ticket, AdmissionTicket):
            raise InvalidModule(Code.ATTESTATION_INVALID, "execution requires an AdmissionTicket")
        if ticket.epoch != self.bundle.epoch:
            self.audit.emit("execution.refused", module_digest=ticket.module_digest, code="STALE_CONFIGURATION")
            raise InvalidModule(Code.STALE_CONFIGURATION, "policy changed since admission; re-validate")
        if not digests_equal(module_digest(ticket.module_bytes), ticket.module_digest):
            self.audit.emit("execution.refused", module_digest=ticket.module_digest, code="DIGEST_MISMATCH")
            raise InvalidModule(Code.DIGEST_MISMATCH, "module bytes changed after admission")
        self.audit.emit("execution.started", module_digest=ticket.module_digest, engine=ticket.engine)
        return runner(ticket.module_bytes)
