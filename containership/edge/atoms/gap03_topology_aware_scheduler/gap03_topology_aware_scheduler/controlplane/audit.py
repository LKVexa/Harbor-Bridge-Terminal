"""MC-013 - Tamper-evident security audit log (GAP03-AUDIT/1).

Separate append-only store (its own directory, never the application log).
Every event is hash-chained through :class:`DurableStore`; every ``BATCH``
events the chain head is signed with Ed25519 (signed checkpoints).  The
service principal gets no delete/rewrite API: the class exposes only
append/query/verify/export.  Retention never deletes events under legal hold
or inside the security-evidence minimum.
"""
from __future__ import annotations

import os
import re
import time
import uuid

from . import canonical
from .canonical import readb
from .durable import DurableStore
from .errors import SchedulerError, safe_text

SCHEMA = "GAP03-AUDIT/1"
BATCH = 64
REQUIRED = ("event_id", "actor", "action", "target", "result", "ts_wall", "ts_mono_ns", "clock_source",
            "clock_uncertainty_ms", "request_id", "generation")
_SECRET_KEYS = re.compile(r"(?i)secret|token|password|private|credential|signature|attestation_raw")
SECURITY_EVIDENCE_MIN_DAYS = 400


def redact(value, depth: int = 0):
    if depth > 6:
        return "<truncated>"
    if isinstance(value, dict):
        return {k: ("<redacted>" if _SECRET_KEYS.search(k) else redact(v, depth + 1)) for k, v in sorted(value.items())[:64]}
    if isinstance(value, list):
        return [redact(v, depth + 1) for v in value[:64]]
    if isinstance(value, str):
        return safe_text(value)
    return value


class _AuditStore(DurableStore):
    KIND = "audit"
    SNAPSHOT_EVERY = 10**12  # the audit chain is never compacted away

    def initial_state(self):
        return {"count": 0, "checkpoints": [], "last_event_id": None}

    def apply(self, state, op):
        if op.get("type") == "event":
            ev = op["event"]
            missing = [k for k in REQUIRED if k not in ev]
            if missing:
                raise SchedulerError("INVALID_ARGUMENT", f"audit event missing {missing}")
            state["count"] += 1
            state["last_event_id"] = ev["event_id"]
        elif op.get("type") == "checkpoint":
            state["checkpoints"].append(op["checkpoint"])
            state["checkpoints"] = state["checkpoints"][-256:]
        elif op.get("type") == "hold":
            state.setdefault("holds", []).append(op["hold"])
        else:
            raise SchedulerError("INVALID_ARGUMENT", "unknown audit op")
        return state["count"]


