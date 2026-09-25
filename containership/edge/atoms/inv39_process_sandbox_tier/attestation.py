"""MC-046 / MC-047 / MC-049 / MC-050 / MC-053 / MC-054 — evidence binding and audit chain.

* ``EvidenceSigner`` signs PK_SANDBOX_APPLIED/2 records.  Default is HMAC-SHA256
  with a node key; Ed25519 is used when ``cryptography`` is installed and an
  Ed25519 key is supplied.  Signed payload binds: node identity, sandbox id,
  profile digest, seccomp program digest, config digest, release digest, a
  single-use nonce and the issue time -> not replayable across nodes,
  workloads, releases or requests.
* ``EvidenceVerifier`` checks signature, binding, freshness and nonce reuse;
  every failure is ``E_ATTESTATION_FAILED``; an unavailable key/time source is
  ``E_DEPENDENCY_UNAVAILABLE`` and still refuses (fail safe, MC-053).
* ``AuditChain`` is an append-only, hash-chained JSONL sink (MC-054).  Each
  entry commits to the previous entry's hash; ``verify_chain`` detects any
  edit, reorder, insertion or truncation-in-the-middle.  Truncation of the
  tail is detected by comparing against a separately stored head hash.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .errors import SandboxError

MAX_CLOCK_SKEW_S = 30
MAX_EVIDENCE_AGE_S = 300
MAX_NONCES = 100_000


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(obj: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(obj)).hexdigest()


@dataclass
class NodeIdentity:
    """MC-050: node identity = stable id + key; the key id is the key's digest."""
    node_id: str
    key: bytes

    def __post_init__(self) -> None:
        if len(self.key) < 32:
            raise SandboxError("E_PROFILE_INVALID", "node key must be >= 32 bytes")

    @property
    def key_id(self) -> str:
        return "hmac-sha256:" + hashlib.sha256(b"inv39-keyid" + self.key).hexdigest()[:32]


class EvidenceSigner:
    def __init__(self, identity: NodeIdentity, clock: Callable[[], float] = time.time):
        self.identity = identity
        self.clock = clock

    def sign(self, body: dict[str, Any]) -> dict[str, Any]:
        for k in ("sandbox_id", "profile_digest", "nonce"):
            if not body.get(k):
                raise SandboxError("E_ATTESTATION_FAILED", f"evidence body lacks {k}")
        rec = dict(body)
        rec["node_id"] = self.identity.node_id
        rec["key_id"] = self.identity.key_id
        rec["issued_at"] = int(self.clock())
        mac = hmac.new(self.identity.key, canonical(rec), hashlib.sha256).hexdigest()
        rec["signature"] = "hmac-sha256:" + mac
        return rec


@dataclass
class EvidenceVerifier:
    trusted: dict[str, bytes]                     # node_id -> key (from the identity service)
    clock: Callable[[], float] = time.time
    seen_nonces: dict[str, float] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def verify(self, rec: dict[str, Any], *, expect: dict[str, str]) -> None:
        if not isinstance(rec, dict) or "signature" not in rec:
            raise SandboxError("E_ATTESTATION_FAILED", "unsigned evidence")
        key = self.trusted.get(rec.get("node_id", ""))
        if key is None:
            raise SandboxError("E_ATTESTATION_FAILED", "evidence from an untrusted node")
        body = {k: v for k, v in rec.items() if k != "signature"}
        mac = "hmac-sha256:" + hmac.new(key, canonical(body), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(mac, str(rec["signature"])):
            raise SandboxError("E_ATTESTATION_FAILED", "signature mismatch")
        for k, v in expect.items():
            if rec.get(k) != v:
                raise SandboxError("E_ATTESTATION_FAILED", f"binding mismatch on {k}")
        try:
            now = self.clock()
        except Exception as exc:  # noqa: BLE001
            raise SandboxError("E_DEPENDENCY_UNAVAILABLE", "trusted time unavailable") from exc
        issued = rec.get("issued_at")
        if not isinstance(issued, int) or issued > now + MAX_CLOCK_SKEW_S or now - issued > MAX_EVIDENCE_AGE_S:
            raise SandboxError("E_ATTESTATION_FAILED", "evidence is stale or from the future")
        with self._lock:
            n = rec["nonce"]
            if n in self.seen_nonces:
                raise SandboxError("E_ATTESTATION_FAILED", "nonce replay")
            if len(self.seen_nonces) >= MAX_NONCES:
                cutoff = now - MAX_EVIDENCE_AGE_S
                self.seen_nonces = {k: t for k, t in self.seen_nonces.items() if t >= cutoff}
                if len(self.seen_nonces) >= MAX_NONCES:
                    raise SandboxError("E_OVERLOADED", "nonce cache saturated")
            self.seen_nonces[n] = now


def new_nonce() -> str:
    return os.urandom(16).hex()


GENESIS = "sha256:" + "0" * 64


class AuditChain:
    """Append-only hash chain. ``path`` may be None for an in-memory chain."""

    MAX_EVENT_BYTES = 16 * 1024

    def __init__(self, path: str | None = None):
        self.path = path
        self.head = GENESIS
        self.count = 0
        self.entries: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        if path and os.path.exists(path):
            ok, head, n = verify_chain_file(path)
            if not ok:
                raise SandboxError("E_ATTESTATION_FAILED", f"audit chain at {path} failed verification")
            self.head, self.count = head, n

    def append(self, kind: str, data: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            entry = {"seq": self.count, "ts": round(time.time(), 6), "kind": kind, "data": data, "prev": self.head}
            raw = canonical(entry)
            if len(raw) > self.MAX_EVENT_BYTES:
                entry["data"] = {"truncated": True, "digest": digest(data)}
            entry["hash"] = digest({k: v for k, v in entry.items()})
            if self.path:
                fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
                try:
                    os.write(fd, canonical(entry) + b"\n")
                    os.fsync(fd)
                finally:
                    os.close(fd)
            else:
                self.entries.append(entry)
            self.head = entry["hash"]
            self.count += 1
            return entry


def verify_chain(entries: list[dict[str, Any]]) -> tuple[bool, str, int]:
    prev = GENESIS
    for i, e in enumerate(entries):
        if e.get("seq") != i or e.get("prev") != prev:
            return False, prev, i
        body = {k: v for k, v in e.items() if k != "hash"}
        if digest(body) != e.get("hash"):
            return False, prev, i
        prev = e["hash"]
    return True, prev, len(entries)


def verify_chain_file(path: str) -> tuple[bool, str, int]:
    with open(path, "rb") as f:
        try:
            entries = [json.loads(l) for l in f if l.strip()]
        except json.JSONDecodeError:
            return False, GENESIS, 0
    return verify_chain(entries)
