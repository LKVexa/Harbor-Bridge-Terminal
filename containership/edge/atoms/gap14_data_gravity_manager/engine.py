"""Standalone decision engine for GAP-14.

This module intentionally has no dependency on ``pk_core`` so the production
cost/residency logic can be unit-tested and embedded independently of the
conformance framework.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from numbers import Real
from types import MappingProxyType
from typing import Any

SCHEMA_VERSION = "PK_GRAVITY_RECOMMENDATION/1"
EGRESS_PER_GB = 1.0
COMPUTE_MOVE_COST = 25.0
_DIRECTION_ORDER = {"move-compute": 0, "move-data": 1}


class GravityDecisionError(RuntimeError):
    """Base error with a stable machine-readable code and structured details."""

    code = "PK_GRAVITY_ERROR"

    def __init__(self, message: str, *, details: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.details = dict(details or {})

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "details": dict(self.details)}


class NoLegalOption(GravityDecisionError):
    """Raised when policy/capability constraints leave no legal recommendation."""

    code = "PK_GRAVITY_NO_LEGAL_OPTION"


class CostModelError(GravityDecisionError):
    """Raised when a legal option cannot be honestly costed."""

    code = "PK_GRAVITY_COST_MODEL_ERROR"


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _nonnegative_finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{label} must be a finite non-negative real number, got {value!r}")
    try:
        normalized = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{label} must be finite, got {value!r}") from exc
    if not isfinite(normalized) or normalized < 0:
        raise ValueError(f"{label} must be finite and non-negative, got {value!r}")
    return normalized


def _checked_product(*values: float, label: str) -> float:
    result = 1.0
    for value in values:
        result *= value
    if not isfinite(result) or result < 0:
        raise CostModelError(
            f"{label} produced a non-finite or negative total",
            details={"inputs": list(values), "total": result},
        )
    return result


@dataclass(frozen=True, slots=True)
class Dataset:
    """Immutable dataset facts consumed by the gravity decision engine."""

    name: str
    site: str
    size_gb: float
    classification: str
    converged: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _identifier(self.name, "dataset name"))
        object.__setattr__(self, "site", _identifier(self.site, "dataset site"))
        object.__setattr__(self, "classification", _identifier(self.classification, "dataset classification"))
        object.__setattr__(self, "size_gb", _nonnegative_finite(self.size_gb, f"{self.name}: size_gb"))
        if not isinstance(self.converged, bool):
            raise ValueError(f"{self.name}: converged must be bool, got {self.converged!r}")


@dataclass(frozen=True, slots=True)
class GravityManager:
    """Decide whether compute moves to data or data moves to compute.

    Configuration is snapshotted and made immutable at construction time.  A
    cross-site route must have an explicit locality multiplier; silently
    inventing a default route cost can produce a wrong placement decision.
    """

    residency: Mapping[str, frozenset[str] | set[str] | tuple[str, ...] | list[str]] = field(default_factory=dict)
    distance: Mapping[tuple[str, str], float] = field(default_factory=dict)
    compute_sites: frozenset[str] | set[str] | tuple[str, ...] | list[str] = frozenset()
    egress_per_gb: Mapping[tuple[str, str], float] = field(default_factory=dict)
    default_egress_per_gb: float = EGRESS_PER_GB
    compute_relocation_cost: float = COMPUTE_MOVE_COST

    def __post_init__(self) -> None:
        normalized_residency: dict[str, frozenset[str]] = {}
        for raw_site, raw_classes in dict(self.residency).items():
            site = _identifier(raw_site, "residency site")
            if raw_classes is None or isinstance(raw_classes, (str, bytes)):
                raise ValueError(f"residency[{site!r}] must be an iterable of classifications")
            try:
                classes = frozenset(_identifier(c, f"classification at {site}") for c in raw_classes)
            except TypeError as exc:
                raise ValueError(f"residency[{site!r}] must be an iterable of classifications") from exc
            normalized_residency[site] = classes

        normalized_distance: dict[tuple[str, str], float] = {}
        for raw_route, raw_value in dict(self.distance).items():
            route = self._normalize_route(raw_route, "distance")
            normalized_distance[route] = _nonnegative_finite(raw_value, f"distance {route[0]}->{route[1]}")

        normalized_egress: dict[tuple[str, str], float] = {}
        for raw_route, raw_value in dict(self.egress_per_gb).items():
            route = self._normalize_route(raw_route, "egress_per_gb")
            normalized_egress[route] = _nonnegative_finite(raw_value, f"egress {route[0]}->{route[1]}")

        if isinstance(self.compute_sites, (str, bytes)):
            raise ValueError("compute_sites must be an iterable of site identifiers, not a string")
        try:
            normalized_compute_sites = frozenset(_identifier(site, "compute site") for site in self.compute_sites)
        except TypeError as exc:
            raise ValueError("compute_sites must be an iterable of site identifiers") from exc
        default_egress = _nonnegative_finite(self.default_egress_per_gb, "default_egress_per_gb")
        compute_cost = _nonnegative_finite(self.compute_relocation_cost, "compute_relocation_cost")

        object.__setattr__(self, "residency", MappingProxyType(normalized_residency))
        object.__setattr__(self, "distance", MappingProxyType(normalized_distance))
        object.__setattr__(self, "compute_sites", normalized_compute_sites)
        object.__setattr__(self, "egress_per_gb", MappingProxyType(normalized_egress))
        object.__setattr__(self, "default_egress_per_gb", default_egress)
        object.__setattr__(self, "compute_relocation_cost", compute_cost)

    @staticmethod
    def _normalize_route(raw_route: Any, label: str) -> tuple[str, str]:
        if not isinstance(raw_route, tuple) or len(raw_route) != 2:
            raise ValueError(f"{label} route keys must be (from_site, to_site) tuples, got {raw_route!r}")
        return (_identifier(raw_route[0], f"{label} from_site"), _identifier(raw_route[1], f"{label} to_site"))

    def legal(self, site: str, classification: str) -> bool:
        site = _identifier(site, "site")
        classification = _identifier(classification, "classification")
        return classification in self.residency.get(site, frozenset())

    def _multiplier(self, from_site: str, to_site: str) -> float:
        from_site = _identifier(from_site, "from_site")
        to_site = _identifier(to_site, "to_site")
        if from_site == to_site:
            return 0.0
        route = (from_site, to_site)
        if route not in self.distance:
            raise CostModelError(
                f"missing locality multiplier for {from_site}->{to_site}",
                details={"from_site": from_site, "to_site": to_site, "field": "distance"},
            )
        return self.distance[route]

    def _egress_rate(self, from_site: str, to_site: str) -> float:
        return self.egress_per_gb.get((from_site, to_site), self.default_egress_per_gb)

    def move_data_cost_breakdown(self, dataset: Dataset, to_site: str) -> dict[str, Any]:
        to_site = _identifier(to_site, "to_site")
        multiplier = self._multiplier(dataset.site, to_site)
        egress_rate = self._egress_rate(dataset.site, to_site)
        total = _checked_product(dataset.size_gb, egress_rate, multiplier, label="move-data cost")
        return {
            "kind": "move-data",
            "from": dataset.site,
            "to": to_site,
            "size_gb": dataset.size_gb,
            "egress_per_gb": egress_rate,
            "locality_multiplier": multiplier,
            "total": total,
        }

    def move_data_cost(self, dataset: Dataset, to_site: str) -> float:
        return self.move_data_cost_breakdown(dataset, to_site)["total"]

    def move_compute_cost_breakdown(self, from_site: str, to_site: str) -> dict[str, Any]:
        from_site = _identifier(from_site, "from_site")
        to_site = _identifier(to_site, "to_site")
        multiplier = self._multiplier(from_site, to_site)
        total = _checked_product(self.compute_relocation_cost, multiplier, label="move-compute cost")
        return {
            "kind": "move-compute",
            "from": from_site,
            "to": to_site,
            "base_compute_move_cost": self.compute_relocation_cost,
            "locality_multiplier": multiplier,
            "total": total,
        }

    def move_compute_cost(self, from_site: str, to_site: str) -> float:
        return self.move_compute_cost_breakdown(from_site, to_site)["total"]

    def recommend(self, dataset: Dataset, compute_site: str) -> dict[str, Any]:
        """Cost all legal directions, then return the cheapest legal option.

        Residency/capability filtering is performed before cost comparison.
        Missing cost data for an otherwise legal option is an error rather than
        an invented default, because comparing incomplete legal options is not
        an honest cost decision.
        """
        if not isinstance(dataset, Dataset):
            raise TypeError(f"dataset must be Dataset, got {type(dataset).__name__}")
        compute_site = _identifier(compute_site, "compute_site")

        if compute_site == dataset.site:
            if not self.legal(dataset.site, dataset.classification):
                raise NoLegalOption(
                    f"{dataset.name}: current dataset location {dataset.site} violates residency for {dataset.classification}",
                    details={
                        "dataset": dataset.name,
                        "site": dataset.site,
                        "classification": dataset.classification,
                        "reason_code": "CURRENT_RESIDENCY_VIOLATION",
                    },
                )
            breakdown = {"kind": "none", "from": dataset.site, "to": dataset.site, "total": 0.0}
            return {
                "schema": SCHEMA_VERSION,
                "direction": "none",
                "to": dataset.site,
                "cost": 0.0,
                "cost_breakdown": breakdown,
                "reason_code": "ALREADY_COLOCATED",
                "reason": "compute and data are already co-located",
                "options": [],
                "eliminated": [],
                "elimination_details": [],
            }

        options: list[dict[str, Any]] = []
        eliminated: list[str] = []
        elimination_details: list[dict[str, str]] = []

        def eliminate(direction: str, code: str, reason: str) -> None:
            text = f"{direction}: {reason}"
            eliminated.append(text)
            elimination_details.append({"direction": direction, "code": code, "reason": reason})

        # Option A: move the compute to the data's site.
        if not self.legal(dataset.site, dataset.classification):
            eliminate("move-compute", "RESIDENCY_FORBIDDEN", f"{dataset.site} may not hold {dataset.classification}")
        elif dataset.site not in self.compute_sites:
            eliminate("move-compute", "COMPUTE_UNAVAILABLE", f"no compute capacity at {dataset.site}")
        else:
            breakdown = self.move_compute_cost_breakdown(compute_site, dataset.site)
            options.append({
                "direction": "move-compute",
                "to": dataset.site,
                "cost": breakdown["total"],
                "cost_breakdown": breakdown,
            })

        # Option B: move the data to the compute's site.
        if not self.legal(compute_site, dataset.classification):
            eliminate("move-data", "RESIDENCY_FORBIDDEN", f"{compute_site} may not hold {dataset.classification}")
        elif not dataset.converged:
            eliminate("move-data", "DATASET_NOT_CONVERGED", f"{dataset.name} has unresolved replication conflicts")
        else:
            breakdown = self.move_data_cost_breakdown(dataset, compute_site)
            options.append({
                "direction": "move-data",
                "to": compute_site,
                "cost": breakdown["total"],
                "cost_breakdown": breakdown,
            })

        if not options:
            raise NoLegalOption(
                f"{dataset.name}: no legal way to co-locate with compute at {compute_site} ({'; '.join(eliminated)})",
                details={
                    "dataset": dataset.name,
                    "compute_site": compute_site,
                    "eliminated": elimination_details,
                },
            )

        # On an exact cost tie, prefer moving compute so data stays resident.
        best = min(options, key=lambda option: (option["cost"], _DIRECTION_ORDER[option["direction"]]))
        ordered_options = sorted(options, key=lambda option: _DIRECTION_ORDER[option["direction"]])
        return {
            "schema": SCHEMA_VERSION,
            "direction": best["direction"],
            "to": best["to"],
            "cost": best["cost"],
            "cost_breakdown": dict(best["cost_breakdown"]),
            "reason_code": "CHEAPEST_LEGAL_OPTION",
            "reason": (
                f"cheapest legal option at {best['cost']:.6g}; "
                f"evaluated {len(options)} legal option(s), eliminated {len(eliminated)}"
            ),
            "options": ordered_options,
            "eliminated": eliminated,
            "elimination_details": elimination_details,
        }
