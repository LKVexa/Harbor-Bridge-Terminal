"""Durable, crash-consistent, tamper-evident offline decision journal.

GAP04-C03 (WAL), C04 (audit chain), C18 (one frame == one atomic transaction),
C20 (storage exhaustion), C07 (durable idempotency ids live in frames).

Frame format (PK_JOURNAL/1), one per line:
    <crc32 hex8> <canonical-json>\n
where the JSON object is {seq, gen, kind, body|enc, prev, h, mac}.
  * ``h``   = sha256(prev || canonical({seq,gen,kind,body|enc,prev}))  (hash chain)
  * ``mac`` = HMAC-SHA256(audit_key, h)                            (keyed integrity)
  * ``enc`` replaces ``body`` when a keyring is configured (AES-256-GCM, AAD = seq).

Recovery: a torn/partial *final* frame (crash mid-append) is truncated; any
invalid frame that is followed by further data is corruption -> fail closed.
Every append is fsync'ed before it is acknowledged.
"""
from __future__ import annotations

import binascii
import hashlib
import json
import os
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

from . import canonical, crypto
from .errors import AuditIntegrityError, Fenced, JournalCorrupt, StorageFull
from .faults import crashpoint, will_fire
from .storage import Keyring, atomic_write, fsync_dir

JOURNAL_VERSION = "PK_JOURNAL/1"
GENESIS = "sha256:" + "0" * 64
CONTROL_KINDS = frozenset({"checkpoint", "state", "freeze", "quarantine", "reconcile_ack", "reconcile_begin",
                           "config", "override", "storage_alarm", "clock", "fence"})


def _chain(prev: str, core: dict) -> str:
    return "sha256:" + hashlib.sha256(prev.encode() + canonical.dumps(core)).hexdigest()


@dataclass
class JournalLimits:
    max_bytes: int = 64 * 1024 * 1024
    reserve_bytes: int = 1 * 1024 * 1024        # reserved for control/audit frames (C20)
    min_disk_free_bytes: int = 16 * 1024 * 1024
    max_frame_bytes: int = 32 * 1024


