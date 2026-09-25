"""Durable state, write-ahead operation journal, segmented signed audit, external anchoring (WS 6).

Layout under ``state_dir``::

    journal.jsonl              write-ahead operation journal (one checksummed record per line)
    state.json                 guest expected-state snapshot (atomic tmp+fsync+rename, digest-checked)
    audit/seg-000001.jsonl     audit segment (hash chain continues across segments)
    audit/seg-000001.head      HMAC-signed segment head written on rotation / anchor
    anchors.jsonl              local copy of anchors exported to the external sink

Durability rule: ``append`` returns only after ``flush`` + ``os.fsync``.  A mutation is never acknowledged
before its journal record *and* audit event are durable.

Torn writes: a final line without a newline or with a bad checksum is a torn tail -- it is quarantined to
``*.torn`` and ignored (it was never acknowledged).  Corruption anywhere else is a ``StoreIntegrityError``
and blocks readiness.

Encryption at rest is **not** implemented in-process (stdlib has no AEAD); it is delegated to the
deployment's encrypted volume (dm-crypt/LUKS or equivalent) -- see RUNBOOKS.md Day-0 step 4 and the
BLOCKED entry WS6-ENCRYPTION in RTM.json.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterable

from . import errors as E
from .model import AUDIT_EVENT_SCHEMA, ZERO_HASH, _canonical_hash

STORE_SCHEMA = "PK_INV32_STORE/1"
PHASES = ("prepared", "provider_requested", "provider_confirmed", "state_committed", "audit_committed")
TERMINAL_PHASES = frozenset({"audit_committed", "failed", "rolled_back", "rejected", "reconciled"})
STATE_CLASSIFICATION = {
    # item: (class, source of truth on recovery, retention)
    "guest_registrations": ("authoritative", "hypervisor list_guests + state.json", "life of guest"),
    "expected_resource_state": ("authoritative", "hypervisor (live) reconciled with state.json", "life of guest"),
    "idempotency_records": ("authoritative", "journal.jsonl", "config.idempotency_retention_s"),
    "pending_operations": ("authoritative", "journal.jsonl reconciled with hypervisor", "until terminal"),
    "audit_events": ("authoritative", "audit segments + external anchors", "config.audit_retention_days"),
    "quarantine_state": ("authoritative", "journal.jsonl (quarantine records)", "until cleared"),
    "config_revision": ("authoritative", "config store (ConfigManager history)", "16 revisions"),
    "controller_epoch": ("authoritative", "lease store", "lease duration"),
    "free_page_reports": ("ephemeral", "guest agent (re-reported)", "config.free_page_report_stale_s"),
    "metrics_traces_logs": ("ephemeral", "telemetry sinks", "telemetry.TELEMETRY_POLICY"),
}


def _fsync_dir(path: Path) -> None:
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _crc(rec: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


class _JsonlLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.torn_tails = 0

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        data = self.path.read_bytes()
        lines = data.split(b"\n")
        tail = lines.pop()  # b"" when file ends with newline
        out: list[dict[str, Any]] = []
        for i, raw in enumerate(lines):
            rec = self._decode(raw)
            if rec is None:
                if i == len(lines) - 1 and not tail:
                    # last complete line bad: treat as torn only if it is the very end
                    self._quarantine_tail(len(data) - len(raw) - 1, data)
                    return out
                raise E.StoreIntegrityError("journal record checksum failure", file=self.path.name, line=i + 1)
            out.append(rec)
        if tail:
            self._quarantine_tail(len(data) - len(tail), data)
        return out

    @staticmethod
    def _decode(raw: bytes) -> dict[str, Any] | None:
        try:
            wrapper = json.loads(raw)
            rec, crc = wrapper["rec"], wrapper["crc"]
        except Exception:
            return None
        return rec if isinstance(rec, dict) and _crc(rec) == crc else None

    def _quarantine_tail(self, offset: int, data: bytes) -> None:
        self.torn_tails += 1
        with open(self.path.with_suffix(self.path.suffix + ".torn"), "ab") as fh:
            fh.write(data[offset:] + b"\n")
        with open(self.path, "r+b") as fh:
            fh.truncate(offset)
            fh.flush()
            os.fsync(fh.fileno())

    def append(self, rec: dict[str, Any]) -> None:
        line = json.dumps({"rec": rec, "crc": _crc(rec)}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())


class DurableStore:
    def __init__(self, state_dir: str | os.PathLike, *, signing_key: bytes, segment_max_events: int = 10_000,
                 anchor_sink: Callable[[dict[str, Any]], None] | None = None, clock=time.time) -> None:
        if len(signing_key) < 32:
            raise ValueError("audit signing key must be >= 256 bits")
        self.dir = Path(state_dir)
        (self.dir / "audit").mkdir(parents=True, exist_ok=True)
        self._key = signing_key
        self._seg_max = segment_max_events
        self._anchor_sink = anchor_sink
        self._clock = clock
        self._lock = threading.RLock()
        self._journal = _JsonlLog(self.dir / "journal.jsonl")
        self._anchors = _JsonlLog(self.dir / "anchors.jsonl")
        self.ops: dict[str, dict[str, Any]] = {}
        self._incomplete: set[str] = set()
        self.audit_events: list[dict[str, Any]] = []
        self.quarantine: dict[str, dict[str, Any]] = {}
        self.state: dict[str, Any] = {"schema": STORE_SCHEMA, "guests": {}}
        self._load()

    # ------------------------------------------------------------------ load / verify
    def _segments(self) -> list[Path]:
        return sorted((self.dir / "audit").glob("seg-*.jsonl"))

    def _load(self) -> None:
        with self._lock:
            for rec in self._journal.load():
                self._apply_journal(rec)
            prev, seq = ZERO_HASH, 0
            self._seg_path, self._seg_count = None, 0
            for seg in self._segments():
                log = _JsonlLog(seg)
                events = log.load()
                self._seg_path, self._seg_count = seg, len(events)
                for ev in events:
                    seq += 1
                    self._check_event(ev, seq, prev)
                    prev = ev["event_hash"]
                    self.audit_events.append(ev)
                head = seg.with_suffix(".head")
                if head.exists():
                    self._verify_head(self._read_json(head), seg.name)
            for anchor in self._anchors.load():
                self.verify_anchor(anchor)
            state_file = self.dir / "state.json"
            if state_file.exists():
                doc = self._read_json(state_file)
                if not isinstance(doc, dict) or _crc(doc.get("state", {})) != doc.get("digest"):
                    raise E.StoreIntegrityError("state snapshot digest mismatch")
                self.state = doc["state"]

    @staticmethod
    def _read_json(path: Path) -> Any:
        try:
            doc = json.loads(path.read_bytes().decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise E.StoreIntegrityError("unparseable store file", file=path.name) from None
        if not isinstance(doc, dict):
            raise E.StoreIntegrityError("store file is not an object", file=path.name)
        return doc

    @staticmethod
    def _check_event(ev: dict[str, Any], seq: int, prev: str) -> None:
        body = dict(ev)
        h = body.pop("event_hash", None)
        if body.get("sequence") != seq or body.get("prev_hash") != prev or body.get("audit_schema") != AUDIT_EVENT_SCHEMA:
            raise E.StoreIntegrityError("audit chain linkage broken", sequence=seq)
        if h != _canonical_hash(body):
            raise E.StoreIntegrityError("audit event hash mismatch", sequence=seq)

    def _sign(self, payload: dict[str, Any]) -> str:
        return hmac.new(self._key, json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(),
                        hashlib.sha256).hexdigest()

    def _verify_head(self, head: dict[str, Any], seg_name: str) -> None:
        sig = head.pop("sig", None)
        try:
            ok = isinstance(sig, str) and hmac.compare_digest(sig, self._sign(head))
        except TypeError:  # non-ASCII sig after corruption
            ok = False
        if not ok:
            raise E.StoreIntegrityError("audit segment head signature invalid", segment=seg_name)
        seq = head.get("last_sequence")
        if not isinstance(seq, int) or seq < 1 or seq > len(self.audit_events) \
                or self.audit_events[seq - 1]["event_hash"] != head.get("head_hash"):
            raise E.StoreIntegrityError("audit segment head does not match chain", segment=seg_name)

    def verify_anchor(self, anchor: dict[str, Any]) -> None:
        a = dict(anchor)
        sig = a.pop("sig", None)
        try:
            ok = isinstance(sig, str) and hmac.compare_digest(sig, self._sign(a))
        except TypeError:
            ok = False
        if not ok:
            raise E.StoreIntegrityError("anchor signature invalid")
        seq = a.get("sequence")
        if not isinstance(seq, int) or seq > len(self.audit_events) or (
                seq > 0 and self.audit_events[seq - 1]["event_hash"] != a.get("head_hash")):
            raise E.StoreIntegrityError("audit chain diverges from external anchor", sequence=seq)

    def verify_against_external(self, anchors: Iterable[dict[str, Any]]) -> None:
        """Detect whole-chain rewrite by a local attacker using anchors held elsewhere."""
        for a in anchors:
            self.verify_anchor(a)

    # ------------------------------------------------------------------ journal
    def _apply_journal(self, rec: dict[str, Any]) -> None:
        t = rec.get("t")
        if t == "op":
            op = self.ops.setdefault(rec["operation_id"], {})
            op.update(rec["data"])
            if op.get("phase") in TERMINAL_PHASES:
                self._incomplete.discard(rec["operation_id"])
            else:
                self._incomplete.add(rec["operation_id"])
        elif t == "quarantine_set":
            self.quarantine[rec["scope"]] = rec["data"]
        elif t == "quarantine_clear":
            self.quarantine.pop(rec["scope"], None)
        elif t == "prune":
            for op in rec["operation_ids"]:
                self.ops.pop(op, None)
                self._incomplete.discard(op)

    def journal(self, rec: dict[str, Any]) -> None:
        with self._lock:
            rec = dict(rec, ts=self._clock())
            self._journal.append(rec)
            self._apply_journal(rec)

    def op_phase(self, operation_id: str, phase: str, **data: Any) -> dict[str, Any]:
        if phase not in PHASES and phase not in TERMINAL_PHASES and phase != "unknown":
            raise ValueError("unknown phase")
        self.journal({"t": "op", "operation_id": operation_id, "data": {**data, "phase": phase}})
        return self.ops[operation_id]

    def incomplete_ops(self) -> dict[str, dict[str, Any]]:
        return {k: self.ops[k] for k in list(self._incomplete)}

    def prune_idempotency(self, retention_s: float) -> int:
        cutoff = self._clock() - retention_s
        victims = [k for k, v in self.ops.items() if v.get("phase") in TERMINAL_PHASES and v.get("created", 0) < cutoff]
        if victims:
            self.journal({"t": "prune", "operation_ids": victims})
        return len(victims)

    def set_quarantine(self, scope: str, data: dict[str, Any]) -> None:
        self.journal({"t": "quarantine_set", "scope": scope, "data": data})

    def clear_quarantine(self, scope: str) -> None:
        self.journal({"t": "quarantine_clear", "scope": scope})

    # ------------------------------------------------------------------ expected state
    def save_state(self) -> None:
        with self._lock:
            doc = {"state": self.state, "digest": _crc(self.state)}
            tmp = self.dir / "state.json.tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(doc, sort_keys=True, separators=(",", ":")))
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.dir / "state.json")
            _fsync_dir(self.dir)

    def guest_state(self, guest: str) -> dict[str, Any] | None:
        return self.state["guests"].get(guest)

    def put_guest_state(self, guest: str, **values: Any) -> None:
        with self._lock:
            cur = self.state["guests"].setdefault(guest, {"version": 0})
            cur.update(values)
            cur["version"] = int(cur.get("version", 0)) + 1
            self.save_state()

    # ------------------------------------------------------------------ audit
    @property
    def audit_head(self) -> str:
        return self.audit_events[-1]["event_hash"] if self.audit_events else ZERO_HASH

    def append_audit(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            ev = dict(payload)
            ev["audit_schema"] = AUDIT_EVENT_SCHEMA
            ev["sequence"] = len(self.audit_events) + 1
            ev["prev_hash"] = self.audit_head
            ev["wall_time"] = self._clock()
            ev["monotonic_ns"] = time.monotonic_ns()
            ev["event_hash"] = _canonical_hash(ev)
            if self._seg_path is None:
                self._seg_path, self._seg_count = self.dir / "audit" / "seg-000001.jsonl", 0
            elif self._seg_count >= self._seg_max:
                self._write_head(self._seg_path)
                n = int(self._seg_path.stem.split("-")[1]) + 1
                self._seg_path, self._seg_count = self.dir / "audit" / f"seg-{n:06d}.jsonl", 0
            _JsonlLog(self._seg_path).append(ev)
            self._seg_count += 1
            self.audit_events.append(ev)
            return dict(ev)

    def _write_head(self, seg: Path) -> None:
        head = {"segment": seg.name, "last_sequence": len(self.audit_events), "head_hash": self.audit_head,
                "signed_at": self._clock(), "alg": "HMAC-SHA256"}
        head["sig"] = self._sign({k: v for k, v in head.items()})
        tmp = seg.with_suffix(".head.tmp")
        tmp.write_text(json.dumps(head, sort_keys=True))
        os.replace(tmp, seg.with_suffix(".head"))

    def anchor(self) -> dict[str, Any]:
        """Export the current audit head to the external sink (and keep a local copy)."""
        with self._lock:
            a = {"schema": "PK_AUDIT_ANCHOR/1", "sequence": len(self.audit_events), "head_hash": self.audit_head,
                 "anchored_at": self._clock(), "alg": "HMAC-SHA256"}
            a["sig"] = self._sign(a)
            self._anchors.append(a)
            if self._anchor_sink is not None:
                self._anchor_sink(dict(a))
            return a

    def verify_recent(self, window: int = 64) -> bool:
        """O(window) check of the chain tail used on the hot mutation path; ``verify`` (full) runs at start-up,
        in readiness probes and every ``full_verify_every`` mutations (see controller)."""
        ev = self.audit_events
        start = max(0, len(ev) - window)
        prev = ev[start - 1]["event_hash"] if start else ZERO_HASH
        try:
            for i in range(start, len(ev)):
                self._check_event(ev[i], i + 1, prev)
                prev = ev[i]["event_hash"]
            return True
        except E.StoreIntegrityError:
            return False

    def verify(self) -> bool:
        try:
            prev = ZERO_HASH
            for i, ev in enumerate(self.audit_events, start=1):
                self._check_event(ev, i, prev)
                prev = ev["event_hash"]
            return True
        except E.StoreIntegrityError:
            return False

    # ------------------------------------------------------------------ backup / restore
    def backup(self, dest: str | os.PathLike) -> dict[str, Any]:
        with self._lock:
            dest = Path(dest)
            if dest.exists():
                raise FileExistsError("backup destination must be new")
            shutil.copytree(self.dir, dest)
            files = {str(p.relative_to(dest)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(dest.rglob("*")) if p.is_file()}
            manifest = {"schema": "PK_INV32_BACKUP/1", "created_at": self._clock(), "files": files,
                        "audit_sequence": len(self.audit_events), "audit_head": self.audit_head}
            manifest["sig"] = self._sign(manifest)
            (dest / "BACKUP_MANIFEST.json").write_text(json.dumps(manifest, sort_keys=True, indent=1))
            return manifest

    @staticmethod
    def restore(src: str | os.PathLike, dest: str | os.PathLike, *, signing_key: bytes) -> DurableStore:
        src, dest = Path(src), Path(dest)
        manifest = json.loads((src / "BACKUP_MANIFEST.json").read_text())
        sig = manifest.pop("sig", "")
        expect = hmac.new(signing_key, json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode(),
                          hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expect):
            raise E.StoreIntegrityError("backup manifest signature invalid")
        for rel, digest in manifest["files"].items():
            p = src / rel
            if not p.exists():
                raise E.StoreIntegrityError("backup is missing a file (partial restore)", file=rel)
            if hashlib.sha256(p.read_bytes()).hexdigest() != digest:
                raise E.StoreIntegrityError("backup file digest mismatch", file=rel)
        if dest.exists():
            raise FileExistsError("restore destination must be new (clean environment)")
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns("BACKUP_MANIFEST.json"))
        store = DurableStore(dest, signing_key=signing_key)
        if store.audit_head != manifest["audit_head"]:
            raise E.StoreIntegrityError("restored audit head differs from backup manifest")
        return store


RETENTION = {
    "idempotency_records": "config.idempotency_retention_s (default 7 d); pruned only when terminal",
    "audit": "config.audit_retention_days (default 400 d); deletion only by segment after external export+anchor",
    "free_page_reports": "memory only; stale after config.free_page_report_stale_s",
    "backups": "RPO 5 min (anchor interval) / RTO 15 min -- see RUNBOOKS.md Day-2 backup",
}
