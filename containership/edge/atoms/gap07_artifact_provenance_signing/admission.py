"""Production admission hook (v6) - the single fail-closed decision point.

``AdmissionController.admit(request)`` is the only function that may return
``outcome == "allow"``.  Outcomes: ``allow`` | ``deny`` | ``defer`` (transient
dependency problem) | ``error`` (defect).  Only ``allow`` is runnable; every
exception path maps to a non-runnable outcome with a stable code.

Pipeline: limiter -> readiness (trust, policy, trusted time) -> namespace ->
quarantine -> decision cache -> signatures (PK_SIGNATURE/3) -> attestations
(DSSE/in-toto/SLSA, SBOM) -> transparency inclusion -> GAP-13 policy (with
verified waivers) -> decision record (+audit, metrics, decision log).

Handoff: ``handoff(decision)`` re-hashes the stored bytes at the moment they
are given to the runtime and refuses if they differ (TOCTOU) or if the
decision is not a current ``allow`` for the same trust/policy state.

Association format ``PK_ARTIFACT_BUNDLE/1`` binds the artifact digest to its
signatures, attestations (DSSE), SBOM attestations, transparency evidence and
registry facts; its canonical digest is recorded in every decision.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from . import algorithms as algs
from . import dsse, sbom
from .canonical import canonical_bytes, exact_fields
from .controls import AdmissionLimiter, QuarantineService, ReplayCache
from .errors import ERROR_CODES, GapError, fail
from .policy import PolicyStore, evaluate, verify_waiver
from .registry import VerifiedContentStore
from .signing import verify_signature
from .store import AuthorityKey, TrustState, verify_config
from .telemetry import Health, Metrics, TraceContext
from .timesrc import TimeBudget
from .tlog import CheckpointCache, LogKey, entry_bytes, verify_inclusion_evidence

BUNDLE_SCHEMA = "PK_ARTIFACT_BUNDLE/1"
DECISION_SCHEMA = "PK_ADMISSION_DECISION/1"
QUARANTINE_ON = frozenset({"SIGNATURE_INVALID", "ATTESTATION_SUBJECT", "REGISTRY_DIGEST_MISMATCH", "TOCTOU", "CERT_REVOKED",
                           "TLOG_PROOF_INVALID", "ATTESTATION_CONFLICT", "IDENTITY_MISMATCH", "SBOM_POLICY"})
PREDICATES = frozenset({dsse.SLSA_V1, sbom.CYCLONEDX, sbom.SPDX})
MAX_SIGNATURES = 16
MAX_ATTESTATIONS = 16


def make_bundle(digest: str, kind: str, *, signatures: Sequence[Mapping[str, Any]] = (), attestations: Sequence[Mapping[str, Any]] = (),
                transparency: Sequence[Mapping[str, Any]] = (), registry: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {"schema": BUNDLE_SCHEMA, "artifact": {"digest": digest, "kind": kind}, "signatures": [dict(s) for s in signatures],
            "attestations": [dict(a) for a in attestations], "transparency": [dict(t) for t in transparency], "registry": dict(registry or {})}


def bundle_digest(bundle: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(bundle)).hexdigest()


@dataclass
class AdmissionConfig:
    time_budget: TimeBudget = field(default_factory=TimeBudget)
    decision_cache_ttl_s: int = 300
    max_checkpoint_age_s: int = 24 * 3600
    max_signature_age_s: int | None = None
    policy_domain: str = "default"
    profile: str = algs.PROFILE_PRODUCTION
    decision_log_path: str | None = None
    replay_cache_path: str | None = None   # durable one-time-token store (break-glass nonces)


class AdmissionController:
    def __init__(self, *, trust_state: TrustState, policy_store: PolicyStore, clock: Any, authorities: Mapping[str, AuthorityKey],
                 log_keys: Mapping[str, LogKey] | None = None, checkpoint_cache: CheckpointCache | None = None,
                 quarantine: QuarantineService | None = None, limiter: AdmissionLimiter | None = None, metrics: Metrics | None = None,
                 audit: Any = None, content_store: VerifiedContentStore | None = None, config: AdmissionConfig | None = None):
        self.trust_state = trust_state
        self.policy = policy_store
        self.clock = clock
        self._auth = dict(authorities)
        self._log_keys = dict(log_keys or {})
        self._cp_cache = checkpoint_cache
        self.quarantine = quarantine or QuarantineService()
        self.limiter = limiter or AdmissionLimiter()
        self.metrics = metrics or Metrics()
        self.audit = audit
        self.content = content_store
        self.cfg = config or AdmissionConfig()
        if self.cfg.profile == algs.PROFILE_PRODUCTION and getattr(clock, "production", True) is False:
            raise fail("TIME_UNTRUSTED", "test clock cannot back a production admission controller")
        self._cache: dict[tuple[str, ...], tuple[int, dict[str, Any]]] = {}
        self._cache_lock = threading.Lock()
        self._replay = ReplayCache(path=self.cfg.replay_cache_path)
        self.decisions: list[dict[str, Any]] = []
        self._dlock = threading.Lock()
        trust_state.subscribe(lambda _gen: self.invalidate("trust_generation_changed"))
        self.health = Health()
        self.health.register("trust", self._ready_trust)
        self.health.register("policy", self._ready_policy)
        self.health.register("time", lambda: self.clock.ready(self.cfg.time_budget))

    # readiness ----------------------------------------------------------
    def _ready_trust(self) -> tuple[bool, str]:
        try:
            self.trust_state.current().check_fresh(self.clock.now(self.cfg.time_budget).value)
            return True, "ok"
        except GapError as exc:
            return False, exc.code

    def _ready_policy(self) -> tuple[bool, str]:
        try:
            self.policy.current(self.clock.now(self.cfg.time_budget).value)
            return True, "ok"
        except GapError as exc:
            return False, exc.code

    def invalidate(self, reason: str) -> None:
        with self._cache_lock:
            n = len(self._cache)
            self._cache.clear()
        if self.audit is not None and n:
            self.audit.append("admission.cache_invalidated", {"reason": reason, "entries": n})

    # main entry ---------------------------------------------------------
    def admit(self, request: Mapping[str, Any]) -> dict[str, Any]:
        t0 = time.perf_counter()
        trace = TraceContext.from_traceparent(request.get("traceparent") if isinstance(request, Mapping) else None)
        rid = str(request.get("request_id") or uuid.uuid4()) if isinstance(request, Mapping) else str(uuid.uuid4())
        base = {"request_id": rid, "trace_id": trace.trace_id}
        try:
            with self.limiter.slot(str(request.get("tenant", "unknown"))[:64] if isinstance(request, Mapping) else "unknown"):
                decision = self._admit(request, base)
        except GapError as exc:
            decision = self._refusal(base, request, exc)
        except Exception as exc:  # noqa: BLE001 - defects must never become allows
            decision = self._refusal(base, request, fail("INTERNAL_ERROR", "unexpected verifier defect", error=type(exc).__name__))
        self.metrics.inc("gap07_admission_total", outcome=decision["outcome"], code=decision["code"], kind=str(decision.get("kind", "")))
        self.metrics.observe("gap07_admission_seconds", time.perf_counter() - t0, outcome=decision["outcome"])
        self._record(decision)
        return decision

    def _refusal(self, base: Mapping[str, Any], request: Any, exc: GapError) -> dict[str, Any]:
        transient = ERROR_CODES.get(exc.code, ("", False, ""))[1]
        outcome = "error" if exc.code == "INTERNAL_ERROR" else "defer" if transient else "deny"
        req = request if isinstance(request, Mapping) else {}
        d = {"schema": DECISION_SCHEMA, **base, "outcome": outcome, "runnable": False, "code": exc.code, "reason": str(exc)[:512],
             "details": _safe(exc.details), "digest": str(req.get("digest", ""))[:200], "kind": str(req.get("kind", ""))[:64]}
        if outcome == "deny" and exc.code in QUARANTINE_ON and isinstance(req.get("digest"), str):
            try:
                self.quarantine.quarantine(req["digest"], exc.code, now=self._now_or_zero(), evidence={"request_id": base["request_id"]})
                d["quarantined"] = True
            except GapError:
                pass
        return d

    def _now_or_zero(self) -> int:
        try:
            return self.clock.now(self.cfg.time_budget).value
        except GapError:
            return 0

    def _admit(self, request: Mapping[str, Any], base: Mapping[str, Any]) -> dict[str, Any]:
        req = exact_fields(request, {"digest", "kind", "tenant", "site", "environment", "bundle"},
                           {"request_id", "traceparent", "workload", "waivers", "break_glass"}, what="admission request")
        digest = req["digest"]
        if not isinstance(digest, str) or not digest.startswith("sha256:") or len(digest) != 71:
            raise fail("MUTABLE_REFERENCE", "admission requires a sha256 content digest")
        hexd = digest.split(":", 1)[1]
        kind = req["kind"]
        now_r = self.clock.now(self.cfg.time_budget)
        now = now_r.value
        try:
            trust = self.trust_state.current()
        except GapError as exc:
            raise fail("NOT_READY", "trust not loaded", dependency="trust") from exc
        trust.check_fresh(now)
        policy = self.policy.current(now)
        ns = trust.namespace
        if policy.tenant not in ("*", ns.tenant):
            raise fail("POLICY_INVALID", "active policy bundle is scoped to another tenant", bundle_tenant=policy.tenant)
        if (req["tenant"], req["site"], req["environment"]) != (ns.tenant, ns.site, ns.environment):
            raise fail("TENANT_MISMATCH", "request namespace differs from this verifier's trust namespace")
        if req.get("break_glass") is not None:
            return self._break_glass(req, base, trust, policy, now_r)
        self.quarantine.check(digest, now=now)
        bundle = exact_fields(req["bundle"], {"schema", "artifact", "signatures", "attestations", "transparency", "registry"}, what="artifact bundle")
        if bundle["schema"] != BUNDLE_SCHEMA:
            raise fail("ENVELOPE_VERSION_UNSUPPORTED", "unsupported artifact bundle schema")
        art = exact_fields(bundle["artifact"], {"digest", "kind"}, what="bundle artifact")
        if art["digest"] != digest or art["kind"] != kind:
            raise fail("ATTESTATION_SUBJECT", "bundle is associated with a different artifact")
        bdg = bundle_digest(bundle)
        key = (digest, kind, trust.digest, policy.digest, bdg, canonical_bytes(req.get("waivers") or []).hex())
        with self._cache_lock:
            hit = self._cache.get(key)
        if hit is not None and now <= hit[0]:
            return {**hit[1], **base, "cache_hit": True}

        if not isinstance(bundle["signatures"], list) or len(bundle["signatures"]) > MAX_SIGNATURES:
            raise fail("INPUT_TOO_LARGE", "too many signatures")
        if not bundle["signatures"]:
            raise fail("UNSIGNED", "artifact bundle carries no signature")
        sig_ev, sig_err = [], []
        for env in bundle["signatures"]:
            try:
                sig_ev.append(verify_signature(env, digest_hex=hexd, kind=kind, trust=trust, now=now, policy_domain=self.cfg.policy_domain,
                                               max_age_s=self.cfg.max_signature_age_s, profile=self.cfg.profile))
            except GapError as exc:
                sig_err.append(exc)
        if not sig_ev:
            raise sig_err[0]

        atts, sbom_facts = [], None
        if not isinstance(bundle["attestations"], list) or len(bundle["attestations"]) > MAX_ATTESTATIONS:
            raise fail("INPUT_TOO_LARGE", "too many attestations")
        verified_atts = []
        for a in bundle["attestations"]:
            va = dsse.verify_envelope(a, artifact_digest=hexd, trust=trust, now=now,
                                      policy=dsse.AttestationPolicy(predicate_types=PREDICATES, require_resolved_dependencies=True),
                                      profile=self.cfg.profile)
            verified_atts.append(va)
            atts.append(va.evidence())
            if va.predicate_type in (sbom.CYCLONEDX, sbom.SPDX):
                if sbom_facts is not None:
                    raise fail("ATTESTATION_CONFLICT", "multiple SBOMs for one artifact")
                sbom_facts = sbom.facts_from_predicate(va.predicate_type, va.predicate)
        dsse.check_no_conflicts(verified_atts)

        tlog_ev = []
        env_digests = {e["envelope_digest"] for e in sig_ev}
        for t in bundle["transparency"] if isinstance(bundle["transparency"], list) else []:
            t = exact_fields(t, {"envelope_digest", "evidence"}, {"consistency"}, what="transparency evidence")
            if t["envelope_digest"] not in env_digests:
                raise fail("TLOG_ENTRY_MISMATCH", "transparency entry does not bind a verified signature envelope")
            ev = verify_inclusion_evidence(t["evidence"], entry=entry_bytes(kind, hexd, t["envelope_digest"]), log_keys=self._log_keys,
                                           now=now, max_checkpoint_age_s=self.cfg.max_checkpoint_age_s, profile=self.cfg.profile)
            if self._cp_cache is not None:
                self._check_view(t["evidence"]["checkpoint"], t.get("consistency"))
            tlog_ev.append(ev)

        waivers = [verify_waiver(w, self._auth, now=now, digest=digest, tenant=ns.tenant, environment=ns.environment)
                   for w in (req.get("waivers") or [])]
        facts = {"tenant": ns.tenant, "environment": ns.environment, "kind": kind, "now": now, "signatures": sig_ev,
                 "attestations": atts, "transparency": tlog_ev, "sbom": sbom_facts}
        pd = evaluate(policy, facts, waivers=waivers)
        if not pd["allow"]:
            raise fail(pd["reason_code"], "policy refused admission", rule_id=pd["rule_id"], bundle_digest=pd["bundle_digest"])
        decision = {"schema": DECISION_SCHEMA, **base, "outcome": "allow", "runnable": True, "code": "ALLOW", "digest": digest, "kind": kind,
                    "namespace": ns.as_dict(), "trust_generation": trust.generation, "trust_digest": trust.digest,
                    "policy": {k: pd[k] for k in ("bundle_id", "bundle_version", "bundle_digest", "rule_id", "waivers_applied", "waiver_ids")},
                    "policy_trace": pd["trace"], "time": now_r.evidence(), "signatures": sig_ev, "attestations": atts, "transparency": tlog_ev,
                    "sbom": sbom_facts, "bundle_digest": bdg, "registry": bundle["registry"], "workload": req.get("workload"), "decided_at": now}
        decision["decision_digest"] = hashlib.sha256(canonical_bytes(_safe(decision))).hexdigest()
        # a cached allow is valid only until the earliest time-bound fact it relied on expires
        bounds = [now + self.cfg.decision_cache_ttl_s, policy.expires, trust.issued_at + trust.max_staleness_s]
        rule = next((r for r in policy.rules if r["rule_id"] == pd["rule_id"]), {"require": {}})
        for s in sig_ev:
            for age in (self.cfg.max_signature_age_s, rule["require"].get("max_signature_age_s")):
                if age is not None:
                    bounds.append(s["issued_at"] + int(age))
            leaf = trust._index["by_kid"].get(s["kid"])
            if leaf is not None:
                bounds.append(leaf["not_after"])
        bounds += [int(w["expires"]) for w in waivers]
        bounds += [int(t["evidence"]["checkpoint"]["timestamp"]) + self.cfg.max_checkpoint_age_s
                   for t in (bundle["transparency"] if isinstance(bundle["transparency"], list) else [])]
        decision["cache_valid_until"] = min(bounds)
        with self._cache_lock:
            self._cache[key] = (min(bounds), decision)
        return decision

    def _check_view(self, cp: Mapping[str, Any], consistency: Any) -> None:
        """Split-view defence: the evidence checkpoint must be consistent with the trusted head."""
        from .canonical import b64u_decode
        from .tlog import verify_consistency
        trusted = self._cp_cache.trusted(cp["origin"])  # type: ignore[union-attr]
        if trusted is None or cp["size"] > trusted["size"]:
            self._cp_cache.observe(cp, consistency)  # type: ignore[union-attr]  (consistency proof required when trusted exists)
            return
        if cp["size"] == trusted["size"]:
            if cp["root"] != trusted["root"]:
                raise fail("TLOG_ROLLBACK", "checkpoint root differs from trusted head at equal size (split view)")
            return
        proof = [b64u_decode(p) for p in (consistency or [])]
        if not verify_consistency(cp["size"], trusted["size"], b64u_decode(cp["root"]), b64u_decode(trusted["root"]), proof):
            raise fail("TLOG_ROLLBACK", "older checkpoint is not provably a prefix of the trusted head (split view)")

    def _break_glass(self, req: Mapping[str, Any], base: Mapping[str, Any], trust: Any, policy: Any, now_r: Any) -> dict[str, Any]:
        now = now_r.value
        if self.cfg.profile == algs.PROFILE_PRODUCTION and not self.cfg.replay_cache_path:
            raise fail("BREAK_GLASS_INVALID", "break-glass requires a durable nonce store (AdmissionConfig.replay_cache_path)")
        body = verify_config(req["break_glass"], self._auth, expect_type="break-glass", profile=self.cfg.profile)
        b = exact_fields(body, {"schema", "id", "digest", "kind", "tenant", "site", "environment", "approvers", "reason", "issued_at", "expires",
                                "nonce", "override_quarantine"}, what="break-glass")
        ns = trust.namespace
        if (b["schema"] != "PK_BREAK_GLASS/1" or b["digest"] != req["digest"] or b["kind"] != req["kind"]
                or (b["tenant"], b["site"], b["environment"]) != (ns.tenant, ns.site, ns.environment)):
            raise fail("BREAK_GLASS_INVALID", "break-glass scope (digest/kind/tenant/site/environment) does not match request")
        if b["override_quarantine"] is not True:
            self.quarantine.check(req["digest"], now=now)
        if len(set(b["approvers"])) < 2 or not b["issued_at"] <= now <= b["expires"] or b["expires"] - b["issued_at"] > 86400:
            raise fail("BREAK_GLASS_INVALID", "break-glass needs 2 approvers and <=24h validity")
        self._replay.use(b["nonce"], expires=b["expires"], now=now)
        if self.audit is not None:
            self.audit.append("admission.break_glass", {"id": b["id"], "digest": b["digest"], "approvers": sorted(set(b["approvers"])),
                                                        "override_quarantine": b["override_quarantine"],
                                                        "reason": b["reason"][:256], "post_event_review": "required"})
        d = {"schema": DECISION_SCHEMA, **base, "outcome": "allow", "runnable": True, "code": "BREAK_GLASS", "digest": req["digest"],
             "kind": req["kind"], "namespace": trust.namespace.as_dict(), "trust_generation": trust.generation, "trust_digest": trust.digest,
             "policy": {"bundle_digest": policy.digest, "bundle_version": policy.version}, "break_glass_id": b["id"], "time": now_r.evidence(),
             "decided_at": now, "post_event_review_required": True}
        d["decision_digest"] = hashlib.sha256(canonical_bytes(_safe(d))).hexdigest()
        return d

    # record / handoff ---------------------------------------------------
    def _record(self, d: Mapping[str, Any]) -> None:
        rec = _safe(d)
        with self._dlock:
            self.decisions.append(rec)
            if self.cfg.decision_log_path:
                with open(self.cfg.decision_log_path, "ab") as fh:
                    fh.write(canonical_bytes(rec) + b"\n")
        if self.audit is not None:
            self.audit.append("admission.decision", {"request_id": d["request_id"], "outcome": d["outcome"], "code": d["code"],
                                                     "digest": d.get("digest"), "trust_generation": d.get("trust_generation"),
                                                     "decision_digest": d.get("decision_digest")})

    def handoff(self, decision: Mapping[str, Any]) -> bytes:
        if decision.get("outcome") != "allow" or not decision.get("runnable"):
            raise fail("POLICY_DENY", "decision is not runnable")
        trust = self.trust_state.current()
        if decision.get("trust_digest") != trust.digest:
            raise fail("TRUST_STALE", "decision was made under a superseded trust generation; re-admit")
        self.quarantine.check(decision["digest"], now=self._now_or_zero())
        if self.content is None:
            raise fail("NOT_READY", "no verified content store configured")
        return self.content.open_verified(decision["digest"])


def _safe(obj: Any) -> Any:
    return json.loads(json.dumps(obj, default=str, sort_keys=True))
