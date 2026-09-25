"""Idempotent command transport (component 14) and a GAP-01 reference supervisor double.

Command envelope ``PK_NODE_COMMAND/1``:

* ``command_id`` — deterministic from (rollout, op, node, target, attempt group),
  so every retry of the same logical operation carries the same id;
* ``fence`` — controller fencing token; the node rejects any token lower than the
  highest it has seen (stale controller cannot act);
* ``nonce`` — single-use, issued by the device registry, echoed in the ack;
* ``deadline`` — absolute; the node refuses expired commands.

Delivery is at-least-once; the node deduplicates by ``command_id`` and returns
the stored ack for duplicates, so replays never re-execute.  Unknown outcomes
(timeouts) are never translated into success — the executor reports
``unknown`` and reconciliation resolves them.

``SimNodeSupervisor``/``SimChannel`` are the reference test double for the
GAP-01 contract and the fault-injection harness (drop request, drop ack,
offline, duplicate, stale fence, node-side failure).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Mapping

from .common import Clock, KeyRing, SystemClock, digest_of, sign_envelope
from .errors import Timeout, ValidationFailed
from .identity import ACK_SCHEMA

COMMAND_SCHEMA = "PK_NODE_COMMAND/1"
OPS = frozenset({"drain", "stage", "install", "activate", "rollback", "quarantine", "query"})


def make_command(*, rollout_id: str, node: str, op: str, fence: int, target_version: str | None,
                 digest: str | None, nonce: str, issued_at: float, deadline: float, attempt_group: int | str = 0
                 ) -> dict[str, Any]:
    if op not in OPS:
        raise ValidationFailed(f"unknown op {op}")
    idem = f"{rollout_id}:{op}:{node}:{target_version}:{attempt_group}"
    return {"schema": COMMAND_SCHEMA, "command_id": "cmd_" + digest_of({"k": idem})[:32], "idempotency_key": idem,
            "rollout_id": rollout_id, "node": node, "op": op, "fence": fence, "target_version": target_version,
            "digest": digest, "nonce": nonce, "issued_at": issued_at, "deadline": deadline}


@dataclass
class SimNodeSupervisor:
    node_id: str
    keyring: KeyRing
    key_id: str
    measurements: dict[str, str]
    version: str
    digest: str | None = None
    clock: Clock = field(default_factory=SystemClock)
    fail_ops: set[str] = field(default_factory=set)       # ops that fail on this node
    installer: Any = None                                   # optional ABInstaller
    payloads: dict[str, bytes] = field(default_factory=dict)  # digest -> bytes (content source)
    previous: tuple[str, str | None] | None = None
    executions: int = 0
    _seen: dict[str, tuple[str, str | None]] = field(default_factory=dict)
    _high_fence: dict[str, int] = field(default_factory=dict)
    _closed: set[str] = field(default_factory=set)   # rollouts this node has rolled back (tombstones)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _ack(self, cmd: Mapping[str, Any], status: str, reason: str | None = None) -> dict[str, Any]:
        body = {"schema": ACK_SCHEMA, "command_id": cmd["command_id"], "rollout_id": cmd["rollout_id"],
                "fence": cmd["fence"], "node": self.node_id, "nonce": cmd["nonce"], "op": cmd["op"],
                "status": status, "reason": reason, "observed_version": self.version,
                "observed_digest": self.digest,
                "attestation": {"measurements": dict(self.measurements), "at": self.clock.now()}}
        return sign_envelope(self.keyring, self.key_id, body)

    def handle(self, cmd: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            if cmd.get("schema") != COMMAND_SCHEMA or cmd.get("node") != self.node_id:
                return self._ack(cmd, "rejected", "misaddressed")
            if cmd["command_id"] in self._seen:
                # dedup: never re-execute; re-attest the stored result for this delivery's nonce/fence
                status, reason = self._seen[cmd["command_id"]]
                return self._ack(cmd, status, reason)
            hf = self._high_fence.get(cmd["rollout_id"], 0)
            if cmd["fence"] < hf:
                return self._ack(cmd, "rejected", "stale_fence")
            self._high_fence[cmd["rollout_id"]] = cmd["fence"]
            if self.clock.now() > cmd["deadline"]:
                return self._ack(cmd, "rejected", "expired")
            op = cmd["op"]
            if op == "install" and cmd["rollout_id"] in self._closed:
                # GAP-01 contract: a rollback tombstones the rollout on the node, so a delayed/reordered
                # install from the same rollout can never re-apply the bad bundle after rollback.
                ack = self._ack(cmd, "rejected", "rollout_rolled_back")
                self._seen[cmd["command_id"]] = ("rejected", "rollout_rolled_back")
                return ack
            if op == "query":
                ack = self._ack(cmd, "ok")
            elif op in self.fail_ops:
                ack = self._ack(cmd, "failed", f"{op} failed on node")
            else:
                self.executions += 1
                if op == "install":
                    self._install(cmd)
                elif op == "rollback":
                    self._rollback(cmd)
                    self._closed.add(cmd["rollout_id"])
                ack = self._ack(cmd, "ok")
            self._seen[cmd["command_id"]] = (ack["body"]["status"], ack["body"]["reason"])
            return ack

    def _install(self, cmd: Mapping[str, Any]) -> None:
        if self.installer is not None:
            data = self.payloads[cmd["digest"]]
            self.installer.stage(data, cmd["digest"])
            self.installer.activate(cmd["digest"])
            self.installer.boot()
            self.installer.confirm()
        self.previous = (self.version, self.digest)
        self.version, self.digest = cmd["target_version"], cmd["digest"]

    def _rollback(self, cmd: Mapping[str, Any]) -> None:
        if self.version == cmd["target_version"]:
            return  # already there: idempotent
        if self.installer is not None:
            self.installer.rollback()
            self.installer.boot()
        if self.previous is not None:
            self.version, self.digest = self.previous
        else:
            self.version = cmd["target_version"]


@dataclass
class SimChannel:
    """Fault-injectable transport between controller and supervisors."""
    nodes: dict[str, SimNodeSupervisor]
    offline: set[str] = field(default_factory=set)
    drop_request: dict[str, int] = field(default_factory=dict)  # node -> remaining drops
    drop_ack: dict[str, int] = field(default_factory=dict)
    duplicate: bool = False
    sent: int = 0

    def send(self, cmd: Mapping[str, Any]) -> dict[str, Any]:
        self.sent += 1
        node = cmd["node"]
        if node in self.offline or node not in self.nodes:
            raise Timeout(f"{node} unreachable", resource=node)
        if self.drop_request.get(node, 0) > 0:
            self.drop_request[node] -= 1
            raise Timeout(f"request to {node} lost", resource=node)
        ack = self.nodes[node].handle(cmd)
        if self.duplicate:
            ack = self.nodes[node].handle(cmd)  # at-least-once duplicate delivery
        if self.drop_ack.get(node, 0) > 0:
            self.drop_ack[node] -= 1
            raise Timeout(f"ack from {node} lost", resource=node)
        return ack
