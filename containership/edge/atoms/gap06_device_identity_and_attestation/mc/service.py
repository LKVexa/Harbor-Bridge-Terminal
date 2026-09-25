"""Integrated GAP-06 attestation service (reference).

Wires every missing-component module into one fail-closed request path:
authn principal -> schema -> idempotency -> authz -> admission -> trusted time
-> single-use durable nonce -> TPM quote verifier under the active signed
policy -> verdict persisted -> audit -> telemetry -> quarantine enforcement.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from . import ops, schemas
from .errors import Gap06Error, fail
from .verifier import EnrolledAK, Verifier

MEASUREMENT_CODES = {"E_PCR_MISMATCH", "E_EVENTLOG_MISMATCH", "E_MEASUREMENT_REJECTED", "E_DUPLICATE_IDENTITY",
                     "E_TPM_CLOCK_UNSAFE", "E_CLOCK_ROLLBACK"}


@dataclass
class AttestationService:
    environment: str
    store: object
    clock: object
    authz: object
    admission: object
    publisher: object
    audit: object
    quarantine: object
    enrollment: object
    challenges: object
    verifier: Verifier = field(default_factory=Verifier)
    telemetry: ops.Telemetry = field(default_factory=ops.Telemetry)
    verdict_ttl: float = 3600.0
    audience: str = "gap06"

    # ---------------------------------------------------------------
    def challenge(self, principal, node: str) -> dict:
        now = self.clock.now()
        self.authz.require(principal, "attest", node=node)
        self.admission.admit(principal.id, now)
        rec = self.store.get("nodes", node)
        if rec is None or rec["status"] != "active":
            raise fail("E_UNKNOWN_NODE", "node not enrolled/active")
        nonce = self.challenges.issue(node, now, audience=self.audience)
        self.audit.append("challenge", now, node=node, nonce=nonce)
        self.telemetry.inc("gap06_challenges_total", op="challenge")
        return {"nonce": nonce, "expires_in": self.challenges.ttl}

    def attest(self, principal, message) -> dict:
        msg = schemas.validate(message)
        if msg["schema"] != "PK_ATTESTATION/1":
            raise fail("E_SCHEMA", "attest endpoint requires PK_ATTESTATION/1")
        idem_key = f"{principal.id}:{msg['idempotency_key']}"
        body_digest = hashlib.sha256(json.dumps(msg, sort_keys=True).encode()).hexdigest()
        prior = self.store.get("idempotency", idem_key)
        if prior is not None:
            if prior["digest"] != body_digest:
                raise fail("E_CONFLICT", "idempotency key reused with a different body")
            return prior["response"]
        now = self.clock.now()
        node = msg["node"]
        self.authz.require(principal, "attest", node=node)
        self.admission.admit(principal.id, now)
        try:
            self.challenges.consume(msg["nonce"], node, now, audience=self.audience)
        except Gap06Error as e:
            if e.code == "E_REPLAY":
                self.audit.append("replay_rejected", now, node=node)
            self.telemetry.inc("gap06_attest_total", result="reject", code=e.code)
            raise
        rec = self.store.get("nodes", node)
        if rec is None or rec["status"] != "active":
            raise fail("E_REVOKED", "node identity not active")
        pol = self.publisher.active()
        if pol is None:
            raise fail("E_MEASUREMENT_REJECTED", "no active signed measurement policy (fail closed)")
        if not self.publisher.rollout_includes(node):
            raise fail("E_MEASUREMENT_REJECTED", "node outside staged rollout of active policy")
        allowed = {int(k): set(v) for k, v in pol["doc"]["accepted"].items()}
        ak = EnrolledAK(node=node, ak_public=rec["ak_pem"].encode(), ak_name=bytes.fromhex(rec["ak_name"]),
                        device_id=rec["ek_fp"])
        d = self.verifier.verify_tpm_quote(
            ak=ak, expected_nonce=bytes.fromhex(msg["nonce"]), attest=bytes.fromhex(msg["attest"]),
            signature=bytes.fromhex(msg["signature"]),
            pcr_values={int(k): bytes.fromhex(v) for k, v in msg["pcrs"].items()},
            event_log=bytes.fromhex(msg["event_log"]) if "event_log" in msg else None,
            allowed_pcrs=allowed, required_pcrs=tuple(sorted(allowed)), policy_version=str(pol["version"]),
            decided_at=f"{now:.3f}")
        self.telemetry.inc("gap06_attest_total", result="ok" if d.ok else "reject", code=d.code)
        if d.ok:
            verdict = {"node": node, "level": d.level, "issued_at": now, "expires_at": now + self.verdict_ttl,
                       "binding": d.record["claims_sha256"], "policy_version": pol["version"],
                       "policy_digest": pol["digest"], "record": d.record}
            with self.store.transaction() as tx:
                tx.put("verdicts", node, verdict)
                tx.put("decisions", node, d.record)
            self.audit.append("verdict", now, node=node, level=d.level, policy=pol["version"])
            if self.quarantine.is_quarantined(node):
                self.audit.append("quarantine", now, node=node, note="verdict held: node remains quarantined")
            response = {"decision": "trusted", "level": d.level, "expires_at": verdict["expires_at"],
                        "policy_version": pol["version"]}
        else:
            with self.store.transaction() as tx:
                tx.delete("verdicts", node)
                tx.put("decisions", node, d.record)
            self.audit.append("reject", now, node=node, code=d.code)
            if d.code in MEASUREMENT_CODES:
                self.quarantine.quarantine(node, d.code, now)
                self.audit.append("quarantine", now, node=node, code=d.code)
            response = {"decision": "rejected", "error": fail(d.code, "attestation rejected").to_dict()}
        self.store.put("idempotency", idem_key, {"digest": body_digest, "response": response})
        return response

    def level_of(self, node: str) -> str:
        now = self.clock.now()
        v = self.store.get("verdicts", node)
        rec = self.store.get("nodes", node)
        if v is None or rec is None or rec["status"] != "active" or self.quarantine.is_quarantined(node):
            return "untrusted"
        return v["level"] if v["issued_at"] <= now < v["expires_at"] else "untrusted"

    def explain(self, principal, node: str) -> dict:
        self.authz.require(principal, "read")
        return ops.explain(self.store.get("decisions", node) or {}, self.publisher.active(),
                           self.store.get("verdicts", node))

    # transport binding
    def handle(self, path: str, principal, body: bytes) -> dict:
        if path == "/v1/challenge":
            return self.challenge(principal, json.loads(body)["node"])
        if path == "/v1/attest":
            return self.attest(principal, body)
        if path == "/v1/level":
            self.authz.require(principal, "read")
            return {"level": self.level_of(json.loads(body)["node"])}
        raise fail("E_SCHEMA", "unknown route")
