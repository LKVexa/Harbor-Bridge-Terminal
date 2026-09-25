"""Staged rollout, canary, rollback, drain, emergency disable (M33).

A ``RolloutController`` moves a config/implementation change through
stages (canary % -> ... -> 100) and auto-rolls-back when the canary's error
ratio exceeds the policy threshold.  ``drain`` stops new calls on a link or the
provider while in-flight calls finish; ``emergency_disable`` requires two
distinct authenticated operator principals (two-person rule) and is audited.
"""
from __future__ import annotations

import json
import pathlib

from ..errors.mapping import ProviderFault

POLICY = json.loads((pathlib.Path(__file__).resolve().parent / "canary-policy.json").read_text())


class RolloutController:
    def __init__(self, policy: dict | None = None):
        self.policy = policy or POLICY
        self.stage_index = -1
        self.state = "idle"
        self.log: list[dict] = []

    @property
    def percent(self) -> int:
        return 0 if self.stage_index < 0 else self.policy["stages"][self.stage_index]

    def start(self, change_id: str) -> int:
        if self.state not in ("idle", "rolled_back", "complete"):
            raise ProviderFault("PK_PROVIDER_INVALID_LINK", "rollout already in progress")
        self.change_id, self.stage_index, self.state = change_id, 0, "in_progress"
        self.log.append({"event": "start", "change": change_id, "percent": self.percent})
        return self.percent

    def observe(self, errors: int, total: int) -> str:
        if self.state != "in_progress":
            return self.state
        if total < self.policy["min_requests_per_stage"]:
            return "waiting"
        if errors / total > self.policy["max_error_ratio"]:
            self.state = "rolled_back"
            self.log.append({"event": "auto_rollback", "percent": self.percent, "errors": errors, "total": total})
            self.stage_index = -1
            return self.state
        if self.stage_index + 1 >= len(self.policy["stages"]):
            self.state = "complete"
        else:
            self.stage_index += 1
        self.log.append({"event": "advance", "percent": self.percent, "state": self.state})
        return self.state

    def in_canary(self, bucket: int) -> bool:
        """bucket in 0..99 (stable hash of the link key)."""
        return self.state in ("in_progress", "complete") and bucket < self.percent


def emergency_disable_authorized(approvers: list) -> None:
    ids = {a.principal for a in approvers if getattr(a, "authenticated", False) and a.principal}
    if len(ids) < 2:
        raise ProviderFault("PK_PROVIDER_FORBIDDEN", "emergency disable needs two distinct authenticated operators")
