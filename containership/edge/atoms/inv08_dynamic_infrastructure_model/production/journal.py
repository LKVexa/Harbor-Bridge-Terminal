"""Component 44 (and 27's idempotent op journal) - write-ahead operation
journal with periodic consistent snapshots and a replay cursor.

Formats
* WAL ``wal.jsonl`` (``PK_DYN_WAL/1``): one canonical-JSON line per record
  {"seq": int (strictly +1), "op_id": str, "status": PENDING|DONE|FAILED|
   TIMED_OUT|ROLLED_BACK, "kind": str, "node_id": str, "ts": float,
   "detail": obj, "crc": sha256 of the other fields}.  Appended + fsynced
  before the side effect it describes (PENDING) and after it (DONE/FAILED).
* Snapshot ``snap-<seq:012d>.json`` (``PK_DYN_SNAPSHOT/1``): {"body":{"schema",
  "cursor": last seq folded in, "state": {...}}, "digest"} written atomically.
  The snapshot's cursor is the replay checkpoint: recovery loads the newest
  valid snapshot and replays WAL records with seq > cursor.
* Recovery: a torn/corrupt tail line (crash mid-write) is truncated and
  reported; corruption *before* the tail (a valid record after a bad one) is
  NOT silently dropped - it raises ``INV08.JOURNAL.CORRUPT``.  A corrupt
  snapshot falls back to the previous one (keep=``keep`` snapshots) and the WAL
  is only compacted up to the *oldest* kept snapshot so fallback is lossless.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .core import Inv08Error, Outcome, canonical, digest, sha256_hex
from .leasestore import _atomic_write

WAL_SCHEMA = "PK_DYN_WAL/1"
SNAP_SCHEMA = "PK_DYN_SNAPSHOT/1"
STATUSES = ("PENDING", "DONE", "FAILED", "TIMED_OUT", "ROLLED_BACK")


def _crc(rec: dict) -> str:
    return sha256_hex(canonical({k: v for k, v in rec.items() if k != "crc"}))


def apply(state: dict, rec: dict) -> dict:
    ops = state.setdefault("ops", {})
    cur = ops.get(rec["op_id"], {"kind": rec["kind"], "node_id": rec["node_id"], "started": rec["ts"]})
    cur = dict(cur, status=rec["status"], updated=rec["ts"], seq=rec["seq"], detail=rec.get("detail", {}))
    ops[rec["op_id"]] = cur
    return state


class Journal:
    def __init__(self, directory: str | os.PathLike, *, keep: int = 2) -> None:
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.wal = self.dir / "wal.jsonl"
        self.keep = max(1, keep)
        self.recovery_report: dict = {}
        self.state, self.seq = self._recover()

    # ------------------------------------------------------------ write
    def append(self, op_id: str, status: str, *, kind: str, node_id: str, ts: float,
               detail: dict | None = None) -> dict:
        if status not in STATUSES:
            raise ValueError(f"bad status {status}")
        rec = {"seq": self.seq + 1, "op_id": op_id, "status": status, "kind": kind,
               "node_id": node_id, "ts": ts, "detail": detail or {}}
        rec["crc"] = _crc(rec)
        with open(self.wal, "ab") as fh:
            fh.write(canonical(rec) + b"\n")
            fh.flush()
            os.fsync(fh.fileno())
        self.seq = rec["seq"]
        apply(self.state, rec)
        return rec

    def snapshot(self) -> Path:
        body = {"schema": SNAP_SCHEMA, "cursor": self.seq, "state": self.state}
        path = self.dir / f"snap-{self.seq:012d}.json"
        _atomic_write(path, json.dumps({"body": body, "digest": digest(body)}, sort_keys=True).encode())
        snaps = self._snapshots()
        for old in snaps[:-self.keep]:
            old.unlink()
        self._compact(self._read_snap_cursor(self._snapshots()[0]))
        return path

    def _compact(self, upto: int | None) -> None:
        if upto is None:
            return
        recs, _ = self._read_wal()
        keep = [r for r in recs if r["seq"] > upto]
        _atomic_write(self.wal, b"".join(canonical(r) + b"\n" for r in keep))

    # ------------------------------------------------------------ read / recover
    def _snapshots(self) -> list[Path]:
        return sorted(self.dir.glob("snap-*.json"))

    @staticmethod
    def _load_snap(path: Path) -> dict | None:
        try:
            doc = json.loads(path.read_bytes())
            body = doc["body"]
            if doc["digest"] != digest(body) or body["schema"] != SNAP_SCHEMA:
                return None
            return body
        except (ValueError, KeyError, TypeError):
            return None

    def _read_snap_cursor(self, path: Path) -> int | None:
        b = self._load_snap(path)
        return b["cursor"] if b else None

    def _read_wal(self) -> tuple[list[dict], dict]:
        if not self.wal.exists():
            return [], {"truncated_tail_bytes": 0}
        raw = self.wal.read_bytes()
        lines = raw.split(b"\n")
        recs, good_len, bad_at = [], 0, None
        for i, line in enumerate(lines):
            if not line:
                good_len += 1 if i < len(lines) - 1 else 0
                continue
            ok = False
            try:
                rec = json.loads(line)
                ok = isinstance(rec, dict) and rec.get("crc") == _crc(rec) and \
                    (not recs or rec["seq"] == recs[-1]["seq"] + 1)
            except (ValueError, KeyError, TypeError):
                ok = False
            if not ok:
                bad_at = i
                break
            recs.append(rec)
            good_len += len(line) + 1
        if bad_at is not None:
            rest = [ln for ln in lines[bad_at + 1:] if ln.strip()]
            if rest:
                raise Inv08Error("INV08.JOURNAL.CORRUPT",
                                 f"corrupt WAL record at line {bad_at + 1} followed by more records",
                                 outcome=Outcome.OPERATOR_REQUIRED, severity="critical",
                                 remediation="restore from snapshot + provider reconciliation; WAL preserved",
                                 details={"line": bad_at + 1})
        return recs, {"truncated_tail_bytes": len(raw) - good_len if bad_at is not None else 0,
                      "good_len": good_len}

    def _recover(self) -> tuple[dict, int]:
        report = {"snapshot": None, "snapshots_rejected": [], "replayed": 0, "truncated_tail_bytes": 0}
        state, cursor = {}, 0
        for snap in reversed(self._snapshots()):
            body = self._load_snap(snap)
            if body is None:
                report["snapshots_rejected"].append(snap.name)
                continue
            state, cursor = body["state"], body["cursor"]
            report["snapshot"] = snap.name
            break
        recs, info = self._read_wal()
        if info["truncated_tail_bytes"]:
            with open(self.wal, "r+b") as fh:
                fh.truncate(info["good_len"])
                fh.flush()
                os.fsync(fh.fileno())
            report["truncated_tail_bytes"] = info["truncated_tail_bytes"]
        if recs and recs[0]["seq"] > cursor + 1:
            raise Inv08Error("INV08.JOURNAL.GAP", f"WAL starts at {recs[0]['seq']} but snapshot cursor is {cursor}",
                             outcome=Outcome.OPERATOR_REQUIRED, severity="critical",
                             remediation="snapshot lost; rebuild state by provider reconciliation",
                             details={"cursor": cursor, "wal_first": recs[0]["seq"]})
        seq = cursor
        for r in recs:
            if r["seq"] > cursor:
                apply(state, r)
                report["replayed"] += 1
            seq = max(seq, r["seq"])
        report["cursor"] = cursor
        self.recovery_report = report
        return state, seq

    def pending(self) -> dict[str, dict]:
        return {k: v for k, v in self.state.get("ops", {}).items() if v["status"] == "PENDING"}
