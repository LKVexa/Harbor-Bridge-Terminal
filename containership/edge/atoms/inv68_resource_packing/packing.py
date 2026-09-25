"""Pure resource-packing engine for INV-68.

This module intentionally has no :mod:`pk_core` dependency.  It can therefore be
unit-tested, embedded, and fuzzed independently of the control-plane integration.
The compatibility wrapper :func:`pack` retains the original ``(hosts, unplaced)``
return shape while :func:`pack_detailed` exposes machine-readable decisions.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
import math
from numbers import Real
from types import MappingProxyType
from typing import Any, Final, Literal

DIMENSIONS: Final[tuple[str, str]] = ("cpu", "mem")
OVERCOMMIT = MappingProxyType({"cpu": 1.5, "mem": 1.0})
_EPSILON: Final[float] = 1e-9
MAX_CPU_OVERCOMMIT: Final[float] = 4.0


def _safe_repr(value: Any) -> str:
    try:
        return repr(value)
    except Exception:
        return f"<{type(value).__name__}>"


def _finite_real(value: Any, label: str, *, positive: bool = False, nonnegative: bool = False) -> float:
    """Return *value* as a finite float or raise a precise validation error."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{label} must be a real number, got {type(value).__name__}")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{label} cannot be represented as a finite float: {_safe_repr(value)}") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite, got {_safe_repr(value)}")
    if positive and number <= 0:
        raise ValueError(f"{label} must be > 0, got {_safe_repr(value)}")
    if nonnegative and number < 0:
        raise ValueError(f"{label} must be >= 0, got {_safe_repr(value)}")
    return number


def _validate_headroom(headroom: Any) -> float:
    value = _finite_real(headroom, "headroom")
    if not 0 <= value < 1:
        raise ValueError(f"headroom must be in [0, 1), got {headroom!r}")
    return value


def _validate_cpu_overcommit(value: Any) -> float:
    """CPU overcommit is configurable in [1, MAX_CPU_OVERCOMMIT]; memory never is."""
    if value is None:
        return OVERCOMMIT["cpu"]
    ratio = _finite_real(value, "cpu_overcommit")
    if not 1.0 <= ratio <= MAX_CPU_OVERCOMMIT:
        raise ValueError(f"cpu_overcommit must be in [1, {MAX_CPU_OVERCOMMIT}], got {value!r}")
    return ratio


def _validate_dimension(dim: str) -> str:
    if dim not in DIMENSIONS:
        raise ValueError(f"unsupported resource dimension {dim!r}; expected one of {DIMENSIONS!r}")
    return dim


def _validate_host_capacity(host_cpu: Any, host_mem: Any) -> tuple[float, float]:
    return (
        _finite_real(host_cpu, "host_cpu", positive=True),
        _finite_real(host_mem, "host_mem", positive=True),
    )


