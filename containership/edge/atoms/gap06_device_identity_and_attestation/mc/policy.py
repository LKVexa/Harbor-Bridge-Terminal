"""MC-09 / MC-34: signed measurement-policy publication and precedence.

A policy bundle = canonical JSON {environment, version (int, strictly
increasing), accepted {pcr: [hex...]}, measurements [..], not_before, rollout}.
Activation requires M-of-N distinct approver signatures (Ed25519) from the
pinned approver set, a version greater than the active one (rollback refused
unless an equally-signed ``rollback_to`` bundle with a *new* version number
reissues the old content), and is atomic: the active pointer changes in one
store transaction.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from . import algorithms as alg
from .errors import fail

MAX_POLICY_BYTES = 256 * 1024


def canonical(doc: dict) -> bytes:
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()


@dataclass
class PolicyPublisher:
    approvers: dict  # approver id -> public key PEM
    threshold: int
    store: object  # DurableStore
    environment: str

    def __post_init__(self):
        if self.threshold < 2 or self.threshold > len(self.approvers):
            raise ValueError("threshold must be >=2 and <= number of approvers")

    def active(self) -> dict | None:
        return self.store.get("policy_active", self.environment)

    def verify_bundle(self, doc: dict, signatures: dict) -> str:
        body = canonical(doc)
        if len(body) > MAX_POLICY_BYTES:
            raise fail("E_SCHEMA", "policy too large")
        for k in ("environment", "version", "accepted", "not_before"):
            if k not in doc:
                raise fail("E_SCHEMA", f"policy missing {k}")
        if doc["environment"] != self.environment:
            raise fail("E_TENANT_BOUNDARY", "policy for another environment")
        if not isinstance(doc["version"], int) or doc["version"] < 1:
            raise fail("E_SCHEMA", "version must be positive int")
        good = set()
        for who, sig in signatures.items():
            pem = self.approvers.get(who)
            if pem is None:
                continue
            try:
                alg.verify(alg.load_public_key(pem), "ed25519", bytes.fromhex(sig), body)
                good.add(who)
            except Exception:
                continue
        if len(good) < self.threshold:
            raise fail("E_QUORUM", f"{len(good)} valid approvals < threshold {self.threshold}")
        return hashlib.sha256(body).hexdigest()

    def activate(self, doc: dict, signatures: dict, *, now: float) -> dict:
        digest = self.verify_bundle(doc, signatures)
        if now < doc["not_before"]:
            raise fail("E_CONFLICT", "policy not yet valid (staged)")
        cur = self.active()
        if cur is not None and doc["version"] <= cur["version"]:
            raise fail("E_POLICY_ROLLBACK", f"version {doc['version']} <= active {cur['version']}")
        rec = {"version": doc["version"], "digest": digest, "doc": doc, "approvers": sorted(signatures)}
        with self.store.transaction() as tx:
            tx.put("policy_history", f"{self.environment}:{doc['version']}", rec)
            tx.put("policy_active", self.environment, rec)
        return rec

    def rollout_includes(self, node: str) -> bool:
        """Staged rollout: policy.rollout.percent of nodes by stable hash."""
        cur = self.active()
        pct = (cur or {}).get("doc", {}).get("rollout", {}).get("percent", 100)
        bucket = int(hashlib.sha256(node.encode()).hexdigest()[:8], 16) % 100
        return bucket < pct


PRECEDENCE = ("security", "residency", "slo", "cost")


def resolve(constraints: list[dict]) -> dict:
    """MC-34: deny-overrides with deterministic precedence.  Each constraint is
    {domain, decision: allow|deny, reason}.  Any deny wins and is attributed to
    the highest-precedence denying domain (security > residency > slo > cost);
    allow requires at least one constraint and no deny.  Empty input => deny."""
    if not constraints:
        return {"decision": "deny", "domain": None, "reason": "no constraints (default deny)", "overridden": []}
    for c in constraints:
        if c.get("domain") not in PRECEDENCE or c.get("decision") not in ("allow", "deny"):
            raise fail("E_SCHEMA", "bad constraint")
    ordered = sorted(constraints, key=lambda c: (PRECEDENCE.index(c["domain"]), c["decision"] != "deny"))
    denies = [c for c in ordered if c["decision"] == "deny"]
    chosen = denies[0] if denies else ordered[0]
    return {"decision": chosen["decision"], "domain": chosen["domain"], "reason": chosen.get("reason", ""),
            "overridden": [c for c in constraints if c is not chosen and c["decision"] != chosen["decision"]]}
