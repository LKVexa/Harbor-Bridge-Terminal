"""Durable, crash-safe link-state store (M05).

Layout under ``root``:
  snapshot.json   -- {"schema_version", "seq", "links": {...}, "revoked": {...}, "checksum"}
  wal.jsonl       -- one checksummed record per mutation, fsync'd before ack

Recovery = load snapshot (verified) then replay WAL records with seq > snapshot
seq.  A torn final WAL line (crash mid-write) is discarded; corruption anywhere
else raises PK_PROVIDER_STATE_CORRUPT (fail closed, no silent partial load).
Revocations are durable tombstones: a revoked key can only come back through
an explicit new ``put`` with a higher config version -- never via replay or
restore of an older snapshot (``restore_guard``).  Optional AES-GCM sealing of
link configs via ``crypto.at_rest.KeyRing``.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from typing import Any, Iterable

from ..errors.mapping import ProviderFault

SCHEMA_VERSION = 2


def _ck(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def key_str(key: Iterable[str]) -> str:
    return json.dumps(list(key), separators=(",", ":"))


def _fsync_dir(path: str) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:  # pragma: no cover - platforms without dir fds
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class LinkStateStore:
    def __init__(self, root: str, *, keyring=None, compact_every: int = 1000):
        self.root = root
        os.makedirs(root, exist_ok=True)
        self._snap = os.path.join(root, "snapshot.json")
        self._wal = os.path.join(root, "wal.jsonl")
        self.keyring = keyring
        self.compact_every = compact_every
        self._lock = threading.RLock()
        self.links: dict[str, dict] = {}
        self.revoked: dict[str, int] = {}  # key -> config_version at revocation
        self.seq = 0
        self.discarded_torn_tail = False
        self._recover()

    # ---- recovery -------------------------------------------------------
    def _recover(self) -> None:
        if os.path.exists(self._snap):
            with open(self._snap, encoding="utf-8") as fh:
                try:
                    snap = json.load(fh)
                except json.JSONDecodeError:
                    raise ProviderFault("PK_PROVIDER_STATE_CORRUPT", "snapshot unparseable") from None
            body = {k: v for k, v in snap.items() if k != "checksum"}
            if snap.get("checksum") != _ck(body):
                raise ProviderFault("PK_PROVIDER_STATE_CORRUPT", "snapshot checksum mismatch")
            if snap.get("schema_version") == 1:
                from .migrations import migrate_v1_to_v2
                body = migrate_v1_to_v2(body)
            elif snap.get("schema_version") != SCHEMA_VERSION:
                raise ProviderFault("PK_PROVIDER_STATE_CORRUPT", "unknown snapshot schema version")
            self.links, self.revoked, self.seq = body["links"], body["revoked"], body["seq"]
        if os.path.exists(self._wal):
            with open(self._wal, "rb") as fh:
                lines = fh.read().split(b"\n")
            last = len(lines) - 1
            for i, raw in enumerate(lines):
                if not raw.strip():
                    continue
                try:
                    rec = json.loads(raw)
                    ok = rec.get("ck") == _ck({k: v for k, v in rec.items() if k != "ck"})
                except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                    ok = False
                if not ok:
                    if i == last:  # final line lacks its newline: torn append from a crash
                        self.discarded_torn_tail = True
                        self._truncate_to(lines[:i])
                        break
                    raise ProviderFault("PK_PROVIDER_STATE_CORRUPT", f"WAL record {i} failed checksum")
                if rec["seq"] <= self.seq:
                    continue
                if rec["seq"] != self.seq + 1:
                    raise ProviderFault("PK_PROVIDER_STATE_CORRUPT", "WAL sequence gap")
                self._apply(rec)

    def _truncate_to(self, good: list[bytes]) -> None:
        data = b"\n".join(x for x in good if x.strip())
        tmp = self._wal + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(data + (b"\n" if data else b""))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self._wal)

    def _apply(self, rec: dict) -> None:
        k = rec["key"]
        if rec["op"] == "put":
            self.links[k] = rec["value"]
            self.revoked.pop(k, None)
        elif rec["op"] == "revoke":
            self.links.pop(k, None)
            self.revoked[k] = rec["version"]
        self.seq = rec["seq"]

    # ---- mutation -------------------------------------------------------
    def _append(self, rec: dict) -> None:
        rec["ck"] = _ck(rec)
        line = (json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n").encode()
        with open(self._wal, "ab") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())

    def _seal(self, key: str, value: dict) -> dict:
        if self.keyring is None:
            return value
        from ..crypto.at_rest import seal
        return {"sealed": seal(self.keyring, json.dumps(value, sort_keys=True).encode(), key.encode())}

    def _unseal(self, key: str, value: dict) -> dict:
        if "sealed" not in value:
            return value
        if self.keyring is None:
            raise ProviderFault("PK_PROVIDER_KEY_UNAVAILABLE", "state is sealed but no keyring configured")
        from ..crypto.at_rest import open_
        return json.loads(open_(self.keyring, value["sealed"], key.encode())[0])

    def put(self, key: Iterable[str], value: dict) -> int:
        k = key_str(key)
        ver = int(value.get("config_version", 1))
        with self._lock:
            if k in self.revoked and ver <= self.revoked[k]:
                raise ProviderFault("PK_PROVIDER_INVALID_LINK", "re-link after revocation needs a higher config version")
            rec = {"op": "put", "key": k, "value": self._seal(k, value), "seq": self.seq + 1}
            self._append(rec)
            self._apply(rec)
            self._maybe_compact()
            return self.seq

    def revoke(self, key: Iterable[str]) -> bool:
        k = key_str(key)
        with self._lock:
            cur = self.links.get(k)
            if cur is None:
                return False
            ver = int(self._unseal(k, cur).get("config_version", 1))
            rec = {"op": "revoke", "key": k, "version": ver, "seq": self.seq + 1}
            self._append(rec)
            self._apply(rec)
            self._maybe_compact()
            return True

    def get(self, key: Iterable[str]) -> dict | None:
        k = key_str(key)
        with self._lock:
            v = self.links.get(k)
            return None if v is None else self._unseal(k, v)

    def items(self) -> list[tuple[list[str], dict]]:
        with self._lock:
            return [(json.loads(k), self._unseal(k, v)) for k, v in sorted(self.links.items())]

    def is_revoked(self, key: Iterable[str]) -> bool:
        with self._lock:
            return key_str(key) in self.revoked

    # ---- compaction / snapshot -----------------------------------------
    def _maybe_compact(self) -> None:
        if self.compact_every and self.seq % self.compact_every == 0:
            self.compact()

    def snapshot_body(self) -> dict:
        with self._lock:
            return {"schema_version": SCHEMA_VERSION, "seq": self.seq,
                    "links": json.loads(json.dumps(self.links)), "revoked": dict(self.revoked)}

    def compact(self) -> None:
        with self._lock:
            body = self.snapshot_body()
            body["checksum"] = _ck(body)
            tmp = self._snap + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(body, fh, sort_keys=True)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self._snap)
            _fsync_dir(self.root)
            open(self._wal, "wb").close()

    def rekey(self) -> int:
        """Re-seal every link under the keyring's current active key (rotation)."""
        with self._lock:
            n = 0
            for k in list(self.links):
                v = self._unseal(k, self.links[k])
                rec = {"op": "put", "key": k, "value": self._seal(k, v), "seq": self.seq + 1}
                self._append(rec)
                self._apply(rec)
                n += 1
            self.compact()
            return n
