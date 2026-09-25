"""Device identity and attestation integration (component 12; GAP-06 contract).

* each node has a registered identity key (by key id; material stays in the
  key ring / HSM, never in rollout state);
* the controller issues single-use **nonces** per command; the node's signed
  acknowledgement must echo the nonce, the command id, rollout id, fencing
  token, its own node id and the resulting observed version + digest;
* the ack carries an attestation claim (boot/runtime measurements); it must
  match the node's expected measurements and be fresh;
* rotation (new key id), revocation and device replacement are explicit;
  an ack signed by node A can never be accepted for node B.
"""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from typing import Any, Mapping

from .common import Clock, KeyRing, SystemClock, digest_of, verify_envelope
from .errors import IdentityRejected

ACK_SCHEMA = "PK_NODE_ACK/1"


@dataclass
class DeviceRecord:
    node_id: str
    key_id: str
    expected_measurements: dict[str, str]
    revoked: bool = False
    generation: int = 1  # bumps on replacement


@dataclass
class DeviceRegistry:
    keyring: KeyRing
    clock: Clock = field(default_factory=SystemClock)
    nonce_ttl_s: float = 600.0
    attestation_max_age_s: float = 3600.0
    _devices: dict[str, DeviceRecord] = field(default_factory=dict)
    _nonces: dict[str, tuple[str, float]] = field(default_factory=dict)  # nonce -> (node, expires)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def enroll(self, node_id: str, key_id: str, measurements: Mapping[str, str]) -> DeviceRecord:
        if not self.keyring.is_active(key_id):
            raise IdentityRejected(f"key {key_id} is not active", resource=node_id)
        with self._lock:
            prev = self._devices.get(node_id)
            rec = DeviceRecord(node_id, key_id, dict(measurements), generation=(prev.generation + 1) if prev else 1)
            self._devices[node_id] = rec
            return rec

    def rotate(self, node_id: str, new_key_id: str) -> None:
        with self._lock:
            rec = self._devices[node_id]
            old = rec.key_id
            rec.key_id = new_key_id
        self.keyring.revoke(old)

    def revoke(self, node_id: str) -> None:
        with self._lock:
            self._devices[node_id].revoked = True

    def record(self, node_id: str) -> DeviceRecord:
        with self._lock:
            rec = self._devices.get(node_id)
        if rec is None or rec.revoked:
            raise IdentityRejected(f"node {node_id} is not enrolled or is revoked", resource=node_id)
        return rec

    def issue_nonce(self, node_id: str) -> str:
        self.record(node_id)
        n = os.urandom(16).hex()
        with self._lock:
            self._nonces[n] = (node_id, self.clock.now() + self.nonce_ttl_s)
        return n

    def verify_ack(self, envelope: Mapping[str, Any], *, command: Mapping[str, Any]) -> dict[str, Any]:
        node = command["node"]
        rec = self.record(node)
        if envelope.get("key_id") != rec.key_id:
            raise IdentityRejected("ack not signed with the node's enrolled key", resource=node)
        body = verify_envelope(self.keyring, envelope)
        if body is None:
            raise IdentityRejected("ack signature invalid", resource=node)
        if body.get("schema") != ACK_SCHEMA:
            raise IdentityRejected("unsupported ack schema", resource=node)
        for k in ("command_id", "rollout_id", "fence", "node", "nonce"):
            if body.get(k) != command.get(k):
                raise IdentityRejected(f"ack field {k} does not match the command", resource=node)
        with self._lock:
            entry = self._nonces.pop(body["nonce"], None)
        if entry is None or entry[0] != node or entry[1] < self.clock.now():
            raise IdentityRejected("ack nonce unknown, reused, expired or for another node", resource=node)
        att = body.get("attestation") or {}
        if not isinstance(att, Mapping) or att.get("measurements") != rec.expected_measurements:
            raise IdentityRejected("attestation measurements mismatch", resource=node)
        at = att.get("at")
        if not isinstance(at, (int, float)) or self.clock.now() - at > self.attestation_max_age_s:
            raise IdentityRejected("attestation stale", resource=node)
        return {**body, "ack_ref": digest_of(dict(envelope)), "identity_generation": rec.generation}
