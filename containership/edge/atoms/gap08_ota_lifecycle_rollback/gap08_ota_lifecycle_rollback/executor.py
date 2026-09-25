"""Real rollback/install executor feedback loop (component 8).

Replaces the v4.2.0 test-only ``fail_nodes`` input with per-node supervisor
acknowledgements.  For every node the executor:

1. issues a nonce and builds a fenced, idempotent command;
2. sends it with bounded, jittered retries (same ``command_id`` each time);
3. verifies the signed ack against device identity/attestation (``identity``);
4. classifies the outcome as ``ok`` / ``failed`` (terminal, with reason) /
   ``unknown`` (no authenticated answer before the deadline).

``unknown`` is never success: for installs it becomes a deferred node pending
reconciliation; for rollbacks it is reported as a rollback failure and the node
is quarantined.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Iterable, Protocol

from .admission import AdmissionController
from .common import Clock, SystemClock
from .errors import Gap08Error, IdentityRejected, Timeout
from .identity import DeviceRegistry
from .retry import BackoffPolicy, CircuitBreaker, retry_call
from .transport import make_command


class Channel(Protocol):
    def send(self, cmd: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class Outcome:
    node: str
    status: str             # ok | failed | unknown
    reason: str | None
    command_id: str
    observed_version: str | None = None
    ack_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class CommandExecutor:
    channel: Channel
    registry: DeviceRegistry
    clock: Clock = field(default_factory=SystemClock)
    backoff: BackoffPolicy = field(default_factory=lambda: BackoffPolicy(0.2, 5.0, 4, 30.0))
    breaker: CircuitBreaker | None = None
    admission: AdmissionController | None = None
    command_ttl_s: float = 300.0
    rng: random.Random = field(default_factory=lambda: random.Random(8))
    site_of: dict[str, str] = field(default_factory=dict)

    def run(self, *, rollout_id: str, fence: int, op: str, nodes: Iterable[str], target_version: str | None,
            digest: str | None, attempt_group: int | str = 0) -> dict[str, Outcome]:
        nodes = list(nodes)
        recovery = op in ("rollback", "quarantine", "query")
        if self.admission is not None:
            self.admission.acquire_commands(len(nodes), recovery=recovery)
        try:
            return {n: self._one(rollout_id, fence, op, n, target_version, digest, attempt_group) for n in nodes}
        finally:
            if self.admission is not None:
                self.admission.release_commands(len(nodes), recovery=recovery)

    def _one(self, rollout_id, fence, op, node, target_version, digest, attempt_group) -> Outcome:
        try:
            nonce = self.registry.issue_nonce(node)
        except IdentityRejected as exc:
            return Outcome(node, "failed", f"identity: {exc.detail}", "")
        now = self.clock.now()
        cmd = make_command(rollout_id=rollout_id, node=node, op=op, fence=fence, target_version=target_version,
                           digest=digest, nonce=nonce, issued_at=now, deadline=now + self.command_ttl_s,
                           attempt_group=attempt_group)
        try:
            ack = retry_call(lambda: self.channel.send(cmd), idempotent=True, policy=self.backoff, clock=self.clock,
                             rng=self.rng, breaker=self.breaker, cohort=self.site_of.get(node, node))
        except Timeout as exc:
            return Outcome(node, "unknown", f"no authenticated ack: {exc.detail}", cmd["command_id"])
        except Gap08Error as exc:
            return Outcome(node, "unknown", f"{exc.code}: {exc.detail}", cmd["command_id"])
        try:
            body = self.registry.verify_ack(ack, command=cmd)
        except IdentityRejected as exc:
            return Outcome(node, "unknown", f"unauthenticated ack rejected: {exc.detail}", cmd["command_id"])
        status = body.get("status")
        if status == "ok":
            if op in ("install", "rollback") and body.get("observed_version") != target_version:
                return Outcome(node, "failed", "ack ok but observed version differs", cmd["command_id"],
                               body.get("observed_version"), body["ack_ref"])
            return Outcome(node, "ok", None, cmd["command_id"], body.get("observed_version"), body["ack_ref"])
        return Outcome(node, "failed", f"{status}: {body.get('reason')}", cmd["command_id"],
                       body.get("observed_version"), body["ack_ref"])
