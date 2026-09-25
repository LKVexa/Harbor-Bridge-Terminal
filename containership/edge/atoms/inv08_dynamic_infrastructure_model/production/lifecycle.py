"""Component 14 - node lifecycle state machine with journal persistence/replay.

Contract (LIFECYCLE_SPEC):
* States: STATES.  TERMINATED is final.
* Only TRANSITIONS edges are legal; anything else raises
  INV08.LIFECYCLE.FORBIDDEN_TRANSITION and changes nothing.
* Guards: LEASED requires ``lease_id``; RECLAIMING from DRAINING requires
  ``busy`` False; RECOVERING->READY requires ``health_ok``.
* Idempotency: a transition carrying an ``op_id`` already applied is a no-op
  that returns the original event (duplicates/retries are safe).
* Timeouts (``sweep``): JOINING past join_timeout -> ORPHANED; LEASED with no
  heartbeat within heartbeat_timeout -> ORPHANED; DRAINING past drain_timeout
  -> QUARANTINED; ORPHANED past orphan_timeout -> RECLAIMING.
* Persistence: every applied event is appended (canonical JSON, one line,
  fsync) with a hash chain.  ``replay`` rebuilds identical state; a torn final
  line (crash mid-write) is discarded; any other corruption is
  INV08.LIFECYCLE.JOURNAL_CORRUPT (operator required, no auto-repair).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .core import Inv08Error, canonical, sha256_hex
from .errors_catalog import error

STATES = ("REQUESTED", "JOINING", "READY", "LEASED", "DRAINING", "QUARANTINED",
          "RECLAIMING", "TERMINATED", "ORPHANED", "RECOVERING")
TRANSITIONS: dict[str, frozenset[str]] = {
    "REQUESTED": frozenset({"JOINING", "TERMINATED"}),
    "JOINING": frozenset({"READY", "QUARANTINED", "ORPHANED", "TERMINATED"}),
    "READY": frozenset({"LEASED", "DRAINING", "QUARANTINED", "ORPHANED"}),
    "LEASED": frozenset({"READY", "DRAINING", "QUARANTINED", "ORPHANED"}),
    "DRAINING": frozenset({"RECLAIMING", "QUARANTINED", "ORPHANED"}),
    "QUARANTINED": frozenset({"RECOVERING", "RECLAIMING"}),
    "RECLAIMING": frozenset({"TERMINATED"}),
    "ORPHANED": frozenset({"RECOVERING", "RECLAIMING"}),
    "RECOVERING": frozenset({"READY", "QUARANTINED", "RECLAIMING"}),
    "TERMINATED": frozenset(),
}
LIFECYCLE_SPEC = {"version": "PK_DYN_LIFECYCLE/1", "states": STATES,
                  "transitions": {k: sorted(v) for k, v in TRANSITIONS.items()}}
DEFAULT_TIMEOUTS = {"join_timeout": 300.0, "heartbeat_timeout": 60.0,
                    "drain_timeout": 900.0, "orphan_timeout": 600.0}
GENESIS = "0" * 64


class Lifecycle:
    def __init__(self, journal: str | os.PathLike | None = None, *, timeouts: dict | None = None) -> None:
        self.timeouts = {**DEFAULT_TIMEOUTS, **(timeouts or {})}
        self.nodes: dict[str, dict] = {}
        self._ops: dict[str, dict] = {}
        self._head = GENESIS
        self._seq = 0
        self.journal = Path(journal) if journal else None
        if self.journal and self.journal.exists():
            self._replay()

    # -------------------------------------------------------------- core
    def register(self, node_id: str, now: float, op_id: str | None = None) -> dict:
        op_id = op_id or f"register:{node_id}"
        if op_id in self._ops:
            return self._ops[op_id]
        if node_id in self.nodes:
            raise error("INV08.LIFECYCLE.FORBIDDEN_TRANSITION", f"{node_id} already registered")
        return self._apply({"node": node_id, "from": None, "to": "REQUESTED", "ts": now,
                            "op_id": op_id, "attrs": {}})

    def state(self, node_id: str) -> str:
        if node_id not in self.nodes:
            raise error("INV08.LIFECYCLE.UNKNOWN_NODE", node_id)
        return self.nodes[node_id]["state"]

    def transition(self, node_id: str, to: str, now: float, *, op_id: str,
                   reason: str = "", **attrs) -> dict:
        if op_id in self._ops:                      # idempotent retry
            return self._ops[op_id]
        cur = self.state(node_id)
        if to not in STATES or to not in TRANSITIONS[cur]:
            raise error("INV08.LIFECYCLE.FORBIDDEN_TRANSITION", f"{node_id}: {cur} -> {to}",
                        details={"node": node_id, "from": cur, "to": to})
        self._guard(node_id, cur, to, attrs)
        return self._apply({"node": node_id, "from": cur, "to": to, "ts": now, "op_id": op_id,
                            "reason": reason, "attrs": attrs})

    def _guard(self, node_id: str, cur: str, to: str, attrs: dict) -> None:
        bad = None
        if to == "LEASED" and not attrs.get("lease_id"):
            bad = "LEASED requires lease_id"
        elif cur == "DRAINING" and to == "RECLAIMING" and attrs.get("busy", True):
            bad = "cannot reclaim while workload busy"
        elif cur == "RECOVERING" and to == "READY" and not attrs.get("health_ok"):
            bad = "READY after recovery requires health_ok"
        if bad:
            raise error("INV08.LIFECYCLE.GUARD_FAILED", f"{node_id}: {bad}",
                        details={"node": node_id, "from": cur, "to": to})

    def heartbeat(self, node_id: str, now: float) -> None:
        self.state(node_id)
        self.nodes[node_id]["last_heartbeat"] = now      # volatile, not journaled

    def sweep(self, now: float) -> list[dict]:
        """Apply timeout/abandonment/orphan transitions deterministically (sorted ids)."""
        out, t = [], self.timeouts
        for nid in sorted(self.nodes):
            n = self.nodes[nid]
            age = now - n["since"]
            hb = now - n.get("last_heartbeat", n["since"])
            to = None
            if n["state"] == "JOINING" and age > t["join_timeout"]:
                to = "ORPHANED"
            elif n["state"] == "LEASED" and hb > t["heartbeat_timeout"]:
                to = "ORPHANED"
            elif n["state"] == "DRAINING" and age > t["drain_timeout"]:
                to = "QUARANTINED"
            elif n["state"] == "ORPHANED" and age > t["orphan_timeout"]:
                to = "RECLAIMING"
            if to:
                out.append(self.transition(nid, to, now, op_id=f"sweep:{nid}:{n['version']}",
                                           reason="timeout"))
        return out

    # -------------------------------------------------------------- persistence
    def _apply(self, ev: dict, *, persist: bool = True) -> dict:
        ev = dict(ev, seq=self._seq + 1, prev=self._head)
        ev["hash"] = sha256_hex(canonical({k: v for k, v in ev.items() if k != "hash"}))
        if persist and self.journal:
            with open(self.journal, "ab") as fh:
                fh.write(canonical(ev) + b"\n")
                fh.flush()
                os.fsync(fh.fileno())
        self._fold(ev)
        return ev

    def _fold(self, ev: dict) -> None:
        n = self.nodes.setdefault(ev["node"], {"version": 0})
        n.update(state=ev["to"], since=ev["ts"], version=n["version"] + 1)
        if "lease_id" in ev["attrs"]:
            n["lease_id"] = ev["attrs"]["lease_id"]
        if ev["to"] == "LEASED":
            n["last_heartbeat"] = ev["ts"]
        self._ops[ev["op_id"]] = ev
        self._seq, self._head = ev["seq"], ev["hash"]

    def _replay(self) -> None:
        raw = self.journal.read_bytes()
        lines = raw.split(b"\n")
        torn = lines[-1] != b""           # last line lacks newline => torn write
        body = lines[:-1]
        for i, line in enumerate(body, 1):
            try:
                ev = json.loads(line)
                ok = (ev["seq"] == self._seq + 1 and ev["prev"] == self._head and
                      ev["hash"] == sha256_hex(canonical({k: v for k, v in ev.items() if k != "hash"})))
                if ok and ev["from"] is not None:
                    ok = ev["node"] in self.nodes and self.nodes[ev["node"]]["state"] == ev["from"] \
                        and ev["to"] in TRANSITIONS[ev["from"]]
            except (ValueError, KeyError, TypeError):
                ok = False
            if not ok:
                raise error("INV08.LIFECYCLE.JOURNAL_CORRUPT", f"journal line {i} invalid",
                            details={"line": i})
            self._fold(ev)
        if torn:   # truncate the partial record so future appends stay line-aligned
            with open(self.journal, "r+b") as fh:
                fh.truncate(len(raw) - len(lines[-1]))

    def snapshot(self) -> dict:
        return {"seq": self._seq, "head": self._head,
                "nodes": {k: {"state": v["state"], "version": v["version"]} for k, v in sorted(self.nodes.items())}}
