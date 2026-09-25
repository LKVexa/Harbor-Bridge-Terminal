"""Thread-safe reference model for INV-05 current control state.

This module intentionally has no :mod:`pk_core` dependency so the core
compare-and-swap, watch, and compaction semantics can be tested in isolation.
It is a conformance/reference model, not a persistent or distributed store.
"""
from __future__ import annotations

from collections.abc import Mapping
from threading import RLock
from typing import Any


class Compacted(LookupError):
    """Raised when a watch requests history that has already been compacted."""


class InvalidStateRequest(ValueError):
    """Raised when a caller supplies an invalid key, revision, or transaction."""


class ControlState:
    """Small, thread-safe model of a revisioned control-state store.

    Revisions are monotonically increasing integers.  Each successful write
    operation receives a distinct global revision.  A transaction's compare
    phase and all of its write operations execute while holding one re-entrant
    lock, so two callers cannot both win the same compare-and-swap race.

    The returned ``data`` and ``history`` properties are snapshots.  Mutating
    those containers does not mutate the store itself.
    """

    def __init__(self) -> None:
        self._revision = 0
        self._data: dict[str, tuple[Any, int]] = {}
        self._history: list[tuple[int, str, Any]] = []
        self._compacted_at = 0
        self._lock = RLock()

    @staticmethod
    def _validate_key(key: object) -> str:
        if not isinstance(key, str) or not key:
            raise InvalidStateRequest(f"state key must be a non-empty string, got {key!r}")
        if "\x00" in key:
            raise InvalidStateRequest("state key must not contain NUL")
        return key

    @staticmethod
    def _validate_revision(revision: object, *, field: str) -> int:
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
            raise InvalidStateRequest(f"{field} must be a non-negative int, got {revision!r}")
        return revision

    @property
    def revision(self) -> int:
        with self._lock:
            return self._revision

    @property
    def compacted_at(self) -> int:
        with self._lock:
            return self._compacted_at

    @property
    def data(self) -> dict[str, tuple[Any, int]]:
        """Return a point-in-time copy of key/value/revision state."""
        with self._lock:
            return dict(self._data)

    @property
    def history(self) -> list[tuple[int, str, Any]]:
        """Return a point-in-time copy of retained history."""
        with self._lock:
            return list(self._history)

    def get(self, key: str) -> tuple[Any, int] | None:
        """Return ``(value, mod_revision)`` for *key*, or ``None`` if absent."""
        key = self._validate_key(key)
        with self._lock:
            return self._data.get(key)

    def txn(self, compare: Mapping[str, int], ops: Mapping[str, Any]) -> bool:
        """Atomically compare revisions and, when they match, apply writes.

        ``compare`` maps keys to expected modification revisions.  An expected
        revision of ``0`` means that the key must not exist.  ``ops`` maps keys
        to replacement values.  Invalid input raises :class:`InvalidStateRequest`;
        a valid compare mismatch returns ``False`` and performs no writes.
        """
        if not isinstance(compare, Mapping):
            raise InvalidStateRequest("compare must be a mapping of key -> expected revision")
        if not isinstance(ops, Mapping):
            raise InvalidStateRequest("ops must be a mapping of key -> value")

        checked_compare: list[tuple[str, int]] = []
        for key, expected in compare.items():
            checked_compare.append(
                (self._validate_key(key), self._validate_revision(expected, field=f"compare[{key!r}]") )
            )
        checked_ops: list[tuple[str, Any]] = [(self._validate_key(key), value) for key, value in ops.items()]

        with self._lock:
            for key, expected in checked_compare:
                if self._data.get(key, (None, 0))[1] != expected:
                    return False

            # Comparison and mutation share the same lock: the transaction is
            # atomic with respect to every other operation on this model.
            for key, value in checked_ops:
                self._revision += 1
                self._data[key] = (value, self._revision)
                self._history.append((self._revision, key, value))
            return True

    def watch(self, from_rev: int) -> list[tuple[int, str, Any]]:
        """Return retained changes whose revision is at least ``from_rev``.

        A request at or before the compaction point raises :class:`Compacted`
        after history has actually been compacted, preventing silent gaps.
        """
        from_rev = self._validate_revision(from_rev, field="watch revision")
        with self._lock:
            if self._compacted_at and from_rev <= self._compacted_at:
                raise Compacted(
                    f"revision {from_rev} compacted (history starts after {self._compacted_at}); relist"
                )
            return [event for event in self._history if event[0] >= from_rev]

    def compact(self, rev: int) -> int:
        """Discard retained events through ``rev`` and return the drop count."""
        rev = self._validate_revision(rev, field="compaction revision")
        with self._lock:
            if rev > self._revision:
                raise InvalidStateRequest(
                    f"cannot compact to {rev!r}: current revision is {self._revision}"
                )
            before = len(self._history)
            self._history = [event for event in self._history if event[0] > rev]
            self._compacted_at = max(self._compacted_at, rev)
            return before - len(self._history)
