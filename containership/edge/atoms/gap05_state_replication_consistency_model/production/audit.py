"""MC10 tamper-evident audit ledger and MC11 bounded audit/quarantine retention.

Each record carries ``prev`` (hash of the previous record) and its own ``hash`` =
sha256(canonical(record without hash)).  After every append the ledger head
``{seq, hash}`` is signed with the node's Ed25519 key.  A hash chain alone cannot detect
*tail truncation* (a shortened chain is still a valid chain), so verification takes an
externally retained signed head and fails if the chain does not reach it.

Retention: the active segment is bounded (``segment_records``).  When it fills, the
segment is sealed, exported to the archive directory with its boundary hashes, verified
there, and only then removed from the active area.  If the archive is unavailable or
the total bound is reached, the ledger *refuses new events* (``CapacityError``) - the
caller must then refuse the write that needed auditing, so an accepted write is never
left unaudited and nothing already recorded is dropped.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .durable import atomic_write, fsync_dir
from .errors import CapacityError, IntegrityError
from .identity import b64, unb64
from .schemas import canonical_bytes

GENESIS = "0" * 64
AUDIT_FORMAT = "GAP05_AUDIT/1"


def record_hash(record: dict) -> str:
    return hashlib.sha256(canonical_bytes({k: v for k, v in record.items() if k != "hash"})).hexdigest()


class AuditLedger:
    def __init__(self, directory: Path, signer: Ed25519PrivateKey, *, segment_records: int = 10_000,
                 max_active_segments: int = 4, archive_dir: Path | None = None):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir = Path(archive_dir) if archive_dir else None
        self.signer = signer
        self.segment_records = segment_records
        self.max_active_segments = max_active_segments
        self._lock = threading.Lock()
        self.pressure = 0.0
        self._load()

    # -- storage ---------------------------------------------------------------
    def _segments(self) -> list[Path]:
        return sorted(self.dir.glob("audit-*.jsonl"))

    def _load(self) -> None:
        segs = self._segments()
        if not segs:
            self._seg = self.dir / "audit-00000001.jsonl"
            self._seg.touch()
            self.head = {"seq": 0, "hash": GENESIS}
            self._seg_count = 0
            return
        self._seg = segs[-1]
        last = None
        count = 0
        with open(self._seg, "rb") as fh:
            lines = fh.read().splitlines()
        for line in lines:
            last = json.loads(line)
            count += 1
        self._seg_count = count
        if last is None:
            hdr = self._segment_start(self._seg)
            self.head = hdr
        else:
            self.head = {"seq": last["seq"], "hash": last["hash"]}

    def last_field(self, name: str):
        """Most recent value of ``name`` in the active segment (recovery helper)."""
        for line in reversed(self._seg.read_bytes().splitlines()):
            rec = json.loads(line)
            if name in rec:
                return rec[name]
        return None

    def _segment_start(self, seg: Path) -> dict:
        marker = seg.with_suffix(".start")
        if marker.exists():
            return json.loads(marker.read_bytes())
        return {"seq": 0, "hash": GENESIS}

    def ensure_capacity(self) -> None:
        """Rotate/archive ahead of time so the next append cannot fail for capacity."""
        with self._lock:
            if self._seg_count >= self.segment_records:
                self._rotate()

    def append(self, event: str, **fields) -> dict:
        with self._lock:
            if self._seg_count >= self.segment_records:
                self._rotate()
            record = {"format": AUDIT_FORMAT, "seq": self.head["seq"] + 1, "prev": self.head["hash"],
                      "event": event, **fields}
            record["hash"] = record_hash(record)
            with open(self._seg, "ab") as fh:
                fh.write(canonical_bytes(record) + b"\n")
                fh.flush()
                os.fsync(fh.fileno())
            self._seg_count += 1
            self.head = {"seq": record["seq"], "hash": record["hash"]}
            self._update_pressure()
            return record

    def _update_pressure(self) -> None:
        total = self.segment_records * self.max_active_segments
        used = (len(self._segments()) - 1) * self.segment_records + self._seg_count
        self.pressure = used / total

    def _rotate(self) -> None:
        segs = self._segments()
        if len(segs) >= self.max_active_segments:
            if not self.archive_sealed():
                raise CapacityError("audit ledger full and archive unavailable; refusing new events",
                                    code="CAP_AUDIT_FULL")
        nxt = self.dir / f"audit-{int(self._seg.stem.split('-')[1]) + 1:08d}.jsonl"
        atomic_write(nxt.with_suffix(".start"), canonical_bytes(self.head))
        nxt.touch()
        fsync_dir(self.dir)
        self._seg, self._seg_count = nxt, 0

    def archive_sealed(self) -> bool:
        """Export sealed segments to the archive, verify the copy, then remove them."""
        if self.archive_dir is None:
            return False
        try:
            self.archive_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False
        moved = False
        for seg in self._segments()[:-1]:
            data = seg.read_bytes()
            start = self._segment_start(seg)
            dest = self.archive_dir / seg.name
            atomic_write(dest, data)
            atomic_write(dest.with_suffix(".start"), canonical_bytes(start))
            if hashlib.sha256(dest.read_bytes()).digest() != hashlib.sha256(data).digest():
                return False
            seg.unlink()
            seg.with_suffix(".start").unlink(missing_ok=True)
            moved = True
        fsync_dir(self.dir)
        return moved

    # -- signing ---------------------------------------------------------------
    def signed_head(self) -> dict:
        head = dict(self.head)
        return {"head": head, "sig": b64(self.signer.sign(canonical_bytes(head)))}

    # -- verification ----------------------------------------------------------
    @staticmethod
    def verify(directories, public_key: Ed25519PublicKey, signed_head: dict) -> dict:
        """Verify the full chain across archive + active directories against a signed head."""
        try:
            public_key.verify(unb64(signed_head["sig"]), canonical_bytes(signed_head["head"]))
        except (InvalidSignature, KeyError) as exc:
            raise IntegrityError("signed head signature invalid", code="CORR_AUDIT_HEAD_SIG") from exc
        segs = sorted({p.name: p for d in directories for p in Path(d).glob("audit-*.jsonl")}.values(),
                      key=lambda p: p.name)
        prev, seq, count = GENESIS, 0, 0
        for seg in segs:
            start_marker = seg.with_suffix(".start")
            if start_marker.exists():
                start = json.loads(start_marker.read_bytes())
                if count == 0:
                    prev, seq = start["hash"], start["seq"]
                elif start["hash"] != prev:
                    raise IntegrityError(f"segment {seg.name} does not continue chain", code="CORR_AUDIT_SEGMENT")
            for line in seg.read_bytes().splitlines():
                rec = json.loads(line)
                if rec.get("prev") != prev or rec.get("seq") != seq + 1:
                    raise IntegrityError(f"chain break at seq {seq + 1}", code="CORR_AUDIT_CHAIN")
                if record_hash(rec) != rec.get("hash"):
                    raise IntegrityError(f"record {rec.get('seq')} altered", code="CORR_AUDIT_TAMPER")
                prev, seq, count = rec["hash"], rec["seq"], count + 1
        head = signed_head["head"]
        if seq != head["seq"] or prev != head["hash"]:
            raise IntegrityError(f"chain ends at {seq}, signed head is {head['seq']} (truncation or fork)",
                                 code="CORR_AUDIT_TRUNCATED")
        return {"records_verified": count, "head_seq": seq}
