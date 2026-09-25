"""Reservation state for INV-72 (C025, C057, C058, C059, C086, C095).

The v4.2.0 matcher recorded ownership by mutating ``Device.tenants`` in memory.  This store makes that
state explicit and survivable:

* **Atomic reserve** - selection + ownership update happen under one lock, so two concurrent callers
  can never be given the same whole device or cross-tenant partition (C058, C086).
* **Idempotency** - a repeated ``idempotency_key`` from the same tenant returns the original
  reservation instead of reserving twice (C025).
* **Fencing** - every mutation carries the controller's fencing token; a token lower than the highest
  seen is refused (``ACCEL_STALE_FENCE``) so a stale controller cannot overwrite a newer one (C058).
* **Write-ahead journal** - each mutation is appended (JSON line + SHA-256 chain) and fsync'd before it
  is acknowledged; ``recover()`` replays the journal, truncating a torn final line and refusing a broken
  chain (C057).  ``snapshot()``/``restore()`` give backup and migration (C095).
* **Quarantine / drain** - operators can exclude devices from selection without losing existing
  reservations; ``revoke_device()`` additionally ends reservations on a device (C059).
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from . import lifecycle
from .errors import AccelError
from .matcher import Device, decide

GENESIS = "0" * 64


def _h(prev: str, body: dict) -> str:
    return hashlib.sha256((prev + json.dumps(body, sort_keys=True, separators=(",", ":"))).encode()).hexdigest()


@dataclass
class Reservation:
    reservation_id: str
    tenant: str
    devices: tuple
    isolation: str
    state: str
    created_at: float
    idempotency_key: str | None = None
    fence: int = 0
    request_digest: str = ""

    def to_dict(self) -> dict:
        return {"reservation_id": self.reservation_id, "tenant": self.tenant, "devices": list(self.devices),
                "isolation": self.isolation, "state": self.state, "created_at": self.created_at,
                "idempotency_key": self.idempotency_key, "fence": self.fence,
                "request_digest": self.request_digest}


@dataclass
class ReservationStore:
    journal_path: Path | None = None
    clock: Callable[[], float] = time.time
    fsync: bool = True
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)
    reservations: dict = field(default_factory=dict)
    by_idem: dict = field(default_factory=dict)
    quarantined: dict = field(default_factory=dict)   # dev_id -> reason (no selection)
    draining: dict = field(default_factory=dict)      # dev_id -> reason (no new selection)
    max_fence: int = 0
    _tip: str = GENESIS
    _seq: int = 0

    # ------------------------------------------------------------------ journal
    def _append(self, op: str, data: dict) -> None:
        body = {"seq": self._seq, "op": op, "data": data}
        h = _h(self._tip, body)
        if self.journal_path is not None:
            line = json.dumps({**body, "prev": self._tip, "hash": h}, sort_keys=True) + "\n"
            with open(self.journal_path, "a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
                if self.fsync:
                    os.fsync(f.fileno())
        self._tip, self._seq = h, self._seq + 1

    @classmethod
    def recover(cls, journal_path: Path, **kw) -> "ReservationStore":
        """Rebuild state by replaying the journal.  A torn last line (crash mid-write) is dropped and
        reported; any chain break earlier in the file is refused, never guessed around."""
        store = cls(journal_path=None, **kw)
        report = {"replayed": 0, "torn_tail": False}
        p = Path(journal_path)
        lines = p.read_text(encoding="utf-8").split("\n") if p.exists() else []
        if lines and lines[-1] == "":
            lines.pop()
        good_bytes = 0
        for i, raw in enumerate(lines):
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                if i == len(lines) - 1:
                    report["torn_tail"] = True
                    break
                raise AccelError("ACCEL_STATE_CORRUPT", f"journal corrupt at line {i + 1}")
            if not isinstance(rec, dict) or not all(k in rec for k in ("seq", "op", "data", "prev", "hash")):
                raise AccelError("ACCEL_STATE_CORRUPT", f"journal record malformed at line {i + 1}")
            body = {k: rec[k] for k in ("seq", "op", "data")}
            if rec["prev"] != store._tip or _h(store._tip, body) != rec["hash"] or rec["seq"] != store._seq:
                raise AccelError("ACCEL_STATE_CORRUPT", f"journal chain broken at line {i + 1}")
            try:
                store._apply(rec["op"], rec["data"])
            except (KeyError, TypeError, AttributeError) as exc:
                raise AccelError("ACCEL_STATE_CORRUPT", f"journal record unusable at line {i + 1}") from exc
            store._tip, store._seq = rec["hash"], store._seq + 1
            report["replayed"] += 1
            good_bytes += len(raw.encode("utf-8")) + 1
        if report["torn_tail"]:
            with open(p, "r+b") as f:
                f.truncate(good_bytes)
        store.journal_path = p
        store.recovery_report = report
        return store

    def _apply(self, op: str, d: dict) -> None:
        if op == "reserve":
            r = Reservation(d["reservation_id"], d["tenant"], tuple(d["devices"]), d["isolation"], "reserved",
                            d["created_at"], d.get("idempotency_key"), d.get("fence", 0), d.get("request_digest", ""))
            self.reservations[r.reservation_id] = r
            if r.idempotency_key:
                self.by_idem[(r.tenant, r.idempotency_key)] = r.reservation_id
            self.max_fence = max(self.max_fence, r.fence)
        elif op in ("release", "revoke"):
            r = self.reservations[d["reservation_id"]]
            r.state = "released" if op == "release" else "revoked"
        elif op == "quarantine":
            self.quarantined[d["dev_id"]] = d["reason"]
            self.draining.pop(d["dev_id"], None)
        elif op == "drain":
            self.draining[d["dev_id"]] = d["reason"]
        elif op == "unquarantine":
            self.quarantined.pop(d["dev_id"], None)
            self.draining.pop(d["dev_id"], None)
        elif op == "fence":
            self.max_fence = max(self.max_fence, d["fence"])
        else:
            raise KeyError(f"unknown journal op {op!r}")

    # ------------------------------------------------------------------ fencing
    def _check_fence(self, fence: int) -> None:
        if isinstance(fence, bool) or not isinstance(fence, int) or fence < 0:
            raise AccelError("ACCEL_STALE_FENCE", "fence must be a non-negative integer")
        if fence < self.max_fence:
            raise AccelError("ACCEL_STALE_FENCE", f"fence {fence} < current {self.max_fence}",
                             fence=fence, current=self.max_fence)

    # ------------------------------------------------------------------ views
    def active(self) -> list[Reservation]:
        return [r for r in self.reservations.values() if r.state == "reserved"]

    def owners(self) -> dict[str, set]:
        out: dict[str, set] = {}
        for r in self.active():
            for d in r.devices:
                out.setdefault(d, set()).add(r.tenant)
        return out

    def tenant_device_count(self, tenant: str) -> int:
        return sum(len(r.devices) for r in self.active() if r.tenant == tenant)

    def excluded(self) -> dict[str, str]:
        return {**{d: f"draining: {w}" for d, w in self.draining.items()},
                **{d: f"quarantined: {w}" for d, w in self.quarantined.items()}}

    def overlay(self, devices: Iterable[Device]) -> list[Device]:
        """Copy discovered devices, replacing tenant ownership with this store's authoritative view."""
        owners = self.owners()
        out = []
        for d in devices:
            held = set(owners.get(d.dev_id, set()))
            if held and not d.partition_of:
                # A reserved whole device is occupied for every later request, including the same
                # tenant's next job.  (v4.2.0's in-memory model handed one whole device to two jobs of
                # the same tenant because ownership was tracked per tenant, not per reservation.)
                held = {"reservation-held"}
            # Copy without re-running Device validation: the inventory was validated at intake and
            # decide() validates every device again before use, so a third pass here only cost time
            # (it was ~36% of a governed request; see evidence/OPTIMIZATION_REPORT.json).
            c = Device.__new__(Device)
            for name in ("dev_id", "cls", "mem_gb", "node", "link_group", "partition_of"):
                setattr(c, name, getattr(d, name))
            c.tenants = held
            out.append(c)
        return out

    # ------------------------------------------------------------------ mutations
    def reserve(self, req: Mapping[str, Any], devices: Iterable[Device], *, fence: int = 0,
                quota: int | None = None) -> tuple[Reservation | None, dict]:
        """Atomically decide and reserve.  Returns (reservation|None, decision)."""
        with self._lock:
            self._check_fence(fence)
            idem = req.get("idempotency_key") if isinstance(req, Mapping) else None
            tenant = req.get("tenant") if isinstance(req, Mapping) else None
            core = {k: v for k, v in req.items() if k in ("class", "mem_gb", "count", "interconnect", "isolation", "tenant")}
            rdig = hashlib.sha256(json.dumps(core, sort_keys=True, default=repr).encode()).hexdigest()
            if idem is not None and (tenant, idem) in self.by_idem:
                r = self.reservations[self.by_idem[(tenant, idem)]]
                if r.request_digest != rdig:
                    raise AccelError("ACCEL_INVALID_REQUIREMENT",
                                     "idempotency_key reused with a different requirement")
                return r, {"selected": list(r.devices), "code": None, "reasons": [],
                           "rationale": [f"idempotent replay of {r.reservation_id}"], "replayed": True}
            decision = decide(core, self.overlay(devices), reserve=False, excluded=self.excluded())
            if decision["selected"] is None:
                return None, decision
            n = len(decision["selected"])
            if quota is not None and self.tenant_device_count(decision["requirement"]["tenant"]) + n > quota:
                decision = {**decision, "selected": None, "code": "ACCEL_QUOTA_EXCEEDED",
                            "reasons": decision["reasons"] + [{"code": "ACCEL_QUOTA_EXCEEDED", "device": None,
                                                               "text": f"tenant quota {quota} device(s) would be exceeded"}]}
                return None, decision
            r = Reservation(f"rsv-{uuid.uuid4().hex[:16]}", decision["requirement"]["tenant"],
                            tuple(decision["selected"]), decision["requirement"]["isolation"], "reserved",
                            self.clock(), idem, fence, rdig)
            self._append("reserve", r.to_dict())
            self._apply("reserve", r.to_dict())
            return r, decision

    def release(self, reservation_id: str, *, tenant: str, fence: int = 0) -> Reservation:
        with self._lock:
            self._check_fence(fence)
            r = self.reservations.get(reservation_id)
            if r is None:
                raise AccelError("ACCEL_UNKNOWN_RESERVATION", reservation_id=reservation_id)
            if r.tenant != tenant:
                raise AccelError("ACCEL_FORBIDDEN", "reservation belongs to another tenant")
            if r.state == "released":
                return r                                     # idempotent release
            lifecycle.check(lifecycle.REQUEST, r.state, "released")
            self._append("release", {"reservation_id": reservation_id})
            self._apply("release", {"reservation_id": reservation_id})
            return r

    def quarantine(self, dev_id: str, reason: str, *, fence: int = 0) -> None:
        with self._lock:
            self._check_fence(fence)
            self._append("quarantine", {"dev_id": dev_id, "reason": reason})
            self._apply("quarantine", {"dev_id": dev_id, "reason": reason})

    def drain(self, dev_id: str, reason: str, *, fence: int = 0) -> None:
        with self._lock:
            self._check_fence(fence)
            self._append("drain", {"dev_id": dev_id, "reason": reason})
            self._apply("drain", {"dev_id": dev_id, "reason": reason})

    def unquarantine(self, dev_id: str, *, fence: int = 0) -> None:
        with self._lock:
            self._check_fence(fence)
            self._append("unquarantine", {"dev_id": dev_id})
            self._apply("unquarantine", {"dev_id": dev_id})

    def revoke_device(self, dev_id: str, reason: str, *, fence: int = 0) -> list[str]:
        """Quarantine a device and revoke every active reservation that includes it."""
        with self._lock:
            self.quarantine(dev_id, reason, fence=fence)
            out = []
            for r in self.active():
                if dev_id in r.devices:
                    self._append("revoke", {"reservation_id": r.reservation_id})
                    self._apply("revoke", {"reservation_id": r.reservation_id})
                    out.append(r.reservation_id)
            return out

    def advance_fence(self, fence: int) -> None:
        with self._lock:
            self._check_fence(fence)
            self._append("fence", {"fence": fence})
            self._apply("fence", {"fence": fence})

    # ------------------------------------------------------------------ backup / migration
    def snapshot(self) -> dict:
        with self._lock:
            body = {"schema": "PK_ACCEL_STATE_SNAPSHOT/1", "journal_seq": self._seq, "journal_tip": self._tip,
                    "max_fence": self.max_fence, "quarantined": dict(self.quarantined), "draining": dict(self.draining),
                    "reservations": [r.to_dict() for r in self.reservations.values()]}
        body["sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        return body

    @classmethod
    def restore(cls, snap: dict, **kw) -> "ReservationStore":
        body = {k: v for k, v in snap.items() if k != "sha256"}
        if snap.get("schema") != "PK_ACCEL_STATE_SNAPSHOT/1":
            raise AccelError("ACCEL_UNSUPPORTED_VERSION", "unknown snapshot schema")
        if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != snap.get("sha256"):
            raise AccelError("ACCEL_STATE_CORRUPT", "snapshot digest mismatch")
        s = cls(**kw)
        for r in snap["reservations"]:
            s._apply("reserve", r)
            if r["state"] != "reserved":
                s.reservations[r["reservation_id"]].state = r["state"]
        s.quarantined, s.draining = dict(snap["quarantined"]), dict(snap["draining"])
        s.max_fence = snap["max_fence"]
        s._tip, s._seq = snap["journal_tip"], snap["journal_seq"]
        return s
