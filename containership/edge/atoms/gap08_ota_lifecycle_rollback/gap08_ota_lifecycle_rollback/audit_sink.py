"""Externally sealed audit sink (component 5).

The in-rollout hash chain detects accidental corruption but a privileged
rewriter can recompute plain hashes.  The sink closes that gap:

* it runs under a **separate trust domain** — it signs with a key the
  controller never holds (``sink_keyring``); the controller only verifies;
* storage is **append-only** (``O_APPEND`` file here; WORM bucket,
  transparency log or ledger DB in production);
* every append returns a signed **receipt** (sequence, chained hash) which the
  controller stores as ``audit_head`` in rollout state;
* a signed **head** records the entry count, so truncation is detectable;
* ``verify_against`` proves every local audit event of a rollout was sealed.

Policy: a mutation is externally visible only after its audit event is
sealed.  If the sink is unavailable the controller fails closed (no new
mutations) — rollback commands are still issued and their events are sealed
once the sink recovers (see ``dependencies.py``).
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .common import KeyRing, canonical_json, sha256_hex
from .errors import DependencyUnavailable, IntegrityFailure
from .secrets_boundary import assert_no_secrets

SINK_SCHEMA = "PK_AUDIT_SEAL/1"
_GENESIS = "0" * 64


@dataclass(frozen=True)
class Receipt:
    seq: int
    sealed_hash: str
    signature: str
    key_id: str

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class FileWormSink:
    def __init__(self, path: str | os.PathLike[str], sink_keyring: KeyRing, key_id: str) -> None:
        self.path = Path(path)
        self.head_path = self.path.with_suffix(".head")
        self._kr = sink_keyring
        self._key = key_id
        self._lock = threading.Lock()
        self.available = True  # fault-injection hook
        self.path.touch(mode=0o600, exist_ok=True)
        self._seq, self._last = self._scan_tail()

    def _scan_tail(self) -> tuple[int, str]:
        seq, last = 0, _GENESIS
        with self.path.open("rb") as fh:
            for line in fh:
                if line.strip():
                    rec = json.loads(line)
                    seq, last = rec["seq"], rec["sealed_hash"]
        return seq, last

    def append(self, event: Mapping[str, Any]) -> Receipt:
        if not self.available:
            raise DependencyUnavailable("audit sink unavailable", resource="audit_sink")
        assert_no_secrets(dict(event), where="audit sink")
        with self._lock:
            seq = self._seq + 1
            body = {"schema": SINK_SCHEMA, "seq": seq, "prev": self._last, "event": dict(event)}
            sealed = sha256_hex(canonical_json(body))
            sig = self._kr.sign(self._key, sealed.encode())
            line = canonical_json({**body, "sealed_hash": sealed, "signature": sig, "key_id": self._key}) + b"\n"
            fd = os.open(self.path, os.O_WRONLY | os.O_APPEND)
            try:
                os.write(fd, line)
                os.fsync(fd)
            finally:
                os.close(fd)
            head = {"schema": "PK_AUDIT_HEAD/1", "seq": seq, "sealed_hash": sealed}
            head_sig = self._kr.sign(self._key, canonical_json(head))
            tmp = self.head_path.with_suffix(".tmp")
            tmp.write_bytes(canonical_json({**head, "signature": head_sig, "key_id": self._key}))
            os.replace(tmp, self.head_path)
            self._seq, self._last = seq, sealed
            return Receipt(seq, sealed, sig, self._key)

    def entries(self) -> list[dict[str, Any]]:
        with self.path.open("rb") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def verify(self, verifier: KeyRing) -> int:
        """Verify chain, every signature and the signed head; return entry count."""
        prev, count = _GENESIS, 0
        for rec in self.entries():
            count += 1
            body = {k: rec[k] for k in ("schema", "seq", "prev", "event")}
            if rec["seq"] != count or rec["prev"] != prev:
                raise IntegrityFailure(f"audit sink chain broken at {count}")
            if sha256_hex(canonical_json(body)) != rec["sealed_hash"]:
                raise IntegrityFailure(f"audit sink entry {count} hash mismatch")
            if not verifier.verify(rec["key_id"], rec["sealed_hash"].encode(), rec["signature"]):
                raise IntegrityFailure(f"audit sink entry {count} signature invalid")
            prev = rec["sealed_hash"]
        if self.head_path.exists():
            head = json.loads(self.head_path.read_bytes())
            hb = {k: head[k] for k in ("schema", "seq", "sealed_hash")}
            if not verifier.verify(head["key_id"], canonical_json(hb), head["signature"]):
                raise IntegrityFailure("audit head signature invalid")
            if head["seq"] != count or head["sealed_hash"] != prev:
                raise IntegrityFailure("audit sink truncated or extended behind the signed head")
        elif count:
            raise IntegrityFailure("audit head missing")
        return count

    def verify_against(self, local_events: Iterable[Mapping[str, Any]]) -> None:
        """Every local event must be sealed *and identical* to its sealed copy (detects post-seal edits)."""
        sealed = {e["event"].get("event_hash"): e["event"] for e in self.entries()}
        missing, altered = [], []
        for e in local_events:
            s = sealed.get(e.get("event_hash"))
            if s is None:
                missing.append(e.get("sequence"))
            elif s.get("event_hash") and canonical_json(dict(e)) != canonical_json(s):
                altered.append(e.get("sequence"))
        if missing or altered:
            raise IntegrityFailure(f"local audit history diverges from sealed copy: missing={missing[:10]} "
                                   f"altered={altered[:10]}")


def reconstruct(sink: FileWormSink, verifier: KeyRing, rollout_id: str) -> list[dict[str, Any]]:
    """Rebuild a rollout's authoritative event chain from the verified external sink alone."""
    sink.verify(verifier)
    events = [e["event"] for e in sink.entries() if e["event"].get("rollout_id") == rollout_id]
    seen: dict[int, dict[str, Any]] = {}
    for ev in events:                       # an event may be sealed twice after a buffered retry
        seen.setdefault(ev["sequence"], ev)
    chain = [seen[k] for k in sorted(seen)]
    prev = "0" * 64
    for i, ev in enumerate(chain, start=1):
        body = {k: v for k, v in ev.items() if k != "event_hash"}
        if ev["sequence"] != i or ev["prev_hash"] != prev or sha256_hex(canonical_json(body)) != ev["event_hash"]:
            raise IntegrityFailure(f"sealed chain for {rollout_id} is broken at {i}")
        prev = ev["event_hash"]
    return chain
