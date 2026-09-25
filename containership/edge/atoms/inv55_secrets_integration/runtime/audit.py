"""Tamper-evident durable audit pipeline (checklist #47, #76).

Each record is canonical JSON carrying ``prev`` (hash of the previous record)
and ``hash`` (SHA-256 over the canonical record without ``hash``), optionally
HMAC-sealed with an audit key held outside the application.  The file sink
appends and fsyncs; ``verify_file`` detects edit, deletion, reordering and -
given the externally stored head - tail truncation.

Records must never carry a secret value: ``append`` refuses any field whose
value is a ``_SecretValue`` and refuses keys named like values.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading

from ..reference import _SecretValue

GENESIS = "0" * 64
FORBIDDEN_KEYS = {"value", "secret", "plaintext", "token", "password"}
ALLOWED_FIELDS = {"op", "tenant", "app", "subject", "secret_ref", "version", "allowed", "reason", "code",
                  "policy_digest", "config_digest", "request_id", "trace_id", "at", "actor", "detail"}


def _canon(d: dict) -> bytes:
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


class AuditLog:
    def __init__(self, path: str | None = None, *, seal_key: str | None = None, max_memory: int = 10_000):
        self.path = path
        self._key = _SecretValue(seal_key) if seal_key else None
        self._lock = threading.Lock()
        self.head = GENESIS
        self.seq = 0
        self.memory: list[dict] = []
        self.max_memory = max_memory
        if path and os.path.exists(path):
            ok, info = verify_file(path, seal_key=seal_key)
            if not ok:
                raise RuntimeError(f"existing audit log failed verification: {info}")
            self.head, self.seq = info["head"], info["count"]

    def append(self, **fields) -> dict:
        for k, v in fields.items():
            if k not in ALLOWED_FIELDS:
                raise ValueError(f"audit field {k!r} not in schema")
            if isinstance(v, _SecretValue):
                raise ValueError("secret value passed to audit")
        # secret NAMES travel as "secret_ref"; value-like keys are never admitted.
        with self._lock:
            rec = {"seq": self.seq + 1, "prev": self.head, **fields}
            rec["hash"] = hashlib.sha256(_canon(rec)).hexdigest()
            if self._key:
                rec["seal"] = hmac.new(self._key._reveal().encode(), rec["hash"].encode(), hashlib.sha256).hexdigest()
            line = _canon(rec) + b"\n"
            if self.path:
                fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
                try:
                    os.write(fd, line)
                    os.fsync(fd)
                finally:
                    os.close(fd)
            self.seq, self.head = rec["seq"], rec["hash"]
            self.memory.append(rec)
            if len(self.memory) > self.max_memory:
                del self.memory[: len(self.memory) - self.max_memory]
            return rec


def verify_records(records, *, seal_key: str | None = None, expected_head: str | None = None):
    prev, n = GENESIS, 0
    for i, rec in enumerate(records, 1):
        body = {k: v for k, v in rec.items() if k not in ("hash", "seal")}
        if rec.get("seq") != i:
            return False, {"error": "sequence_gap", "at": i}
        if rec.get("prev") != prev:
            return False, {"error": "broken_chain", "at": i}
        if hashlib.sha256(_canon(body)).hexdigest() != rec.get("hash"):
            return False, {"error": "hash_mismatch", "at": i}
        if seal_key is not None:
            want = hmac.new(seal_key.encode(), rec["hash"].encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(want, rec.get("seal", "")):
                return False, {"error": "bad_seal", "at": i}
        if any(k in FORBIDDEN_KEYS for k in rec):
            return False, {"error": "value_field_present", "at": i}
        prev, n = rec["hash"], i
    if expected_head is not None and prev != expected_head:
        return False, {"error": "head_mismatch_truncation_or_fork", "head": prev}
    return True, {"head": prev, "count": n}


def verify_file(path, *, seal_key=None, expected_head=None):
    recs = []
    with open(path, "rb") as f:
        for ln, line in enumerate(f, 1):
            try:
                recs.append(json.loads(line))
            except ValueError:
                return False, {"error": "unparseable_line", "at": ln}
    return verify_records(recs, seal_key=seal_key, expected_head=expected_head)
