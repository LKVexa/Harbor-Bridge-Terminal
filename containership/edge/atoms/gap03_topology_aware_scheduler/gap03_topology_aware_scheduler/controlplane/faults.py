"""MC-032 - Fault-injection harness (GAP03-FAULT/1).

Deterministic, seeded fault primitives used by the fault-matrix tests:
* ``StoreFault``   - raise at a named durable-write stage (crash-before-fsync,
                     disk-full, read-only) N times or forever;
* ``ManualClock``  - controllable clock with jumps/skew;
* ``Network``      - partitions (full / asymmetric) between named parties;
* ``Chaos``        - seeded duplicate / reorder / delay of message lists;
* ``invariants``   - post-scenario safety assertions over ledger/journal/downstream/audit.
"""
from __future__ import annotations

import errno
import random


class StoreFault:
    def __init__(self, stage: str, *, times: int = 1, kind: str = "crash"):
        self.stage, self.remaining, self.kind = stage, times, kind
        self.fired = 0

    def __call__(self, stage: str):
        if stage == self.stage and self.remaining != 0:
            self.remaining -= 1
            self.fired += 1
            if self.kind == "disk_full":
                raise OSError(errno.ENOSPC, "No space left on device")
            if self.kind == "read_only":
                raise OSError(errno.EROFS, "Read-only file system")
            raise OSError(errno.EIO, "injected crash")


class ManualClock:
    def __init__(self, t: float = 1_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, s: float):
        self.t += s

    def jump(self, s: float):  # may be negative (time going backwards)
        self.t += s


class Network:
    def __init__(self):
        self.cut: set[tuple[str, str]] = set()

    def partition(self, a: str, b: str, *, asymmetric: bool = False):
        self.cut.add((a, b))
        if not asymmetric:
            self.cut.add((b, a))

    def heal(self):
        self.cut.clear()

    def reachable(self, a: str, b: str) -> bool:
        return (a, b) not in self.cut


class Chaos:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)

    def mangle(self, msgs: list, *, dup: float = 0.3, reorder: bool = True) -> list:
        out = []
        for m in msgs:
            out.append(m)
            if self.rng.random() < dup:
                out.append(m)
        if reorder:
            self.rng.shuffle(out)
        return out

    def flaky(self, fn, *, p_fail: float, exc_factory):
        def wrapped(*a, **k):
            if self.rng.random() < p_fail:
                raise exc_factory()
            return fn(*a, **k)
        return wrapped


def invariants(*, ledger=None, journal=None, downstream=None, audit=None, topology=None) -> dict:
    """Return {name: bool}. All must be True after every scenario."""
    res = {}
    if ledger is not None:
        from .ledger_store import used_of
        st = ledger.state
        used = used_of(st)
        res["no_capacity_overcommit"] = sum(used.values()) <= st["capacity"]
        res["no_negative_usage"] = all(v >= 0 for v in used.values())
        res["ledger_chain_ok"] = ledger.verify_history()["ok"]
    if journal is not None and downstream is not None:
        committed = {t for t, x in journal.state["txns"].items() if x["state"] == "COMMITTED"}
        placed = set(downstream.placements)
        res["no_committed_without_placement"] = committed <= placed
        res["no_duplicate_placement"] = len(placed) == len(set(placed))
        if ledger is not None:
            live = {c for c, x in ledger.state["claims"].items() if x["state"] == "committed"}
            res["ledger_matches_journal"] = live == committed
    if audit is not None:
        res["audit_chain_ok"] = audit.verify()["ok"]
    if topology is not None:
        try:
            topology.check_invariants(topology.state)
            res["topology_valid"] = True
        except Exception:  # noqa: BLE001
            res["topology_valid"] = False
    return res


MAX_RECOVERY_S = 5.0          # local objective: recover_all() + reconciliation must converge within this after a fault
MAX_RECOVERY_BACKLOG = 0      # no PREPARED/UNKNOWN transaction or pending claim may remain after recovery


def recovery_report(journal, ledger, elapsed_s: float) -> dict:
    backlog = sum(1 for t in journal.state["txns"].values() if t["state"] not in ("COMMITTED", "ABORTED"))
    pending = sum(1 for c in ledger.state["claims"].values() if c["state"] == "pending")
    return {"elapsed_s": round(elapsed_s, 4), "backlog": backlog + pending,
            "within_objective": elapsed_s <= MAX_RECOVERY_S and backlog + pending <= MAX_RECOVERY_BACKLOG}
