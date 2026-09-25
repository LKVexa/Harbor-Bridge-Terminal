"""Checklist 11: node/collector authentication chain for posture read-backs.

Scope actually implemented here: a symmetric (HMAC-SHA256) signed envelope
binding a read-back to a registered collector key, a node identity, a
monotonically increasing sequence number, a nonce, an issue time and an
expiry.  The verifier rejects unknown keys, keys bound to a different node,
revoked or expired keys, bad MACs, replays (sequence <= last accepted),
expired envelopes and future-dated envelopes beyond a skew bound.

NOT implemented (and therefore not claimed): hardware-rooted attestation
(TPM quote / SEV-SNP / TDX report) proving that the collector binary and
kernel are the measured ones.  That needs the platform attestation service
and is tracked as BLOCKED in remediation/STATUS.json item 11.

Key material never appears in ``repr``, errors, logs or evidence; see
``tests/test_security.py::SecretLeakageTest``.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from dataclasses import dataclass, field

from .defense import MitigationMissing, _require_identifier

ENVELOPE_SCHEMA = "PK_ATTESTED_READBACK/1"
MAX_SKEW_S = 30.0
MAX_ENVELOPE_BYTES = 256 * 1024


class AttestationError(MitigationMissing):
    def __init__(self, message: str, code: str, **details):
        super().__init__(message, code=code, details=details)


@dataclass
class CollectorKey:
    key_id: str
    node: str
    _secret: bytes = field(repr=False)
    not_after_unix: float = float("inf")
    revoked: bool = False

    def __repr__(self) -> str:  # never render the secret
        return f"CollectorKey(key_id={self.key_id!r}, node={self.node!r}, revoked={self.revoked})"


class KeyRegistry:
    """Enrolment registry: key id -> (node binding, secret, lifetime)."""

    def __init__(self) -> None:
        self._keys: dict[str, CollectorKey] = {}
        self._last_seq: dict[str, int] = {}
        self._lock = threading.Lock()

    def enrol(self, node: str, *, key_id: str | None = None, secret: bytes | None = None,
              not_after_unix: float = float("inf")) -> tuple[str, bytes]:
        node = _require_identifier(node, "node")
        kid = key_id or f"k-{secrets.token_hex(8)}"
        sec = secret if secret is not None else secrets.token_bytes(32)
        if len(sec) < 32:
            raise ValueError("collector secret must be at least 32 bytes")
        with self._lock:
            if kid in self._keys:
                raise ValueError("key id already enrolled")
            self._keys[kid] = CollectorKey(kid, node, sec, not_after_unix)
        return kid, sec

    def revoke(self, key_id: str) -> None:
        with self._lock:
            if key_id in self._keys:
                self._keys[key_id].revoked = True

    def rotate(self, key_id: str, *, now: float | None = None) -> tuple[str, bytes]:
        with self._lock:
            old = self._keys[key_id]
        new = self.enrol(old.node)
        self.revoke(key_id)
        return new

    def _get(self, key_id: str) -> CollectorKey | None:
        with self._lock:
            return self._keys.get(key_id)

    def _accept_seq(self, key_id: str, seq: int) -> bool:
        with self._lock:
            last = self._last_seq.get(key_id, -1)
            if seq <= last:
                return False
            self._last_seq[key_id] = seq
            return True


def _canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def seal(payload: dict, *, node: str, key_id: str, secret: bytes, seq: int,
         ttl_s: float = 120.0, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    header = {
        "schema": ENVELOPE_SCHEMA,
        "node": node,
        "key_id": key_id,
        "seq": int(seq),
        "nonce": secrets.token_hex(12),
        "issued_at": now,
        "expires_at": now + ttl_s,
        "payload_sha256": hashlib.sha256(_canonical(payload)).hexdigest(),
    }
    mac = hmac.new(secret, _canonical(header), hashlib.sha256).digest()
    return {"header": header, "payload": payload, "mac": base64.b64encode(mac).decode()}


def verify(envelope: dict, registry: KeyRegistry, *, now: float | None = None) -> dict:
    """Return the payload of an authentic, fresh, non-replayed envelope.

    Every failure raises :class:`AttestationError` with a stable code; there
    is no path that returns an unverified payload.
    """
    now = time.time() if now is None else now
    if not isinstance(envelope, dict) or set(envelope) != {"header", "payload", "mac"}:
        raise AttestationError("malformed envelope", "attestation_malformed")
    if len(_canonical(envelope)) > MAX_ENVELOPE_BYTES:
        raise AttestationError("envelope too large", "attestation_oversize")
    h, payload, mac_b64 = envelope["header"], envelope["payload"], envelope["mac"]
    if not isinstance(h, dict) or h.get("schema") != ENVELOPE_SCHEMA:
        raise AttestationError("unsupported envelope schema", "attestation_schema")
    key = registry._get(str(h.get("key_id")))
    if key is None:
        raise AttestationError("unknown collector key", "attestation_unknown_key")
    try:
        mac = base64.b64decode(mac_b64, validate=True)
    except Exception:
        raise AttestationError("malformed mac", "attestation_malformed") from None
    expected = hmac.new(key._secret, _canonical(h), hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        raise AttestationError("bad signature", "attestation_bad_mac", key_id=key.key_id)
    if hashlib.sha256(_canonical(payload)).hexdigest() != h.get("payload_sha256"):
        raise AttestationError("payload digest mismatch", "attestation_payload_mismatch")
    if key.revoked:
        raise AttestationError("revoked collector key", "attestation_revoked_key", key_id=key.key_id)
    if now > key.not_after_unix:
        raise AttestationError("expired collector key", "attestation_expired_key", key_id=key.key_id)
    if h.get("node") != key.node or (isinstance(payload, dict) and payload.get("node") != key.node):
        raise AttestationError("key not bound to this node", "attestation_node_mismatch",
                               key_node=key.node, claimed=h.get("node"))
    if not isinstance(h.get("issued_at"), (int, float)) or h["issued_at"] > now + MAX_SKEW_S:
        raise AttestationError("envelope from the future", "attestation_clock_skew")
    if now > h.get("expires_at", 0):
        raise AttestationError("envelope expired", "attestation_expired")
    seq = h.get("seq")
    if not isinstance(seq, int) or isinstance(seq, bool) or not registry._accept_seq(key.key_id, seq):
        raise AttestationError("replayed or out-of-order envelope", "attestation_replay", seq=seq)
    return payload
