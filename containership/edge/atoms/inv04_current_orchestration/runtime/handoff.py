"""Hand-off integrity to the successor scheduler (components 36-39).

* 36 ``Snapshot`` carries id, timestamp, source resourceVersion, per-pod UID /
  generation / owner references and a content digest (consistency marker).
* 37 ``HandoffSession`` tracks acknowledgement by digest: at-least-once
  delivery, resume from last acked sequence, exactly-once *application* by the
  receiver via sequence dedupe.
* 38 ``ChangeStream`` emits incremental diffs with contiguous sequence numbers;
  the receiver detects gaps and must resync from a fresh snapshot.
* 39 ``OwnershipRegistry`` records which controller is authoritative per
  workload and refuses dual ownership during migration.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Sequence

from .errors import HandoffGap, OwnershipConflict
from .journal import digest
from .objects import PodSpec


@dataclass(frozen=True)
class Snapshot:
    snapshot_id: str
    taken_at: float
    source_rv: int
    workloads: dict
    digest: str
    seq: int = 0

    def as_dict(self) -> dict:
        return {"snapshot_id": self.snapshot_id, "taken_at": self.taken_at, "source_rv": self.source_rv,
                "seq": self.seq, "digest": self.digest, "workloads": self.workloads}

    def inventory(self) -> dict[str, list[str]]:
        """Legacy PK_ORCH_INVENTORY/1 view."""
        return {w: sorted(p["node"] for p in pods) for w, pods in sorted(self.workloads.items())}


def _pod_entry(p: PodSpec) -> dict:
    return {"name": p.meta.key, "uid": p.meta.uid, "node": p.node, "generation": p.meta.generation,
            "resource_version": p.meta.resource_version,
            "owner": {"kind": p.meta.owner_kind, "name": p.meta.owner_name, "uid": p.meta.owner_uid}}


def take_snapshot(pods: Sequence[PodSpec], source_rv: int, *, clock: Callable[[], float] = time.time,
                  include_terminal: bool = False) -> Snapshot:
    wl: dict[str, list[dict]] = {}
    for p in pods:
        if not p.workload or p.mirror:
            continue
        if not include_terminal and p.phase in ("Succeeded", "Failed"):
            continue
        wl.setdefault(p.workload, []).append(_pod_entry(p))
    body = {w: sorted(v, key=lambda e: e["uid"]) for w, v in sorted(wl.items())}
    return Snapshot(str(uuid.uuid4()), clock(), source_rv, body, digest({"rv": source_rv, "workloads": body}))


def diff(old: Snapshot, new: Snapshot) -> list[dict]:
    ops = []
    o = {e["uid"]: (w, e) for w, es in old.workloads.items() for e in es}
    n = {e["uid"]: (w, e) for w, es in new.workloads.items() for e in es}
    for uid in sorted(set(o) - set(n)):
        ops.append({"op": "remove", "workload": o[uid][0], "uid": uid})
    for uid in sorted(set(n) - set(o)):
        ops.append({"op": "add", "workload": n[uid][0], "pod": n[uid][1]})
    for uid in sorted(set(o) & set(n)):
        if o[uid][1] != n[uid][1]:
            ops.append({"op": "update", "workload": n[uid][0], "pod": n[uid][1]})
    return ops


class ChangeStream:
    def __init__(self, base: Snapshot):
        self.base = base
        self.current = base
        self.seq = 0
        self.log: list[dict] = []
        self._lock = threading.Lock()

    def publish(self, new: Snapshot) -> dict | None:
        with self._lock:
            ops = diff(self.current, new)
            if not ops:
                return None
            self.seq += 1
            msg = {"seq": self.seq, "from_digest": self.current.digest, "to_digest": new.digest,
                   "source_rv": new.source_rv, "ops": ops}
            self.log.append(msg)
            self.current = new
            return msg

    def since(self, seq: int) -> list[dict]:
        with self._lock:
            return [m for m in self.log if m["seq"] > seq]


class Receiver:
    """Successor-side applier: dedupes, detects gaps and digest divergence."""

    def __init__(self, snapshot: Snapshot):
        self.workloads = {w: {e["uid"]: e for e in es} for w, es in snapshot.workloads.items()}
        self.digest = snapshot.digest
        self.seq = 0

    def apply(self, msg: dict) -> bool:
        if msg["seq"] <= self.seq:
            return False  # duplicate delivery: exactly-once application
        if msg["seq"] != self.seq + 1 or msg["from_digest"] != self.digest:
            raise HandoffGap(f"expected seq {self.seq + 1} from {self.digest[:12]}, got {msg['seq']}",
                             details={"expected": self.seq + 1, "got": msg["seq"]})
        for op in msg["ops"]:
            bucket = self.workloads.setdefault(op["workload"], {})
            if op["op"] == "remove":
                bucket.pop(op["uid"], None)
            else:
                bucket[op["pod"]["uid"]] = op["pod"]
            if not bucket:
                self.workloads.pop(op["workload"], None)
        self.seq, self.digest = msg["seq"], msg["to_digest"]
        return True

    def state_digest(self, source_rv: int) -> str:
        body = {w: sorted(v.values(), key=lambda e: e["uid"]) for w, v in sorted(self.workloads.items())}
        return digest({"rv": source_rv, "workloads": body})


@dataclass
class HandoffSession:
    """Sender-side ack tracking with resume."""

    stream: ChangeStream
    acked_seq: int = 0
    acked_snapshot: str = ""
    attempts: dict[int, int] = field(default_factory=dict)

    def ack_snapshot(self, snapshot_digest: str) -> None:
        if snapshot_digest != self.stream.base.digest:
            raise HandoffGap("snapshot acknowledgement digest mismatch")
        self.acked_snapshot = snapshot_digest

    def pending(self) -> list[dict]:
        if not self.acked_snapshot:
            raise HandoffGap("snapshot not yet acknowledged")
        msgs = self.stream.since(self.acked_seq)
        for m in msgs:
            self.attempts[m["seq"]] = self.attempts.get(m["seq"], 0) + 1
        return msgs

    def ack(self, seq: int, to_digest: str) -> None:
        match = [m for m in self.stream.log if m["seq"] == seq]
        if not match or match[0]["to_digest"] != to_digest:
            raise HandoffGap(f"ack for seq {seq} does not match sent digest")
        self.acked_seq = max(self.acked_seq, seq)


class OwnershipRegistry:
    """Exactly one authoritative controller per workload (39)."""

    def __init__(self) -> None:
        self.owner: dict[str, str] = {}
        self.history: list[tuple[str, str, str]] = []
        self._lock = threading.Lock()

    def claim(self, workload: str, controller: str) -> None:
        with self._lock:
            cur = self.owner.get(workload)
            if cur and cur != controller:
                raise OwnershipConflict(f"{workload} is owned by {cur}", details={"workload": workload, "owner": cur})
            self.owner[workload] = controller

    def transfer(self, workload: str, frm: str, to: str) -> None:
        with self._lock:
            if self.owner.get(workload) != frm:
                raise OwnershipConflict(f"{workload} not owned by {frm}", details={"workload": workload})
            self.owner[workload] = to
            self.history.append((workload, frm, to))

    def may_reconcile(self, workload: str, controller: str) -> bool:
        return self.owner.get(workload, controller) == controller
