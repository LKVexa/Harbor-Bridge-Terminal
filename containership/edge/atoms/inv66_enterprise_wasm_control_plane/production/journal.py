"""Durable, hash-chained, anchor-signed journal — the INV-66 source of truth.

Covers MC-005 (source of truth), MC-035 (tamper-evident anchoring), MC-038 (crash
recovery/replay), MC-046 (bounded retention), MC-070 (query/export), MC-034 (at-rest
encryption of record bodies).

Layout under ``root``::

    segments/000001.jsonl ...   append-only records, one JSON object per line
    summaries.jsonl             one line per compacted segment (range + boundary hash)
    anchors/                    signed checkpoints (seq, hash) — the external anchor sink
    holds.json                  legal holds (segments under hold are never compacted)

Every record is ``{seq, prev, ts, kind, body|sealed, hash}`` with
``hash = sha256("PK_ECP_AUDIT/2\\0" || canonical(record without hash))``.

Recovery rules on open (fail closed except for the one safe case):

* a torn *final* line (no trailing newline or unparseable last line) is the
  signature of a crash mid-append: it is truncated and reported in
  ``recovery["truncated_tail_bytes"]``; that record was never acknowledged
  because ``append`` returns only after write+fsync.
* any other break (bad hash, gap, unparseable interior line) raises
  ``ECP_STORE_CORRUPT`` — restore from backup (runbook RB-BACKUP).

A hash chain alone cannot detect an actor who rewrites *and recomputes* the whole
chain, nor tail truncation.  ``anchor()`` therefore signs ``(seq, hash)`` with an
Ed25519 key that the journal writer role does not need to hold, and ``verify``
checks every anchor: a recomputed chain no longer matches the signed hashes, and
a truncated chain ends below the newest anchor.
"""
from __future__ import annotations

import fcntl
import json
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator, Optional

from .errors import EcpError
from .keys import Keyring, Signer, verify_sig
from .util import atomic_write, canonical_json, now, sha256_hex

DOMAIN = b"PK_ECP_AUDIT/2\0"
GENESIS = "0" * 64
JOURNAL_SCHEMA = "PK_ECP_AUDIT/2"


def _hash(rec: dict[str, Any]) -> str:
    return sha256_hex(DOMAIN + canonical_json(rec))


