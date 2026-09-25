"""Artifact trust verification (C045).

Verification order (fail-closed at every step):
    1. artifact class known to the trust policy
    2. policy itself integrity-verified (policy digest pinned by the caller)
    3. content digest == expected digest (sha256 only)
    4. source/registry allowlisted and version approved and not revoked
    5. signature valid for an approved signer of that class (where class requires it)
    6. provenance present and bound (generated code: request/model/toolchain binding)
Result is cached ONLY keyed by the immutable content digest + policy digest and
only within ``cache_ttl_s``.  Generated code is never executed in the fast tier.

Signature scheme: this stdlib-only build ships ``HmacSigner`` (HMAC-SHA256
over a shared trust root) behind the ``Signer`` interface.  Asymmetric
signatures (Sigstore / Ed25519) need an approved crypto dependency and are a
recorded blocker (WAIVERS.json W-003), not silently claimed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol
import hashlib
import hmac
import json
import threading
import time

from .errors import AgentError

TRUST_POLICY_SCHEMA = "PK_AGENT_TRUST_POLICY/1"
ARTIFACT_CLASSES = ("tool_plugin", "policy_bundle", "config_bundle", "generated_code", "dependency_package")


class Signer(Protocol):
    def verify(self, key_id: str, message: bytes, signature: str) -> bool: ...


class HmacSigner:
    def __init__(self, keys: Mapping[str, bytes]):
        self._keys = dict(keys)

    def sign(self, key_id: str, message: bytes) -> str:
        return hmac.new(self._keys[key_id], message, hashlib.sha256).hexdigest()

    def verify(self, key_id: str, message: bytes, signature: str) -> bool:
        key = self._keys.get(key_id)
        if key is None or not isinstance(signature, str):
            return False
        return hmac.compare_digest(hmac.new(key, message, hashlib.sha256).hexdigest(), signature)


def policy_digest(policy: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(policy, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Artifact:
    name: str
    klass: str
    version: str
    source: str
    content: bytes
    expected_digest: str
    signature: str | None = None
    key_id: str | None = None
    provenance: Mapping[str, Any] | None = None


class ArtifactVerifier:
    def __init__(self, policy: Mapping[str, Any], *, pinned_policy_digest: str, signer: Signer,
                 cache_ttl_s: float = 300.0, clock=time.time, audit=None):
        if policy.get("schema") != TRUST_POLICY_SCHEMA:
            raise AgentError("AGT-INT-002", "unsupported trust policy schema")
        if not hmac.compare_digest(policy_digest(policy), pinned_policy_digest):
            raise AgentError("AGT-INT-002", "trust policy digest does not match pinned digest")
        self.policy, self.policy_digest = policy, pinned_policy_digest
        self.signer, self.ttl, self._clock = signer, cache_ttl_s, clock
        self._cache: dict[tuple[str, str], tuple[float, dict]] = {}
        self._lock = threading.Lock()
        self.audit = audit if audit is not None else []

    def _fail(self, art: Artifact, digest: str, why: str) -> None:
        rec = {"schema": "PK_AGENT_ARTIFACT_DECISION/1", "artifact": art.name, "class": art.klass, "version": art.version,
               "digest": digest, "signer": art.key_id, "policy_version": self.policy.get("version"),
               "decision": "rejected", "why": why, "at": self._clock()}
        self.audit.append(rec)
        raise AgentError("AGT-INT-002", why, details={"artifact": art.name, "digest": digest})

    def verify(self, art: Artifact) -> dict[str, Any]:
        digest = hashlib.sha256(art.content).hexdigest()
        key = (digest, self.policy_digest)
        with self._lock:
            hit = self._cache.get(key)
            if hit and self._clock() - hit[0] <= self.ttl and hit[1]["artifact"] == art.name:
                return dict(hit[1], cached=True)
        rules = self.policy["classes"].get(art.klass)
        if art.klass not in ARTIFACT_CLASSES or rules is None:
            self._fail(art, digest, "artifact class not covered by trust policy")
        if not isinstance(art.expected_digest, str) or not hmac.compare_digest(digest, art.expected_digest.lower()):
            self._fail(art, digest, "content digest mismatch")
        if digest in self.policy.get("revoked_digests", []):
            self._fail(art, digest, "digest revoked")
        if art.source not in rules["allowed_sources"]:
            self._fail(art, digest, "source not allowlisted")
        approved = rules.get("approved_versions", {}).get(art.name)
        if approved is not None and art.version not in approved:
            self._fail(art, digest, "version not approved")
        if rules.get("require_signature", True):
            if not art.key_id or art.key_id not in rules["signers"]:
                self._fail(art, digest, "signer not approved for class")
            msg = f"{art.klass}\n{art.name}\n{art.version}\n{digest}".encode()
            if not self.signer.verify(art.key_id, msg, art.signature or ""):
                self._fail(art, digest, "signature invalid")
        tier = rules.get("execution_tier", "heavy")
        if art.klass == "generated_code":
            p = art.provenance or {}
            missing = [f for f in ("request_id", "model", "toolchain", "input_digest") if not p.get(f)]
            if missing:
                self._fail(art, digest, f"generated code lacks provenance binding: {missing}")
            tier = "heavy" if tier != "reject" else "reject"
            if tier == "reject":
                self._fail(art, digest, "policy rejects generated code execution")
        elif rules.get("require_provenance") and not art.provenance:
            self._fail(art, digest, "provenance required")
        rec = {"schema": "PK_AGENT_ARTIFACT_DECISION/1", "artifact": art.name, "class": art.klass,
               "version": art.version, "digest": digest, "signer": art.key_id,
               "provenance_ref": (art.provenance or {}).get("request_id") or (art.provenance or {}).get("ref"),
               "policy_version": self.policy.get("version"), "decision": "accepted", "execution_tier": tier,
               "at": self._clock()}
        self.audit.append(rec)
        with self._lock:
            self._cache[key] = (self._clock(), rec)
        return dict(rec, cached=False)
