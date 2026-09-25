"""Component 17 - disconnected-operation semantics for node agents.

Contract (PARTITION_SPEC):
* Reachability from the node's view, by age of the last controller contact:
  CONNECTED (< suspect_after), SUSPECT (< partitioned_after), PARTITIONED.
* Lease while disconnected: the lease stays valid until ``expires_at``; the
  node may keep running existing work for ``grace`` seconds past expiry
  (LEASE_GRACE) and then MUST self-fence (FENCED): stop work, accept nothing.
  The controller never re-grants a lease on a node until expires_at + grace
  + clock_skew has passed (``controller_may_regrant``) - so both sides never
  own it simultaneously given bounded skew.
* Stale commands: every command carries (epoch, seq).  Epoch is the
  controller leadership generation.  Commands with epoch < highest seen, or
  same epoch and seq <= last seq, are rejected (INV08.PARTITION.STALE_COMMAND).
  A higher epoch resets seq tracking.
* Autonomy: while not CONNECTED only AUTONOMOUS_ACTIONS are allowed; at most
  ``max_local_reclaims`` local reclaims; everything else ->
  INV08.PARTITION.AUTONOMY_LIMIT.  FENCED allows only 'report'.
* Reconcile after reconnect (``reconcile``): per node, terminal facts win
  (a node that fenced/terminated locally stays so); otherwise the higher
  (epoch, version) wins; equal keys with different state are conflicts that
  resolve to the controller view and are reported.
"""
from __future__ import annotations

from .errors_catalog import error

AUTONOMOUS_ACTIONS = frozenset({"heartbeat_attempt", "drain", "local_reclaim", "report", "self_fence"})
TERMINAL_FACTS = frozenset({"FENCED", "TERMINATED"})


class NodeAgent:
    def __init__(self, node_id: str, *, suspect_after: float = 15.0, partitioned_after: float = 45.0,
                 grace: float = 30.0, max_local_reclaims: int = 1) -> None:
        if not 0 < suspect_after < partitioned_after or grace < 0:
            raise ValueError("need 0 < suspect_after < partitioned_after and grace >= 0")
        self.node_id = node_id
        self.suspect_after, self.partitioned_after = suspect_after, partitioned_after
        self.grace, self.max_local_reclaims = grace, max_local_reclaims
        self.last_contact: float | None = None
        self.lease_expires: float | None = None
        self.epoch, self.seq = -1, -1
        self.fenced = False
        self.local_reclaims = 0
        self.local_log: list[dict] = []

    def contact(self, now: float) -> None:
        if not self.fenced:
            self.last_contact = now
            self.local_reclaims = 0

    def reachability(self, now: float) -> str:
        if self.fenced:
            return "FENCED"
        if self.last_contact is None:
            return "PARTITIONED"
        age = now - self.last_contact
        if age < self.suspect_after:
            return "CONNECTED"
        return "SUSPECT" if age < self.partitioned_after else "PARTITIONED"

    def lease_state(self, now: float) -> str:
        """VALID | GRACE | FENCED | NONE; transitions to FENCED are sticky."""
        if self.fenced:
            return "FENCED"
        if self.lease_expires is None:
            return "NONE"
        if now < self.lease_expires:
            return "VALID"
        if now < self.lease_expires + self.grace:
            return "GRACE"
        self.fenced = True
        self.local_log.append({"action": "self_fence", "ts": now, "reason": "grace expired"})
        return "FENCED"

    def command(self, cmd: dict, now: float) -> dict:
        """Apply a controller command {epoch, seq, action, ...}."""
        e, s = cmd["epoch"], cmd["seq"]
        if e < self.epoch or (e == self.epoch and s <= self.seq):
            raise error("INV08.PARTITION.STALE_COMMAND", f"({e},{s}) <= ({self.epoch},{self.seq})",
                        details={"node": self.node_id, "epoch": e, "seq": s})
        if self.fenced:
            raise error("INV08.PARTITION.FENCED", f"{self.node_id} is fenced")
        self.epoch, self.seq = e, s
        self.contact(now)
        if cmd["action"] == "renew":
            self.lease_expires = cmd["expires_at"]
        return {"accepted": True, "epoch": e, "seq": s}

    def act_locally(self, action: str, now: float) -> dict:
        r = self.reachability(now)
        self.lease_state(now)
        if self.fenced and action != "report":
            raise error("INV08.PARTITION.FENCED", f"{action} refused: fenced")
        if r != "CONNECTED":
            if action not in AUTONOMOUS_ACTIONS:
                raise error("INV08.PARTITION.AUTONOMY_LIMIT", f"{action} not allowed while {r}")
            if action == "local_reclaim":
                if self.local_reclaims >= self.max_local_reclaims:
                    raise error("INV08.PARTITION.AUTONOMY_LIMIT", "local reclaim budget exhausted")
                self.local_reclaims += 1
        entry = {"action": action, "ts": now, "reachability": r}
        self.local_log.append(entry)
        return entry


def controller_may_regrant(lease_expires: float, grace: float, now: float, max_skew: float) -> bool:
    return now >= lease_expires + grace + max_skew


def reconcile(controller_view: dict[str, dict], node_reports: dict[str, dict]) -> dict:
    """Views map node_id -> {state, epoch, version}.  Deterministic merge."""
    merged, conflicts = {}, []
    for nid in sorted(set(controller_view) | set(node_reports)):
        c, n = controller_view.get(nid), node_reports.get(nid)
        if c is None or n is None:
            merged[nid] = dict(c or n)
            if c is None:
                conflicts.append({"node": nid, "kind": "unknown_to_controller", "resolution": "node"})
            continue
        if n["state"] in TERMINAL_FACTS and c["state"] not in TERMINAL_FACTS:
            merged[nid] = dict(n)
            conflicts.append({"node": nid, "kind": "local_terminal_fact", "resolution": "node"})
        elif c["state"] in TERMINAL_FACTS:
            merged[nid] = dict(c)
        elif (n["epoch"], n["version"]) > (c["epoch"], c["version"]):
            merged[nid] = dict(n)
        elif (n["epoch"], n["version"]) == (c["epoch"], c["version"]) and n["state"] != c["state"]:
            merged[nid] = dict(c)
            conflicts.append({"node": nid, "kind": "divergent_same_version", "resolution": "controller"})
        else:
            merged[nid] = dict(c)
    return {"merged": merged, "conflicts": conflicts}
