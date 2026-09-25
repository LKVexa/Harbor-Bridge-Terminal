"""Persistent deferred-node scheduler (component 13).

The queue lives *inside* the durable rollout state (``state["deferred_queue"]``)
so it survives controller restarts with the same CAS/fencing guarantees as
everything else.  Each entry tracks first-deferral time, attempts, next
eligible time (exponential backoff with deterministic jitter), expiry and the
last reason.  Reconnect detection is by node-query; expired entries are
escalated (quarantine candidate) rather than retried forever.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DeferredPolicy:
    base_s: float = 60.0
    cap_s: float = 3600.0
    max_attempts: int = 10
    expiry_s: float = 7 * 24 * 3600.0


def _jitter(node: str, attempt: int) -> float:
    h = int(hashlib.sha256(f"{node}:{attempt}".encode()).hexdigest()[:8], 16)
    return (h % 1000) / 1000.0  # [0,1)


def enqueue(queue: dict[str, dict[str, Any]], node: str, *, now: float, reason: str,
            policy: DeferredPolicy = DeferredPolicy()) -> None:
    e = queue.get(node)
    if e is None:
        queue[node] = {"node": node, "first_deferred_at": now, "attempts": 0, "next_attempt_at": now + policy.base_s,
                       "expires_at": now + policy.expiry_s, "last_reason": reason, "status": "waiting"}
    else:
        e["last_reason"] = reason


def record_attempt(queue: dict[str, dict[str, Any]], node: str, *, now: float, ok: bool, reason: str | None,
                   policy: DeferredPolicy = DeferredPolicy()) -> None:
    e = queue[node]
    if ok:
        del queue[node]
        return
    e["attempts"] += 1
    e["last_reason"] = reason or "retry failed"
    delay = min(policy.cap_s, policy.base_s * 2 ** e["attempts"]) * (0.5 + _jitter(node, e["attempts"]) / 2)
    e["next_attempt_at"] = now + delay
    if e["attempts"] >= policy.max_attempts or now >= e["expires_at"]:
        e["status"] = "escalated"


def due(queue: dict[str, dict[str, Any]], *, now: float) -> list[str]:
    out = []
    for node, e in sorted(queue.items()):
        if e["status"] == "waiting" and now >= e["expires_at"]:
            e["status"] = "escalated"
        if e["status"] == "waiting" and e["next_attempt_at"] <= now:
            out.append(node)
    return out


def escalated(queue: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(n for n, e in queue.items() if e["status"] == "escalated")


def ages(queue: dict[str, dict[str, Any]], *, now: float) -> dict[str, float]:
    return {n: now - e["first_deferred_at"] for n, e in queue.items()}
