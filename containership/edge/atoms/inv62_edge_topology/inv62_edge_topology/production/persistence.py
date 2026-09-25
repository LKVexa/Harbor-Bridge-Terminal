"""Crash-consistent state persistence: authenticated write-ahead log plus
atomic snapshots (MC-047, MC-084; at-rest protection for MC-037).

Recovery contract:
  1. Load ``snapshot.json`` (MAC-verified) if present.
  2. Replay ``wal.jsonl`` records with ``seq`` greater than the snapshot's
     ``seq_upto`` in order.  Every record is MAC-verified and chained to the
     previous record's digest; a gap, duplicate, reorder or edit refuses
     startup (fail closed).  Only a *torn final line* (crash during append)
     is tolerated and truncated.
  3. The service then re-derives modes and leases; leases are *never*
     restored (they expire), only term high-water marks, so a restarted
     authority cannot resurrect a stale leader.

At rest: records are HMAC-SHA256 authenticated with the state key.  When
``encrypt_at_rest`` is configured the payload is sealed with AES-256-GCM via
the optional ``cryptography`` package; if it is not installed, startup fails
closed rather than writing plaintext.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import threading
from pathlib import Path
from typing import Any
from collections.abc import Iterator

from . import errors

GENESIS = "0" * 64


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


class Sealer:
    def __init__(self, key: bytes, encrypt: bool):
        self.mac_key = hashlib.sha256(b"inv62-mac" + key).digest()
        self._aead = None
        if encrypt:
            try:
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore
            except Exception:  # pragma: no cover - depends on environment
                raise errors.TopoError(errors.DEPENDENCY_UNAVAILABLE,
                                       "encrypt_at_rest requested but AES-GCM is unavailable",
                                       {"dependency": "cryptography"}) from None
            self._aead = AESGCM(hashlib.sha256(b"inv62-enc" + key).digest())

    def seal(self, payload: Any) -> Any:
        if self._aead is None:
            return payload
        nonce = os.urandom(12)
        ct = self._aead.encrypt(nonce, _canon(payload), b"inv62-state")
        return {"enc": "A256GCM", "n": base64.b64encode(nonce).decode(), "c": base64.b64encode(ct).decode()}

    def open(self, payload: Any) -> Any:
        if isinstance(payload, dict) and payload.get("enc") == "A256GCM":
            if self._aead is None:
                raise errors.TopoError(errors.DEPENDENCY_UNAVAILABLE, "state is encrypted but no AEAD configured")
            pt = self._aead.decrypt(base64.b64decode(payload["n"]), base64.b64decode(payload["c"]), b"inv62-state")
            return json.loads(pt)
        if self._aead is not None:
            raise errors.TopoError(errors.INVALID_REQUEST, "plaintext state found while encryption is required")
        return payload

    def mac(self, body: dict) -> str:
        return hmac.new(self.mac_key, _canon(body), hashlib.sha256).hexdigest()


class StateStore:
    def __init__(self, directory: str | os.PathLike[str], key: bytes, *, encrypt: bool = False, fsync: bool = True):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.sealer = Sealer(key, encrypt)
        self.fsync = fsync
        self.wal = self.dir / "wal.jsonl"
        self.snap = self.dir / "snapshot.json"
        self._lock = threading.Lock()
        self.seq = 0
        self.prev = GENESIS

    # ---------------------------------------------------------------- write
    def append(self, kind: str, tenant: str | None, payload: Any) -> int:
        with self._lock:
            body = {"seq": self.seq + 1, "prev": self.prev, "kind": kind, "tenant": tenant,
                    "payload": self.sealer.seal(payload)}
            digest = hashlib.sha256(_canon(body)).hexdigest()
            body["mac"] = self.sealer.mac(body)
            line = json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n"
            with open(self.wal, "a", encoding="utf-8") as fh:
                fh.write(line)
                fh.flush()
                if self.fsync:
                    os.fsync(fh.fileno())
            self.seq += 1
            self.prev = digest
            return self.seq

    def write_snapshot(self, state: dict[str, Any]) -> None:
        """Atomically persist full state and truncate the WAL."""
        with self._lock:
            body = {"seq_upto": self.seq, "prev": self.prev, "state": self.sealer.seal(state)}
            body["mac"] = self.sealer.mac(body)
            tmp = self.snap.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(body, fh, sort_keys=True)
                fh.flush()
                if self.fsync:
                    os.fsync(fh.fileno())
            os.replace(tmp, self.snap)
            tmpw = self.wal.with_suffix(".tmp")
            tmpw.write_text("")
            os.replace(tmpw, self.wal)

    # ----------------------------------------------------------------- read
    def load(self) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        snapshot = None
        seq, prev = 0, GENESIS
        if self.snap.exists():
            body = json.loads(self.snap.read_text())
            mac = body.pop("mac", "")
            if not hmac.compare_digest(mac, self.sealer.mac(body)):
                raise errors.TopoError(errors.INTERNAL, "snapshot authentication failed; refusing to start")
            snapshot = self.sealer.open(body["state"])
            seq, prev = body["seq_upto"], body["prev"]
        records = []
        for rec in self._wal_records():
            mac = rec.get("mac", "")
            body = {k: v for k, v in rec.items() if k != "mac"}
            if not hmac.compare_digest(mac, self.sealer.mac(body)):
                raise errors.TopoError(errors.INTERNAL, f"WAL record {rec.get('seq')} failed authentication")
            if rec["seq"] <= seq:
                continue  # already folded into snapshot
            if rec["seq"] != seq + 1 or rec["prev"] != prev:
                raise errors.TopoError(errors.INTERNAL, f"WAL gap/reorder at seq {rec.get('seq')}")
            seq, prev = rec["seq"], hashlib.sha256(_canon(body)).hexdigest()
            records.append({"seq": rec["seq"], "kind": rec["kind"], "tenant": rec["tenant"],
                            "payload": self.sealer.open(rec["payload"])})
        self.seq, self.prev = seq, prev
        return snapshot, records

    def _wal_records(self) -> Iterator[dict[str, Any]]:
        if not self.wal.exists():
            return
        raw = self.wal.read_text(encoding="utf-8")
        lines = raw.split("\n")
        complete, tail = lines[:-1], lines[-1]
        good_bytes = 0
        for i, line in enumerate(complete):
            try:
                rec = json.loads(line)
            except ValueError:
                raise errors.TopoError(errors.INTERNAL, f"corrupt WAL line {i + 1}") from None
            good_bytes += len(line.encode()) + 1
            yield rec
        if tail.strip():
            # torn final append: truncate to the last complete record
            with open(self.wal, "r+b") as fh:
                fh.truncate(good_bytes)
