"""M40 - tamper-evident, append-only audit ledger (hash chain + optional HMAC).

Each record: {seq, ts, kind, actor, data, prev, hash[, mac]} where hash =
sha256(canonical(record without hash/mac)). Verification detects modification,
deletion, reordering and insertion; tail truncation is detected by comparing the
externally anchored head (seq, hash) - the known blind spot of any bare chain.
Persisted as JSON lines; data is redacted before it is written.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from pathlib import Path

from .errors import FabricError, redact_detail

GENESIS = "0" * 64


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()


class AuditLedger:
    def __init__(self, path: str | os.PathLike | None = None, *, mac_key: bytes | None = None, clock=time.time):
        self.path = Path(path) if path else None
        self.mac_key = mac_key
        self.clock = clock
        self.records: list[dict] = []
        self._lock = threading.Lock()
        if self.path and self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    self.records.append(json.loads(line))
            self.verify()

    @property
    def head(self) -> tuple[int, str]:
        if not self.records:
            return (0, GENESIS)
        return (self.records[-1]["seq"], self.records[-1]["hash"])

    def append(self, kind: str, actor: str | None, data: dict) -> dict:
        with self._lock:
            return self._append(kind, actor, data)

    def _append(self, kind: str, actor: str | None, data: dict) -> dict:
        seq, prev = self.head
        rec = {"seq": seq + 1, "ts": round(self.clock(), 6), "kind": kind, "actor": actor,
               "data": redact_detail(data) if isinstance(data, dict) else {"value": str(data)}, "prev": prev}
        rec["hash"] = hashlib.sha256(_canon(rec)).hexdigest()
        if self.mac_key:
            rec["mac"] = hmac.new(self.mac_key, rec["hash"].encode(), hashlib.sha256).hexdigest()
        self.records.append(rec)
        if self.path:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        return rec

    def verify(self, anchored_head: tuple[int, str] | None = None) -> int:
        prev, expect = GENESIS, 1
        for rec in self.records:
            body = {k: v for k, v in rec.items() if k not in ("hash", "mac")}
            if rec.get("seq") != expect or rec.get("prev") != prev:
                raise FabricError("LEDGER_BROKEN", f"chain break at seq {rec.get('seq')}")
            if hashlib.sha256(_canon(body)).hexdigest() != rec.get("hash"):
                raise FabricError("LEDGER_BROKEN", f"hash mismatch at seq {rec.get('seq')}")
            if self.mac_key and not hmac.compare_digest(
                    rec.get("mac", ""), hmac.new(self.mac_key, rec["hash"].encode(), hashlib.sha256).hexdigest()):
                raise FabricError("LEDGER_BROKEN", f"mac mismatch at seq {rec.get('seq')}")
            prev, expect = rec["hash"], expect + 1
        if anchored_head is not None:
            seq, h = anchored_head
            if seq > len(self.records) or (seq and self.records[seq - 1]["hash"] != h):
                raise FabricError("LEDGER_BROKEN", "ledger truncated or diverged from anchored head")
        return len(self.records)
