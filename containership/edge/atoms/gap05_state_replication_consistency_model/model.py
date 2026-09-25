"""Core in-memory causal replication model for GAP-05.

This module intentionally has no ``pk_core`` dependency so the state-machine logic can
be unit tested in isolation.  It models a causal frontier with a bounded active
conflict set and a deterministic quarantine for overflow writes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Iterable


class UnknownReplica(KeyError):
    """Raised when a version vector references a site that is not a declared replica."""


class InvalidWrite(ValueError):
    """Raised when a write does not conform to the replicated-write schema."""


class VectorEquivocationError(InvalidWrite):
    """Raised when one causal vector is reused for different write content."""


def _non_empty_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise InvalidWrite(f"{field_name} must be a non-empty string")
    return value


@dataclass(frozen=True, slots=True)
class Write:
    """One write, stamped with the causal context its author had seen.

    ``vector`` is normalized into a canonical site-sorted tuple during construction.
    A site's own counter must be present and every counter must be a positive integer.
    Replica-membership validation is performed by :meth:`ReplicatedKey.apply` because
    the write itself does not own the replica set.
    """

    key: str
    value: str
    site: str
    vector: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        _non_empty_text(self.key, "key")
        _non_empty_text(self.site, "site")
        if not isinstance(self.value, str):
            raise InvalidWrite("value must be a string")
        if isinstance(self.vector, (str, bytes)):
            raise InvalidWrite("vector must be an iterable of (site, counter) pairs")
        try:
            raw_entries = tuple(self.vector)
        except TypeError as exc:  # pragma: no cover - defensive branch
            raise InvalidWrite("vector must be iterable") from exc
        if not raw_entries:
            raise InvalidWrite("vector must contain at least the author's counter")

        normalized: list[tuple[str, int]] = []
        seen: set[str] = set()
        for entry in raw_entries:
            if not isinstance(entry, (tuple, list)) or len(entry) != 2:
                raise InvalidWrite(f"vector entry must be a two-item pair: {entry!r}")
            vector_site, counter = entry
            _non_empty_text(vector_site, "vector site")
            if vector_site in seen:
                raise InvalidWrite(f"vector names site {vector_site!r} more than once")
            if isinstance(counter, bool) or not isinstance(counter, int) or counter <= 0:
                raise InvalidWrite(
                    f"vector counter for {vector_site!r} must be a positive integer"
                )
            seen.add(vector_site)
            normalized.append((vector_site, counter))

        if self.site not in seen:
            raise InvalidWrite(f"author {self.site!r} did not stamp its own counter")
        object.__setattr__(self, "vector", tuple(sorted(normalized)))

    def vector_map(self) -> dict[str, int]:
        return dict(self.vector)

    def identity(self) -> tuple[object, ...]:
        """Stable identity used for deterministic ordering and duplicate checks."""
        return (self.vector, self.site, self.value, self.key)


def dominates(a: dict[str, int], b: dict[str, int]) -> bool:
    """Return whether vector ``a`` causally succeeds vector ``b``."""
    sites = set(a) | set(b)
    ge = all(a.get(site, 0) >= b.get(site, 0) for site in sites)
    gt = any(a.get(site, 0) > b.get(site, 0) for site in sites)
    return ge and gt


def concurrent(a: dict[str, int], b: dict[str, int]) -> bool:
    """Return whether vectors are distinct and neither causally dominates the other."""
    return a != b and not dominates(a, b) and not dominates(b, a)


def _write_sort_key(write: Write) -> tuple[object, ...]:
    # Vector-first ordering makes the bounded active frontier independent of delivery
    # order.  site/value/key are deterministic tie-breakers; equal-vector conflicting
    # content is rejected before ordering as equivocation.
    return write.identity()


@dataclass
class ReplicatedKey:
    """One replicated key with a causally maximal unresolved frontier.

    At most ``max_siblings`` writes are exposed as active ``siblings``.  Additional
    mutually concurrent frontier members are preserved in ``quarantine``.  The active
    subset is selected deterministically from the *entire* unresolved frontier, so
    identical write sets converge to the same active/quarantined partition regardless
    of delivery order.

    The object is thread-safe for calls through its methods.  Its public list fields are
    retained for backwards compatibility; callers should treat them as read-only.
    """

    key: str
    replicas: frozenset[str]
    siblings: list[Write] = field(default_factory=list)
    discarded: list[dict[str, object]] = field(default_factory=list)
    max_siblings: int = 8
    quarantine: list[dict[str, object]] = field(default_factory=list)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not self.key:
            raise ValueError("key must be a non-empty string")
        if isinstance(self.replicas, (str, bytes)):
            raise ValueError("replicas must be an iterable of site names, not a string")
        try:
            replicas = frozenset(self.replicas)
        except TypeError as exc:
            raise ValueError("replicas must be an iterable of site names") from exc
        if not replicas:
            raise ValueError("replicas must not be empty")
        if any(not isinstance(site, str) or not site for site in replicas):
            raise ValueError("every replica name must be a non-empty string")
        if isinstance(self.max_siblings, bool) or not isinstance(self.max_siblings, int) or self.max_siblings <= 0:
            raise ValueError("max_siblings must be a positive integer")
        self.replicas = replicas
        # Normalize caller-provided initial state through one invariant check.
        self._validate_existing_state()
        self._rebalance_frontier(self._all_unresolved())

    def _validate_membership(self, write: Write) -> None:
        if write.key != self.key:
            raise InvalidWrite(f"{self.key}: write addressed to key {write.key!r}")
        unknown = set(write.vector_map()) - set(self.replicas)
        if unknown or write.site not in self.replicas:
            offenders = sorted(unknown) if unknown else [write.site]
            raise UnknownReplica(f"{self.key}: write references non-replica {offenders!r}")

    def _validate_existing_state(self) -> None:
        for write in self.siblings:
            if not isinstance(write, Write):
                raise ValueError("siblings must contain Write instances")
            self._validate_membership(write)
        for entry in self.quarantine:
            if not isinstance(entry, dict) or not isinstance(entry.get("write"), Write):
                raise ValueError("quarantine entries must be mappings containing a Write")
            self._validate_membership(entry["write"])
        for entry in self.discarded:
            if not isinstance(entry, dict) or not isinstance(entry.get("write"), Write):
                raise ValueError("discarded entries must be mappings containing a Write")

        unresolved = self._all_unresolved()
        seen_vectors: dict[tuple[tuple[str, int], ...], Write] = {}
        for write in unresolved:
            previous = seen_vectors.get(write.vector)
            if previous is not None:
                if previous == write:
                    raise ValueError("initial unresolved state contains the same write more than once")
                raise VectorEquivocationError(
                    f"{self.key}: initial unresolved state reuses vector {write.vector!r}"
                )
            seen_vectors[write.vector] = write
        for index, write in enumerate(unresolved):
            for other in unresolved[index + 1 :]:
                if dominates(write.vector_map(), other.vector_map()) or dominates(
                    other.vector_map(), write.vector_map()
                ):
                    raise ValueError(
                        "initial unresolved state contains causally dominated writes; "
                        "restore only the causal frontier"
                    )

    def _all_unresolved(self) -> list[Write]:
        return list(self.siblings) + [entry["write"] for entry in self.quarantine]

    @staticmethod
    def _find_same_vector(writes: Iterable[Write], incoming: Write) -> Write | None:
        for existing in writes:
            if existing.vector == incoming.vector:
                return existing
        return None

    def _rebalance_frontier(self, frontier: Iterable[Write]) -> None:
        ordered = sorted(frontier, key=_write_sort_key)
        active = ordered[: self.max_siblings]
        overflow = ordered[self.max_siblings :]
        self.siblings = active
        self.quarantine = [
            {
                "write": write,
                "reason": (
                    f"conflict frontier exceeds max_siblings={self.max_siblings}; "
                    f"deterministic overflow rank={index}"
                ),
            }
            for index, write in enumerate(overflow, start=self.max_siblings + 1)
        ]

    def apply(self, write: Write) -> str:
        """Apply a write atomically.

        Returns one of ``converged``, ``conflict``, ``duplicate``, ``superseded`` or
        ``quarantined``.  A write is never silently lost: causal supersession and replay
        are recorded in ``discarded``; overflow writes remain live in ``quarantine``.
        """
        if not isinstance(write, Write):
            raise TypeError("apply() requires a Write instance")
        with self._lock:
            self._validate_membership(write)
            unresolved = self._all_unresolved()

            same_vector = self._find_same_vector(unresolved, write)
            if same_vector is not None:
                if same_vector == write:
                    location = "active frontier" if same_vector in self.siblings else "quarantine"
                    self.discarded.append(
                        {"write": write, "reason": f"duplicate replay: already present in {location}"}
                    )
                    return "duplicate"
                raise VectorEquivocationError(
                    f"{self.key}: vector {write.vector!r} already identifies different write content"
                )

            incoming = write.vector_map()
            dominators = [existing for existing in unresolved if dominates(existing.vector_map(), incoming)]
            if dominators:
                causal_winner = min(dominators, key=_write_sort_key)
                self.discarded.append(
                    {
                        "write": write,
                        "reason": f"superseded by causally newer write from {causal_winner.site}",
                    }
                )
                return "superseded"

            surviving: list[Write] = []
            for existing in unresolved:
                if dominates(incoming, existing.vector_map()):
                    self.discarded.append(
                        {"write": existing, "reason": f"superseded by {write.site}"}
                    )
                else:
                    surviving.append(existing)
            surviving.append(write)

            self._rebalance_frontier(surviving)
            if any(entry["write"] == write for entry in self.quarantine):
                return "quarantined"
            return "conflict" if not self.converged else "converged"

    @property
    def converged(self) -> bool:
        with self._lock:
            return len(self.siblings) + len(self.quarantine) <= 1

    def value(self) -> str | None:
        with self._lock:
            if not self.converged:
                total = len(self.siblings) + len(self.quarantine)
                raise ValueError(f"{self.key}: {total} concurrent writes await resolution")
            return self.siblings[0].value if self.siblings else None

    def conflict_set(self) -> dict[str, object]:
        with self._lock:
            return {
                "schema": "PK_CONFLICT_SET/1",
                "key": self.key,
                "siblings": [
                    {"site": write.site, "value": write.value, "vector": list(write.vector)}
                    for write in self.siblings
                ],
                "quarantined": [
                    {
                        "site": entry["write"].site,
                        "value": entry["write"].value,
                        "vector": list(entry["write"].vector),
                        "reason": entry["reason"],
                    }
                    for entry in self.quarantine
                ],
                "open": not self.converged,
                "total_unresolved": len(self.siblings) + len(self.quarantine),
            }

    def resolve(self, value: str, site: str) -> Write:
        """Resolve the whole unresolved frontier with one causally dominating write.

        Quarantined overflow writes participate in the merged vector and are cleared only
        after being recorded as resolved, preventing an old quarantined write from
        reappearing as concurrent after resolution.
        """
        if not isinstance(value, str):
            raise InvalidWrite("resolved value must be a string")
        if not isinstance(site, str) or not site:
            raise InvalidWrite("resolver site must be a non-empty string")
        if site not in self.replicas:
            raise UnknownReplica(f"{self.key}: resolver {site!r} is not a declared replica")
        with self._lock:
            unresolved = self._all_unresolved()
            merged: dict[str, int] = {}
            for pending in unresolved:
                for vector_site, counter in pending.vector:
                    merged[vector_site] = max(merged.get(vector_site, 0), counter)
            merged[site] = merged.get(site, 0) + 1
            winner = Write(self.key, value, site, tuple(merged.items()))
            for pending in unresolved:
                self.discarded.append({"write": pending, "reason": f"resolved by {site}"})
            self.siblings = [winner]
            self.quarantine = []
            return winner
