"""GAP-15 production certification service facade.

Wires every production component into one path so no alternate supported
API can bypass a control (EXIT-01 intent): ingestion boundary (10),
admission integration (30), explain (28), conflict workflow (31), lifecycle
(20), revocation / quarantine (13), emergency disable (46), readiness (14).

Every public operation: authenticate -> authorize -> validate -> decide ->
commit atomically (ledger + matrix + revision + audit) -> metrics/log/trace.
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from . import schemas
from .attestation import AttestationPolicy, verify_quote
from .authn import AuthError, Authenticator, Principal
from .authz import Authorizer, AuthzError
from .canonical import CanonicalError, digest, parse, sha256_hex
from .capacity import CapacityError, ConcurrencyGate, LIMITS, RateLimiter
from .features import FeatureEvidence, FeatureGraph, aggregate, subset_decision
from .observability import Logger, Metrics, Tracer, hash_id
from .partition import Partition, PartitionError
from .policy import PolicySet, WaiverRegistry, evaluate
from .provenance import ArtifactId, ProvenanceError, TagResolver, verify_provenance, DIGEST_RE
from .signing import KeyProvider, TrustStore, verify_payload
from .state import (CERTIFIED, CertKey, CertPolicy, StateError, certify as pure_certify)
from .store import Conflict, Store, StoreError
from .timepolicy import TimeError_, TrustedClock

SERVICE_VERSION = "4.3.0"
API_VERSION = "1"
CATEGORIES = {"validation", "authn", "authz", "conflict", "rate-limit", "dependency", "timeout", "internal", "duplicate"}


class ServiceError(Exception):
    def __init__(self, category: str, code: str, message: str = "", *, retry_after: float = 0.0, http: int = 400) -> None:
        super().__init__(f"{category}/{code}: {message}")
        assert category in CATEGORIES
        self.category, self.code, self.message, self.retry_after, self.http = category, code, message, retry_after, http

    def as_dict(self) -> dict:
        d = {"error": {"category": self.category, "code": self.code, "message": self.message[:300]}}
        if self.retry_after:
            d["error"]["retry_after_s"] = round(self.retry_after, 3)
        return d


_HTTP = {"validation": 400, "authn": 401, "authz": 403, "conflict": 409, "rate-limit": 429, "dependency": 503,
         "timeout": 504, "internal": 500, "duplicate": 200}


def _err(category: str, code: str, message: str = "", **kw) -> ServiceError:
    return ServiceError(category, code, message, http=_HTTP[category], **kw)


@dataclass
class ServiceConfig:
    environment: str
    partitions: frozenset
    cert_policy: CertPolicy = field(default_factory=CertPolicy)
    conflict_quarantine: bool = True
    bulk_revocation_max_fraction: float = 0.25
    require_sbom: bool = True
    production: bool = False


class CertificationService:
    def __init__(self, *, config: ServiceConfig, store: Store, trust: TrustStore, authn: Authenticator,
                 authz: Authorizer, clock: TrustedClock, key_provider: KeyProvider, service_key_id: str,
                 policy: PolicySet, attestation_policy: AttestationPolicy, tags: Optional[TagResolver] = None,
                 waivers: Optional[WaiverRegistry] = None, limiter: Optional[RateLimiter] = None,
                 feature_graph: Optional[FeatureGraph] = None) -> None:
        if config.production and not key_provider.production_grade:
            raise _err("dependency", "E_KEY_PROVIDER_NOT_PRODUCTION", "production mode requires an HSM/KMS key provider")
        self.cfg, self.store, self.trust, self.authn, self.authz = config, store, trust, authn, authz
        self.clock, self.keys, self.service_key_id, self.policy = clock, key_provider, service_key_id, policy
        self.att_policy, self.tags = attestation_policy, tags or TagResolver()
        self.waivers = waivers or WaiverRegistry()
        self.limiter = limiter or RateLimiter(per_key_rate=50, per_key_burst=100, global_rate=2000, global_burst=4000)
        self.features = feature_graph or FeatureGraph()
        self.metrics, self.tracer = Metrics(), Tracer(sample_ratio=0.05)
        self.log = Logger("gap15", SERVICE_VERSION)
        self.gate = ConcurrencyGate()
        self._nonces: dict = {}
        self._lock = threading.RLock()
        self.decisions: dict = {}
        self.admissions: dict = {}
        self.conflict_cases: dict = {}
        self.feature_evidence: dict = {}
        self.emergency: dict = {}  # scope -> {"until", "incident", "actor"}
        self.shutting_down = False
        self.in_flight = 0
        self._rehydrate()
        self._refresh_revisions()

    def _rehydrate(self) -> None:
        """Durable state that lives outside the matrix is rebuilt from ledger/audit on start."""
        for cases in self.store.state.conflicts.values():
            for case_id, ev in cases.items():
                self.conflict_cases[case_id] = dict(ev)
        for a in self.store.audit_events():
            if a.get("action") == "emergency.disable":
                d = a["detail"]
                self.emergency[d["scope"]] = {"until": d["until"], "incident": d["incident"],
                                              "actor": (a.get("actor") or {}).get("subject"), "reason": "rehydrated"}

    # ------------------------------------------------------------ utilities
    def _refresh_revisions(self) -> None:
        self.log.revisions = {"schema": schemas.SCHEMA_SET_VERSION, "policy": self.policy.revision,
                              "authz": self.authz.bundle.revision, "matrix": self.store.revision,
                              "truststore": self.trust.revision}

    def _now(self) -> int:
        try:
            return self.clock.require().wall
        except TimeError_ as exc:
            raise _err("dependency", exc.code, "trusted time unavailable") from exc

    def _principal(self, token: str, now: int, **kw) -> Principal:
        try:
            return self.authn.authenticate(token, now=now, **kw)
        except AuthError as exc:
            self.metrics.inc("gap15_evidence_rejections_total", category="auth")
            raise _err("authn", exc.code) from None

    def _authorize(self, p: Principal, action: str, partition: str, **kw):
        try:
            return self.authz.authorize(p, action, partition, **kw)
        except AuthzError as exc:
            self._audit_only("authz.denied", p, partition, {"action": action, "code": exc.code})
            raise _err("authz", exc.code, action) from None

    def _audit_event(self, action: str, p: Optional[Principal], partition: str, detail: dict, *, result: str = "ok",
                     classification: str = "security", trace_id: Optional[str] = None) -> dict:
        now = self.clock.now()
        body = {"action": action, "actor": p.as_audit() if p else None, "partition": partition, "detail": detail,
                "result": result, "classification": classification, "at": now.wall,
                "time_confidence": now.confidence, "trace_id": trace_id, "matrix_revision": self.store.revision}
        body["event_id"] = "au-" + digest({**body, "n": os.urandom(8).hex()})[7:31]
        return body

    def _audit_only(self, action: str, p: Optional[Principal], partition: str, detail: dict, result: str = "rejected") -> None:
        self.store.audit_only([self._audit_event(action, p, partition, detail, result=result)])

    def issue_nonce(self, partition: str) -> str:
        n = os.urandom(16).hex()
        with self._lock:
            self._nonces[n] = (partition, time.monotonic())
            if len(self._nonces) > 100000:
                self._nonces.pop(next(iter(self._nonces)))
        return n

    def _consume_nonce(self, nonce: str, partition: str) -> None:
        with self._lock:
            got = self._nonces.pop(nonce, None)
        if got is None or got[0] != partition or time.monotonic() - got[1] > self.att_policy.freshness_s:
            raise _err("validation", "E_ATT_NONCE_UNKNOWN", "attestation nonce was not issued for this session")

    def _emergency_blocked(self, scope: str, now: int) -> Optional[dict]:
        e = self.emergency.get(scope)
        if e and now < e["until"]:
            return e
        return None

    # --------------------------------------------------------------- ingest
    def _validate_submission(self, p: Principal, raw: bytes, now: int) -> tuple:
        try:
            env = parse(raw, max_bytes=LIMITS["max_body_bytes"])
            schemas.validate("GAP15_EVIDENCE/1", env)
        except (CanonicalError, schemas.SchemaError) as exc:
            self.metrics.inc("gap15_evidence_rejections_total", category="schema")
            raise _err("validation", exc.code, str(exc)) from None
        try:
            part = Partition.parse(env["partition"])
        except PartitionError as exc:
            raise _err("validation", exc.code) from None
        self._authorize(p, "evidence.submit", part.key)
        if part.key not in self.cfg.partitions:
            raise _err("authz", "E_PARTITION_UNKNOWN", "partition not served here")
        if env["producer"] != p.subject:
            raise _err("authz", "E_PRODUCER_MISMATCH", "producer must be the authenticated principal")
        if env["observed_at"] > now + 5:
            self.metrics.inc("gap15_evidence_rejections_total", category="time")
            raise _err("validation", "E_TIME_FUTURE_EVIDENCE", "observed_at is in the future")
        body = {k: v for k, v in env.items() if k != "signature"}
        sig = verify_payload(self.trust, env["signature"], message_type="evidence", environment=part.environment,
                             payload=body, required_scope=f"evidence:submit:{part.environment}", evaluated_at=now + 5)
        if not sig.ok or sig.signer != env["producer"]:
            self.metrics.inc("gap15_evidence_rejections_total", category="signature")
            raise _err("validation", sig.code if not sig.ok else "E_SIG_SIGNER_NOT_PRODUCER")
        try:
            art = ArtifactId(env["artifact"]["digest"], env["artifact"]["media_type"])
        except ProvenanceError as exc:
            raise _err("validation", exc.code) from None
        existing = self.store.find_idempotent(part.key, f"{env['producer']}|{env['producer_event_id']}")
        if existing is not None and existing["payload_digest"] == env["signature"]["payload_digest"]:
            # exact authenticated retry: idempotent even though its attestation nonce was already consumed
            return {"duplicate_of": existing}, part
        prov = verify_provenance(self.trust, art, env["provenance"]["statement"], env["provenance"]["signature"],
                                 sbom=env["provenance"].get("sbom"), environment=part.environment,
                                 require_sbom=self.cfg.require_sbom)
        if not prov.ok:
            self.metrics.inc("gap15_evidence_rejections_total", category="provenance")
            raise _err("validation", prov.code)
        self._consume_nonce(env["attestation"]["nonce"], part.key)
        att = verify_quote(self.trust, env["attestation"]["quote"], env["attestation"]["signature"],
                           nonce=env["attestation"]["nonce"], now=now, policy=self.att_policy, environment=part.environment)
        if not att.ok:
            self.metrics.inc("gap15_evidence_rejections_total", category="attestation")
            raise _err("validation", att.code)
        runtime = f"{att.profile.get('runtime.name')}@{att.profile.get('runtime.version')}"
        if runtime != env["runtime"]:
            raise _err("validation", "E_RUNTIME_NOT_ATTESTED", "claimed runtime differs from attested runtime")
        event = {
            "event_type": "evidence", "partition": part.key, "artifact_digest": art.digest, "runtime": runtime,
            "profile_id": att.profile.identity(), "result": env["result"], "observed_at": env["observed_at"],
            "failure_class": env.get("failure_class"), "producer": env["producer"],
            "producer_event_id": env["producer_event_id"], "signer_key_id": sig.key_id,
            "signed_at": env["signature"]["signed_at"], "ingested_at": now, "test_suite": env["test_suite"],
            "payload_digest": env["signature"]["payload_digest"], "provenance": prov.as_dict(),
            "attestation": att.summary(), "trust_store_revision": sig.trust_store_revision,
            "idem_key": f"{env['producer']}|{env['producer_event_id']}", "schema_version": "GAP15_EVIDENCE/1",
            "time_confidence": env.get("time_confidence", "high"), "supersedes": env.get("supersedes"),
            "features": env.get("features", []),
        }
        if event["failure_class"] is None:
            del event["failure_class"]
        event["evidence_id"] = event["event_id"] = "ev-" + digest(event)[7:31]
        return event, part

    def ingest(self, token: str, raw: bytes, *, traceparent: Optional[str] = None, channel_binding: Optional[str] = None) -> dict:
        return self.ingest_batch(token, [raw], traceparent=traceparent, channel_binding=channel_binding)["items"][0]

    def ingest_batch(self, token: str, raws: list, *, traceparent: Optional[str] = None,
                     channel_binding: Optional[str] = None, expected_revision: Optional[int] = None) -> dict:
        """All-or-nothing batch with per-item status (MC-10-09)."""
        span = self.tracer.start("ingest", traceparent=traceparent)
        t0 = time.perf_counter()
        try:
            with self.gate:
                if self.shutting_down:
                    raise _err("dependency", "E_SHUTTING_DOWN", retry_after=1.0)
                if not isinstance(raws, list) or not 1 <= len(raws) <= LIMITS["max_batch_items"]:
                    raise _err("validation", "E_BATCH_SIZE")
                if sum(len(r) for r in raws) > LIMITS["max_body_bytes"] * 4:
                    raise _err("validation", "E_PAYLOAD_TOO_LARGE")
                now = self._now()
                p = self._principal(token, now, channel_binding=channel_binding)
                try:
                    self.limiter.check(f"p:{p.subject}", cost=len(raws), op="ingest")
                except CapacityError as exc:
                    self.metrics.inc("gap15_evidence_rejections_total", category="capacity")
                    raise _err("rate-limit", exc.code, retry_after=exc.retry_after) from None
                if self._emergency_blocked("ingestion", now):
                    raise _err("dependency", "E_EMERGENCY_INGESTION_DISABLED")
                events, items, audits, conflicts = [], [], [], []
                for i, raw in enumerate(raws):
                    try:
                        ev, part = self._validate_submission(p, raw, now)
                    except ServiceError as exc:
                        self._audit_only("evidence.rejected", p, "", {"index": i, "code": exc.code,
                                         "payload_sha256": sha256_hex(raw if isinstance(raw, bytes) else b""),
                                         "payload_bytes": len(raw) if isinstance(raw, bytes) else 0})
                        raise
                    if "duplicate_of" in ev:
                        items.append({"index": i, "status": "duplicate", "evidence_id": ev["duplicate_of"]["evidence_id"]})
                        continue
                    existing = self.store.find_idempotent(ev["partition"], ev["idem_key"])
                    if existing is not None:
                        conflicts.append(self._conflict_event("same-producer-event-different-payload", ev, existing, now))
                        items.append({"index": i, "status": "conflict", "evidence_id": ev["evidence_id"]})
                        continue
                    k = CertKey(ev["partition"], ev["artifact_digest"], ev["runtime"], ev["profile_id"])
                    prev = self.store.state.evidence.get(k)
                    if prev is not None and prev["result"] != ev["result"] and prev["producer"] != ev["producer"]:
                        conflicts.append(self._conflict_event("trusted-producers-disagree", ev, prev, now))
                    events.append(ev)
                    self._record_features(ev)
                    items.append({"index": i, "status": "accepted", "evidence_id": ev["evidence_id"],
                                  "profile_id": ev["profile_id"]})
                    audits.append(self._audit_event("evidence.accepted", p, ev["partition"],
                                                    {"evidence_id": ev["evidence_id"], "result": ev["result"]},
                                                    trace_id=span.trace_id))
                if conflicts and self.cfg.conflict_quarantine:
                    for c in conflicts:
                        audits.append(self._audit_event("conflict.opened", p, c["partition"], {"case_id": c["case_id"]}))
                all_events = [e for e in events] + conflicts
                if all_events:
                    try:
                        res = self.store.commit(all_events, audit=audits, expected_revision=expected_revision, recorded_at=now)
                    except Conflict as exc:
                        self.metrics.inc("gap15_revision_conflicts_total")
                        self.log.log("warn", "revision.conflict", trace=span, subject=p.subject, operation="ingest",
                                     expected_revision=exc.expected, current_revision=exc.current,
                                     keys=[hash_id(e["idem_key"]) for e in events], resolution="caller-retry")
                        self._audit_only("revision.conflict", p, events[0]["partition"] if events else "",
                                         {"expected": exc.expected, "current": exc.current})
                        raise _err("conflict", "E_REVISION_CONFLICT", str(exc)) from None
                    except StateError as exc:
                        raise _err("conflict", exc.code, str(exc)) from None
                    for c in conflicts:
                        self.conflict_cases[c["case_id"]] = dict(c)
                    self.metrics.inc("gap15_evidence_accepted_total", len(events))
                else:
                    res = None
                self._refresh_revisions()
                self.metrics.inc("gap15_requests_total", op="ingest", outcome="ok")
                self.log.log("info", "evidence.ingested", trace=span, accepted=len(events), batch=len(raws))
                return {"status": "committed" if res else "no-op", "revision": self.store.revision, "items": items,
                        "trace_id": span.trace_id}
        except CapacityError as exc:
            self.tracer.finish(span, status="error")
            raise _err("rate-limit", exc.code, retry_after=exc.retry_after) from None
        except ServiceError:
            self.metrics.inc("gap15_requests_total", op="ingest", outcome="error")
            self.tracer.finish(span, status="error", security=True)
            raise
        finally:
            self.metrics.observe("gap15_request_seconds", time.perf_counter() - t0, op="ingest")
            if span.end is None:
                self.tracer.finish(span)

    def _record_features(self, ev: dict) -> None:
        k = CertKey(ev["partition"], ev["artifact_digest"], ev["runtime"], ev["profile_id"])
        for f in ev.get("features", []):
            self.feature_evidence.setdefault(k, []).append(
                FeatureEvidence(f["feature"], f["result"], ev["evidence_id"], ev["observed_at"]))

    def _conflict_event(self, ctype: str, new: dict, old: dict, now: int) -> dict:
        case_id = "case-" + digest([new["evidence_id"], old.get("evidence_id"), ctype])[7:23]
        return {"event_type": "conflict", "event_id": "cf-" + case_id, "case_id": case_id, "ctype": ctype,
                "partition": new["partition"], "artifact_digest": new["artifact_digest"], "runtime": new["runtime"],
                "profile_id": new["profile_id"], "evidence": [old.get("evidence_id"), new["evidence_id"]],
                "status": "open", "severity": "high", "opened_at": now, "owner": None, "sla_s": 86400}

    # ------------------------------------------------------------- certify
    def certify(self, token: str, key: CertKey, *, new_admission: bool = True, required_features: Optional[set] = None,
                traceparent: Optional[str] = None) -> dict:
        span = self.tracer.start("certify", traceparent=traceparent)
        now = self._now()
        p = self._principal(token, now)
        self._authorize(p, "certify", key.partition)
        d = self._decide(key, now, new_admission=new_admission, required_features=required_features)
        self.tracer.finish(span)
        return d

    def certify_request(self, token: str, doc: dict, *, traceparent: Optional[str] = None) -> dict:
        """Authenticate first, then validate the request shape (MC-10-02 ordering)."""
        now = self._now()
        p = self._principal(token, now)
        try:
            key = CertKey(**doc["key"])
        except (TypeError, KeyError):
            raise _err("validation", "E_KEY_SHAPE") from None
        self._authorize(p, "certify", key.partition)
        feats = set(doc["features"]) if isinstance(doc.get("features"), list) else None
        return self._decide(key, now, new_admission=doc.get("new_admission", True) is True, required_features=feats)

    def _decide(self, key: CertKey, now: int, *, new_admission: bool = True, required_features: Optional[set] = None) -> dict:
        v = self.store.certify(key, now, self.cfg.cert_policy, new_admission=new_admission)
        ctx = {"verdict": v["verdict"], "runtime": key.runtime, "partition": key.partition,
               "artifact_digest": key.artifact_digest, "profile_id": key.profile_id,
               "lifecycle": (v.get("lifecycle") or {}).get("state", "active")}
        pol = evaluate(self.policy, ctx, now, self.waivers)
        v["policy"] = {k: pol[k] for k in ("effect", "decided_by", "policy_revision", "policy_digest", "waivers")}
        v["trace"].append({"rule": "policy", "effect": pol["effect"], "decided_by": pol["decided_by"]})
        if v["deployable"] and pol["effect"] != "allow":
            v["deployable"] = False
            v["reason_code"], v["reason"] = "R_POLICY_DENIED", f"policy rule {pol['decided_by']} denies"
        if self._emergency_blocked(f"runtime:{key.runtime}", now) or self._emergency_blocked(f"artifact:{key.artifact_digest}", now):
            v["deployable"], v["reason_code"], v["reason"] = False, "R_EMERGENCY_DISABLED", "emergency disable in force"
        if required_features is not None:
            status = aggregate(self.feature_evidence.get(key, []), now=now, ttl_s=self.cfg.cert_policy.ttl_s)
            sub = subset_decision(set(required_features), self.features, status)
            v["feature_subset"] = sub
            if not sub["compatible"]:
                v["deployable"] = False
                v["reason_code"], v["reason"] = "R_FEATURES_UNCERTIFIED", f"required features not certified: {sub['blocked']}"
        v["decision_id"] = "dc-" + digest({k: v[k] for k in ("key", "ledger_seq", "evaluated_at", "verdict")} | {"n": os.urandom(4).hex()})[7:27]
        schemas.validate("PK_CERTIFICATION/1", {k: x for k, x in v.items()})
        self.decisions[v["decision_id"]] = v
        self.metrics.inc("gap15_certifications_total", verdict=v["verdict"])
        return v

    # -------------------------------------------------------------- explain
    def explain(self, token: str, decision_id: str, *, reevaluate: bool = False, page: int = 0, page_size: int = 50) -> dict:
        now = self._now()
        p = self._principal(token, now)
        d = self.decisions.get(decision_id)
        if d is None:
            raise _err("validation", "E_DECISION_UNKNOWN")
        self._authorize(p, "explain.read", d["key"]["partition"])
        key = CertKey(**d["key"])
        # historical explain replays the ledger at the recorded position (MC-28-05, MC-28-08)
        replayed = self.store.reconstruct(key, d["evaluated_at"], d["ledger_seq"], self.cfg.cert_policy)
        consistent = replayed["verdict"] == d["verdict"]
        hist = d.get("evidence_history", [])
        page_size = max(1, min(page_size, 200))
        out = {"schema": "GAP15_EXPLAIN/1", "decision_id": decision_id, "verdict": d["verdict"],
               "reason_code": d["reason_code"], "reason": d["reason"], "remediation": REMEDIATION.get(d["reason_code"], "contact the service owner"),
               "matrix_revision": d["matrix_revision"], "ledger_seq": d["ledger_seq"], "policy": d.get("policy"),
               "lifecycle": d.get("lifecycle"), "evidence_id": d.get("evidence_id"), "evidence_age_s": d.get("age"),
               "trace": d["trace"], "replay_consistent": consistent,
               "evidence_history": hist[page * page_size:(page + 1) * page_size], "history_total": len(hist),
               "replacement_runtime": (d.get("lifecycle") or {}).get("replacement"),
               "open_conflicts": [c["case_id"] for c in self.conflict_cases.values()
                                  if c["status"] == "open" and c["partition"] == key.partition and c["runtime"] == key.runtime
                                  and c["artifact_digest"] == key.artifact_digest]}
        if reevaluate:
            self._authorize(p, "certify", key.partition)
            out["current"] = {k: v for k, v in self._decide(key, now).items() if k in ("verdict", "reason_code", "decision_id")}
        if not consistent:
            self.log.log("error", "explain.replay_mismatch", decision=decision_id)
        return out

    # ----------------------------------------------------------- lifecycle
    def lifecycle(self, token: str, *, partition: str, runtime: str, state: str, effective_at: int, reason: str,
                  source: str, replacement: Optional[str] = None, waiver_id: Optional[str] = None,
                  second_approver_token: Optional[str] = None, deadline: Optional[int] = None) -> dict:
        now = self._now()
        p = self._principal(token, now)
        action = "lifecycle.reactivate" if state == "reactivated-by-waiver" else "lifecycle.mutate"
        second = self._principal(second_approver_token, now) if second_approver_token else None
        self._authorize(p, action, partition, **({"second_approver": second} if action == "lifecycle.reactivate" else {}))
        if waiver_id is not None:
            w = self.waivers.current(waiver_id)
            if w is None or w.wtype != "lifecycle-reactivation" or not w.applies({"runtime": runtime, "partition": partition}, effective_at):
                raise _err("validation", "E_WAIVER_INVALID", "waiver does not cover this reactivation")
        ev = {"event_type": "lifecycle", "partition": partition, "runtime": runtime, "state": state,
              "effective_at": effective_at, "announced_at": now, "deadline": deadline, "reason": reason, "source": source,
              "approver": second.subject if second else p.subject, "replacement": replacement, "waiver_id": waiver_id,
              "policy_revision": self.policy.revision}
        ev["event_id"] = "lc-" + digest(ev)[7:31]
        try:
            res = self.store.commit([ev], audit=[self._audit_event(action, p, partition, {"runtime": runtime, "state": state,
                                                                                         "waiver_id": waiver_id})], recorded_at=now)
        except StateError as exc:
            raise _err("conflict", exc.code, str(exc)) from None
        self._refresh_revisions()
        return {"event_id": ev["event_id"], "revision": res.revision}

    def lifecycle_view(self, partition: str, now: int) -> dict:
        from .state import lifecycle_at
        rts = sorted({rt for (pt, rt) in self.store.state.lifecycle if pt in (partition, "*")})
        rows = []
        for rt in rts:
            e = lifecycle_at(self.store.state, partition, rt, now)
            if e:
                rows.append({"runtime": rt, "state": e["state"], "effective_at": e["effective_at"],
                             "replacement": e.get("replacement"), "reason": e.get("reason", ""), "waiver_id": e.get("waiver_id")})
        v = {"schema": "PK_RUNTIME_LIFECYCLE/1", "partition": partition, "revision": self.store.revision, "runtimes": rows}
        schemas.validate("PK_RUNTIME_LIFECYCLE/1", v)
        return v

    def upcoming_lifecycle(self, partition: str, now: int, horizon_s: int) -> list:
        out = []
        for (pt, rt), evs in self.store.state.lifecycle.items():
            if pt in (partition, "*"):
                for e in evs:
                    if now < e["effective_at"] <= now + horizon_s:
                        out.append({"runtime": rt, "state": e["state"], "effective_at": e["effective_at"],
                                    "replacement": e.get("replacement")})
        return sorted(out, key=lambda e: e["effective_at"])

    # ---------------------------------------------------------- revocation
    def revoke(self, token: str, *, subject_type: str, subject_id: str, partition: str, reason: str, severity: str,
               quarantine: bool = False, expires_at: Optional[int] = None, incident: Optional[str] = None) -> dict:
        now = self._now()
        p = self._principal(token, now)
        return self._revoke(p, now, subject_type=subject_type, subject_id=subject_id, partition=partition, reason=reason,
                            severity=severity, quarantine=quarantine, expires_at=expires_at, incident=incident)

    def _revoke(self, p: Principal, now: int, *, subject_type: str, subject_id: str, partition: str, reason: str,
                severity: str, quarantine: bool = False, expires_at: Optional[int] = None, incident: Optional[str] = None) -> dict:
        """Internal path for an already-authenticated principal (tokens are single-use)."""
        self._authorize(p, "quarantine.create" if quarantine else "revocation.create", partition)
        if subject_type not in ("artifact", "runtime", "profile", "node", "signer", "producer", "evidence", "policy", "verdict"):
            raise _err("validation", "E_REVOCATION_SUBJECT")
        ev = {"event_type": "quarantine" if quarantine else "revoke", "partition": partition, "subject_type": subject_type,
              "subject_id": subject_id, "reason": reason, "severity": severity, "effective_at": now, "issuer": p.subject,
              "expires_at": expires_at, "incident": incident}
        ev["event_id"] = "rv-" + digest(ev)[7:31]
        res = self.store.commit([ev], audit=[self._audit_event(ev["event_type"], p, partition,
                                                               {"subject_type": subject_type, "subject": hash_id(subject_id)})],
                                recorded_at=now)
        if subject_type == "signer" and not quarantine:
            try:
                self.trust.mark_compromised(subject_id, now)
            except KeyError:
                pass
        self._refresh_revisions()
        return {"event_id": ev["event_id"], "revision": res.revision, "affected_evidence": self.affected_by(subject_type, subject_id)}

    def reinstate(self, token: str, second_approver_token: str, *, subject_type: str, subject_id: str, partition: str, reason: str) -> dict:
        now = self._now()
        p = self._principal(token, now)
        second = self._principal(second_approver_token, now)
        cur = self.store.state.revocations.get((subject_type, subject_id))
        action = "revocation.reverse" if cur and cur["event_type"] == "revoke" else "quarantine.release"
        self._authorize(p, action, partition, second_approver=second)
        ev = {"event_type": "reinstate", "partition": partition, "subject_type": subject_type, "subject_id": subject_id,
              "reason": reason, "effective_at": now, "issuer": p.subject, "second_approver": second.subject}
        ev["event_id"] = "ri-" + digest(ev)[7:31]
        try:
            res = self.store.commit([ev], audit=[self._audit_event("reinstate", p, partition, {"subject_type": subject_type})], recorded_at=now)
        except StateError as exc:
            raise _err("conflict", exc.code) from None
        return {"event_id": ev["event_id"], "revision": res.revision}

    def affected_by(self, subject_type: str, subject_id: str) -> list:
        col = {"signer": "signer_key_id", "producer": "producer", "artifact": "artifact_digest", "runtime": "runtime",
               "profile": "profile_id", "evidence": "evidence_id"}.get(subject_type)
        if col is None:
            return []
        return sorted(e["evidence_id"] for e in self.store.events() if e["event_type"] == "evidence" and e.get(col) == subject_id)

    def bulk_revoke_preview(self, predicate: dict) -> dict:
        """Mandatory dry-run for bulk revocation with a blast-radius guard (MC-13-08)."""
        keys = list(self.store.state.evidence)
        hit = [k for k in keys if all(getattr(k, a) == v for a, v in predicate.items())]
        frac = len(hit) / max(len(keys), 1)
        return {"predicate": predicate, "matched": len(hit), "total": len(keys), "fraction": round(frac, 4),
                "allowed": 0 < frac <= self.cfg.bulk_revocation_max_fraction,
                "preview_digest": digest([k.as_dict() for k in hit])}

    def bulk_revoke(self, token: str, predicate: dict, preview_digest: str, *, partition: str, reason: str) -> dict:
        prev = self.bulk_revoke_preview(predicate)
        if prev["preview_digest"] != preview_digest:
            raise _err("conflict", "E_BULK_PREVIEW_STALE", "state changed since preview")
        if not prev["allowed"]:
            raise _err("validation", "E_BULK_BLAST_RADIUS", f"{prev['fraction']:.0%} exceeds guard")
        now = self._now()
        p = self._principal(token, now)
        out = []
        for k in [k for k in self.store.state.evidence if all(getattr(k, a) == v for a, v in predicate.items())]:
            out.append(self._revoke(p, now, subject_type="artifact", subject_id=k.artifact_digest, partition=partition,
                                   reason=reason, severity="high"))
        return {"revoked": len(out)}

    # ------------------------------------------------------------ conflicts
    def resolve_conflict(self, token: str, second_approver_token: str, case_id: str, *, decision: str, rationale: str) -> dict:
        now = self._now()
        p = self._principal(token, now)
        second = self._principal(second_approver_token, now)
        case = self.conflict_cases.get(case_id)
        if case is None:
            raise _err("validation", "E_CASE_UNKNOWN")
        self._authorize(p, "conflict.resolve", case["partition"])
        if second.subject == p.subject:
            raise _err("authz", "E_AUTHZ_SOD")
        if decision not in ("uphold-newer", "uphold-older", "both-invalid"):
            raise _err("validation", "E_CASE_DECISION")
        ev = {**{k: case[k] for k in ("partition", "artifact_digest", "runtime", "profile_id", "case_id", "ctype", "evidence")},
              "event_type": "conflict", "status": "resolved", "decision": decision, "rationale": rationale,
              "resolved_by": [p.subject, second.subject], "resolved_at": now}
        ev["event_id"] = "cr-" + digest(ev)[7:31]
        # resolution appends a record; the open case stays in history (MC-31-05)
        self.store.commit([ev], audit=[self._audit_event("conflict.resolved", p, case["partition"], {"case_id": case_id})], recorded_at=now)
        case["status"] = "resolved"
        if decision == "both-invalid":
            for eid in case["evidence"]:
                if eid:
                    self._revoke(p, now, subject_type="evidence", subject_id=eid, partition=case["partition"],
                                reason=f"conflict {case_id} resolved both-invalid", severity="high", quarantine=True)
        return {"case_id": case_id, "status": "resolved"}

    # ------------------------------------------------------------ admission
    def admit(self, token: str, request: dict) -> dict:
        """Admission contract for GAP-08 / SCH-01 / PLN-04 (component 30)."""
        now = self._now()
        p = self._principal(token, now)
        need = {"request_id", "artifact", "runtime", "profile_id", "partition", "intent"}
        if not isinstance(request, dict) or not need <= set(request):
            raise _err("validation", "E_ADMISSION_SHAPE")
        self._authorize(p, "admission.decide", request["partition"])
        rid = request["request_id"]
        if rid in self.admissions:
            prior = self.admissions[rid]
            if prior["request_digest"] != digest(request):
                raise _err("conflict", "E_ADMISSION_REQUEST_REUSED")
            return prior  # idempotent retry (MC-30-05)
        if not DIGEST_RE.match(request["artifact"]):
            raise _err("validation", "E_ADMISSION_UNBOUND_ARTIFACT", "admission needs an immutable digest, not a tag or name")
        if self._emergency_blocked("admissions", now):
            raise _err("dependency", "E_EMERGENCY_ADMISSIONS_DISABLED")
        key = CertKey(request["partition"], request["artifact"], request["runtime"], request["profile_id"])
        d = self._decide(key, now, new_admission=request["intent"] == "new",
                         required_features=set(request["features"]) if request.get("features") else None)
        record = {"schema": "GAP15_ADMISSION/1", "request_id": rid, "request_digest": digest(request),
                  "admitted": bool(d["deployable"]), "verdict": d["verdict"], "reason_code": d["reason_code"],
                  "remediation": REMEDIATION.get(d["reason_code"], "contact the service owner"),
                  "decision_id": d["decision_id"], "matrix_revision": d["matrix_revision"], "ledger_seq": d["ledger_seq"],
                  "policy_revision": d["policy"]["policy_revision"], "evaluated_at": now,
                  "valid_until": min(d.get("expires_at", now), now + 60) if d["deployable"] else now,
                  "workload": request.get("workload")}
        self.store.audit_only([self._audit_event("admission.decided", p, request["partition"],
                                                 {"request_id": rid, "admitted": record["admitted"], "decision_id": d["decision_id"],
                                                  "evidence_id": d.get("evidence_id")})])
        self.admissions[rid] = record
        return record

    def prestart_recheck(self, token: str, request_id: str) -> dict:
        """Final TOCTOU recheck immediately before launch (MC-30-09)."""
        now = self._now()
        p = self._principal(token, now)
        rec = self.admissions.get(request_id)
        if rec is None:
            raise _err("validation", "E_ADMISSION_UNKNOWN")
        d = self.decisions[rec["decision_id"]]
        self._authorize(p, "admission.decide", d["key"]["partition"])
        fresh = self._decide(CertKey(**d["key"]), now)
        ok = rec["admitted"] and fresh["deployable"] and now <= rec["valid_until"]
        return {"request_id": request_id, "launch_allowed": ok, "verdict": fresh["verdict"],
                "reason_code": fresh["reason_code"] if not ok else "R_CERTIFIED"}

    # ------------------------------------------------------------ emergency
    def emergency_disable(self, token: str, *, scope: str, partition: str, reason: str, incident: str, until: int) -> dict:
        now = self._now()
        p = self._principal(token, now)
        self._authorize(p, "emergency.disable", partition)
        if not incident or until <= now or until - now > 86400:
            raise _err("validation", "E_EMERGENCY_PARAMS", "incident reference and expiry <= 24h required")
        if not (scope in ("admissions", "ingestion") or scope.startswith(("runtime:", "artifact:", "signer:"))):
            raise _err("validation", "E_EMERGENCY_SCOPE")
        self.emergency[scope] = {"until": until, "incident": incident, "actor": p.subject, "reason": reason}
        self.store.audit_only([self._audit_event("emergency.disable", p, partition, {"scope": scope, "incident": incident, "until": until})])
        return {"scope": scope, "until": until}

    # --------------------------------------------------------------- health
    def health(self) -> dict:
        return {"status": "alive", "version": SERVICE_VERSION, "api": API_VERSION}

    def readiness(self) -> dict:
        checks = {}
        try:
            self.store.verify_chain("ledger")
            self.store.verify_chain("audit")
            checks["chains"] = "ok"
        except StoreError as exc:
            checks["chains"] = exc.code
        try:
            self.clock.require()
            checks["time"] = "ok"
        except TimeError_ as exc:
            checks["time"] = exc.code
        checks["key_provider"] = "ok" if (self.keys.production_grade or not self.cfg.production) else "not-production"
        checks["accepting"] = "ok" if not self.shutting_down else "draining"
        ready = all(v == "ok" for v in checks.values())
        self.metrics.set("gap15_audit_chain_ok", 1 if checks["chains"] == "ok" else 0)
        return {"ready": ready, "checks": checks, "revisions": dict(self.log.revisions)}

    def update_gauges(self, requested: list, now: int, horizon_s: int = 3600) -> dict:
        tested = sum(1 for k in set(requested) if k in self.store.state.evidence)
        cov = tested / len(set(requested)) if requested else 1.0
        self.metrics.set("gap15_matrix_coverage_ratio", round(cov, 4))
        backlog = 0
        oldest = 0
        for k, e in self.store.state.evidence.items():
            if e["result"] == "compatible":
                age = now - e["observed_at"]
                oldest = max(oldest, age)
                if age + horizon_s > self.cfg.cert_policy.ttl_s:
                    backlog += 1
        self.metrics.set("gap15_expiry_backlog", backlog)
        self.metrics.set("gap15_evidence_age_seconds", oldest)
        self.metrics.set("gap15_conflicts_open", sum(1 for c in self.conflict_cases.values() if c["status"] == "open"))
        for risk in ("low", "medium", "high"):
            self.metrics.set("gap15_waivers_active", self.waivers.report(now)["by_risk"][risk], risk=risk)
        return {"coverage": cov, "expiry_backlog": backlog, "oldest_positive_age_s": oldest}

    def begin_shutdown(self) -> None:
        self.shutting_down = True


REMEDIATION = {
    "R_NO_EVIDENCE": "schedule a compatibility test for this exact artifact/runtime/profile",
    "R_EXPIRED": "re-run the compatibility test; the positive result aged out",
    "R_INCOMPATIBLE": "fix the incompatibility or choose a certified runtime/profile",
    "R_NEGATIVE_AGED": "the negative result is due for retest; it does not authorise deployment",
    "R_EOL": "migrate to the replacement runtime named in the lifecycle record",
    "R_BLOCKED_FOR_NEW": "new admissions are closed for this runtime; use the replacement",
    "R_REVOKED": "a subject in this decision is revoked; see the revocation record",
    "R_QUARANTINED": "a subject is quarantined pending investigation",
    "R_CONFLICT": "an evidence conflict is open; it needs a two-person resolution",
    "R_POLICY_DENIED": "a policy rule denies this combination; request a waiver if the control is waivable",
    "R_FUTURE_EVIDENCE": "evidence timestamp is ahead of trusted time; check producer clocks",
    "R_EMERGENCY_DISABLED": "an emergency disable is in force; see the incident reference",
    "R_FEATURES_UNCERTIFIED": "certify the listed features for this exact key",
    "R_CERTIFIED": "none",
}
