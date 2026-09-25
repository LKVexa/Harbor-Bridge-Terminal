"""#6 #7 #49: outcome semantics, durable lifecycle state machine, fencing, backup/restore.

State machine (``PK_TRANSFER_LIFECYCLE/1``)::

    admitted -> in_flight -> completed
        |           |-----> failed        (retryable or terminal, with code)
        |           |-----> quarantined   (integrity mismatch)
        |           '-----> cancelled
        '-----> failed (no transport) | cancelled | expired

Every transition is appended to a write-ahead journal (JSON lines, fsync'd)
*before* it is applied in memory, tagged with the controller's fencing epoch.
Replay after restart rebuilds exactly the open set.  A controller holding a
stale epoch (split brain / stale leader) is refused by :class:`FencingLease`.
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import time
from collections.abc import Callable, Mapping
from pathlib import Path

from .data_plane import _StructuredError

STATES = ("admitted", "in_flight", "completed", "failed", "quarantined", "cancelled", "expired")
TERMINAL = frozenset({"completed", "failed", "quarantined", "cancelled", "expired"})
TRANSITIONS = {
    None: {"admitted"},
    "admitted": {"in_flight", "failed", "cancelled", "expired"},
    "in_flight": {"completed", "failed", "quarantined", "cancelled", "expired"},
}

# #6 outcome / degraded-state semantics: what each outcome means to the caller.
OUTCOMES = {
    "completed": {"delivered": True, "verified": True, "caller_action": "none"},
    "failed": {"delivered": False, "verified": False, "caller_action": "retry if retryable else escalate"},
    "quarantined": {"delivered": False, "verified": False, "caller_action": "investigate; never auto-retry"},
    "cancelled": {"delivered": False, "verified": False, "caller_action": "none"},
    "expired": {"delivered": "unknown", "verified": False, "caller_action": "reconcile with receiver"},
    "partial": {"delivered": "subset", "verified": "per-chunk", "caller_action": "resume missing chunks"},
}

# Which functions stay available when a dependency is lost (degraded mode matrix).
DEGRADED_MODES = {
    "policy_source_down": {"admit": "last verified policy until max_policy_age, then refuse",
                           "complete": "allowed", "policy.update": "refused"},
    "label_authority_down": {"admit": "refuse (fail closed)", "complete": "allowed"},
    "key_service_down": {"admit": "refuse (fail closed)", "complete": "allowed if no signing needed",
                         "audit": "buffer refused; admission blocked"},
    "journal_unwritable": {"admit": "refuse", "complete": "refuse", "health": "not ready"},
    "bulk_transport_down": {"admit": "inline only", "failover": "residency-safe alternates only"},
    "control_transport_down": {"admit": "bulk only; VM control verbs refused"},
    "telemetry_sink_down": {"admit": "allowed; bounded local buffer, drop-oldest counted"},
}


class LifecycleError(_StructuredError, RuntimeError):
    code = "PK_LIFECYCLE_INVALID"


class StaleController(_StructuredError, PermissionError):
    code = "PK_STALE_CONTROLLER"


class FencingLease:
    """File-backed monotonically increasing epoch with lease expiry.

    ``acquire`` bumps the epoch; any holder of an older epoch is rejected by
    :meth:`check`.  The same idea maps to etcd/Consul/ZooKeeper leases in a
    fleet (see docs/ARCHITECTURE-DECISIONS).
    """

    def __init__(self, path: str | os.PathLike[str], *, ttl: float = 15.0, clock: Callable[[], float] = time.time):
        self._path = Path(path)
        self._ttl = ttl
        self._clock = clock
        self._lock = threading.Lock()

    def _read(self) -> dict[str, object]:
        if not self._path.exists():
            return {"epoch": 0, "holder": None, "expires": 0.0}
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _write(self, state: Mapping[str, object]) -> None:
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state), encoding="utf-8")
        os.replace(tmp, self._path)

    def acquire(self, holder: str, *, force: bool = False) -> int:
        with self._lock:
            state = self._read()
            if (state["holder"] not in (None, holder) and self._clock() < float(state["expires"])  # type: ignore[arg-type]
                    and not force):
                raise StaleController("lease held by another controller", holder=state["holder"])
            epoch = int(state["epoch"]) + 1  # type: ignore[call-overload]
            self._write({"epoch": epoch, "holder": holder, "expires": self._clock() + self._ttl})
            return epoch

    def renew(self, holder: str, epoch: int) -> None:
        with self._lock:
            self.check(holder, epoch)
            self._write({"epoch": epoch, "holder": holder, "expires": self._clock() + self._ttl})

    def check(self, holder: str, epoch: int) -> None:
        state = self._read()
        if int(state["epoch"]) != epoch or state["holder"] != holder:  # type: ignore[call-overload]
            raise StaleController("fencing epoch superseded", held=epoch, current=state["epoch"])
        if self._clock() > float(state["expires"]):  # type: ignore[arg-type]
            raise StaleController("lease expired", epoch=epoch)


class TransferJournal:
    """Write-ahead journal + in-memory projection of transfer lifecycle."""

    def __init__(self, path: str | os.PathLike[str] | None = None, *, lease: FencingLease | None = None,
                 holder: str = "controller", clock: Callable[[], float] = time.time, fsync: bool = True):
        self._path = Path(path) if path else None
        self._lease = lease
        self._holder = holder
        self._epoch = lease.acquire(holder) if lease else 0
        self._clock = clock
        self._fsync = fsync
        self._lock = threading.RLock()
        self.state: dict[str, dict[str, object]] = {}
        self.replayed = 0
        if self._path and self._path.exists():
            self._replay()

    @property
    def epoch(self) -> int:
        return self._epoch

    def _replay(self) -> None:
        if self._path is None:
            return
        with open(self._path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh):
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    # torn final write after crash: ignore only if it is the last line
                    rest = fh.read()
                    if rest.strip():
                        raise LifecycleError("corrupt journal record", line=lineno) from None
                    break
                self._apply(rec)
                self.replayed += 1

    def _apply(self, rec: Mapping[str, object]) -> None:
        tid = str(rec["transfer_id"])
        cur = self.state.get(tid)
        prev = None if cur is None else cur["state"]
        new = str(rec["state"])
        if prev in TERMINAL and new == prev:
            return  # idempotent duplicate terminal
        if new not in TRANSITIONS.get(prev, set()):  # type: ignore[arg-type, call-overload]
            raise LifecycleError("illegal transition", transfer_id=tid, frm=prev, to=new)
        entry = dict(cur or {})
        entry.update({k: v for k, v in rec.items() if k not in ("transfer_id",)})
        entry["history"] = [*(cur or {}).get("history", []), new]  # type: ignore[misc]
        self.state[tid] = entry

    def transition(self, transfer_id: str, state: str, **fields: object) -> dict[str, object]:
        if state not in STATES:
            raise LifecycleError("unknown state", state=state)
        with self._lock:
            if self._lease is not None:
                self._lease.check(self._holder, self._epoch)
            rec = {"transfer_id": transfer_id, "state": state, "ts": self._clock(), "epoch": self._epoch, **fields}
            cur = self.state.get(transfer_id)
            prev = None if cur is None else cur["state"]
            if prev in TERMINAL and prev == state:
                return dict(cur)  # type: ignore[arg-type]
            if state not in TRANSITIONS.get(prev, set()):  # type: ignore[arg-type, call-overload]
                raise LifecycleError("illegal transition", transfer_id=transfer_id, frm=prev, to=state)
            if self._path is not None:
                with open(self._path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, sort_keys=True) + "\n")
                    fh.flush()
                    if self._fsync:
                        os.fsync(fh.fileno())
            self._apply(rec)
            return dict(self.state[transfer_id])

    def open_transfers(self) -> dict[str, dict[str, object]]:
        with self._lock:
            return {k: dict(v) for k, v in self.state.items() if v["state"] not in TERMINAL}

    def expire_older_than(self, max_age: float) -> list[str]:
        """Stall handling: move non-terminal transfers past ``max_age`` to ``expired``."""
        now = self._clock()
        out = []
        for tid, rec in self.open_transfers().items():
            if now - float(rec["admitted_ts"] if "admitted_ts" in rec else rec["ts"]) > max_age:  # type: ignore[arg-type]
                self.transition(tid, "expired", reason="stall_timeout")
                out.append(tid)
        return out

    # ---- #49 backup / restore / reconstruction ---------------------------------

    def backup(self, dest: str | os.PathLike[str]) -> dict[str, object]:
        if self._path is None:
            raise LifecycleError("in-memory journal cannot be backed up to file")
        with self._lock:
            shutil.copyfile(self._path, dest)
        import hashlib
        raw = Path(dest).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        return {"schema": "PK_JOURNAL_BACKUP/1", "records": raw.count(b"\n"),
                "sha256": digest, "epoch": self._epoch}

    @classmethod
    def restore(cls, backup: str | os.PathLike[str], target: str | os.PathLike[str], *,
                expected_sha256: str | None = None, **kwargs: object) -> TransferJournal:
        import hashlib
        data = Path(backup).read_bytes()
        if expected_sha256 is not None and hashlib.sha256(data).hexdigest() != expected_sha256:
            raise LifecycleError("backup checksum mismatch")
        Path(target).write_bytes(data)
        return cls(target, **kwargs)  # type: ignore[arg-type]
