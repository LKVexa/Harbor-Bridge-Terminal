"""Dependency-free structural interface compatibility model for INV-11.

This module intentionally does not import ``pk_core``.  It can therefore be
unit-tested and used by tooling that only needs interface-definition and
compatibility semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

ADDITIVE: Final = "additive"
COMPATIBLE: Final = "compatible"
BREAKING: Final = "breaking"


class Incompatible(TypeError):
    """Raised when two interfaces cannot be linked safely."""


def _nonempty_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


@dataclass(frozen=True)
class Func:
    """One function in an interface.

    ``params`` is an ordered tuple of ``(name, type)`` pairs. ``results`` is an
    ordered tuple of result/variant labels.  Order is retained because changing
    an externally visible signature must never be hidden by set comparison.
    """

    name: str
    params: tuple[tuple[str, str], ...]
    results: tuple[str, ...]

    def __post_init__(self) -> None:
        _nonempty_text(self.name, "function name")

        if isinstance(self.params, (str, bytes)):
            raise ValueError("params must be an iterable of (name, type) pairs")
        try:
            params = tuple(tuple(p) for p in self.params)
        except TypeError as exc:
            raise ValueError("params must be an iterable of (name, type) pairs") from exc
        normalized_params: list[tuple[str, str]] = []
        for index, param in enumerate(params):
            if len(param) != 2:
                raise ValueError(f"parameter {index} must contain exactly name and type")
            pname = _nonempty_text(param[0], f"parameter {index} name")
            ptype = _nonempty_text(param[1], f"parameter {index} type")
            normalized_params.append((pname, ptype))
        param_names = [name for name, _ in normalized_params]
        if len(param_names) != len(set(param_names)):
            duplicates = sorted({name for name in param_names if param_names.count(name) > 1})
            raise ValueError(f"duplicate parameter name(s): {duplicates}")

        if isinstance(self.results, (str, bytes)):
            raise ValueError("results must be an iterable of result labels/types")
        try:
            results = tuple(self.results)
        except TypeError as exc:
            raise ValueError("results must be an iterable of result labels/types") from exc
        normalized_results = tuple(
            _nonempty_text(result, f"result {index}") for index, result in enumerate(results)
        )

        object.__setattr__(self, "params", tuple(normalized_params))
        object.__setattr__(self, "results", normalized_results)


@dataclass(frozen=True)
class Interface:
    """A typed interface whose compatibility is structural, not version-based."""

    name: str
    version: str
    functions: frozenset[Func]

    def __post_init__(self) -> None:
        _nonempty_text(self.name, "interface name")
        _nonempty_text(self.version, "interface version")
        if isinstance(self.functions, (str, bytes)):
            raise ValueError("functions must be an iterable of Func values")
        try:
            raw_functions = tuple(self.functions)
        except TypeError as exc:
            raise ValueError("functions must be an iterable of Func values") from exc
        if any(not isinstance(func, Func) for func in raw_functions):
            raise TypeError("functions must contain only Func values")

        names = [func.name for func in raw_functions]
        if len(names) != len(set(names)):
            duplicates = sorted({name for name in names if names.count(name) > 1})
            raise ValueError(f"duplicate function name(s): {duplicates}")
        object.__setattr__(self, "functions", frozenset(raw_functions))

    def by_name(self) -> dict[str, Func]:
        """Return a deterministic name-indexed view of this interface."""
        return {func.name: func for func in sorted(self.functions, key=lambda f: f.name)}


def _result_change_reason(name: str, old: tuple[str, ...], new: tuple[str, ...]) -> str:
    added = [item for item in new if item not in old]
    removed = [item for item in old if item not in new]
    details: list[str] = []
    if added:
        details.append(f"added {added}")
    if removed:
        details.append(f"removed {removed}")
    common_old = [item for item in old if item in new]
    common_new = [item for item in new if item in old]
    if common_old != common_new:
        details.append("reordered existing result cases")
    if not details:
        details.append("ordered result signature changed")
    return f"{name}: result signature changed ({'; '.join(details)})"


def classify(old: Interface, new: Interface) -> dict[str, object]:
    """Classify a change by comparing structure, never version numbers.

    Added functions are additive. Removed functions, parameter changes, or any
    result-signature change are breaking. A version-only change is compatible.
    The reasons list is complete even when additive and breaking edits coexist.
    """
    if old.name != new.name:
        raise ValueError("cannot compare two differently named interfaces")

    old_by_name, new_by_name = old.by_name(), new.by_name()
    reasons: list[str] = []
    breaking = False

    removed = sorted(set(old_by_name) - set(new_by_name))
    if removed:
        reasons.append(f"functions removed: {removed}")
        breaking = True

    for name in sorted(set(old_by_name) & set(new_by_name)):
        old_func, new_func = old_by_name[name], new_by_name[name]
        if old_func.params != new_func.params:
            reasons.append(f"{name}: parameter signature changed")
            breaking = True
        if old_func.results != new_func.results:
            reasons.append(_result_change_reason(name, old_func.results, new_func.results))
            breaking = True

    added = sorted(set(new_by_name) - set(old_by_name))
    if added:
        reasons.append(f"functions added: {added}")

    if breaking:
        change_class = BREAKING
    elif added:
        change_class = ADDITIVE
    else:
        change_class = COMPATIBLE
        reasons.append("structurally identical")

    return {
        "schema": "PK_INTERFACE_DIFF/1",
        "interface": old.name,
        "from": old.version,
        "to": new.version,
        "class": change_class,
        "reasons": reasons,
        "linkable": change_class != BREAKING,
    }


def check_link(producer: Interface, consumer: Interface) -> dict[str, object]:
    """Require a producer to satisfy every consumer function identically."""
    if producer.name != consumer.name:
        raise Incompatible(
            f"producer offers {producer.name!r} but consumer expects {consumer.name!r}"
        )

    producer_by_name, consumer_by_name = producer.by_name(), consumer.by_name()
    missing = sorted(set(consumer_by_name) - set(producer_by_name))
    if missing:
        raise Incompatible(f"{producer.name}: producer does not offer {missing}")

    for name in sorted(consumer_by_name):
        producer_func = producer_by_name[name]
        consumer_func = consumer_by_name[name]
        if (
            producer_func.params != consumer_func.params
            or producer_func.results != consumer_func.results
        ):
            raise Incompatible(
                f"{name}: producer and consumer signatures differ structurally"
            )

    return {
        "schema": "PK_INTERFACE/1",
        "interface": producer.name,
        "producer_version": producer.version,
        "consumer_version": consumer.version,
        "linked": True,
        "functions": sorted(consumer_by_name),
    }