class Journal:
    def __init__(self, directory: Path, keyring: Keyring, *, generation: Callable[[], int],
                 limits: JournalLimits | None = None, encrypt: bool = True,
                 on_pressure: Callable[[str, dict], None] | None = None):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "journal.wal"
        self.keyring = keyring
        self.limits = limits or JournalLimits()
        self.encrypt = encrypt
        self._generation = generation
        self._on_pressure = on_pressure or (lambda *_: None)
        self._lock = threading.RLock()
        self.head = GENESIS
        self.seq = 0
        self.base_seq = 0
        self.anchor = GENESIS
        self.size = 0
        self.truncated_tail = 0
        self._recover()

    # ------------------------------------------------------------- recovery
    def _parse_line(self, line: bytes) -> dict:
        if not line.endswith(b"\n"):
            raise ValueError("torn frame")
        crc, _, payload = line[:-1].partition(b" ")
        if len(crc) != 8 or f"{binascii.crc32(payload) & 0xffffffff:08x}".encode() != crc:
            raise ValueError("crc mismatch")
        return canonical.loads(payload)

    def _verify_frame(self, fr: dict, prev: str, expect_seq: int | None) -> None:
        core = {k: fr[k] for k in fr if k not in ("h", "mac")}
        if fr.get("prev") != prev:
            raise AuditIntegrityError("hash chain discontinuity", details={"seq": fr.get("seq")})
        if expect_seq is not None and fr.get("seq") != expect_seq:
            raise AuditIntegrityError("sequence gap", details={"seq": fr.get("seq"), "expected": expect_seq})
        if not crypto.ct_equal(_chain(prev, core), fr.get("h", "")):
            raise AuditIntegrityError("frame hash mismatch", details={"seq": fr.get("seq")})
        if not crypto.ct_equal(crypto.hmac256(bytes(self.keyring.audit_key), fr["h"].encode()), fr.get("mac", "")):
            raise AuditIntegrityError("frame MAC mismatch", details={"seq": fr.get("seq")})

    def _header(self, anchor: str, base_seq: int) -> bytes:
        doc = {"anchor": anchor, "base_seq": base_seq,
               "mac": crypto.hmac256(bytes(self.keyring.audit_key), f"{anchor}|{base_seq}".encode())}
        return b"A " + canonical.dumps(doc) + b"\n"

    def _recover(self) -> None:
        if not self.path.exists():
            atomic_write(self.path, b"")
            return
        data = self.path.read_bytes()
        lines = data.splitlines(keepends=True)
        pos, prev = 0, GENESIS
        if lines and lines[0].startswith(b"A "):
            try:
                hdr = canonical.loads(lines[0][2:-1])
            except Exception:
                raise JournalCorrupt("anchor header corrupt") from None
            if not crypto.ct_equal(crypto.hmac256(bytes(self.keyring.audit_key), f"{hdr['anchor']}|{hdr['base_seq']}".encode()), hdr["mac"]):
                raise AuditIntegrityError("anchor header MAC mismatch")
            prev, self.base_seq = hdr["anchor"], hdr["base_seq"]
            pos = len(lines[0])
            lines = lines[1:]
        self.anchor = prev
        seq = self.base_seq + 1
        for i, line in enumerate(lines):
            try:
                fr = self._parse_line(line)
            except Exception as e:
                if i == len(lines) - 1:  # torn tail from a crash mid-append
                    self.truncated_tail = len(data) - pos
                    with open(self.path, "r+b") as f:
                        f.truncate(pos)
                        f.flush()
                        os.fsync(f.fileno())
                    break
                raise JournalCorrupt(f"corrupt frame at offset {pos}: {e}", details={"offset": pos}) from None
            self._verify_frame(fr, prev, seq)
            prev, seq = fr["h"], fr["seq"] + 1
            pos += len(line)
        self.head, self.seq, self.size = prev, seq - 1, pos

    # ------------------------------------------------------------- append
    def usage(self) -> dict:
        du = shutil.disk_usage(self.dir)
        return {"bytes": self.size, "max_bytes": self.limits.max_bytes, "reserve_bytes": self.limits.reserve_bytes,
                "utilization_ppm": self.size * 1_000_000 // self.limits.max_bytes, "disk_free": du.free, "seq": self.seq}

    def append(self, kind: str, body: dict, *, generation: int | None = None) -> dict:
        with self._lock:
            gen = self._generation() if generation is None else generation
            persisted = self._generation()
            if gen < persisted:
                raise Fenced("stale controller generation", details={"gen": gen, "current": persisted})
            seq = self.seq + 1
            core: dict[str, Any] = {"seq": seq, "gen": gen, "kind": kind, "prev": self.head}
            if self.encrypt:
                core["enc"] = self.keyring.encrypt(canonical.dumps(body), f"seq:{seq}".encode())
            else:
                core["body"] = body
            h = _chain(self.head, core)
            fr = dict(core, h=h, mac=crypto.hmac256(bytes(self.keyring.audit_key), h.encode()))
            payload = canonical.dumps(fr)
            line = f"{binascii.crc32(payload) & 0xffffffff:08x} ".encode() + payload + b"\n"
            self._admit(kind, len(line))
            crashpoint("journal.before_write")
            with open(self.path, "ab") as f:
                if will_fire("journal.partial_write"):
                    f.write(line[: len(line) // 2]); f.flush(); os.fsync(f.fileno())
                crashpoint("journal.partial_write")
                f.write(line)
                f.flush()
                os.fsync(f.fileno())
            crashpoint("journal.after_fsync")
            self.head, self.seq, self.size = h, seq, self.size + len(line)
            return {"seq": seq, "h": h, "gen": gen}

    def _admit(self, kind: str, n: int) -> None:
        L = self.limits
        if n > L.max_frame_bytes:
            raise StorageFull("frame exceeds max frame size", details={"bytes": n})
        free = shutil.disk_usage(self.dir).free
        budget = L.max_bytes if kind in CONTROL_KINDS else L.max_bytes - L.reserve_bytes
        if self.size + n > budget or free - n < (0 if kind in CONTROL_KINDS else L.min_disk_free_bytes):
            self._on_pressure("journal_full", {"kind": kind, **self.usage()})
            raise StorageFull("durable journal cannot accept frame", details={"kind": kind, "size": self.size})
        if self.size + n > 0.8 * L.max_bytes:
            self._on_pressure("journal_high_watermark", self.usage())

    # ------------------------------------------------------------- read/export
    def frames(self, *, decrypt: bool = True) -> Iterator[dict]:
        with self._lock:
            data = self.path.read_bytes()
        for line in data.splitlines(keepends=True):
            if line.startswith(b"A "):
                continue
            fr = self._parse_line(line)
            if decrypt and "enc" in fr:
                fr = dict(fr, body=json.loads(self.keyring.decrypt(fr["enc"], f"seq:{fr['seq']}".encode())))
            yield fr

    def export(self, after_seq: int = 0) -> dict:
        """Verifiable export for reconnect (C04): anchor + frames + head."""
        anchor, out = self.anchor, []
        for f in self.frames(decrypt=False):
            if f["seq"] <= after_seq:
                anchor = f["h"]
            else:
                out.append(f)
        return {"version": JOURNAL_VERSION, "anchor": anchor, "head": self.head, "frames": out}

    @staticmethod
    def verify_export(export: dict, audit_key: bytes) -> str:
        prev, expect = export["anchor"], None
        for fr in export["frames"]:
            core = {k: fr[k] for k in fr if k not in ("h", "mac")}
            if fr["prev"] != prev or (expect is not None and fr["seq"] != expect):
                raise AuditIntegrityError("export chain discontinuity", details={"seq": fr["seq"]})
            if _chain(prev, core) != fr["h"] or not crypto.ct_equal(crypto.hmac256(audit_key, fr["h"].encode()), fr["mac"]):
                raise AuditIntegrityError("export frame integrity failure", details={"seq": fr["seq"]})
            prev, expect = fr["h"], fr["seq"] + 1
        if prev != export["head"]:
            raise AuditIntegrityError("export head mismatch")
        return prev

    # ------------------------------------------------------------- compaction
    def compact(self, upto_seq: int, archive_dir: Path | None = None) -> dict:
        """Drop acknowledged frames <= upto_seq without re-chaining the rest: the new
        file begins with a MAC'd anchor header naming the last dropped hash, and is
        written atomically, so a crash leaves either the old or the new segment."""
        with self._lock:
            raw = [l for l in self.path.read_bytes().splitlines(keepends=True) if not l.startswith(b"A ")]
            keep, anchor, base = [], self.anchor, self.base_seq
            for line in raw:
                fr = self._parse_line(line)
                if fr["seq"] <= upto_seq:
                    anchor, base = fr["h"], fr["seq"]
                else:
                    keep.append(line)
            if base == self.base_seq:
                return {"dropped": 0}
            if archive_dir is not None:
                Path(archive_dir).mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.path, Path(archive_dir) / f"journal-upto-{base}.wal")
            blob = self._header(anchor, base) + b"".join(keep)
            crashpoint("compact.before_replace")
            atomic_write(self.path, blob)
            dropped = base - self.base_seq
            self.anchor, self.base_seq, self.size = anchor, base, len(blob)
            return {"dropped": dropped, "anchor": anchor, "head": self.head}
