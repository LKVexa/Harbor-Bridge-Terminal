"""Component 37 - canary/staged rollout controller.

Promotes a policy (or code) revision through cohorts keyed by site and
hardware class. Each stage must soak for ``soak_s`` and pass every guard;
any guard breach rolls back automatically and is audited.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

DEFAULT_STAGES = (0.01, 0.05, 0.25, 1.0)


@dataclass
class Guard:
    name: str
    check: Callable[[set], bool]   # returns True when healthy for the cohort


@dataclass
class RolloutController:
    policies: object                # PolicyService
    scope: str
    revision_id: str
    nodes_by_cohort: dict[tuple[str, str], list[str]]   # (site, hw_class) -> nodes
    guards: list[Guard]
    stages: tuple[float, ...] = DEFAULT_STAGES
    soak_s: float = 600.0
    actor: str = "rollout-controller"
    stage_index: int = -1
    stage_started: float = 0.0
    state: str = "pending"          # pending | canary | complete | rolled-back
    history: list[dict] = field(default_factory=list)

    def _cohort(self, fraction: float) -> set[str]:
        """Take ``fraction`` of *every* (site, hw_class) cohort, minimum one node,
        so each hardware class and site is represented in the first canary."""
        chosen = set()
        for key in sorted(self.nodes_by_cohort):
            nodes = sorted(self.nodes_by_cohort[key])
            k = max(1, int(len(nodes) * fraction + 0.999999)) if nodes else 0
            chosen.update(nodes[:k])
        return chosen

    def start(self, now: float) -> None:
        self.stage_index, self.state = 0, "canary"
        self._apply(now)

    def _apply(self, now: float) -> None:
        frac = self.stages[self.stage_index]
        self.stage_started = now
        if frac >= 1.0:
            self.policies.activate(self.scope, self.revision_id, actor=self.actor, now=now)
            self.state = "complete"
        else:
            cohort = self._cohort(frac)
            self.policies.stage(self.scope, self.revision_id, cohort, actor=self.actor, now=now)
        self.history.append({"at": now, "stage": frac, "state": self.state})

    def tick(self, now: float) -> str:
        if self.state != "canary":
            return self.state
        cohort = self._cohort(self.stages[self.stage_index])
        failed = [g.name for g in self.guards if not g.check(cohort)]
        if failed:
            self.policies.staged.pop(self.scope, None)
            self.state = "rolled-back"
            if getattr(self.policies, "audit", None) is not None:
                self.policies.audit.append("rollout.rolled_back", self.actor, now, revision=self.revision_id,
                                           failed=",".join(failed))
            self.history.append({"at": now, "rolled_back": failed})
            return self.state
        if now - self.stage_started >= self.soak_s:
            self.stage_index += 1
            if getattr(self.policies, "audit", None) is not None:
                self.policies.audit.append("rollout.promoted", self.actor, now, revision=self.revision_id,
                                           stage=self.stages[self.stage_index])
            self._apply(now)
        return self.state
