"""Cross-rollout conflict detector (component 3).

Blocks a rollout whose scope overlaps an active rollout on the same
environment + (node | site | artifact lineage).  Reservations are keyed by
rollout id, are idempotent for the same scope, and are rebuilt from the
durable store on controller restart (``rebuild``), so a restart cannot open a
window in which two rollouts touch the same node.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Iterable

from .errors import Conflict, ValidationFailed


@dataclass(frozen=True)
class Scope:
    environment: str
    nodes: frozenset[str]
    sites: frozenset[str] = frozenset()
    artifact_lineage: str | None = None  # e.g. "edge-agent" — one rollout per lineage per env

    @classmethod
    def of(cls, environment: str, nodes: Iterable[str], sites: Iterable[str] = (),
           artifact_lineage: str | None = None) -> "Scope":
        if not environment:
            raise ValidationFailed("scope requires an environment")
        return cls(environment, frozenset(nodes), frozenset(sites), artifact_lineage)

    def overlaps(self, other: "Scope") -> list[str]:
        if self.environment != other.environment:
            return []
        reasons = []
        if self.nodes & other.nodes:
            reasons.append(f"nodes {sorted(self.nodes & other.nodes)[:5]}")
        if self.sites & other.sites:
            reasons.append(f"sites {sorted(self.sites & other.sites)[:5]}")
        if self.artifact_lineage and self.artifact_lineage == other.artifact_lineage:
            reasons.append(f"artifact lineage {self.artifact_lineage}")
        return reasons


@dataclass
class ConflictDetector:
    _active: dict[str, Scope] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def reserve(self, rollout_id: str, scope: Scope) -> None:
        with self._lock:
            existing = self._active.get(rollout_id)
            if existing is not None:
                if existing != scope:
                    raise Conflict(f"{rollout_id} already reserved with a different scope", resource=rollout_id)
                return
            for other_id, other in self._active.items():
                reasons = scope.overlaps(other)
                if reasons:
                    raise Conflict(f"rollout {rollout_id} overlaps active rollout {other_id}: {'; '.join(reasons)}",
                                   resource=rollout_id, blocking_rollout=other_id)
            self._active[rollout_id] = scope

    def release(self, rollout_id: str) -> None:
        with self._lock:
            self._active.pop(rollout_id, None)

    def active(self) -> dict[str, Scope]:
        with self._lock:
            return dict(self._active)

    def rebuild(self, scopes: dict[str, Scope]) -> None:
        with self._lock:
            self._active = {}
        for rid, sc in sorted(scopes.items()):
            self.reserve(rid, sc)
