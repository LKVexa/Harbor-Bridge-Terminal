"""MC-18 - Tamper-evident security audit trail (PK_ASYNC_AUDIT/1).

Append-only JSON-lines, each record hash-chained to its predecessor
(``prev`` = sha256 of the previous canonical record).  Every ``checkpoint_every``
records a checkpoint is signed (Ed25519 when ``cryptography`` is installed,
otherwise HMAC-SHA256 with a key reference - the signature algorithm is written
into the checkpoint so a verifier cannot be fooled about which was used).
``verify_file`` is the offline verifier: it detects modification, deletion,
reordering and tail truncation beyond the last checkpoint head.

Sink outage: records buffer up to ``max_buffer``; past that, ``emit`` raises
``AuditUnavailable`` and security-relevant callers refuse the action
(fail-closed, see security.OUTAGE_POLICY).  Loss is itself counted.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from .security import redact

SCHEMA = "PK_ASYNC_AUDIT/1"
GENESIS = "0" * 64
RETENTION = {"security_events_days": 400, "export": "JSONL + checkpoint signatures",
             "access": "read: security-auditor role; write: component only (append)",
             "minimisation": "tenant/workload pseudonymised; no payloads, fds or secrets"}


class AuditUnavailable(RuntimeError):
    pass


def _canon(rec: dict) -> bytes:
    return json.dumps(rec, sort_keys=True, separators=(",", ":")).encode()


class Signer:
    """Ed25519 if available, else HMAC-SHA256 (algorithm recorded)."""

    def __init__(self, seed: bytes | None = None) -> None:
        seed = seed or os.urandom(32)
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from cryptography.hazmat.primitives import serialization
            self._sk = Ed25519PrivateKey.from_private_bytes(seed)
            self.alg = "ed25519"
            self.public = self._sk.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
        except Exception:  # pragma: no cover - depends on host
            self._sk = None
            self._k = seed
            self.alg = "hmac-sha256"
            self.public = hashlib.sha256(b"pub" + seed).hexdigest()[:16]

    def sign(self, data: bytes) -> str:
        if self._sk is not None:
            return self._sk.sign(data).hex()
        return hmac.new(self._k, data, hashlib.sha256).hexdigest()

    def verify(self, data: bytes, sig: str) -> bool:
        if self._sk is not None:
            from cryptography.exceptions import InvalidSignature
            try:
                self._sk.public_key().verify(bytes.fromhex(sig), data)
                return True
            except (InvalidSignature, ValueError):
                return False
        return hmac.compare_digest(self.sign(data), sig)


def verify_public(alg: str, public_hex: str, data: bytes, sig: str) -> bool:
    if alg != "ed25519":
        return False  # HMAC checkpoints need the key; offline public verification impossible
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex)).verify(bytes.fromhex(sig), data)
        return True
    except (InvalidSignature, ValueError):
        return False


@dataclass
class AuditLog:
    path: str | None = None
    signer: Signer = field(default_factory=Signer)
    checkpoint_every: int = 64
    max_buffer: int = 4096
    release: str = "5.0.0"
    config_digest: str = ""
    sink_up: bool = True
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _head: str = field(default=GENESIS, init=False)
    _seq: int = field(default=0, init=False)
    _buffer: list[dict] = field(default_factory=list, init=False)
    records: list[dict] = field(default_factory=list, init=False)
    lost: int = field(default=0, init=False)
    export_failures: int = field(default=0, init=False)

    def emit(self, action: str, outcome: str, *, actor: str, tenant: str, workload: str,
             resource: str = "", error: str | None = None, **extra: Any) -> dict:
        with self._lock:
            if len(self._buffer) >= self.max_buffer:
                self.lost += 1
                raise AuditUnavailable("audit buffer exhausted; refusing security-relevant action")
            self._seq += 1
            rec = {"schema": SCHEMA, "seq": self._seq, "ts": time.time(), "actor": actor,
                   "tenant": tenant, "workload": workload, "action": action,
                   "resource": resource, "outcome": outcome, "error": error,
                   "release": self.release, "config_digest": self.config_digest,
                   "extra": redact(extra), "prev": self._head}
            self._head = hashlib.sha256(_canon(rec)).hexdigest()
            self._buffer.append(rec)
            if self._seq % self.checkpoint_every == 0:
                cp = {"schema": SCHEMA, "checkpoint": self._seq, "head": self._head,
                      "alg": self.signer.alg, "public": self.signer.public}
                cp["sig"] = self.signer.sign(_canon({k: cp[k] for k in ("checkpoint", "head", "alg")}))
                self._buffer.append(cp)
            self._flush_locked()
            return rec

    def _flush_locked(self) -> None:
        if not self.sink_up:
            self.export_failures += 1
            return
        if self.path:
            with open(self.path, "a", encoding="utf-8") as fh:
                for r in self._buffer:
                    fh.write(json.dumps(r, sort_keys=True) + "\n")
        self.records.extend(self._buffer)
        self._buffer.clear()

    def flush(self) -> None:
        with self._lock:
            self._flush_locked()

    @property
    def head(self) -> str:
        return self._head

    @property
    def buffered(self) -> int:
        return len(self._buffer)


def verify_records(records: list[dict], expected_head: str | None = None,
                   signer: Signer | None = None) -> tuple[bool, str]:
    prev, seq, last_cp = GENESIS, 0, 0
    for r in records:
        if "checkpoint" in r:
            if r["head"] != prev or r["checkpoint"] != seq:
                return False, f"checkpoint {r['checkpoint']} does not match chain"
            body = _canon({k: r[k] for k in ("checkpoint", "head", "alg")})
            ok = (signer.verify(body, r["sig"]) if signer is not None
                  else verify_public(r["alg"], r["public"], body, r["sig"]))
            if not ok:
                return False, f"checkpoint {r['checkpoint']} signature invalid"
            last_cp = seq
            continue
        if r.get("prev") != prev:
            return False, f"chain broken at seq {r.get('seq')} (modified, deleted or reordered)"
        if r.get("seq") != seq + 1:
            return False, f"sequence gap at {r.get('seq')} (deletion or reordering)"
        seq = r["seq"]
        prev = hashlib.sha256(_canon(r)).hexdigest()
    if expected_head is not None and prev != expected_head:
        return False, "head mismatch (tail truncated or extended)"
    return True, f"ok: {seq} records, last signed checkpoint {last_cp}"


def verify_file(path: str, expected_head: str | None = None) -> tuple[bool, str]:
    with open(path, encoding="utf-8") as fh:
        recs = [json.loads(line) for line in fh if line.strip()]
    return verify_records(recs, expected_head)
