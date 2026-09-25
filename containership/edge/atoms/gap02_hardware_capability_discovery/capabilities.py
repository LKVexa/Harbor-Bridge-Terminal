"""Core capability-state model for GAP-02.

This module intentionally has no dependency on ``pk_core`` so the probing model can
be tested and reused in bootstrap environments before the wider control-plane
package is on ``PYTHONPATH``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from collections.abc import Callable, Iterable
from typing import Any, Final

PRESENT: Final = "present"
ABSENT: Final = "absent"
UNPROBED: Final = "unprobed"
VALID_STATES: Final = frozenset({PRESENT, ABSENT, UNPROBED})

#: How many seconds old the oldest probe may be before consumers must refuse the report.
FRESHNESS_BOUND_SECONDS: Final = 60
# Backward-compatible alias used by the v4.1.0 integration code.
FRESHNESS_BOUND: Final = FRESHNESS_BOUND_SECONDS

_CAPABILITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/+@-]{0,127}$")


class ProbeUnavailable(RuntimeError):
    """Raised when a probe cannot run in this environment."""


class ReportStale(RuntimeError):
    """Raised when a consumer is handed a report older than its freshness bound."""


class ReportInvalid(ValueError):
    """Raised when a capability report violates its structural invariants."""


def _validate_name(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value or not _CAPABILITY_RE.fullmatch(value):
        raise ValueError(
            f"{field_name} must match {_CAPABILITY_RE.pattern!r}; got {value!r}"
        )
    return value


def _validate_tick(value: int, field_name: str = "timestamp") -> int:
    # bool is an int subclass and must not be accepted as a clock value.
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer; got {value!r}")
    return value


@dataclass
class CapabilityReport:
    """A node's probed capabilities.

    ``results`` intentionally keeps the v1 wire-compatible shape
    ``capability -> (state, probed_at)``. Runtime diagnostics are kept separately
    and are never promoted into the signed report unless a future schema version
    explicitly defines them.
    """

    node: str
    results: dict[str, tuple[str, int]] = field(default_factory=dict)
    published_at: int = 0
    diagnostics: dict[str, str] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        _validate_name(self.node, "node")
        _validate_tick(self.published_at, "published_at")

    def record(
        self,
        capability: str,
        state: str,
        now: int,
        *,
        diagnostic: str | None = None,
    ) -> None:
        _validate_name(capability, "capability")
        _validate_tick(now, "probed_at")
        if state not in VALID_STATES:
            raise ValueError(f"unknown probe state: {state!r}")
        self.results[capability] = (state, now)
        self.published_at = max(self.published_at, now)
        if diagnostic:
            # Bound diagnostics to prevent accidental huge exception strings from
            # becoming an unbounded local-memory/logging vector.
            self.diagnostics[capability] = str(diagnostic)[:512]
        else:
            self.diagnostics.pop(capability, None)

    def state(self, capability: str) -> str:
        _validate_name(capability, "capability")
        record = self.results.get(capability)
        if record is None:
            return UNPROBED
        try:
            return record[0]
        except (IndexError, TypeError):
            return UNPROBED

    def present(self) -> set[str]:
        """Return only capabilities whose successful probe is still recorded."""
        return {
            capability
            for capability, record in self.results.items()
            if isinstance(record, tuple) and len(record) == 2 and record[0] == PRESENT
        }

    def age(self, now: int) -> int:
        """Return age of the oldest probe so a fresh re-probe cannot launder stale entries."""
        _validate_tick(now, "now")
        if not self.results:
            return now - self.published_at
        timestamps: list[int] = []
        for record in self.results.values():
            if not isinstance(record, tuple) or len(record) != 2:
                raise ReportInvalid("malformed capability record")
            timestamps.append(_validate_tick(record[1], "probed_at"))
        return now - min(timestamps)

    def consistency_defects(self, now: int | None = None) -> list[str]:
        """Return structural defects without trusting mutable caller-supplied state."""
        if now is not None:
            _validate_tick(now, "now")
        defects: list[str] = []
        if not self.results:
            defects.append("report contains no probe results")
            return defects

        max_timestamp = -1
        for capability in sorted(self.results, key=str):
            try:
                _validate_name(capability, "capability")
            except ValueError as exc:
                defects.append(str(exc))
                continue
            record = self.results[capability]
            if not isinstance(record, tuple) or len(record) != 2:
                defects.append(f"{capability}: malformed record {record!r}")
                continue
            state, probed_at = record
            if state not in VALID_STATES:
                defects.append(f"{capability}: unknown state {state!r}")
            try:
                tick = _validate_tick(probed_at, "probed_at")
            except ValueError as exc:
                defects.append(f"{capability}: {exc}")
                continue
            max_timestamp = max(max_timestamp, tick)
            if now is not None and tick > now:
                defects.append(f"{capability}: probe timestamp {tick} is in the future of now={now}")

        if max_timestamp >= 0 and self.published_at != max_timestamp:
            defects.append(
                f"published_at={self.published_at} does not equal newest probe timestamp={max_timestamp}"
            )
        return defects

    def for_consumer(self, now: int, *, freshness_bound: int = FRESHNESS_BOUND) -> dict[str, Any]:
        """Return the v1 consumer view, failing closed on malformed or stale data."""
        _validate_tick(now, "now")
        _validate_tick(freshness_bound, "freshness_bound")
        defects = self.consistency_defects(now)
        if defects:
            raise ReportInvalid(f"{self.node}: report failed its consistency check: {defects}")
        age = self.age(now)
        if age < 0:
            raise ReportInvalid(f"{self.node}: report age became negative ({age})")
        if age > freshness_bound:
            raise ReportStale(f"{self.node}: report is {age} seconds old")
        return {
            "schema": "PK_NODE_CAPABILITIES/1",
            "node": self.node,
            "present": sorted(self.present()),
            "absent": sorted(c for c, (s, _) in self.results.items() if s == ABSENT),
            "unprobed": sorted(c for c, (s, _) in self.results.items() if s == UNPROBED),
            "published_at": self.published_at,
            "age": age,
        }

    def canonical_bytes(self, now: int, *, freshness_bound: int = FRESHNESS_BOUND) -> bytes:
        """Serialize stable report facts deterministically for signing or hashing.

        ``age`` is intentionally excluded because it is a consumer-time derived
        value; signing it would make a reconstructed report change every tick.
        Freshness is still validated before canonicalization.
        """
        view = self.for_consumer(now, freshness_bound=freshness_bound)
        signed_view = {key: value for key, value in view.items() if key != "age"}
        return json.dumps(
            signed_view,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")


def probe(
    report: CapabilityReport,
    capability: str,
    prober: Callable[[], bool],
    now: int,
) -> str:
    """Run one fail-closed, three-valued probe.

    Only the literal booleans ``True`` and ``False`` become ``present`` and
    ``absent``. Any unavailable, crashing, or ambiguous probe becomes
    ``unprobed`` and overwrites any older state, preventing sticky capabilities.
    """
    if not callable(prober):
        raise TypeError("prober must be callable")
    _validate_name(capability, "capability")
    _validate_tick(now, "now")
    diagnostic: str | None = None
    try:
        result = prober()
    except ProbeUnavailable as exc:
        result = None
        diagnostic = f"ProbeUnavailable: {exc}"
    except Exception as exc:  # fail closed; never let a crashing probe preserve PRESENT
        result = None
        diagnostic = f"{type(exc).__name__}: {exc}"

    state = (PRESENT if result else ABSENT) if isinstance(result, bool) else UNPROBED
    if not isinstance(result, bool) and diagnostic is None:
        diagnostic = f"ambiguous probe result type: {type(result).__name__}"
    report.record(capability, state, now, diagnostic=diagnostic)
    return state


@dataclass(frozen=True)
class ProbeSchedule:
    """Bounded re-probe policy for a declared set of capabilities."""

    capabilities: tuple[str, ...]
    interval: int = FRESHNESS_BOUND

    def __post_init__(self) -> None:
        _validate_tick(self.interval, "interval")
        if self.interval == 0:
            raise ValueError("interval must be greater than zero")
        if not self.capabilities:
            raise ValueError("at least one capability must be declared")
        if len(set(self.capabilities)) != len(self.capabilities):
            raise ValueError("capabilities must be unique")
        for capability in self.capabilities:
            _validate_name(capability, "capability")

    @classmethod
    def from_iterable(cls, capabilities: Iterable[str], interval: int = FRESHNESS_BOUND) -> "ProbeSchedule":
        return cls(tuple(capabilities), interval)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "PK_PROBE_SCHEDULE/1",
            "capabilities": list(self.capabilities),
            "interval_seconds": self.interval,
        }

    def due(
        self,
        report: CapabilityReport,
        now: int,
        *,
        hot_added: Iterable[str] = (),
    ) -> list[str]:
        """Return declared capabilities that must be probed now.

        A capability is due when never probed, when its own record reaches the
        configured interval, or when a hot-add event explicitly names it.
        """
        _validate_tick(now, "now")
        hot = set(hot_added)
        unknown_hot = hot.difference(self.capabilities)
        if unknown_hot:
            raise ValueError(f"hot-added capabilities are not declared: {sorted(unknown_hot)!r}")

        due: list[str] = []
        for capability in self.capabilities:
            record = report.results.get(capability)
            if capability in hot or record is None:
                due.append(capability)
                continue
            if not isinstance(record, tuple) or len(record) != 2:
                due.append(capability)
                continue
            probed_at = record[1]
            try:
                _validate_tick(probed_at, "probed_at")
            except ValueError:
                due.append(capability)
                continue
            if probed_at > now or now - probed_at >= self.interval:
                due.append(capability)
        return due
