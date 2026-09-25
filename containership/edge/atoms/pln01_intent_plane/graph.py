"""Hardened in-memory intent graph and dry-run planner for PLN-01.

This module deliberately depends only on the Python standard library so the
core graph can be unit-tested even when the surrounding ``pk_core`` monorepo is
not installed. It plans desired state; it never executes reconciliation steps.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from functools import wraps
from hashlib import sha256
import heapq
import json
from threading import RLock
from typing import Any, TypeAlias

from .metadata import SCHEMA_PLAN

NodeKey: TypeAlias = tuple[str, str, str]
AdmissionPolicy: TypeAlias = Callable[[NodeKey, Mapping[str, Any], tuple[NodeKey, ...], str], tuple[bool, str]]


class IntentError(RuntimeError):
    """Base class for intent-graph domain failures."""


class ValidationError(IntentError, ValueError):
    """Raised when untrusted declaration or report input is malformed."""


class CycleError(IntentError, ValueError):
    """Raised when the declared graph cannot be totally ordered."""


class VersionConflictError(IntentError):
    """Raised when optimistic concurrency detects a stale writer."""


class DependencyInUseError(IntentError):
    """Raised when a node with dependents is retracted without cascade."""


class AdmissionRejectedError(IntentError, PermissionError):
    """Raised when admission policy rejects a declaration."""


class ReplayError(IntentError):
    """Raised when a mutation request identifier is replayed."""


class HistoryUnavailableError(IntentError):
    """Raised when a requested graph version has aged out of retained history."""


@dataclass(frozen=True)
class AuditEvent:
    """Hash-chained, security-sensitive in-memory audit event."""

    sequence: int
    graph_version: int
    actor: str
    operation: str
    target: tuple[NodeKey, ...]
    outcome: str
    reason: str
    previous_hash: str
    event_hash: str


@dataclass(frozen=True)
class _Delta:
    """One committed graph transition, sufficient to reconstruct recent state."""

    from_version: int
    to_version: int
    before_nodes: dict[NodeKey, dict[str, Any] | None]
    before_edges: dict[NodeKey, frozenset[NodeKey] | None]
    after_nodes: dict[NodeKey, dict[str, Any] | None]
    after_edges: dict[NodeKey, frozenset[NodeKey] | None]


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"value must be finite JSON-compatible data: {exc}") from exc


def _normalise_key(value: Sequence[str] | NodeKey, *, label: str = "node") -> NodeKey:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) != 3:
        raise ValidationError(f"{label} must be a 3-item (tenant, environment, name) sequence")
    tenant, environment, name = value
    if not all(isinstance(part, str) and part.strip() and part == part.strip() for part in (tenant, environment, name)):
        raise ValidationError(f"{label} tenant, environment and name must be non-empty trimmed strings")
    return tenant, environment, name


def _synchronized(method):
    """Serialize access to one graph instance with a re-entrant lock."""
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return wrapped


def _topological_order(
    nodes: Mapping[NodeKey, Mapping[str, Any]],
    edges: Mapping[NodeKey, frozenset[NodeKey]],
) -> list[NodeKey]:
    indegree = {key: len(edges.get(key, frozenset())) for key in nodes}
    dependents: dict[NodeKey, list[NodeKey]] = {key: [] for key in nodes}
    for node, deps in edges.items():
        for dep in deps:
            if dep in dependents:
                dependents[dep].append(node)
    ready = [key for key, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)
    out: list[NodeKey] = []
    while ready:
        key = heapq.heappop(ready)
        out.append(key)
        for node in dependents[key]:
            indegree[node] -= 1
            if indegree[node] == 0:
                heapq.heappush(ready, node)
    if len(out) != len(nodes):
        cyclic = sorted(key for key, degree in indegree.items() if degree > 0)
        raise CycleError(f"dependency cycle among {cyclic}")
    return out


class IntentGraph:
    """Authoritative desired-state graph with bounded history and replay guards.

    Nodes are addressed by ``(tenant, environment, name)``. Edges mean
    "reconcile this node after those dependencies". Mutations support optimistic
    concurrency, a bounded replay window, bounded delta history, rollback, and a
    bounded hash-chained audit trail.

    The model is intentionally process-local. Durable replicated storage,
    authentication, external authorization, and cryptographic artifact
    verification require integrations that are not present in this repository.
    """

    def __init__(
        self,
        *,
        max_nodes: int = 10_000,
        max_dependencies_per_node: int = 256,
        max_spec_bytes: int = 1_048_576,
        max_history: int = 64,
        replay_window: int = 4096,
        max_audit_events: int = 8192,
        admission_policy: AdmissionPolicy | None = None,
        on_commit: Callable[[int, dict, dict], None] | None = None,
    ) -> None:
        limits = {
            "max_nodes": max_nodes,
            "max_dependencies_per_node": max_dependencies_per_node,
            "max_spec_bytes": max_spec_bytes,
            "max_history": max_history,
            "replay_window": replay_window,
            "max_audit_events": max_audit_events,
        }
        if not all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in limits.values()):
            raise ValueError("all graph limits must be positive integers")
        self.max_nodes = max_nodes
        self.max_dependencies_per_node = max_dependencies_per_node
        self.max_spec_bytes = max_spec_bytes
        self.max_history = max_history
        self.replay_window = replay_window
        self.max_audit_events = max_audit_events
        self._admission_policy = admission_policy
        self._on_commit = on_commit
        self._tenant_counts: dict[str, int] = {}
        self._lock = RLock()
        self._nodes: dict[NodeKey, dict[str, Any]] = {}
        self._edges: dict[NodeKey, frozenset[NodeKey]] = {}
        self.version = 0
        self._history: deque[_Delta] = deque()
        self._request_ids: set[str] = set()
        self._request_order: deque[str] = deque()
        self._audit: deque[AuditEvent] = deque()
        self._audit_anchor_hash = "0" * 64
        self._audit_sequence = 0

    def __len__(self) -> int:
        return len(self._nodes)

    @property
    def audit_events(self) -> tuple[AuditEvent, ...]:
        """Return retained audit events in append order."""
        with self._lock:
            return tuple(self._audit)

    @property
    def oldest_retained_version(self) -> int:
        """Oldest version reconstructable from the bounded delta journal."""
        with self._lock:
            return self.version - len(self._history)

    def _check_actor(self, actor: str) -> str:
        if not isinstance(actor, str) or not actor.strip() or actor != actor.strip():
            raise ValidationError("actor must be a non-empty trimmed string")
        if len(actor) > 256:
            raise ValidationError("actor exceeds 256 characters")
        return actor

    def _check_expected_version(self, expected_version: int | None) -> None:
        if expected_version is None:
            return
        if not isinstance(expected_version, int) or isinstance(expected_version, bool) or expected_version < 0:
            raise ValidationError("expected_version must be a non-negative integer")
        if expected_version != self.version:
            raise VersionConflictError(f"stale graph version {expected_version}; current version is {self.version}")

    def _reserve_request_id(self, request_id: str | None) -> None:
        if request_id is None:
            return
        if not isinstance(request_id, str) or not request_id.strip() or request_id != request_id.strip():
            raise ValidationError("request_id must be a non-empty trimmed string")
        if len(request_id) > 256:
            raise ValidationError("request_id exceeds 256 characters")
        if request_id in self._request_ids:
            raise ReplayError(f"replayed mutation request_id: {request_id}")
        self._request_ids.add(request_id)
        self._request_order.append(request_id)
        while len(self._request_order) > self.replay_window:
            old = self._request_order.popleft()
            self._request_ids.discard(old)

    def _record_audit(
        self,
        *,
        actor: str,
        operation: str,
        targets: Sequence[NodeKey],
        outcome: str,
        reason: str,
    ) -> None:
        previous_hash = self._audit[-1].event_hash if self._audit else self._audit_anchor_hash
        self._audit_sequence += 1
        body = {
            "sequence": self._audit_sequence,
            "graph_version": self.version,
            "actor": actor,
            "operation": operation,
            "target": [list(t) for t in targets],
            "outcome": outcome,
            "reason": reason,
            "previous_hash": previous_hash,
        }
        event_hash = sha256(_canonical_json(body).encode("utf-8")).hexdigest()
        event = AuditEvent(
            sequence=self._audit_sequence,
            graph_version=self.version,
            actor=actor,
            operation=operation,
            target=tuple(targets),
            outcome=outcome,
            reason=reason,
            previous_hash=previous_hash,
            event_hash=event_hash,
        )
        self._audit.append(event)
        while len(self._audit) > self.max_audit_events:
            evicted = self._audit.popleft()
            self._audit_anchor_hash = evicted.event_hash

    @_synchronized
    def verify_audit_chain(self) -> bool:
        """Return whether the retained in-memory audit chain verifies."""
        previous_hash = self._audit_anchor_hash
        for event in self._audit:
            if event.previous_hash != previous_hash:
                return False
            body = {
                "sequence": event.sequence,
                "graph_version": event.graph_version,
                "actor": event.actor,
                "operation": event.operation,
                "target": [list(t) for t in event.target],
                "outcome": event.outcome,
                "reason": event.reason,
                "previous_hash": event.previous_hash,
            }
            expected = sha256(_canonical_json(body).encode("utf-8")).hexdigest()
            if expected != event.event_hash:
                return False
            previous_hash = event.event_hash
        return True

    def _prepare_spec(self, spec: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(spec, Mapping):
            raise ValidationError("spec must be a mapping")
        materialised = deepcopy(dict(spec))
        encoded = _canonical_json(materialised).encode("utf-8")
        if len(encoded) > self.max_spec_bytes:
            raise ValidationError(f"spec exceeds max_spec_bytes={self.max_spec_bytes}")
        return materialised

    def _commit(
        self,
        before_nodes: dict[NodeKey, dict[str, Any] | None],
        before_edges: dict[NodeKey, frozenset[NodeKey] | None],
    ) -> None:
        old_version = self.version
        self.version += 1
        changed = set(before_nodes) | set(before_edges)
        after_nodes = {key: self._nodes.get(key) for key in changed}
        after_edges = {key: self._edges.get(key) for key in changed}
        self._history.append(
            _Delta(
                from_version=old_version,
                to_version=self.version,
                before_nodes=dict(before_nodes),
                before_edges=dict(before_edges),
                after_nodes=after_nodes,
                after_edges=after_edges,
            )
        )
        while len(self._history) > self.max_history:
            self._history.popleft()
        self._count_delta(before_nodes, after_nodes, +1)
        if self._on_commit is not None:
            # Write-ahead hook (durable store). A failure here must abort the
            # mutation, so the caller's exception handler restores prior state.
            try:
                self._on_commit(self.version, deepcopy(after_nodes), dict(after_edges))
            except BaseException:
                self._count_delta(before_nodes, after_nodes, -1)
                self._history.pop()
                self.version = old_version
                self._apply_values(self._nodes, before_nodes)
                self._apply_values(self._edges, before_edges)
                raise

    def _count_delta(self, before: Mapping, after: Mapping, sign: int) -> None:
        for key in set(before) | set(after):
            change = (after.get(key) is not None) - (before.get(key) is not None)
            if change:
                self._tenant_counts[key[0]] = self._tenant_counts.get(key[0], 0) + sign * change

    def tenant_node_count(self, tenant: str) -> int:
        """O(1) count of desired nodes owned by ``tenant`` (quota accounting)."""
        with self._lock:
            return self._tenant_counts.get(tenant, 0)

    def contains(self, key: Sequence[str] | NodeKey) -> bool:
        with self._lock:
            return _normalise_key(key) in self._nodes

    def _restore_state(self, version: int, nodes: dict, edges: dict) -> None:
        """Install recovered durable state (used only by :mod:`store`)."""
        with self._lock:
            self._nodes = {k: deepcopy(v) for k, v in nodes.items()}
            self._edges = {k: frozenset(v) for k, v in edges.items()}
            self.version = version
            self._history.clear()
            self._tenant_counts = {}
            for key in self._nodes:
                self._tenant_counts[key[0]] = self._tenant_counts.get(key[0], 0) + 1

    @staticmethod
    def _apply_values(target: dict, values: Mapping[NodeKey, Any | None]) -> None:
        for key, value in values.items():
            if value is None:
                target.pop(key, None)
            else:
                target[key] = value

    def _state_at(self, target_version: int) -> tuple[dict[NodeKey, dict[str, Any]], dict[NodeKey, frozenset[NodeKey]]]:
        if not isinstance(target_version, int) or isinstance(target_version, bool) or target_version < 0:
            raise ValidationError("version must be a non-negative integer")
        if target_version > self.version or target_version < self.oldest_retained_version:
            raise HistoryUnavailableError(
                f"graph version {target_version} is not retained; available range is "
                f"{self.oldest_retained_version}..{self.version}"
            )
        nodes = dict(self._nodes)
        edges = dict(self._edges)
        for delta in reversed(self._history):
            if delta.to_version <= target_version:
                break
            self._apply_values(nodes, delta.before_nodes)
            self._apply_values(edges, delta.before_edges)
        return nodes, edges

    @_synchronized
    def declare(
        self,
        tenant: str,
        environment: str,
        name: str,
        spec: Mapping[str, Any],
        after: Sequence[Sequence[str] | NodeKey] = (),
        *,
        expected_version: int | None = None,
        request_id: str | None = None,
        actor: str = "local",
    ) -> NodeKey:
        """Admit and apply one declaration atomically.

        Dependencies must already exist in the same tenant *and* environment.
        Supplying ``expected_version`` provides optimistic concurrency. A
        repeated ``request_id`` is refused within the configured replay window.
        """
        actor = self._check_actor(actor)
        key = _normalise_key((tenant, environment, name))
        self._check_expected_version(expected_version)
        self._reserve_request_id(request_id)
        old_node = self._nodes.get(key)
        old_edges = self._edges.get(key)
        try:
            prepared = self._prepare_spec(spec)
            if isinstance(after, (str, bytes)) or not isinstance(after, Sequence):
                raise ValidationError("after must be a sequence of node keys")
            deps = tuple(_normalise_key(dep, label="dependency") for dep in after)
            if len(deps) > self.max_dependencies_per_node:
                raise ValidationError(f"dependency count exceeds max_dependencies_per_node={self.max_dependencies_per_node}")
            if len(set(deps)) != len(deps):
                raise ValidationError("duplicate dependencies are not allowed")
            for dep in deps:
                if dep[0] != tenant:
                    raise AdmissionRejectedError(f"cross-tenant edge refused: {key} -> {dep}")
                if dep[1] != environment:
                    raise AdmissionRejectedError(f"cross-environment edge refused: {key} -> {dep}")
                if dep == key:
                    raise CycleError(f"{key} may not depend on itself")
                if dep not in self._nodes:
                    raise ValidationError(f"unknown dependency {dep} for {key}")
            if key not in self._nodes and len(self._nodes) >= self.max_nodes:
                raise AdmissionRejectedError(f"graph node capacity {self.max_nodes} reached")
            if self._admission_policy is not None:
                allowed, reason = self._admission_policy(key, deepcopy(prepared), deps, actor)
                if not isinstance(allowed, bool) or not isinstance(reason, str):
                    raise ValidationError("admission_policy must return (bool, str)")
                if not allowed:
                    raise AdmissionRejectedError(reason or "admission policy rejected declaration")

            new_edges = frozenset(deps)
            if old_node == prepared and old_edges == new_edges:
                self._record_audit(
                    actor=actor,
                    operation="declare",
                    targets=(key,),
                    outcome="admitted_noop",
                    reason="declaration already matches intent",
                )
                return key

            if old_node is not None and self._would_create_cycle(key, new_edges):
                raise CycleError(f"dependency update would create a cycle at {key}")
            self._nodes[key] = prepared
            self._edges[key] = new_edges
            self._commit({key: old_node}, {key: old_edges})
            self._record_audit(
                actor=actor,
                operation="declare",
                targets=(key,),
                outcome="admitted",
                reason="validated and committed",
            )
            return key
        except Exception as exc:
            self._apply_values(self._nodes, {key: old_node})
            self._apply_values(self._edges, {key: old_edges})
            self._record_audit(
                actor=actor,
                operation="declare",
                targets=(key,),
                outcome="rejected",
                reason=f"{type(exc).__name__}: {exc}",
            )
            raise

    @_synchronized
    def retract(
        self,
        key: Sequence[str] | NodeKey,
        *,
        cascade: bool = False,
        expected_version: int | None = None,
        request_id: str | None = None,
        actor: str = "local",
    ) -> tuple[NodeKey, ...]:
        """Retract a node, refusing to orphan dependents unless ``cascade`` is true."""
        actor = self._check_actor(actor)
        norm = _normalise_key(key)
        self._check_expected_version(expected_version)
        self._reserve_request_id(request_id)
        try:
            if norm not in self._nodes:
                self._record_audit(
                    actor=actor,
                    operation="retract",
                    targets=(norm,),
                    outcome="admitted_noop",
                    reason="node not present",
                )
                return ()
            reverse: dict[NodeKey, set[NodeKey]] = {node: set() for node in self._nodes}
            for node, deps in self._edges.items():
                for dep in deps:
                    if dep in reverse:
                        reverse[dep].add(node)
            removal = {norm}
            frontier = [norm]
            while frontier:
                current = frontier.pop()
                direct = reverse.get(current, set()) - removal
                if direct and not cascade:
                    raise DependencyInUseError(f"cannot retract {norm}; dependents exist: {sorted(direct)}")
                removal.update(direct)
                frontier.extend(direct)
            ordered = tuple(sorted(removal))
            before_nodes = {item: self._nodes.get(item) for item in removal}
            before_edges = {item: self._edges.get(item) for item in removal}
            for item in removal:
                self._nodes.pop(item, None)
                self._edges.pop(item, None)
            self._commit(before_nodes, before_edges)
            self._record_audit(
                actor=actor,
                operation="retract",
                targets=ordered,
                outcome="admitted",
                reason="cascade" if cascade else "retracted",
            )
            return ordered
        except Exception as exc:
            self._record_audit(
                actor=actor,
                operation="retract",
                targets=(norm,),
                outcome="rejected",
                reason=f"{type(exc).__name__}: {exc}",
            )
            raise

    def _would_create_cycle(self, key: NodeKey, new_dependencies: frozenset[NodeKey]) -> bool:
        """Return whether assigning ``new_dependencies`` to ``key`` closes a cycle."""
        stack = list(new_dependencies)
        seen: set[NodeKey] = set()
        while stack:
            current = stack.pop()
            if current == key:
                return True
            if current in seen:
                continue
            seen.add(current)
            stack.extend(self._edges.get(current, frozenset()))
        return False

    @_synchronized
    def order(self) -> list[NodeKey]:
        """Return deterministic topological order, or raise :class:`CycleError`."""
        return _topological_order(self._nodes, self._edges)

    @_synchronized
    def _planning_state(self) -> tuple[int, dict[NodeKey, dict[str, Any]], dict[NodeKey, frozenset[NodeKey]]]:
        """Capture one immutable-by-convention planning view under the graph lock."""
        return self.version, dict(self._nodes), dict(self._edges)

    @_synchronized
    def node_spec(self, key: Sequence[str] | NodeKey) -> dict[str, Any]:
        """Return a defensive copy of one desired-state spec."""
        norm = _normalise_key(key)
        if norm not in self._nodes:
            raise KeyError(norm)
        return deepcopy(self._nodes[norm])

    @staticmethod
    def _project(version: int, nodes: Mapping[NodeKey, Mapping[str, Any]], edges: Mapping[NodeKey, frozenset[NodeKey]]) -> dict[str, Any]:
        return {
            "version": version,
            "nodes": [
                {
                    "node": list(key),
                    "spec": deepcopy(nodes[key]),
                    "after": [list(dep) for dep in sorted(edges.get(key, frozenset()))],
                }
                for key in sorted(nodes)
            ],
        }

    @_synchronized
    def snapshot(self, version: int | None = None) -> dict[str, Any]:
        """Return a defensive, serializable graph projection for a retained version."""
        target = self.version if version is None else version
        nodes, edges = self._state_at(target)
        return self._project(target, nodes, edges)

    @_synchronized
    def diff(self, from_version: int, to_version: int | None = None) -> dict[str, Any]:
        """Return a deterministic change summary between retained versions."""
        target = self.version if to_version is None else to_version
        a_nodes, a_edges = self._state_at(from_version)
        b_nodes, b_edges = self._state_at(target)
        keys = set(a_nodes) | set(b_nodes)
        added = sorted(k for k in keys if k not in a_nodes)
        removed = sorted(k for k in keys if k not in b_nodes)
        changed = sorted(k for k in keys if k in a_nodes and k in b_nodes and a_nodes[k] != b_nodes[k])
        dependencies_changed = sorted(
            k
            for k in keys
            if k in a_nodes and k in b_nodes and a_edges.get(k, frozenset()) != b_edges.get(k, frozenset())
        )
        return {
            "from_version": from_version,
            "to_version": target,
            "added": [list(k) for k in added],
            "removed": [list(k) for k in removed],
            "changed": [list(k) for k in changed],
            "dependencies_changed": [list(k) for k in dependencies_changed],
        }

    @_synchronized
    def rollback(
        self,
        target_version: int,
        *,
        expected_version: int | None = None,
        request_id: str | None = None,
        actor: str = "local",
    ) -> int:
        """Restore a retained snapshot as a new monotonically increasing version."""
        actor = self._check_actor(actor)
        self._check_expected_version(expected_version)
        self._reserve_request_id(request_id)
        try:
            target_nodes, target_edges = self._state_at(target_version)
            changed = {
                key
                for key in set(self._nodes) | set(target_nodes)
                if self._nodes.get(key) != target_nodes.get(key) or self._edges.get(key) != target_edges.get(key)
            }
            if not changed:
                self._record_audit(
                    actor=actor,
                    operation="rollback",
                    targets=(),
                    outcome="admitted_noop",
                    reason=f"current state already matches version {target_version}",
                )
                return self.version
            before_nodes = {key: self._nodes.get(key) for key in changed}
            before_edges = {key: self._edges.get(key) for key in changed}
            self._nodes = dict(target_nodes)
            self._edges = dict(target_edges)
            self._commit(before_nodes, before_edges)
            self._record_audit(
                actor=actor,
                operation="rollback",
                targets=tuple(sorted(changed)),
                outcome="admitted",
                reason=f"restored version {target_version} as new version {self.version}",
            )
            return self.version
        except Exception as exc:
            self._record_audit(
                actor=actor,
                operation="rollback",
                targets=(),
                outcome="rejected",
                reason=f"{type(exc).__name__}: {exc}",
            )
            raise

    @_synchronized
    def drift(self, actual: Mapping[Sequence[str] | NodeKey, Mapping[str, Any]]) -> list[NodeKey]:
        """Return desired nodes missing or divergent in reported actual state."""
        if not isinstance(actual, Mapping):
            raise ValidationError("actual state must be a mapping")
        normalised: dict[NodeKey, Mapping[str, Any]] = {}
        for key, spec in actual.items():
            norm = _normalise_key(key, label="actual-state node")
            if not isinstance(spec, Mapping):
                raise ValidationError(f"actual state for {norm} must be a mapping")
            normalised[norm] = spec
        return [key for key, spec in sorted(self._nodes.items()) if normalised.get(key) != spec]


def plan(graph: IntentGraph, actual: Mapping[Sequence[str] | NodeKey, Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Produce a deterministic dry-run reconciliation plan for ``graph``."""
    if not isinstance(graph, IntentGraph):
        raise TypeError("graph must be an IntentGraph")
    actual = {} if actual is None else actual
    if not isinstance(actual, Mapping):
        raise ValidationError("actual state must be a mapping")
    normalised_actual: dict[NodeKey, Mapping[str, Any]] = {}
    for key, spec in actual.items():
        norm = _normalise_key(key, label="actual-state node")
        if not isinstance(spec, Mapping):
            raise ValidationError(f"actual state for {norm} must be a mapping")
        normalised_actual[norm] = spec

    graph_version, desired_nodes, desired_edges = graph._planning_state()
    order = _topological_order(desired_nodes, desired_edges)
    steps = []
    for n, key in enumerate(order, 1):
        desired = desired_nodes[key]
        action = "create" if key not in normalised_actual else ("update" if normalised_actual[key] != desired else "noop")
        steps.append({"step": n, "node": list(key), "action": action})
    drifted = [key for key, spec in sorted(desired_nodes.items()) if normalised_actual.get(key) != spec]
    rollback_target = max(graph_version - 1, graph_version - min(graph_version, graph.max_history))
    plan_body = {
        "schema": SCHEMA_PLAN,
        "graph_version": graph_version,
        "dry_run": True,
        "rollback_target": rollback_target,
        "steps": steps,
        "drift": [list(k) for k in drifted],
    }
    plan_body["plan_id"] = sha256(_canonical_json(plan_body).encode("utf-8")).hexdigest()
    return plan_body
