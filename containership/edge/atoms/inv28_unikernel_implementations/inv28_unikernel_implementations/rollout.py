"""Canary / staged rollout of new toolchain versions, with automatic halt and rollback (MC-043, MC-068, MC-069).

A toolchain version that is *under rollout* is selectable only for the cohort its current stage
admits.  Cohort membership is a deterministic hash of the site id (or workload id when no site is
given) into [0, 100), so the same workload lands in the same cohort on every evaluation.

``promote`` advances one stage only if the supplied health signal is within budget (refusal-rate
and binding-failure budgets); otherwise the rollout halts.  ``rollback`` ends the rollout and
removes the version from every cohort - selection falls back to the previously admitted versions
immediately (the registry itself is untouched; use ``Registry.rollback`` for data rollback).

GAP-08 (OTA lifecycle/rollback) is a *peer*: every plan, promotion, halt and rollback is announced
to an injected ``Gap08Port``.  If the port is down, promotion is refused (we do not advance a
rollout the OTA side cannot follow); rollback proceeds locally and the failed announcement is
recorded for retry - stopping bad software never waits on a peer.
"""
from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass, field
from typing import Protocol

from .errors import Inv28Error, Reason, ValidationError
from .model import sha256_hex


class Gap08Port(Protocol):
    def announce(self, event: dict) -> None: ...


@dataclass
class Stage:
    name: str
    percent: int          # 0..100 cohort share
    sites: frozenset = frozenset()   # explicit site allow-list for this stage (unioned with percent)


@dataclass
class Plan:
    ref: str
    stages: list
    index: int = 0
    state: str = "in_progress"    # in_progress | halted | completed | rolled_back
    history: list = field(default_factory=list)


def cohort(value: str) -> int:
    return int(hashlib.sha256(value.encode()).hexdigest()[:8], 16) % 100


class RolloutController:
    def __init__(self, gap08: Gap08Port | None = None, *, max_refusal_rate: float = 0.05,
                 max_binding_failures: int = 0):
        self._plans: dict[str, Plan] = {}
        self._gap08 = gap08
        self._max_refusal = max_refusal_rate
        self._max_bind = max_binding_failures
        self._lock = threading.RLock()
        self.pending_announcements: list = []

    @property
    def digest(self) -> str:
        with self._lock:
            return sha256_hex({r: [p.index, p.state] for r, p in sorted(self._plans.items())})

    def plan(self, ref: str, stages: list) -> Plan:
        if not stages or any(not 0 <= s.percent <= 100 for s in stages):
            raise ValidationError("rollout stages must have percent in [0, 100]")
        if [s.percent for s in stages] != sorted(s.percent for s in stages) or stages[-1].percent != 100:
            raise ValidationError("rollout stages must be non-decreasing and end at 100%")
        with self._lock:
            if ref in self._plans and self._plans[ref].state == "in_progress":
                raise ValidationError(f"{ref} already has a rollout in progress")
            p = Plan(ref, list(stages))
            self._plans[ref] = p
            self._announce({"event": "plan", "ref": ref, "stages": [s.name for s in stages]}, required=True)
            return p

    def admits(self, ref: str, req) -> bool:
        """completed -> everyone; rolled_back -> no one; in_progress/halted -> the current stage's cohort
        (a halted rollout is frozen, never widened)."""
        with self._lock:
            p = self._plans.get(ref)
            if p is None or p.state == "completed":
                return True
            if p.state == "rolled_back":
                return False
            st = p.stages[p.index]
            site = getattr(req, "site", None)
            if site is not None and site.site_id in st.sites:
                return True
            return cohort(site.site_id if site is not None else req.workload_id) < st.percent

    def promote(self, ref: str, *, selections: int, refusals: int, binding_failures: int) -> Plan:
        with self._lock:
            p = self._plans[ref]
            if p.state != "in_progress":
                raise ValidationError(f"rollout for {ref} is {p.state}")
            rate = refusals / selections if selections else 1.0
            if rate > self._max_refusal or binding_failures > self._max_bind:
                p.state = "halted"
                p.history.append({"event": "halt", "refusal_rate": rate, "binding_failures": binding_failures})
                self._announce({"event": "halt", "ref": ref}, required=False)
                return p
            self._announce({"event": "promote", "ref": ref, "to": p.index + 1}, required=True)
            if p.index + 1 >= len(p.stages):
                p.state = "completed"
            else:
                p.index += 1
            p.history.append({"event": "promote", "index": p.index, "refusal_rate": rate})
            return p

    def rollback(self, ref: str, *, reason: str) -> Plan:
        with self._lock:
            p = self._plans[ref]
            p.state = "rolled_back"
            p.history.append({"event": "rollback", "reason": reason})
            self._announce({"event": "rollback", "ref": ref, "reason": reason}, required=False)
            return p

    def state(self, ref: str) -> Plan | None:
        return self._plans.get(ref)

    def _announce(self, event: dict, *, required: bool):
        if self._gap08 is None:
            return
        try:
            self._gap08.announce(event)
        except Exception as exc:  # noqa: BLE001
            if required:
                raise Inv28Error(Reason.DEPENDENCY_UNAVAILABLE, f"GAP-08 unavailable: {exc}") from None
            self.pending_announcements.append(event)