def _normalize_workload(workload: Any, index: int | None = None) -> dict[str, Any]:
    where = f"workloads[{index}]" if index is not None else "workload"
    if not isinstance(workload, Mapping):
        raise TypeError(f"{where} must be a mapping, got {type(workload).__name__}")

    missing = [key for key in ("name", "cpu", "mem") if key not in workload]
    if missing:
        raise ValueError(f"{where} missing required field(s): {', '.join(missing)}")

    name = workload["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"{where}.name must be a non-empty string")

    return {
        "name": name,
        "cpu": _finite_real(workload["cpu"], f"{where}.cpu", nonnegative=True),
        "mem": _finite_real(workload["mem"], f"{where}.mem", nonnegative=True),
    }


def _normalize_workloads(workloads: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(workloads, (str, bytes)):
        raise TypeError("workloads must be an iterable of mappings, not text")
    try:
        source = list(workloads)
    except TypeError as exc:
        raise TypeError("workloads must be an iterable of mappings") from exc

    normalized: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for index, workload in enumerate(source):
        item = _normalize_workload(workload, index)
        if item["name"] in seen_names:
            raise ValueError(f"duplicate workload name {item['name']!r}; workload identities must be unique")
        seen_names.add(item["name"])
        normalized.append(item)
    return normalized


@dataclass
class Host:
    """Mutable host accounting record with validated capacity and usage."""

    name: str
    cpu: float
    mem: float
    used: dict[str, float] = field(default_factory=lambda: {"cpu": 0.0, "mem": 0.0})

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("host name must be a non-empty string")
        self.cpu, self.mem = _validate_host_capacity(self.cpu, self.mem)
        if not isinstance(self.used, Mapping):
            raise TypeError("host used must be a mapping")
        self.used = {
            dim: _finite_real(self.used.get(dim, 0.0), f"host {self.name!r} used.{dim}", nonnegative=True)
            for dim in DIMENSIONS
        }

    def limit(self, dim: str, headroom: float = 0.1, cpu_overcommit: float | None = None) -> float:
        dim = _validate_dimension(dim)
        reserve = _validate_headroom(headroom)
        ratio = _validate_cpu_overcommit(cpu_overcommit) if dim == "cpu" else OVERCOMMIT["mem"]
        limit = getattr(self, dim) * ratio * (1.0 - reserve)
        if not math.isfinite(limit) or limit <= 0:
            raise ValueError(f"effective {dim} capacity for host {self.name!r} must be finite and > 0")
        return limit

    def remaining(self, dim: str, headroom: float = 0.1) -> float:
        dim = _validate_dimension(dim)
        remaining = self.limit(dim, headroom) - self.used[dim]
        return 0.0 if -_EPSILON <= remaining < 0 else remaining

    def fits(self, workload: Mapping[str, Any], headroom: float = 0.1) -> bool:
        item = _normalize_workload(workload)
        reserve = _validate_headroom(headroom)
        return all(
            self.used[dim] + item[dim] <= self.limit(dim, reserve) + _EPSILON
            for dim in DIMENSIONS
        )

    def place(self, workload: Mapping[str, Any], headroom: float = 0.1) -> None:
        item = _normalize_workload(workload)
        reserve = _validate_headroom(headroom)
        if not self.fits(item, reserve):
            raise ValueError(f"workload {item['name']!r} does not fit host {self.name!r}")
        for dim in DIMENSIONS:
            self.used[dim] += item[dim]


@dataclass(frozen=True)
class PlacementDecision:
    """Explain one deterministic placement decision."""

    workload: str
    status: Literal["placed", "unplaced"]
    host: str | None
    reason: str
    cpu: float
    mem: float


@dataclass(frozen=True)
class PackingResult:
    """Detailed packing result for auditability and operator explain views."""

    hosts: tuple[Host, ...]
    unplaced: tuple[str, ...]
    assignments: Mapping[str, str]
    decisions: tuple[PlacementDecision, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "assignments", MappingProxyType(dict(self.assignments)))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable object matching ``PK_PACK_RESPONSE/1``."""
        return {
            "hosts": [
                {
                    "name": host.name,
                    "cpu": host.cpu,
                    "mem": host.mem,
                    "used": dict(host.used),
                }
                for host in self.hosts
            ],
            "unplaced": list(self.unplaced),
            "assignments": dict(self.assignments),
            "decisions": [
                {
                    "workload": decision.workload,
                    "status": decision.status,
                    "host": decision.host,
                    "reason": decision.reason,
                    "cpu": decision.cpu,
                    "mem": decision.mem,
                }
                for decision in self.decisions
            ],
        }


def effective_capacity(host_cpu: float, host_mem: float, headroom: float = 0.1,
                       cpu_overcommit: float | None = None) -> dict[str, float]:
    """Return effective per-host capacity after overcommit and headroom policy.

    ``cpu_overcommit`` (4.3.0) lets the validated configuration (``config.py``)
    choose the CPU ratio in ``[1, MAX_CPU_OVERCOMMIT]``; memory is always 1.0.
    """
    cpu, mem = _validate_host_capacity(host_cpu, host_mem)
    reserve = _validate_headroom(headroom)
    ratio = _validate_cpu_overcommit(cpu_overcommit)
    effective = {
        "cpu": cpu * ratio * (1.0 - reserve),
        "mem": mem * OVERCOMMIT["mem"] * (1.0 - reserve),
    }
    for dim, value in effective.items():
        if not math.isfinite(value) or value <= 0:
            raise ValueError(
                f"effective {dim} capacity must be finite and > 0 after overcommit/headroom policy"
            )
    return effective


def capacity_report(host_cpu: float, host_mem: float, headroom: float = 0.1,
                    cpu_overcommit: float | None = None) -> dict[str, float]:
    """Return a JSON-serializable object matching ``PK_PACK_CAPACITY/1``."""
    cpu, mem = _validate_host_capacity(host_cpu, host_mem)
    reserve = _validate_headroom(headroom)
    effective = effective_capacity(cpu, mem, reserve, cpu_overcommit)
    return {
        "cpu": cpu,
        "mem": mem,
        "headroom": reserve,
        "effective_cpu": effective["cpu"],
        "effective_mem": effective["mem"],
    }


def pack_detailed(
    workloads: Iterable[Mapping[str, Any]],
    host_cpu: float,
    host_mem: float,
    headroom: float = 0.1,
    cpu_overcommit: float | None = None,
) -> PackingResult:
    """Pack workloads using deterministic multi-dimensional first-fit decreasing.

    The input mappings are copied during validation and are never mutated.  Memory
    overcommit remains fixed at 1.0; CPU uses the policy in :data:`OVERCOMMIT`.
    Workloads that individually exceed effective host capacity are returned as
    unplaced instead of forcing an invalid host state.
    """
    normalized = _normalize_workloads(workloads)
    limits = effective_capacity(host_cpu, host_mem, headroom, cpu_overcommit)
    cpu, mem = _validate_host_capacity(host_cpu, host_mem)

    def dominant_share(item: Mapping[str, Any]) -> float:
        return max(item["cpu"] / limits["cpu"], item["mem"] / limits["mem"])

    order = sorted(normalized, key=lambda item: (-dominant_share(item), item["name"]))
    lim_cpu, lim_mem = limits["cpu"], limits["mem"]
    hosts: list[Host] = []
    unplaced: list[str] = []
    assignments: dict[str, str] = {}
    decisions: list[PlacementDecision] = []

    # 4.3.0 performance fix (INV-68 MC-22): the 4.2.0 loop re-validated every
    # workload for every candidate host (O(n*h) validations) and kept full hosts
    # in the scan forever, giving ~350 ms for 1000 workloads (SLO: p99 < 100 ms)
    # and ~4 s when every workload needs its own host.  Validation now happens
    # once; hosts that cannot fit the smallest *remaining* request in some
    # dimension are closed.  Closing never changes the first-fit choice, because a
    # closed host could not have accepted any later workload (proved by the
    # differential test against the preserved 4.2.0 reference algorithm).
    n = len(order)
    suffix_min_cpu = [math.inf] * (n + 1)
    suffix_min_mem = [math.inf] * (n + 1)
    for i in range(n - 1, -1, -1):
        suffix_min_cpu[i] = min(suffix_min_cpu[i + 1], order[i]["cpu"])
        suffix_min_mem[i] = min(suffix_min_mem[i + 1], order[i]["mem"])
    open_hosts: list[Host] = []

    for index, item in enumerate(order):
        ic, im = item["cpu"], item["mem"]
        if ic > lim_cpu + _EPSILON or im > lim_mem + _EPSILON:
            unplaced.append(item["name"])
            decisions.append(
                PlacementDecision(
                    workload=item["name"],
                    status="unplaced",
                    host=None,
                    reason="request_exceeds_effective_host_capacity",
                    cpu=ic,
                    mem=im,
                )
            )
            continue

        target = None
        for candidate in open_hosts:
            used = candidate.used
            if used["cpu"] + ic <= lim_cpu + _EPSILON and used["mem"] + im <= lim_mem + _EPSILON:
                target = candidate
                break
        reason = "first_existing_host_with_capacity"
        if target is None:
            target = Host(f"h{len(hosts)}", cpu, mem)
            hosts.append(target)
            open_hosts.append(target)
            reason = "opened_new_host"

        target.used["cpu"] += ic
        target.used["mem"] += im
        assignments[item["name"]] = target.name
        decisions.append(
            PlacementDecision(
                workload=item["name"],
                status="placed",
                host=target.name,
                reason=reason,
                cpu=ic,
                mem=im,
            )
        )
        next_cpu, next_mem = suffix_min_cpu[index + 1], suffix_min_mem[index + 1]
        if (target.used["cpu"] + next_cpu > lim_cpu + _EPSILON
                or target.used["mem"] + next_mem > lim_mem + _EPSILON):
            open_hosts.remove(target)

    return PackingResult(tuple(hosts), tuple(unplaced), assignments, tuple(decisions))


def pack(
    workloads: Iterable[Mapping[str, Any]],
    host_cpu: float,
    host_mem: float,
    headroom: float = 0.1,
    cpu_overcommit: float | None = None,
) -> tuple[list[Host], list[str]]:
    """Backward-compatible packing API returning ``(hosts, unplaced)``."""
    result = pack_detailed(workloads, host_cpu, host_mem, headroom, cpu_overcommit)
    return list(result.hosts), list(result.unplaced)


def lower_bound(
    workloads: Iterable[Mapping[str, Any]],
    host_cpu: float,
    host_mem: float,
    headroom: float = 0.1,
    cpu_overcommit: float | None = None,
    placeable_only: bool = False,
) -> int:
    """Return the resource-volume lower bound for the required host count.

    ``placeable_only=True`` (4.3.0) excludes workloads that exceed the effective
    capacity of an empty host.  The default keeps the 4.2.0 semantics, which count
    unplaceable volume and therefore overstate the bound whenever anything is
    unplaced -- efficiency figures (bench, explain, service) use the placeable
    bound so an unplaced whale cannot make packing look better than it is.
    """
    normalized = _normalize_workloads(workloads)
    limits = effective_capacity(host_cpu, host_mem, headroom, cpu_overcommit)
    if placeable_only:
        normalized = [w for w in normalized if all(w[d] <= limits[d] + _EPSILON for d in DIMENSIONS)]
    if not normalized:
        return 0
    totals: dict[str, float] = {}
    for dim in DIMENSIONS:
        try:
            total = math.fsum(item[dim] for item in normalized)
        except OverflowError as exc:
            raise ValueError(f"aggregate workload {dim} request overflowed finite arithmetic") from exc
        if not math.isfinite(total):
            raise ValueError(f"aggregate workload {dim} request must remain finite")
        totals[dim] = total
    ratios = [totals[dim] / limits[dim] for dim in DIMENSIONS]
    if not all(math.isfinite(r) for r in ratios):
        # 4.3.0 fix (fuzz finding): 4.2.0 raised OverflowError from math.ceil here,
        # escaping the documented TypeError/ValueError contract.
        raise ValueError("lower bound is not finitely representable for these requests and capacities")
    return max(math.ceil(r) for r in ratios)


def fragmentation(hosts: Iterable[Host], headroom: float = 0.1,
                  cpu_overcommit: float | None = None) -> dict[str, float]:
    """Return stranded effective capacity and reject impossible host accounting."""
    reserve = _validate_headroom(headroom)
    ratio = _validate_cpu_overcommit(cpu_overcommit)
    try:
        host_list = list(hosts)
    except TypeError as exc:
        raise TypeError("hosts must be an iterable of Host instances") from exc

    totals = {dim: 0.0 for dim in DIMENSIONS}
    for index, host in enumerate(host_list):
        if not isinstance(host, Host):
            raise TypeError(f"hosts[{index}] must be Host, got {type(host).__name__}")
        for dim in DIMENSIONS:
            remaining = host.limit(dim, reserve, ratio) - host.used[dim]
            if remaining < -_EPSILON:
                raise ValueError(
                    f"host {host.name!r} exceeds effective {dim} capacity by {-remaining:.6g}"
                )
            totals[dim] += max(0.0, remaining)
    return {dim: round(total, 3) for dim, total in totals.items()}


__all__ = [
    "DIMENSIONS",
    "MAX_CPU_OVERCOMMIT",
    "OVERCOMMIT",
    "Host",
    "PackingResult",
    "PlacementDecision",
    "capacity_report",
    "effective_capacity",
    "fragmentation",
    "lower_bound",
    "pack",
    "pack_detailed",
]