class Journal:
    def __init__(self, root: Path, *, segment_records: int = 10_000, fsync: bool = True,
                 keyring: Optional[Keyring] = None, clock: Callable[[], float] = now,
                 writer_fault: Optional[Callable[[], None]] = None):
        self.root = Path(root)
        self.seg_dir = self.root / "segments"
        self.anchor_dir = self.root / "anchors"
        self.seg_dir.mkdir(parents=True, exist_ok=True)
        self.anchor_dir.mkdir(parents=True, exist_ok=True)
        self.segment_records = int(segment_records)
        self.fsync = fsync
        self.keyring = keyring
        self.clock = clock
        self._fault = writer_fault  # test hook: raise OSError to simulate disk-full/IO failure
        self._lock = threading.RLock()
        self.recovery: dict[str, Any] = {}
        self._seq, self._head = 0, GENESIS
        self._disk_mark: tuple = ()
        self._recover()

    # ------------------------------------------------------------------ recovery
    def _segments(self) -> list[Path]:
        return sorted(self.seg_dir.glob("*.jsonl"))

    def _summaries(self) -> list[dict[str, Any]]:
        p = self.root / "summaries.jsonl"
        if not p.exists():
            return []
        return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]

    def _recover(self) -> None:
        truncated = 0
        seq, head = 0, GENESIS
        sums = self._summaries()
        if sums:
            seq, head = sums[-1]["last_seq"], sums[-1]["last_hash"]
        segs = self._segments()
        for i, seg in enumerate(segs):
            raw = seg.read_bytes()
            lines = raw.split(b"\n")
            tail = lines.pop()  # bytes after the last newline ('' when well-formed)
            last_seg = i == len(segs) - 1
            if tail:
                if not last_seg:
                    raise EcpError("ECP_STORE_CORRUPT", "unterminated record in sealed segment", index=i)
                truncated += len(tail)
            good_len = 0
            for n, line in enumerate(lines):
                try:
                    rec = json.loads(line)
                    h = rec.pop("hash")
                    ok = rec.get("seq") == seq + 1 and rec.get("prev") == head and h == _hash(rec)
                except (ValueError, KeyError, TypeError):
                    ok = False
                    h = None
                if not ok:
                    if last_seg and n == len(lines) - 1 and not tail:
                        # last complete-looking line is garbage: torn write that happened to end in \n
                        truncated += len(line) + 1
                        break
                    raise EcpError("ECP_STORE_CORRUPT", "journal chain broken", index=seq + 1)
                seq, head = rec["seq"], h
                good_len += len(line) + 1
            if last_seg and truncated:
                with seg.open("r+b") as fh:
                    fh.truncate(good_len)
                    fh.flush()
                    os.fsync(fh.fileno())
        self._seq, self._head = seq, head
        self._disk_mark = self._mark()
        self.recovery = {"head_seq": seq, "head_hash": head, "truncated_tail_bytes": truncated,
                         "segments": len(segs), "compacted_segments": len(sums)}

    def _mark(self) -> tuple:
        segs = self._segments()
        return (segs[-1].name, segs[-1].stat().st_size) if segs else ()

    @contextmanager
    def _flock(self):
        """Cross-process exclusive section: two writers can never fork the chain."""
        fd = os.open(str(self.root / "journal.lock"), os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def reload_tail(self) -> None:
        """Re-derive the head from disk (another fenced writer may have appended)."""
        with self._lock:
            self._recover()

    # ------------------------------------------------------------------ append
    def _current_segment(self) -> Path:
        segs = self._segments()
        if segs:
            last = segs[-1]
            first_seq = int(last.stem)
            if self._seq - first_seq + 1 < self.segment_records:
                return last
        return self.seg_dir / f"{self._seq + 1:012d}.jsonl"

    def append(self, kind: str, body: dict[str, Any]) -> dict[str, Any]:
        """Durably append; returns only after write+fsync. Raises ECP_AUDIT_UNAVAILABLE on IO failure."""
        with self._lock:
            rec: dict[str, Any] = {"schema": JOURNAL_SCHEMA, "seq": self._seq + 1, "prev": self._head,
                                   "ts": round(self.clock(), 6), "kind": kind}
            if self.keyring is not None:
                rec["sealed"] = self.keyring.seal(canonical_json(body), str(rec["seq"]).encode())
            else:
                rec["body"] = body
            h = _hash(rec)
            line = json.dumps({**rec, "hash": h}, sort_keys=True, separators=(",", ":")) + "\n"
            with self._flock():
                if self._mark() != self._disk_mark:  # another process appended: re-derive head first
                    self._recover()
                    rec["seq"], rec["prev"] = self._seq + 1, self._head
                    if "sealed" in rec and self.keyring is not None:
                        rec["sealed"] = self.keyring.seal(canonical_json(body), str(rec["seq"]).encode())
                    h = _hash(rec)
                    line = json.dumps({**rec, "hash": h}, sort_keys=True, separators=(",", ":")) + "\n"
                seg = self._current_segment()
                try:
                    if self._fault:
                        self._fault()
                    with seg.open("ab") as fh:
                        fh.write(line.encode())
                        fh.flush()
                        if self.fsync:
                            os.fsync(fh.fileno())
                except OSError:
                    raise EcpError("ECP_AUDIT_UNAVAILABLE", "journal append failed", dependency="journal") from None
                self._seq, self._head = rec["seq"], h
                self._disk_mark = self._mark()
            return {**rec, "hash": h}

    @property
    def head(self) -> tuple[int, str]:
        with self._lock:
            return self._seq, self._head

    # ------------------------------------------------------------------ read
    def body(self, rec: dict[str, Any]) -> dict[str, Any]:
        if "sealed" in rec:
            if self.keyring is None:
                raise EcpError("ECP_STORE_CORRUPT", "sealed record but no keyring", index=rec.get("seq"))
            return json.loads(self.keyring.open(rec["sealed"], str(rec["seq"]).encode()))
        return rec["body"]

    def records(self, from_seq: int = 1, to_seq: Optional[int] = None) -> Iterator[dict[str, Any]]:
        for seg in self._segments():
            with seg.open("rb") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    if rec["seq"] < from_seq:
                        continue
                    if to_seq is not None and rec["seq"] > to_seq:
                        return
                    yield rec

    def replay(self) -> Iterator[tuple[str, dict[str, Any], dict[str, Any]]]:
        for rec in self.records():
            yield rec["kind"], self.body(rec), rec

    # ------------------------------------------------------------------ anchors
    def anchor(self, signer: Signer) -> dict[str, Any]:
        with self._lock:
            seq, h = self._seq, self._head
        a = {"schema": "PK_ECP_ANCHOR/1", "seq": seq, "hash": h, "ts": round(self.clock(), 6),
             "key_id": signer.key_id, "public_key": signer.public_b64()}
        a["sig"] = signer.sign(canonical_json({k: a[k] for k in ("schema", "seq", "hash", "ts", "key_id")}))
        atomic_write(self.anchor_dir / f"{seq:012d}.json", canonical_json(a), fsync=self.fsync)
        return a

    def anchors(self) -> list[dict[str, Any]]:
        return [json.loads(p.read_bytes()) for p in sorted(self.anchor_dir.glob("*.json"))]

    def verify(self, trusted_keys: Optional[dict[str, str]] = None,
               anchors: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
        """Full verification: chain continuity + every anchor signed by a trusted key and still matching."""
        sums = self._summaries()
        seq, head = (sums[-1]["last_seq"], sums[-1]["last_hash"]) if sums else (0, GENESIS)
        hashes: dict[int, str] = {s["last_seq"]: s["last_hash"] for s in sums}
        count = 0
        for rec in self.records():
            h = rec.pop("hash")
            if rec["seq"] != seq + 1 or rec["prev"] != head or h != _hash(rec):
                raise EcpError("ECP_AUDIT_TAMPERED", "journal chain broken", index=rec.get("seq"))
            seq, head = rec["seq"], h
            hashes[seq] = h
            count += 1
        anchors = self.anchors() if anchors is None else anchors
        floor = sums[-1]["last_seq"] if sums else 0
        for a in anchors:
            body = canonical_json({k: a[k] for k in ("schema", "seq", "hash", "ts", "key_id")})
            pub = (trusted_keys or {}).get(a["key_id"]) if trusted_keys is not None else a.get("public_key")
            if not pub or not verify_sig(pub, a["sig"], body):
                raise EcpError("ECP_AUDIT_TAMPERED", "anchor signature invalid or untrusted key", key_id=a["key_id"])
            if a["seq"] > seq:
                raise EcpError("ECP_AUDIT_TAMPERED", "journal truncated below a signed anchor",
                               observed=seq, limit=a["seq"])
            if a["seq"] >= floor and a["seq"] > 0 and hashes.get(a["seq"]) != a["hash"]:
                raise EcpError("ECP_AUDIT_TAMPERED", "anchored record rewritten", index=a["seq"])
        return {"result": "INTACT", "records": count, "head_seq": seq, "head_hash": head,
                "anchors_verified": len(anchors), "compacted_segments": len(sums)}

    # ------------------------------------------------------------------ retention
    def holds(self) -> dict[str, Any]:
        p = self.root / "holds.json"
        return json.loads(p.read_bytes()) if p.exists() else {}

    def set_hold(self, hold_id: str, from_seq: int, to_seq: int, reason: str) -> None:
        h = self.holds()
        h[hold_id] = {"from_seq": from_seq, "to_seq": to_seq, "reason": reason[:256]}
        atomic_write(self.root / "holds.json", canonical_json(h), fsync=self.fsync)

    def release_hold(self, hold_id: str) -> None:
        h = self.holds()
        h.pop(hold_id, None)
        atomic_write(self.root / "holds.json", canonical_json(h), fsync=self.fsync)

    def compact(self, keep_after_seq: int, archive: Optional[Callable[[Path], None]] = None) -> dict[str, Any]:
        """Drop whole sealed segments ending at or below ``keep_after_seq`` (retention).

        A segment overlapping a legal hold, or the active segment, is never dropped.
        Each dropped segment leaves a summary line so the chain stays verifiable.
        ``archive`` (e.g. copy to WORM storage) runs before deletion; if it raises,
        nothing is deleted.
        """
        dropped = []
        with self._lock:
            segs = self._segments()
            holds = list(self.holds().values())
            for seg in segs[:-1]:
                recs = list(self._read_seg(seg))
                if not recs:
                    continue
                first, last = recs[0]["seq"], recs[-1]["seq"]
                if last > keep_after_seq:
                    break
                if any(not (h["to_seq"] < first or h["from_seq"] > last) for h in holds):
                    break
                if archive:
                    archive(seg)
                summary = {"segment": seg.name, "first_seq": first, "last_seq": last,
                           "last_hash": recs[-1]["hash"], "compacted_at": round(self.clock(), 6)}
                with (self.root / "summaries.jsonl").open("a") as fh:
                    fh.write(json.dumps(summary, sort_keys=True) + "\n")
                    fh.flush()
                    if self.fsync:
                        os.fsync(fh.fileno())
                seg.unlink()
                dropped.append(summary)
        return {"dropped_segments": len(dropped), "summaries": dropped}

    @staticmethod
    def _read_seg(seg: Path) -> Iterator[dict[str, Any]]:
        with seg.open("rb") as fh:
            for line in fh:
                if line.strip():
                    yield json.loads(line)

    def disk_bytes(self) -> int:
        return sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file())

    # ------------------------------------------------------------------ export / query
    def query(self, *, kind: Optional[str] = None, tenant: Optional[str] = None, lattice: Optional[str] = None,
              outcome: Optional[bool] = None, from_seq: int = 1, to_seq: Optional[int] = None,
              limit: int = 1000, from_ts: Optional[float] = None, to_ts: Optional[float] = None,
              subject: Optional[str] = None, request_id: Optional[str] = None,
              decision_id: Optional[str] = None) -> list[dict[str, Any]]:
        out = []
        for rec in self.records(from_seq, to_seq):
            if kind and rec["kind"] != kind:
                continue
            if (from_ts is not None and rec["ts"] < from_ts) or (to_ts is not None and rec["ts"] > to_ts):
                continue
            b = self.body(rec)
            if subject and ((b.get("principal") or {}).get("subject") != subject and b.get("by") != subject):
                continue
            if request_id and b.get("request_id") != request_id:
                continue
            if decision_id and b.get("decision_id") != decision_id:
                continue
            if tenant and b.get("tenant") != tenant:
                continue
            if lattice and b.get("lattice") != lattice:
                continue
            if outcome is not None and b.get("admitted") is not outcome:
                continue
            out.append({"seq": rec["seq"], "ts": rec["ts"], "kind": rec["kind"], "hash": rec["hash"], "body": b})
            if len(out) >= min(limit, 10_000):
                break
        return out

    def export(self, from_seq: int = 1, to_seq: Optional[int] = None) -> dict[str, Any]:
        """Self-verifying export: raw records + the anchors covering them (SIEM/legal)."""
        recs = list(self.records(from_seq, to_seq))
        return {"schema": "PK_ECP_AUDIT_EXPORT/1", "from_seq": from_seq,
                "to_seq": recs[-1]["seq"] if recs else from_seq - 1,
                "records": recs, "anchors": [a for a in self.anchors()
                                             if recs and recs[0]["seq"] <= a["seq"] <= recs[-1]["seq"]]}


def verify_export(export: dict[str, Any], trusted_keys: dict[str, str]) -> dict[str, Any]:
    recs = export["records"]
    by_seq = {}
    prev = recs[0]["prev"] if recs else GENESIS
    for n, r in enumerate(recs):
        r = dict(r)
        h = r.pop("hash")
        if r["prev"] != prev or h != _hash(r) or (n and r["seq"] != recs[n - 1]["seq"] + 1):
            raise EcpError("ECP_AUDIT_TAMPERED", "export chain broken", index=r.get("seq"))
        prev = h
        by_seq[r["seq"]] = h
    for a in export["anchors"]:
        body = canonical_json({k: a[k] for k in ("schema", "seq", "hash", "ts", "key_id")})
        pub = trusted_keys.get(a["key_id"])
        if not pub or not verify_sig(pub, a["sig"], body) or by_seq.get(a["seq"]) != a["hash"]:
            raise EcpError("ECP_AUDIT_TAMPERED", "export anchor invalid", key_id=a["key_id"])
    return {"result": "INTACT", "records": len(recs), "anchors": len(export["anchors"])}