class AuditLog:
    def __init__(self, directory: str, *, signer=None, clock=time.time, fault=None, alert=None):
        self._store = _AuditStore(directory, clock=clock, fault=fault)
        self.signer, self.clock, self.alert = signer, clock, alert
        self.write_failures = 0

    @property
    def count(self) -> int:
        return self._store.state["count"]

    def append(self, *, actor: str, action: str, target: str, result: str, detail: dict | None = None,
               request_id: str = "", generation: int | None = None, before=None, after=None, reason: str = "") -> str:
        ev = {"schema": SCHEMA, "event_id": str(uuid.uuid4()), "actor": safe_text(actor), "action": safe_text(action),
              "target": safe_text(target), "result": safe_text(result), "reason": safe_text(reason),
              "ts_wall": int(self.clock() * 1000), "ts_mono_ns": time.monotonic_ns(), "clock_source": "system+monotonic",
              "clock_uncertainty_ms": 1000, "request_id": safe_text(request_id)[:64],
              "generation": generation if generation is not None else -1,
              "before_digest": canonical.digest(redact(before)) if before is not None else None,
              "after_digest": canonical.digest(redact(after)) if after is not None else None,
              "detail": redact(detail or {})}
        try:
            count = self._store.submit({"type": "event", "event": ev})
        except SchedulerError:
            self.write_failures += 1
            if self.alert:
                self.alert("AUDIT_WRITE_FAILURE")
            raise
        if self.signer is not None and count % BATCH == 0:
            self.checkpoint()
        return ev["event_id"]

    def checkpoint(self) -> dict:
        stmt = {"schema": SCHEMA, "seq": self._store.seq, "head": self._store.head, "count": self.count,
                "ts_wall": int(self.clock() * 1000)}
        from .identity import b64
        cp = {"statement": stmt, "kid": self.signer.kid, "issuer": self.signer.issuer,
              "signature": b64(self.signer.sign(canonical.dumps(stmt)))}
        self._store.submit({"type": "checkpoint", "checkpoint": cp})
        return cp

    def place_hold(self, *, actor: str, scope: str, reason: str, until_ms: int) -> None:
        self._store.submit({"type": "hold", "hold": {"actor": actor, "scope": scope, "reason": reason, "until_ms": until_ms}})

    def _events(self):
        d = self._store.dir
        segs = sorted(os.listdir(os.path.join(d, "archive")), key=lambda n: int(n.split("-")[-1].split(".")[0]))
        paths = [os.path.join(d, "archive", s) for s in segs] + [self._store.wal_path]
        for path in paths:
            if not os.path.exists(path):
                continue
            for line in readb(path).split(b"\n"):
                if line:
                    rec = canonical.loads(line, max_bytes=1 << 24)
                    if rec["op"]["type"] == "event":
                        yield rec["seq"], rec["op"]["event"]

    def query(self, *, principal_roles: set[str], actor: str | None = None, request_id: str | None = None,
              action_prefix: str | None = None, generation: int | None = None, since_ms: int | None = None,
              page_token: int = 0, page_size: int = 100) -> dict:
        if "audit.read" not in principal_roles:
            raise SchedulerError("PERMISSION_DENIED", "audit.read required")
        page_size = max(1, min(page_size, 500))
        out, next_token = [], None
        for seq, ev in self._events():
            if seq <= page_token:
                continue
            if actor and ev["actor"] != actor:
                continue
            if request_id and ev["request_id"] != request_id:
                continue
            if action_prefix and not ev["action"].startswith(action_prefix):
                continue
            if generation is not None and ev["generation"] != generation:
                continue
            if since_ms and ev["ts_wall"] < since_ms:
                continue
            if len(out) == page_size:
                next_token = out[-1]["_seq"]
                break
            out.append(dict(ev, _seq=seq))
        return {"events": out, "next_page_token": next_token, "chain": self.verify()}

    def verify(self, trust_store=None) -> dict:
        """Verify hash chain, sequence continuity, duplicate event IDs and checkpoint signatures."""
        hist = self._store.verify_history()
        ids, dup = set(), 0
        for _, ev in self._events():
            if ev["event_id"] in ids:
                dup += 1
            ids.add(ev["event_id"])
        bad_cp = 0
        if trust_store is not None:
            from . import ed25519
            from .identity import unb64
            for cp in self._store.state["checkpoints"]:
                try:
                    key = trust_store._key(cp["issuer"], cp["kid"], trust_store.clock())
                    ok = ed25519.verify(key.public, canonical.dumps(cp["statement"]), unb64(cp["signature"]))
                except SchedulerError:
                    ok = False
                bad_cp += 0 if ok else 1
        ok = hist["ok"] and dup == 0 and bad_cp == 0
        if not ok and self.alert:
            self.alert("AUDIT_INTEGRITY_FAILURE")
        return {"ok": ok, "verified_records": hist.get("verified"), "duplicate_event_ids": dup, "bad_checkpoints": bad_cp,
                "break_at": hist.get("break_at")}

    def retention_plan(self, *, now_ms: int, retention_days: int) -> dict:
        """Compute what *could* be archived; never deletes held or security-minimum evidence."""
        eff = max(retention_days, SECURITY_EVIDENCE_MIN_DAYS)
        cutoff = now_ms - eff * 86400_000
        holds = self._store.state.get("holds", [])
        eligible = [ev["event_id"] for _, ev in self._events() if ev["ts_wall"] < cutoff and
                    not any(h["until_ms"] > now_ms for h in holds)]
        return {"effective_retention_days": eff, "eligible_for_cold_archive": len(eligible), "deleted": 0,
                "policy": "archive-to-WORM only; deletion requires a separate approved legal process"}

    def export(self, *, principal_roles: set[str]) -> dict:
        if "audit.export" not in principal_roles:
            raise SchedulerError("PERMISSION_DENIED", "audit.export required")
        events = [ev for _, ev in self._events()]
        return {"schema": SCHEMA, "events": events, "head": self._store.head, "digest": canonical.digest(events)}
