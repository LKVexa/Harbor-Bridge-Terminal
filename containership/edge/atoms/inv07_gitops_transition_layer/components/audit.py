"""Tamper-evident audit ledger (component 12; adapted from the shop's GAP-09
v5.1.0 ``audit_ledger.py``).

* Append-only JSON-lines; each entry has ``seq``, ``prev`` and
  ``hash = sha256(JCS(entry without hash))`` -- editing, deleting or
  reordering any entry breaks the chain.
* A hash chain cannot see *tail truncation*, so ``head()`` gives
  ``(count, last_hash)`` and ``seal()`` appends an **Ed25519-signed head
  checkpoint** made by a separate audit-signing key; ``verify(expected_head=...,
  seal_keys=...)`` detects truncation (against an externally anchored head)
  and forged seals.
* Payloads pass through ``redact.scrub`` -- secrets never enter the ledger.
* Writes are ``fsync``'d; the file is opened append-only and the ledger never
  rewrites earlier bytes (WORM storage/object-lock is a deployment control,
  documented in docs/BACKUP_RESTORE.md).
* ``export`` writes a self-verifying bundle (entries + head + seals).
* Retention: ``retained_since`` lets operators archive the prefix *only* by
  exporting it first; the ledger itself never deletes (retention is policy on
  the exported archives, docs/TELEMETRY_POLICY.md).
"""
from __future__ import annotations

import hashlib
import json
import os
import threading

from . import ed25519
from .canonical import canonicalize
from .errors import Corrupted
from .redact import scrub

GENESIS = "0" * 64


class AuditLedger:
    def __init__(self, path: str | None = None, *, clock=None) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._entries: list[dict] = []
        self._clock = clock or (lambda: 0)
        if path and os.path.exists(path):
            self._entries = self._load(path)
            self.verify_entries(self._entries)

    @staticmethod
    def _load(path: str) -> list[dict]:
        out = []
        with open(path, "r", encoding="utf-8") as fh:
            for n, line in enumerate(fh):
                if not line.endswith("\n"):
                    raise Corrupted("audit ledger has a torn final line", line=n)
                try:
                    out.append(json.loads(line))
                except ValueError as exc:
                    raise Corrupted("audit ledger line is not JSON", line=n) from exc
        return out

    def append(self, kind: str, payload: dict, *, actor: str, correlation_id: str | None = None) -> dict:
        with self._lock:
            prev = self._entries[-1]["hash"] if self._entries else GENESIS
            entry = {"seq": len(self._entries), "kind": kind, "actor": str(scrub(actor)), "at": self._clock(),
                     "payload": scrub(payload), "prev": prev, "cid": correlation_id}
            entry["hash"] = hashlib.sha256(canonicalize(entry).encode()).hexdigest()
            if self.path:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(entry, sort_keys=True) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
            self._entries.append(entry)
            return entry

    def entries(self) -> list[dict]:
        with self._lock:
            return list(self._entries)

    def head(self) -> tuple[int, str]:
        with self._lock:
            return len(self._entries), (self._entries[-1]["hash"] if self._entries else GENESIS)

    def seal(self, secret: bytes, key_id: str) -> dict:
        n, h = self.head()
        sig = ed25519.sign(secret, f"PK-AUDIT-SEAL/1|{n}|{h}".encode()).hex()
        return self.append("audit.seal", {"count": n, "head": h, "key_id": key_id, "sig": sig}, actor="audit-sealer")

    @staticmethod
    def verify_entries(entries: list[dict], expected_head: tuple[int, str] | None = None,
                       seal_keys: dict[str, bytes] | None = None) -> dict:
        prev, seals = GENESIS, 0
        for i, e in enumerate(entries):
            if e.get("seq") != i or e.get("prev") != prev:
                raise Corrupted("audit chain broken", seq=i)
            body = {k: v for k, v in e.items() if k != "hash"}
            h = hashlib.sha256(canonicalize(body).encode()).hexdigest()
            if h != e.get("hash"):
                raise Corrupted("audit entry hash mismatch", seq=i)
            if e.get("kind") == "audit.seal" and seal_keys is not None:
                p = e["payload"]
                pub = seal_keys.get(p.get("key_id", ""))
                if pub is None or p.get("count") != i or p.get("head") != prev or not ed25519.verify(
                        pub, f"PK-AUDIT-SEAL/1|{p['count']}|{p['head']}".encode(), bytes.fromhex(p["sig"])):
                    raise Corrupted("audit seal invalid", seq=i)
                seals += 1
            prev = h
        if expected_head is not None and (len(entries), prev) != tuple(expected_head):
            raise Corrupted("audit ledger head does not match the external anchor (truncation or fork)")
        return {"entries": len(entries), "head": prev, "seals": seals}

    def verify(self, expected_head=None, seal_keys=None) -> dict:
        ents = self._load(self.path) if self.path else self.entries()
        return self.verify_entries(ents, expected_head, seal_keys)

    def export(self, dest: str) -> dict:
        ents = self.entries()
        info = self.verify_entries(ents)
        with open(dest, "w", encoding="utf-8") as fh:
            json.dump({"schema": "PK_GITOPS_AUDIT_EXPORT/1", "head": [len(ents), info["head"]], "entries": ents},
                      fh, sort_keys=True)
        return info
