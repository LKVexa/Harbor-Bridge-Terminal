"""Deterministic application composition resolver for PLN-02.

This module deliberately has no dependency on ``pk_core`` so the resolver can be
unit-tested and embedded independently of the conformance/gating framework.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import hmac
import json
import re
from typing import Any, Mapping, Sequence

MAX_COMPONENTS = 200
MAX_EDGES = 4096
MAX_CAPABILITIES_PER_COMPONENT = 128
MAX_CATALOGUE_ENTRIES = 4096
MAX_INTERFACES_PER_COMPONENT = 128
MAX_IDENTIFIER_LENGTH = 256
MAX_VERSION_LENGTH = 128

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+\-]*$")
_COMPONENT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@+\-]*$")
_COMPONENT_FIELDS = frozenset({"name", "requires", "exports", "imports"})

APPLICATION_SCHEMA = "PK_APPLICATION/1"
CATALOGUE_SCHEMA = "PK_PROVIDER_CATALOGUE/1"
REVISION_SCHEMA = "PK_APPLICATION_REVISION/1"


class ResolutionError(ValueError):
    """Base class for deterministic, machine-readable resolver refusals."""

    code = "RESOLUTION_ERROR"

    def __init__(self, message: str, *, details: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.details = dict(details or {})

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "details": deepcopy(self.details)}


class ValidationError(ResolutionError):
    """Raised when a composition or provider catalogue violates the input contract."""

    code = "INVALID_APPLICATION"


class UnsatisfiedRequirement(ResolutionError):
    """Raised when a required capability has no provider in the environment."""

    code = "UNSATISFIED_CAPABILITY"


class IncompatibleInterface(ResolutionError):
    """Raised when a composition edge cannot satisfy an imported interface."""

    code = "INCOMPATIBLE_INTERFACE"


class RevisionIntegrityError(ResolutionError):
    """Raised when a revision no longer matches its content address."""

    code = "REVISION_INTEGRITY_ERROR"


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValidationError("input contains a non-canonical JSON value") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _require_sequence(value: Any, field: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValidationError(f"{field} must be a sequence", details={"field": field})
    return value


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field} must be an object", details={"field": field})
    return value


def _identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_IDENTIFIER_LENGTH:
        raise ValidationError(
            f"{field} must be a non-empty string no longer than {MAX_IDENTIFIER_LENGTH} characters",
            details={"field": field},
        )
    if not _IDENTIFIER.fullmatch(value):
        raise ValidationError(
            f"{field} contains unsupported characters",
            details={"field": field, "value": value},
        )
    return value


def _component_name(value: Any, field: str) -> str:
    value = _identifier(value, field)
    if not _COMPONENT_NAME.fullmatch(value):
        raise ValidationError(
            f"{field} contains unsupported component-name characters",
            details={"field": field, "value": value},
        )
    return value


def _version(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_VERSION_LENGTH:
        raise ValidationError(
            f"{field} must be a non-empty version string no longer than {MAX_VERSION_LENGTH} characters",
            details={"field": field},
        )
    if any(ord(ch) < 0x20 for ch in value):
        raise ValidationError(f"{field} contains a control character", details={"field": field})
    return value


def _normalize_components(components: Sequence[Any]) -> list[dict[str, Any]]:
    if len(components) > MAX_COMPONENTS:
        raise ValidationError(
            f"composition exceeds the {MAX_COMPONENTS}-component resolver limit",
            details={"limit": MAX_COMPONENTS, "actual": len(components)},
        )

    normalized: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for index, raw in enumerate(components):
        component = _require_mapping(raw, f"components[{index}]")
        unknown = sorted(str(k) for k in set(component) - _COMPONENT_FIELDS)
        if unknown:
            raise ValidationError(
                f"components[{index}] contains unsupported fields: {', '.join(unknown)}",
                details={"field": f"components[{index}]", "unsupported_fields": unknown},
            )
        if "name" not in component:
            raise ValidationError(
                f"components[{index}] is missing name",
                details={"field": f"components[{index}].name"},
            )
        name = _component_name(component["name"], f"components[{index}].name")
        if name in seen_names:
            raise ValidationError("duplicate component name", details={"component": name})
        seen_names.add(name)

        requires_raw = _require_mapping(component.get("requires", {}), f"components[{index}].requires")
        if len(requires_raw) > MAX_CAPABILITIES_PER_COMPONENT:
            raise ValidationError(
                f"component {name!r} exceeds the capability limit",
                details={"component": name, "limit": MAX_CAPABILITIES_PER_COMPONENT},
            )
        requires: dict[str, bool] = {}
        for capability, required in requires_raw.items():
            cap = _identifier(capability, f"components[{index}].requires key")
            if type(required) is not bool:
                raise ValidationError(
                    f"capability requirement {name}:{cap} must be boolean",
                    details={"component": name, "capability": cap},
                )
            requires[cap] = required

        normalized_interfaces: dict[str, dict[str, str]] = {}
        for direction in ("exports", "imports"):
            raw_interfaces = _require_mapping(
                component.get(direction, {}), f"components[{index}].{direction}"
            )
            if len(raw_interfaces) > MAX_INTERFACES_PER_COMPONENT:
                raise ValidationError(
                    f"component {name!r} exceeds the {direction} interface limit",
                    details={
                        "component": name,
                        "direction": direction,
                        "limit": MAX_INTERFACES_PER_COMPONENT,
                    },
                )
            interfaces: dict[str, str] = {}
            for interface, version in raw_interfaces.items():
                interface_name = _identifier(interface, f"components[{index}].{direction} key")
                interfaces[interface_name] = _version(
                    version, f"components[{index}].{direction}.{interface_name}"
                )
            normalized_interfaces[direction] = dict(sorted(interfaces.items()))

        normalized.append(
            {
                "name": name,
                "requires": dict(sorted(requires.items())),
                "exports": normalized_interfaces["exports"],
                "imports": normalized_interfaces["imports"],
            }
        )

    return sorted(normalized, key=lambda item: item["name"])


def _normalize_catalogue(catalogue: Mapping[str, Any]) -> dict[str, str]:
    if len(catalogue) > MAX_CATALOGUE_ENTRIES:
        raise ValidationError(
            f"catalogue exceeds the {MAX_CATALOGUE_ENTRIES}-entry resolver limit",
            details={"limit": MAX_CATALOGUE_ENTRIES, "actual": len(catalogue)},
        )
    normalized: dict[str, str] = {}
    for capability, provider in catalogue.items():
        cap = _identifier(capability, "catalogue capability")
        normalized[cap] = _identifier(provider, f"catalogue[{cap!r}]")
    return dict(sorted(normalized.items()))


def _normalize_edges(edges: Sequence[Any]) -> list[tuple[str, str, str]]:
    if len(edges) > MAX_EDGES:
        raise ValidationError(
            f"composition exceeds the {MAX_EDGES}-edge resolver limit",
            details={"limit": MAX_EDGES, "actual": len(edges)},
        )
    normalized: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for index, edge in enumerate(edges):
        edge = _require_sequence(edge, f"edges[{index}]")
        if len(edge) != 3:
            raise ValidationError(
                f"edges[{index}] must contain producer, consumer, and interface",
                details={"field": f"edges[{index}]"},
            )
        item = (
            _component_name(edge[0], f"edges[{index}].producer"),
            _component_name(edge[1], f"edges[{index}].consumer"),
            _identifier(edge[2], f"edges[{index}].interface"),
        )
        if item in seen:
            raise ValidationError("duplicate composition edge", details={"edge": list(item)})
        seen.add(item)
        normalized.append(item)
    return sorted(normalized)


def resolve(components: list[dict], edges: list[tuple], catalogue: dict) -> dict:
    """Resolve a composition into a deterministic, content-addressed revision.

    ``components`` contain ``name``, ``requires`` (capability -> required bool),
    and ``exports``/``imports`` (interface -> version). ``catalogue`` maps a
    capability name to the exact provider identifier selected for the
    environment. Every declared import is required and must have exactly one
    incoming composition edge.

    The returned dictionary remains convenient for JSON callers. Publication
    systems should treat it as immutable and may call :func:`verify_revision`
    before use to detect mutation.
    """
    components_seq = _require_sequence(components, "components")
    edges_seq = _require_sequence(edges, "edges")
    catalogue_map = _require_mapping(catalogue, "catalogue")

    normalized_components = _normalize_components(components_seq)
    normalized_edges = _normalize_edges(edges_seq)
    normalized_catalogue = _normalize_catalogue(catalogue_map)
    by_name = {component["name"]: component for component in normalized_components}

    bindings: dict[str, str] = {}
    dropped: list[str] = []
    for component in normalized_components:
        for capability, required in component["requires"].items():
            provider = normalized_catalogue.get(capability)
            if provider is None:
                if required:
                    raise UnsatisfiedRequirement(
                        f"{component['name']}: no provider for required capability {capability!r}",
                        details={"component": component["name"], "capability": capability},
                    )
                dropped.append(f"{component['name']}:{capability}")
                continue
            bindings[f"{component['name']}:{capability}"] = provider

    incoming: dict[tuple[str, str], tuple[str, str, str]] = {}
    for producer, consumer, interface in normalized_edges:
        if producer not in by_name or consumer not in by_name:
            raise IncompatibleInterface(
                f"{producer}->{consumer}: edge names an unknown component",
                details={"producer": producer, "consumer": consumer, "interface": interface},
            )
        exported = by_name[producer]["exports"].get(interface)
        imported = by_name[consumer]["imports"].get(interface)
        if exported is None or imported is None:
            raise IncompatibleInterface(
                f"{producer}->{consumer}: interface {interface!r} is not declared on both sides",
                details={"producer": producer, "consumer": consumer, "interface": interface},
            )
        if exported != imported:
            raise IncompatibleInterface(
                f"{producer}->{consumer}: {interface} exported {exported}, imported {imported}",
                details={
                    "producer": producer,
                    "consumer": consumer,
                    "interface": interface,
                    "exported_version": exported,
                    "imported_version": imported,
                },
            )
        key = (consumer, interface)
        if key in incoming:
            raise IncompatibleInterface(
                f"{consumer}: import {interface!r} has more than one producer",
                details={"consumer": consumer, "interface": interface},
            )
        incoming[key] = (producer, consumer, interface)

    for component in normalized_components:
        for interface in component["imports"]:
            if (component["name"], interface) not in incoming:
                raise IncompatibleInterface(
                    f"{component['name']}: required import {interface!r} is unbound",
                    details={"consumer": component["name"], "interface": interface},
                )

    bindings = dict(sorted(bindings.items()))
    dropped = sorted(dropped)
    edge_lists = [list(edge) for edge in normalized_edges]
    content = {
        "schema": REVISION_SCHEMA,
        # Retain the v4.1 names-only field for compatibility; component_specs is
        # the complete normalized semantic input covered by the content address.
        "components": [component["name"] for component in normalized_components],
        "component_specs": normalized_components,
        "edges": edge_lists,
        "bindings": bindings,
        "dropped_optional": dropped,
        "provider_binding_digest": _digest(bindings),
    }
    content["revision"] = _digest(content)
    return content


def resolve_document(application: Mapping[str, Any], catalogue: Mapping[str, Any]) -> dict:
    """Resolve the versioned external document contracts.

    ``application`` must be a ``PK_APPLICATION/1`` envelope containing
    ``components`` and ``edges``. ``catalogue`` must be a
    ``PK_PROVIDER_CATALOGUE/1`` envelope containing ``providers``. Unknown
    envelope fields are rejected so callers cannot assume unaudited semantics.
    """
    application = _require_mapping(application, "application")
    catalogue = _require_mapping(catalogue, "catalogue_document")

    allowed_application = {"schema", "components", "edges"}
    allowed_catalogue = {"schema", "providers"}
    application_unknown = sorted(str(k) for k in set(application) - allowed_application)
    catalogue_unknown = sorted(str(k) for k in set(catalogue) - allowed_catalogue)
    if application_unknown:
        raise ValidationError(
            "application document contains unsupported fields",
            details={"unsupported_fields": application_unknown},
        )
    if catalogue_unknown:
        raise ValidationError(
            "catalogue document contains unsupported fields",
            details={"unsupported_fields": catalogue_unknown},
        )
    if application.get("schema") != APPLICATION_SCHEMA:
        raise ValidationError(
            f"application schema must be {APPLICATION_SCHEMA!r}",
            details={"schema": application.get("schema")},
        )
    if catalogue.get("schema") != CATALOGUE_SCHEMA:
        raise ValidationError(
            f"catalogue schema must be {CATALOGUE_SCHEMA!r}",
            details={"schema": catalogue.get("schema")},
        )
    if "components" not in application or "edges" not in application:
        raise ValidationError("application document requires components and edges")
    if "providers" not in catalogue:
        raise ValidationError("catalogue document requires providers")
    return resolve(application["components"], application["edges"], catalogue["providers"])


def verify_revision(revision: Mapping[str, Any]) -> bool:
    """Verify that a resolved revision still matches its SHA-256 content address.

    Returns ``True`` on success and raises :class:`RevisionIntegrityError` on
    malformed or modified input.
    """
    revision = _require_mapping(revision, "revision")
    claimed = revision.get("revision")
    if not isinstance(claimed, str) or not re.fullmatch(r"[0-9a-f]{64}", claimed):
        raise RevisionIntegrityError("revision has no valid SHA-256 content address")
    body = deepcopy(dict(revision))
    body.pop("revision", None)
    actual = _digest(body)
    if not hmac.compare_digest(claimed, actual):
        raise RevisionIntegrityError(
            "revision content does not match its content address",
            details={"claimed": claimed, "actual": actual},
        )
    return True
