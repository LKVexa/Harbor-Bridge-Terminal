"""GAP02-MC-15 — Atomic sweep semantics.

A sweep builds a *fresh* CapabilityReport under a new generation id; it is
published by a single reference swap, only after every declared capability has
an entry (present/absent/unprobed). Consumers read ``SnapshotStore.current()``
and therefore never see a mix of generations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import threading
from typing import Iterable

from ..capabilities import UNPROBED, CapabilityReport
from .errors import Code, Gap02Error
from .evidence import ProbeEvidence, promote


@dataclass(frozen=True)
class Snapshot:
    generation: str
    sequence: int
    report: CapabilityReport
    evidence: tuple[dict, ...]
    topology_digest: str


class SweepBuilder:
    def __init__(self, node: str, declared: Iterable[str], now: int, sequence: int):
        self.report = CapabilityReport(node)
        self.declared = tuple(declared)
        self.now, self.sequence = now, sequence
        self.evidence: list[ProbeEvidence] = []
        self._sealed = False

    def add(self, ev: ProbeEvidence) -> str:
        if self._sealed:
            raise Gap02Error(Code.INTERNAL, "sweep already sealed")
        state = promote(ev)
        self.report.record(ev.capability, state, self.now, diagnostic=ev.error)
        self.evidence.append(ev)
        return state

    def seal(self) -> Snapshot:
        for cap in self.declared:  # declared but not produced → explicit unprobed
            if cap not in self.report.results:
                self.report.record(cap, UNPROBED, self.now, diagnostic="GAP02-E004 not completed in sweep")
        defects = self.report.consistency_defects(self.now)
        if defects:
            raise Gap02Error(Code.MALFORMED_RESPONSE, f"sweep inconsistent: {defects[:3]}")
        self._sealed = True
        states = sorted((c, s) for c, (s, _) in self.report.results.items())
        topo = hashlib.sha256(repr(states).encode()).hexdigest()
        gen = hashlib.sha256(f"{self.report.node}|{self.sequence}|{self.now}|{topo}".encode()).hexdigest()[:24]
        return Snapshot(gen, self.sequence, self.report, tuple(e.to_dict() for e in self.evidence), topo)


class SnapshotStore:
    def __init__(self) -> None:
        self._cur: Snapshot | None = None
        self._lock = threading.Lock()

    def publish(self, snap: Snapshot) -> None:
        with self._lock:
            if self._cur is not None and snap.sequence <= self._cur.sequence:
                raise Gap02Error(Code.REPLAY_DETECTED, "older sweep cannot replace newer")
            self._cur = snap

    def current(self) -> Snapshot | None:
        return self._cur
