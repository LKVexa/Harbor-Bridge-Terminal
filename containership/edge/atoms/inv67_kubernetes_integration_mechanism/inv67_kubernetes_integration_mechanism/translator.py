"""Pure Kubernetes Pod-subset translation primitives for INV-67.

This module intentionally has no dependency on ``pk_core`` so its untrusted-input
boundary can be unit tested and reused independently from the checklist harness.
The translator is strict: fields outside the documented subset are rejected by
path instead of being silently discarded.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import math
import re
from collections.abc import Mapping
from typing import Any

TRANSLATE_SCHEMA = "PK_K8S_TRANSLATE/1"
REFUSAL_SCHEMA = "PK_K8S_REFUSE/1"
STATUS_SCHEMA = "PK_K8S_STATUS/1"

PHASES = {
    "pending": "Pending",
    "running": "Running",
    "exited-0": "Succeeded",
    "failed": "Failed",
}

_MAX_QUANTITY = Decimal(2**63 - 1)
_QUANTITY_RE = re.compile(
    r"^(?P<number>[+-]?(?:\d+(?:\.\d*)?|\.\d+))"
    r"(?:(?P<exponent>[eE][+-]?\d+)|(?P<suffix>Ki|Mi|Gi|Ti|Pi|Ei|[numkMGTPE]?))$"
)
_DECIMAL_SUFFIX = {
    "n": Decimal("1e-9"),
    "u": Decimal("1e-6"),
    "m": Decimal("1e-3"),
    "": Decimal(1),
    "k": Decimal(1000),
    "M": Decimal(1000) ** 2,
    "G": Decimal(1000) ** 3,
    "T": Decimal(1000) ** 4,
    "P": Decimal(1000) ** 5,
    "E": Decimal(1000) ** 6,
}
_BINARY_SUFFIX = {
    "Ki": Decimal(1024),
    "Mi": Decimal(1024) ** 2,
    "Gi": Decimal(1024) ** 3,
    "Ti": Decimal(1024) ** 4,
    "Pi": Decimal(1024) ** 5,
    "Ei": Decimal(1024) ** 6,
}


@dataclass(frozen=True)
class RefusalDetail:
    """Machine-readable refusal detail for an unsupported or invalid field."""

    field: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {"field": self.field, "reason": self.reason}


class TranslationError(ValueError):
    """Base class for fail-closed translation errors."""

    code = "PK_K8S_INVALID"

    def __init__(self, message: str, *, details: list[RefusalDetail] | None = None):
        super().__init__(message)
        self.details = tuple(details or ())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": REFUSAL_SCHEMA,
            "code": self.code,
            "message": str(self),
            "details": [d.to_dict() for d in self.details],
        }


class Unsupported(TranslationError):
    """Raised when input requests semantics outside the supported subset."""

    code = "PK_K8S_UNSUPPORTED_FIELD"


class InvalidPod(TranslationError):
    """Raised when input is malformed or cannot be translated safely."""

    code = "PK_K8S_INVALID_POD"


def _normalise_number(value: Decimal) -> int | float:
    """Return integers exactly and fractional values compatibly as floats."""
    integral = value.to_integral_value()
    if value == integral:
        return int(integral)
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("quantity is outside the supported numeric range")
    return result


def quantity(q: str) -> int | float:
    """Parse a Kubernetes-style resource quantity into a normalized number.

    Supported suffixes include DecimalSI (n/u/m/k/M/G/T/P/E), BinarySI
    (Ki/Mi/Gi/Ti/Pi/Ei), and decimal exponent notation. Negative values,
    malformed values, and values above Kubernetes' 2^63-1 quantity ceiling are
    rejected. The implementation uses ``Decimal`` internally to avoid the
    binary-float parsing errors of the previous implementation.
    """
    if not isinstance(q, str) or not q or len(q) > 128 or q != q.strip():
        raise ValueError(f"invalid quantity {q!r}")
    match = _QUANTITY_RE.fullmatch(q)
    if not match:
        raise ValueError(f"invalid quantity {q!r}")
    try:
        number = Decimal(match.group("number"))
        exponent = match.group("exponent")
        if exponent:
            value = Decimal(f"{match.group('number')}{exponent}")
        else:
            suffix = match.group("suffix") or ""
            multiplier = _BINARY_SUFFIX.get(suffix, _DECIMAL_SUFFIX.get(suffix))
            if multiplier is None:
                raise ValueError
            value = number * multiplier
    except (InvalidOperation, ValueError):
        raise ValueError(f"invalid quantity {q!r}") from None
    if not number.is_finite() or number < 0:
        raise ValueError(f"invalid quantity {q!r}")
    if not value.is_finite() or value > _MAX_QUANTITY:
        raise ValueError(f"invalid quantity {q!r}")
    return _normalise_number(value)


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise InvalidPod(f"{path} must be an object", details=[RefusalDetail(path, "expected object")])
    return value


def _string(value: Any, path: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value):
        raise InvalidPod(f"{path} must be a{' non-empty' if nonempty else ''} string",
                         details=[RefusalDetail(path, "expected string")])
    return value


def _string_map(value: Any, path: str) -> dict[str, str]:
    if value is None:
        return {}
    obj = _mapping(value, path)
    out: dict[str, str] = {}
    for key, item in obj.items():
        if not isinstance(key, str) or not isinstance(item, str):
            raise InvalidPod(
                f"{path} keys and values must be strings",
                details=[RefusalDetail(path, "expected string-to-string map")],
            )
        out[key] = item
    return out


def _unknown_keys(obj: Mapping[str, Any], allowed: set[str], path: str) -> list[RefusalDetail]:
    prefix = f"{path}." if path else ""
    return [RefusalDetail(prefix + str(key), "field is outside the supported translation subset")
            for key in obj if key not in allowed]


def _resource_map(value: Any, path: str) -> dict[str, int | float]:
    if value is None:
        return {}
    obj = _mapping(value, path)
    unknown = _unknown_keys(obj, {"cpu", "memory"}, path)
    if unknown:
        _raise_unsupported(unknown)
    result: dict[str, int | float] = {}
    for name in ("cpu", "memory"):
        if name in obj:
            raw = obj[name]
            if not isinstance(raw, str):
                raise InvalidPod(
                    f"{path}.{name} must be a Kubernetes quantity string",
                    details=[RefusalDetail(f"{path}.{name}", "expected quantity string")],
                )
            try:
                result[name] = quantity(raw)
            except ValueError as exc:
                raise InvalidPod(
                    f"invalid {path}.{name}: {raw!r}",
                    details=[RefusalDetail(f"{path}.{name}", str(exc))],
                ) from None
    return result


def _raise_unsupported(details: list[RefusalDetail]) -> None:
    if not details:
        return
    # Deduplicate while preserving the encounter order.
    unique: list[RefusalDetail] = []
    seen: set[tuple[str, str]] = set()
    for detail in details:
        key = (detail.field, detail.reason)
        if key not in seen:
            seen.add(key)
            unique.append(detail)
    raise Unsupported(
        "; ".join(f"{d.field} ({d.reason})" for d in unique),
        details=unique,
    )


def translate(pod: dict[str, Any]) -> dict[str, Any]:
    """Translate the documented Pod subset into a placement request.

    Supported input:
    * top level: ``apiVersion`` (v1), ``kind`` (Pod), ``metadata``, ``spec``
    * metadata: ``name``, ``namespace``, ``labels``, ``annotations``
    * spec: ``containers`` plus explicit security fields that are refused when enabled
    * container: ``name``, ``image``, ``resources``; an empty securityContext is tolerated
    * resources: ``requests`` and ``limits`` containing ``cpu`` and/or ``memory``

    Any other requested semantics are rejected by field path. This deliberately
    favors an explicit refusal over a lossy migration.
    """
    root = _mapping(pod, "pod")
    unsupported: list[RefusalDetail] = []
    unsupported.extend(_unknown_keys(root, {"apiVersion", "kind", "metadata", "spec"}, ""))

    if "apiVersion" in root and root["apiVersion"] != "v1":
        unsupported.append(RefusalDetail("apiVersion", "only Kubernetes core/v1 Pod input is supported"))
    if "kind" in root and root["kind"] != "Pod":
        unsupported.append(RefusalDetail("kind", "only kind Pod is supported"))

    metadata = _mapping(root.get("metadata"), "metadata")
    unsupported.extend(_unknown_keys(metadata, {"name", "namespace", "labels", "annotations"}, "metadata"))
    name = _string(metadata.get("name"), "metadata.name")
    namespace = _string(metadata.get("namespace", "default"), "metadata.namespace")
    labels = _string_map(metadata.get("labels"), "metadata.labels")
    annotations = _string_map(metadata.get("annotations"), "metadata.annotations")

    spec = _mapping(root.get("spec"), "spec")
    allowed_spec = {"containers", "hostNetwork", "hostPID", "volumes", "initContainers"}
    unsupported.extend(_unknown_keys(spec, allowed_spec, "spec"))
    if spec.get("hostNetwork") not in (None, False):
        unsupported.append(RefusalDetail("spec.hostNetwork", "host networking is unsupported"))
    if spec.get("hostPID") not in (None, False):
        unsupported.append(RefusalDetail("spec.hostPID", "host PID namespace is unsupported"))

    volumes = spec.get("volumes", [])
    if volumes is None:
        volumes = []
    if not isinstance(volumes, list):
        raise InvalidPod("spec.volumes must be an array",
                         details=[RefusalDetail("spec.volumes", "expected array")])
    for i, volume in enumerate(volumes):
        path = f"spec.volumes[{i}]"
        v = _mapping(volume, path)
        if "hostPath" in v:
            unsupported.append(RefusalDetail(f"{path}.hostPath", "host path mounts are unsupported"))
        else:
            unsupported.append(RefusalDetail(path, "volumes are outside the supported translation subset"))

    init_containers = spec.get("initContainers", [])
    if init_containers is None:
        init_containers = []
    if not isinstance(init_containers, list):
        raise InvalidPod("spec.initContainers must be an array",
                         details=[RefusalDetail("spec.initContainers", "expected array")])
    if init_containers:
        unsupported.append(RefusalDetail("spec.initContainers", "init containers are outside the supported translation subset"))

    containers = spec.get("containers")
    if not isinstance(containers, list) or not containers:
        raise InvalidPod(
            "spec.containers must be a non-empty array",
            details=[RefusalDetail("spec.containers", "expected non-empty array")],
        )

    units: list[dict[str, Any]] = []
    names: set[str] = set()
    for i, container in enumerate(containers):
        path = f"spec.containers[{i}]"
        c = _mapping(container, path)
        unsupported.extend(_unknown_keys(c, {"name", "image", "resources", "securityContext"}, path))
        cname = _string(c.get("name"), f"{path}.name")
        if cname in names:
            raise InvalidPod(
                f"duplicate container name {cname!r}",
                details=[RefusalDetail(f"{path}.name", "container names must be unique")],
            )
        names.add(cname)
        image = _string(c.get("image"), f"{path}.image")

        security_context = c.get("securityContext")
        if security_context not in (None, {}):
            sc = _mapping(security_context, f"{path}.securityContext")
            if sc.get("privileged") is True:
                unsupported.append(RefusalDetail(
                    f"{path}.securityContext.privileged", "privileged containers are unsupported"
                ))
            else:
                unsupported.append(RefusalDetail(
                    f"{path}.securityContext", "container securityContext is outside the supported translation subset"
                ))

        resources = c.get("resources", {})
        resources_obj = _mapping(resources, f"{path}.resources")
        unsupported.extend(_unknown_keys(resources_obj, {"requests", "limits"}, f"{path}.resources"))
        requests = _resource_map(resources_obj.get("requests"), f"{path}.resources.requests")
        limits = _resource_map(resources_obj.get("limits"), f"{path}.resources.limits")
        unit = {
            "name": cname,
            "image": image,
            # Backward-compatible request aliases used by the v4.1 reference implementation.
            "cpu": requests.get("cpu", 0),
            "memory": requests.get("memory", 0),
            "requests": requests,
            "limits": limits,
        }
        units.append(unit)

    _raise_unsupported(unsupported)
    return {
        "schema": TRANSLATE_SCHEMA,
        "app": name,
        "namespace": namespace,
        "labels": labels,
        "annotations": annotations,
        "units": units,
    }


def project_status(state: str) -> str:
    """Project the reference runtime state into a Kubernetes Pod phase."""
    if not isinstance(state, str):
        raise TypeError("state must be a string")
    return PHASES.get(state, "Unknown")
