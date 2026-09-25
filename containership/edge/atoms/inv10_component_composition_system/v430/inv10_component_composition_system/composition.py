"""Deterministic, fail-closed component composition primitives for INV-10.

This module deliberately has no dependency on :mod:`pk_core` so that the
linker itself can be unit-tested and embedded independently of the checklist
and evidence framework.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import unicodedata
from collections.abc import Iterable
from typing import Any

COMPOSITION_SCHEMA = "PK_COMPOSITION/1"
IDENTITY_PROFILE = "PK_COMPOSITION_ID/2"
DIGEST_ALGORITHM = "sha256"


@dataclass(frozen=True)
class CompositionLimits:
    """Fail-closed resource ceilings for one composition operation."""

    max_components: int = 4096
    max_interfaces_per_component: int = 4096
    max_external_imports: int = 16384
    max_total_interface_references: int = 262144
    max_identifier_length: int = 512

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


DEFAULT_LIMITS = CompositionLimits()


class CompositionError(ValueError):
    """Base class for machine-readable, fail-closed composition failures."""

    code = "COMPOSITION_ERROR"

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.details = dict(details)

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "details": dict(self.details)}


class InvalidComposition(CompositionError):
    code = "INVALID_COMPOSITION"


class UnsatisfiedImport(CompositionError):
    """Raised when a composition leaves an internal import with no export."""

    code = "UNSATISFIED_IMPORT"


class AmbiguousExport(CompositionError):
    """Raised when exports or component identities are ambiguous."""

    code = "AMBIGUOUS_EXPORT"


class CompositionCycle(CompositionError):
    """Raised when components depend on each other in a cycle."""

    code = "COMPOSITION_CYCLE"


class ResourceLimitExceeded(CompositionError):
    code = "RESOURCE_LIMIT_EXCEEDED"


@dataclass(frozen=True)
class Unit:
    """A unit of composition: its stable name, imports, and exports."""

    name: str
    imports: frozenset[str]
    exports: frozenset[str]


def _validated_identifier(value: Any, *, kind: str, limits: CompositionLimits) -> str:
    if not isinstance(value, str):
        raise InvalidComposition(
            f"{kind} must be a string, got {type(value).__name__}",
            field=kind,
            observed_type=type(value).__name__,
        )
    if not value or value != value.strip():
        raise InvalidComposition(
            f"{kind} must be non-empty and have no leading/trailing whitespace",
            field=kind,
        )
    if len(value) > limits.max_identifier_length:
        raise ResourceLimitExceeded(
            f"{kind} exceeds {limits.max_identifier_length} characters",
            field=kind,
            limit=limits.max_identifier_length,
            observed=len(value),
        )
    if unicodedata.normalize("NFC", value) != value:
        raise InvalidComposition(
            f"{kind} must be NFC-normalized",
            field=kind,
        )
    if any(unicodedata.category(ch).startswith("C") for ch in value):
        raise InvalidComposition(
            f"{kind} contains a control/format character",
            field=kind,
        )
    return value


def _validated_interfaces(
    values: Any,
    *,
    component: str,
    field_name: str,
    limits: CompositionLimits,
) -> frozenset[str]:
    if isinstance(values, (str, bytes)):
        raise InvalidComposition(
            f"{component}.{field_name} must be an iterable of interface identifiers, not a scalar string",
            component=component,
            field=field_name,
        )
    try:
        raw = tuple(values)
    except TypeError as exc:
        raise InvalidComposition(
            f"{component}.{field_name} must be iterable",
            component=component,
            field=field_name,
        ) from exc
    if len(raw) > limits.max_interfaces_per_component:
        raise ResourceLimitExceeded(
            f"{component}.{field_name} exceeds the per-component interface limit",
            component=component,
            field=field_name,
            limit=limits.max_interfaces_per_component,
            observed=len(raw),
        )
    validated = tuple(
        _validated_identifier(v, kind=f"{component}.{field_name}[]", limits=limits)
        for v in raw
    )
    if len(set(validated)) != len(validated):
        raise InvalidComposition(
            f"{component}.{field_name} contains duplicate interface identifiers",
            component=component,
            field=field_name,
        )
    return frozenset(validated)


def _find_cycle(edges: dict[str, set[str]]) -> list[str]:
    """Return one deterministic cycle path, including the repeated start node."""

    visited: set[str] = set()
    active: set[str] = set()
    path: list[str] = []

    def visit(node: str) -> list[str] | None:
        visited.add(node)
        active.add(node)
        path.append(node)
        for dep in sorted(edges[node]):
            if dep not in edges:
                continue
            if dep in active:
                start = path.index(dep)
                return path[start:] + [dep]
            if dep not in visited:
                found = visit(dep)
                if found:
                    return found
        path.pop()
        active.remove(node)
        return None

    for node in sorted(edges):
        if node not in visited:
            found = visit(node)
            if found:
                return found
    return []


def _canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compose(
    components: Iterable[Unit],
    *,
    external: Iterable[str] = frozenset(),
    limits: CompositionLimits = DEFAULT_LIMITS,
) -> dict[str, Any]:
    """Link components into a deterministic, internally closed composition.

    Imports must bind either to exactly one export in this composition or to an
    explicitly declared external interface. Component dependency cycles,
    including self-cycles, are rejected. The returned composition identifier is
    the SHA-256 digest of a canonical manifest containing every unit's imports,
    exports, and resolved bindings.
    """

    if not isinstance(limits, CompositionLimits):
        raise InvalidComposition("limits must be a CompositionLimits instance", field="limits")
    if isinstance(components, (str, bytes)):
        raise InvalidComposition("components must be an iterable of Unit objects", field="components")
    try:
        parts = tuple(components)
    except TypeError as exc:
        raise InvalidComposition("components must be iterable", field="components") from exc
    if len(parts) > limits.max_components:
        raise ResourceLimitExceeded(
            "component count exceeds the configured limit",
            limit=limits.max_components,
            observed=len(parts),
        )

    validated: list[tuple[str, frozenset[str], frozenset[str]]] = []
    total_refs = 0
    for index, component in enumerate(parts):
        if not isinstance(component, Unit):
            raise InvalidComposition(
                f"components[{index}] must be Unit, got {type(component).__name__}",
                index=index,
                observed_type=type(component).__name__,
            )
        name = _validated_identifier(component.name, kind=f"components[{index}].name", limits=limits)
        imports = _validated_interfaces(
            component.imports,
            component=name,
            field_name="imports",
            limits=limits,
        )
        exports = _validated_interfaces(
            component.exports,
            component=name,
            field_name="exports",
            limits=limits,
        )
        total_refs += len(imports) + len(exports)
        if total_refs > limits.max_total_interface_references:
            raise ResourceLimitExceeded(
                "total interface references exceed the configured limit",
                limit=limits.max_total_interface_references,
                observed=total_refs,
            )
        validated.append((name, imports, exports))

    names = [name for name, _, _ in validated]
    if len(set(names)) != len(names):
        duplicates = sorted(name for name in set(names) if names.count(name) > 1)
        raise AmbiguousExport(
            f"component names must be unique: {duplicates}",
            duplicate_components=duplicates,
        )

    if isinstance(external, (str, bytes)):
        raise InvalidComposition("external must be an iterable of interface identifiers", field="external")
    try:
        external_raw = tuple(external)
    except TypeError as exc:
        raise InvalidComposition("external must be iterable", field="external") from exc
    if len(external_raw) > limits.max_external_imports:
        raise ResourceLimitExceeded(
            "external interface declaration exceeds the configured limit",
            limit=limits.max_external_imports,
            observed=len(external_raw),
        )
    external_set = frozenset(
        _validated_identifier(v, kind="external[]", limits=limits) for v in external_raw
    )
    if len(external_set) != len(external_raw):
        raise InvalidComposition("external contains duplicate interface identifiers", field="external")

    provider: dict[str, str] = {}
    for name, _, exports in sorted(validated, key=lambda item: item[0]):
        for interface in sorted(exports):
            if interface in provider:
                raise AmbiguousExport(
                    f"{interface!r} exported by both {provider[interface]} and {name}",
                    interface=interface,
                    providers=[provider[interface], name],
                )
            provider[interface] = name

    edges: dict[str, set[str]] = {}
    remaining: set[str] = set()
    bindings: list[dict[str, Any]] = []
    for name, imports, _ in validated:
        deps: set[str] = set()
        for interface in sorted(imports):
            if interface in provider:
                target = provider[interface]
                deps.add(target)
                bindings.append({"consumer": name, "interface": interface, "provider": target})
            elif interface in external_set:
                remaining.add(interface)
                bindings.append({"consumer": name, "interface": interface, "external": True})
            else:
                raise UnsatisfiedImport(
                    f"{name}: import {interface!r} has no export and is not declared external",
                    component=name,
                    interface=interface,
                )
        edges[name] = deps

    pending = {name: set(deps) for name, deps in edges.items()}
    order: list[str] = []
    while pending:
        ready = sorted(name for name, deps in pending.items() if not deps)
        if not ready:
            cycle = _find_cycle(edges)
            raise CompositionCycle(
                f"dependency cycle detected: {' -> '.join(cycle) if cycle else sorted(pending)}",
                cycle=cycle,
            )
        order.extend(ready)
        for name in ready:
            del pending[name]
        for deps in pending.values():
            deps.difference_update(ready)

    units_manifest = [
        {"name": name, "imports": sorted(imports), "exports": sorted(exports)}
        for name, imports, exports in sorted(validated, key=lambda item: item[0])
    ]
    bindings.sort(key=lambda b: (b["consumer"], b["interface"], b.get("provider", "")))
    providers = {interface: provider[interface] for interface in sorted(provider)}

    identity_material = {
        "schema": COMPOSITION_SCHEMA,
        "identity_profile": IDENTITY_PROFILE,
        "units": units_manifest,
        "bindings": bindings,
        "external_imports": sorted(remaining),
    }
    composition_id = _canonical_digest(identity_material)

    return {
        "components": sorted(names),
        "order": order,
        "external_imports": sorted(remaining),
        "exports": sorted(provider),
        "providers": providers,
        "bindings": bindings,
        "composition": composition_id,
        "digest_algorithm": DIGEST_ALGORITHM,
        "identity_profile": IDENTITY_PROFILE,
        "schema": COMPOSITION_SCHEMA,
        "closed": True,
    }
