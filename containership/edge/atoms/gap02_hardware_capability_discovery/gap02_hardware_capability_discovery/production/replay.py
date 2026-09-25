"""GAP02-MC-11 — Replay protection and report sequencing.

Each envelope carries (boot_id, epoch, sequence, topology_digest, nonce).
``ReplayGuard`` (consumer side) accepts only strictly increasing (epoch, sequence)
per node+boot, rejects a reused nonce, and rejects a report whose topology
digest predates a topology-change notice it has already seen.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
import hashlib
import json
import os
import threading

from .errors import Code, Gap02Error


def topology_digest(facts: dict) -> str:
    return hashlib.sha256(json.dumps(facts, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def new_nonce() -> str:
    return os.urandom(16).hex()


@dataclass
class Sequencer:
    """Producer side: monotonic sequence, bumps epoch on topology change."""
    boot_id: str
    epoch: int = 0
    sequence: int = 0
    topology: str = ""

    def next(self, topology: str) -> dict:
        if topology != self.topology:
            self.epoch += 1
            self.topology = topology
        self.sequence += 1
        return {"boot_id": self.boot_id, "epoch": self.epoch, "sequence": self.sequence,
                "topology_digest": topology, "nonce": new_nonce()}


@dataclass
class ReplayGuard:
    max_nonces: int = 10_000
    _hw: dict = field(default_factory=dict)          # (node, boot) -> (epoch, seq)
    _nonces: OrderedDict = field(default_factory=OrderedDict)
    _min_epoch: dict = field(default_factory=dict)    # node -> epoch required after change notice
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def topology_changed(self, node: str, boot_id: str, new_epoch: int) -> None:
        with self._lock:
            self._min_epoch[(node, boot_id)] = max(self._min_epoch.get((node, boot_id), 0), new_epoch)

    def admit(self, node: str, seq: dict) -> None:
        try:
            key = (node, str(seq["boot_id"]))
            pos = (int(seq["epoch"]), int(seq["sequence"]))
            nonce = str(seq["nonce"])
        except (KeyError, TypeError, ValueError) as e:
            raise Gap02Error(Code.MALFORMED_RESPONSE, "sequence block") from e
        with self._lock:
            if nonce in self._nonces:
                raise Gap02Error(Code.REPLAY_DETECTED, "nonce reused")
            if pos[0] < self._min_epoch.get(key, 0):
                raise Gap02Error(Code.REPLAY_DETECTED, "report predates known topology change")
            last = self._hw.get(key)
            if last is not None and pos <= last:
                raise Gap02Error(Code.REPLAY_DETECTED, f"(epoch,seq) {pos} <= last {last}")
            self._hw[key] = pos
            self._nonces[nonce] = None
            while len(self._nonces) > self.max_nonces:
                self._nonces.popitem(last=False)
