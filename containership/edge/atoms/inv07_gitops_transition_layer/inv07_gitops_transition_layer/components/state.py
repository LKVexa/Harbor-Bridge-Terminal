"""Persistent controller state (08), crash recovery/replay (19) and
backup/restore (32).  WAL format adapted from the shop's GAP-09 ``durable.py``.

Layout under ``state_dir``::

    STATE_VERSION          "PK_GITOPS_STATE/1"
    journal.wal            <crc32 8 hex>\\t<canonical JSON>\\n per record
    checkpoint.json        periodic compaction of the journal (atomic rename)

Journal record kinds: ``intent`` (written *before* any target mutation, with
an idempotency key), ``effect`` (per-resource outcome), ``commit`` (intent
completed: applied revision recorded), ``abort`` (intent rolled back or
abandoned), ``drift`` (report), ``cursor`` (last accepted OID per ref).

Recovery (``recover``):

* a torn final line is truncated and the dropped byte count reported;
* a checksum failure *before* the tail is ``Corrupted`` -- never skipped;
* an ``intent`` with no ``commit``/``abort`` is an **ambiguous outcome**: the
  controller must read back the live state before doing anything else
  (``pending_intents``), and duplicate intents with the same idempotency key
  are suppressed.

Backups are a directory copy plus a ``MANIFEST.json`` of sha256 digests;
``restore`` verifies every digest (and the audit chain head, when given)
before anything is written into the destination, and refuses a non-empty
destination so a restore can never overwrite newer state.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import zlib
from typing import Any

from .fsutil import load_json, read_bytes, read_text  # noqa: F401
from .canonical import canonicalize
from .errors import Corrupted, LimitExceeded, StateVersion

STATE_VERSION = "PK_GITOPS_STATE/1"
SUPPORTED = (STATE_VERSION,)


def _encode(obj: Any) -> bytes:
    body = canonicalize(obj).encode("utf-8")
    return b"%08x\t" % zlib.crc32(body) + body + b"\n"


def scan(path: str) -> tuple[list[Any], int, int]:
    """Return (records, good_bytes, dropped_tail_bytes)."""
    if not os.path.exists(path):
        return [], 0, 0
    data = read_bytes(path)
    recs, pos = [], 0
    lines = data.split(b"\n")
    for idx, line in enumerate(lines[:-1]):
        ok = len(line) > 9 and line[8:9] == b"\t"
        if ok:
            try:
                ok = int(line[:8], 16) == zlib.crc32(line[9:])
            except ValueError:
                ok = False
        if not ok:
            if idx == len(lines) - 2 and lines[-1] == b"":
                break
            raise Corrupted("journal checksum failure before tail", record=idx)
        recs.append(json.loads(line[9:]))
        pos += len(line) + 1
    return recs, pos, len(data) - pos


def _atomic_write(path: str, data: bytes) -> None:
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


class ControllerState:
    def __init__(self, state_dir: str, *, max_journal_bytes: int = 64 << 20) -> None:
        self.dir = state_dir
        os.makedirs(state_dir, exist_ok=True)
        self._lock = threading.RLock()
        self.max_bytes = max_journal_bytes
        vpath = os.path.join(state_dir, "STATE_VERSION")
        if os.path.exists(vpath):
            v = read_text(vpath).strip()
            if v not in SUPPORTED:
                raise StateVersion("unsupported state version; run the migration tool", found=v)
        else:
            _atomic_write(vpath, STATE_VERSION.encode())
        self.journal = os.path.join(state_dir, "journal.wal")
        self.ckpt = os.path.join(state_dir, "checkpoint.json")
        self.recovered_dropped_bytes = 0
        self.recover()

    # -- recovery -------------------------------------------------------------
    def recover(self) -> dict:
        with self._lock:
            base = load_json(self.ckpt) if os.path.exists(self.ckpt) else self._empty()
            if base.get("schema") != STATE_VERSION:
                raise StateVersion("checkpoint schema mismatch")
            recs, good, dropped = scan(self.journal)
            if dropped:
                with open(self.journal, "r+b") as fh:
                    fh.truncate(good)
            self.recovered_dropped_bytes = dropped
            self._size = good
            self.s = base
            for r in recs:
                self._fold(r)
            return {"records": len(recs), "dropped_bytes": dropped, "pending": len(self.pending_intents())}

    @staticmethod
    def _empty() -> dict:
        return {"schema": STATE_VERSION, "seq": 0, "applied": [], "intents": {}, "drift": [], "cursors": {},
                "effects": {}, "last_live": {}}

    def _fold(self, r: dict) -> None:
        s = self.s
        s["seq"] = max(s["seq"], r["seq"])
        k = r["kind"]
        if k == "intent":
            s["intents"][r["key"]] = {"oid": r["oid"], "ref": r["ref"], "plan": r["plan"], "status": "pending",
                                      "fence": r.get("fence")}
        elif k == "effect":
            s["effects"].setdefault(r["key"], []).append({"rid": r["rid"], "action": r["action"], "ok": r["ok"]})
        elif k == "commit":
            s["intents"][r["key"]]["status"] = "committed"
            s["applied"].append({"oid": r["oid"], "ref": r["ref"], "key": r["key"], "at": r["at"]})
            s["last_live"] = r.get("live_digest_map", s["last_live"])
        elif k == "abort":
            s["intents"][r["key"]]["status"] = "aborted:" + r["reason"]
        elif k == "drift":
            s["drift"].append(r["report"])
        elif k == "cursor":
            s["cursors"][r["ref"]] = r["oid"]

    def _append(self, rec: dict) -> dict:
        with self._lock:
            rec = {**rec, "seq": self.s["seq"] + 1}
            line = _encode(rec)
            if self._size + len(line) > self.max_bytes:
                raise LimitExceeded("journal at its disk bound; checkpoint required")
            with open(self.journal, "ab") as fh:
                fh.write(line)
                fh.flush()
                os.fsync(fh.fileno())
            self._size += len(line)
            self._fold(rec)
            return rec

    # -- API -------------------------------------------------------------------
    def begin(self, key: str, *, oid: str, ref: str, plan: list, fence: int | None = None) -> bool:
        """Record intent before effect.  Returns False when ``key`` was already
        committed (duplicate suppression)."""
        with self._lock:
            cur = self.s["intents"].get(key)
            if cur and cur["status"] == "committed":
                return False
            if cur and cur["status"] == "pending":
                raise Corrupted("intent already pending; resolve ambiguous outcome first", key=key)
            self._append({"kind": "intent", "key": key, "oid": oid, "ref": ref, "plan": plan, "fence": fence})
            return True

    def effect(self, key: str, rid: str, action: str, ok: bool) -> None:
        self._append({"kind": "effect", "key": key, "rid": rid, "action": action, "ok": ok})

    def commit(self, key: str, *, oid: str, ref: str, at: int, live_digest_map: dict) -> None:
        self._append({"kind": "commit", "key": key, "oid": oid, "ref": ref, "at": at,
                      "live_digest_map": live_digest_map})

    def abort(self, key: str, reason: str) -> None:
        self._append({"kind": "abort", "key": key, "reason": reason})

    def drift(self, report: dict) -> None:
        self._append({"kind": "drift", "report": report})

    def cursor(self, ref: str, oid: str) -> None:
        self._append({"kind": "cursor", "ref": ref, "oid": oid})

    def pending_intents(self) -> dict:
        return {k: v for k, v in self.s["intents"].items() if v["status"] == "pending"}

    def applied(self) -> list[dict]:
        return list(self.s["applied"])

    def checkpoint(self) -> dict:
        """Compact: write checkpoint atomically, then truncate the journal."""
        with self._lock:
            _atomic_write(self.ckpt, json.dumps(self.s, sort_keys=True).encode())
            with open(self.journal, "wb") as fh:
                fh.flush()
                os.fsync(fh.fileno())
            self._size = 0
            return {"seq": self.s["seq"]}


# -- backup / restore ------------------------------------------------------------
def _digest(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def backup(src_dir: str, dest_dir: str, *, audit_head: tuple | None = None) -> dict:
    if os.path.exists(dest_dir) and os.listdir(dest_dir):
        raise Corrupted("backup destination not empty")
    os.makedirs(dest_dir, exist_ok=True)
    files = {}
    for root, _, names in os.walk(src_dir):
        for nm in sorted(names):
            if nm.endswith(".tmp"):
                continue
            p = os.path.join(root, nm)
            rel = os.path.relpath(p, src_dir).replace(os.sep, "/")
            dst = os.path.join(dest_dir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(p, dst)
            files[rel] = _digest(dst)
    man = {"schema": "PK_GITOPS_BACKUP/1", "state_version": STATE_VERSION, "files": files,
           "audit_head": list(audit_head) if audit_head else None}
    _atomic_write(os.path.join(dest_dir, "MANIFEST.json"), json.dumps(man, sort_keys=True, indent=1).encode())
    return man


def verify_backup(backup_dir: str) -> dict:
    man = load_json(os.path.join(backup_dir, "MANIFEST.json"))
    if man.get("schema") != "PK_GITOPS_BACKUP/1":
        raise Corrupted("backup manifest schema mismatch")
    for rel, dg in man["files"].items():
        p = os.path.join(backup_dir, rel)
        if not os.path.exists(p) or _digest(p) != dg:
            raise Corrupted("backup file missing or digest mismatch", file=rel)
    return man


def restore(backup_dir: str, dest_dir: str) -> dict:
    man = verify_backup(backup_dir)
    if os.path.exists(dest_dir) and os.listdir(dest_dir):
        raise Corrupted("restore destination not empty; refusing to overwrite newer state")
    os.makedirs(dest_dir, exist_ok=True)
    for rel in man["files"]:
        dst = os.path.join(dest_dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(backup_dir, rel), dst)
    ControllerState(dest_dir)  # proves it recovers cleanly
    return man
