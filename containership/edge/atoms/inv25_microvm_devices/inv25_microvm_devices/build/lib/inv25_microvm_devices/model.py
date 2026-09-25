"""Dependency-free device catalogue model for INV-25.

This module deliberately has no ``pk_core`` dependency so the security-critical
catalogue rules can be tested in a standalone component checkout.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any

try:  # package import
    from .errors import Inv25Error
except ImportError:  # standalone file load (tests/test_model.py): stay dependency-free
    import importlib.util as _ilu, pathlib as _pl, sys as _sys
    _errs = _sys.modules.get("inv25_errors")
    if _errs is None:
        _spec = _ilu.spec_from_file_location("inv25_errors", _pl.Path(__file__).with_name("errors.py"))
        _errs = _ilu.module_from_spec(_spec)
        _sys.modules["inv25_errors"] = _errs
        _spec.loader.exec_module(_errs)
    Inv25Error = _errs.Inv25Error

# Reviewed resource ceilings (docs/limits.md). Changing these requires owner review.
MAX_DEVICES = 64
MAX_REGISTERS_PER_DEVICE = 256
MAX_AGGREGATE_REGISTERS = 4096
MAX_EXPORT_BYTES = 1_048_576
LEGACY_CLASSES = frozenset({"legacy-emulation"})
HOST_EXPOSURE_CLASSES = frozenset({"host-passthrough", "raw-mmio"})

FORBIDDEN_CLASSES = frozenset({"legacy-emulation", "host-passthrough", "raw-mmio"})
PERMITTED_CLASSES = frozenset({"paravirtual"})

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+(?:\.[0-9]+)?(?:[-+][0-9A-Za-z.-]+)?$")
_REGISTER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class DeviceRejected(Inv25Error, PermissionError):
    """Raised when a device may not enter the catalogue. Carries a stable ``code``."""

    code = "INV25_INVALID_FIELD"


class LimitExceeded(DeviceRejected):
    code = "INV25_LIMIT_EXCEEDED"


def _clean_text(value: Any, field_name: str, *, max_len: int = 256, code: str = "INV25_INVALID_FIELD",
                empty_code: str | None = None) -> str:
    if not isinstance(value, str):
        raise DeviceRejected(f"{field_name} must be a string", code=code, field=field_name)
    if len(value) > max_len * 4:  # bound work before stripping/scanning pathological input
        raise LimitExceeded(f"{field_name} exceeds {max_len} characters", field=field_name, limit=max_len)
    value = value.strip()
    if not value:
        raise DeviceRejected(f"{field_name} must not be empty", code=empty_code or code, field=field_name)
    if len(value) > max_len:
        raise LimitExceeded(f"{field_name} exceeds {max_len} characters", field=field_name, limit=max_len)
    if any(ord(ch) < 32 or 127 <= ord(ch) < 160 or ch in "\u2028\u2029\u200b\u200e\u200f\u202e\ufeff" for ch in value):
        raise DeviceRejected(f"{field_name} contains control or invisible characters", code=code, field=field_name)
    return value


@dataclass(frozen=True)
class DeviceSpec:
    """One paravirtual device: what the guest can see, and why it exists."""

    name: str
    device_class: str
    version: str
    registers: frozenset[str]
    rationale: str = ""
    reviewer: str = ""

    @property
    def surface(self) -> int:
        return len(self.registers)

    def validated(self) -> "DeviceSpec":
        name = _clean_text(self.name, "device name", max_len=64, code="INV25_INVALID_NAME")
        if not _NAME_RE.fullmatch(name):
            raise DeviceRejected(f"{name!r}: invalid device name", code="INV25_INVALID_NAME")
        device_class = _clean_text(self.device_class, "device class", max_len=64, code="INV25_INVALID_CLASS")
        if device_class in LEGACY_CLASSES:
            raise DeviceRejected(f"{name}: device class {device_class!r} is never permitted",
                                 code="INV25_FORBIDDEN_LEGACY_EMULATION", device_class=device_class)
        if device_class in HOST_EXPOSURE_CLASSES:
            raise DeviceRejected(f"{name}: device class {device_class!r} is never permitted",
                                 code="INV25_FORBIDDEN_HOST_EXPOSURE", device_class=device_class)
        if device_class not in PERMITTED_CLASSES:
            raise DeviceRejected(f"{name}: device class {device_class!r} is not a recognised permitted class",
                                 code="INV25_INVALID_CLASS")
        version = _clean_text(self.version, "device version", max_len=64, code="INV25_INVALID_VERSION")
        if not _VERSION_RE.fullmatch(version):
            raise DeviceRejected(f"{name}: version {version!r} is not a supported version identifier",
                                 code="INV25_INVALID_VERSION")
        if not isinstance(self.registers, frozenset):
            raise DeviceRejected(f"{name}: guest-visible registers must be declared as a frozenset",
                                 code="INV25_INVALID_REGISTER")
        if len(self.registers) > MAX_REGISTERS_PER_DEVICE:
            raise LimitExceeded(f"{name}: more than {MAX_REGISTERS_PER_DEVICE} registers",
                                limit=MAX_REGISTERS_PER_DEVICE)
        for register in self.registers:
            if not isinstance(register, str) or not _REGISTER_RE.fullmatch(register):
                raise DeviceRejected(f"{name}: invalid guest-visible register", code="INV25_INVALID_REGISTER")
        folded = {r.casefold() for r in self.registers}
        if len(folded) != len(self.registers):
            raise DeviceRejected(f"{name}: case-variant duplicate registers are ambiguous",
                                 code="INV25_INVALID_REGISTER")
        rationale = _clean_text(self.rationale, "rationale", max_len=1024, code="INV25_INVALID_FIELD",
                                empty_code="INV25_MISSING_RATIONALE")
        reviewer = _clean_text(self.reviewer, "reviewer", max_len=256, code="INV25_INVALID_FIELD",
                               empty_code="INV25_MISSING_REVIEWER")
        return DeviceSpec(name, device_class, version, self.registers, rationale, reviewer)

    def as_dict(self) -> dict[str, Any]:
        spec = self.validated()
        return {
            "name": spec.name,
            "device_class": spec.device_class,
            "version": spec.version,
            "registers": sorted(spec.registers),
            "rationale": spec.rationale,
            "reviewer": spec.reviewer,
        }


@dataclass
class DeviceCatalogue:
    """Closed, reviewed set of devices a microVM may attach."""

    environment: str
    devices: dict[str, DeviceSpec] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.environment = _clean_text(self.environment, "environment", max_len=128)
        if not _NAME_RE.fullmatch(self.environment):
            raise DeviceRejected("environment must match the device-name grammar", code="INV25_INVALID_FIELD")
        if not isinstance(self.devices, dict):
            raise DeviceRejected("devices must be a mapping", code="INV25_INVALID_FIELD")
        if self.devices:
            original = list(self.devices.values())
            self.devices = {}
            for spec in original:
                self.register(spec)

    def register(self, spec: DeviceSpec) -> DeviceSpec:
        if not isinstance(spec, DeviceSpec):
            raise DeviceRejected("catalogue entries must be DeviceSpec instances")
        spec = spec.validated()
        existing = self.devices.get(spec.name)
        if existing is not None and existing != spec:
            raise DeviceRejected(
                f"{spec.name}: already catalogued at {existing.version}; a changed entry must use replace()",
                code="INV25_REPLACE_REQUIRED")
        if existing is None:
            if len(self.devices) >= MAX_DEVICES:
                raise LimitExceeded(f"catalogue already holds {MAX_DEVICES} devices", limit=MAX_DEVICES)
            if self.total_surface() + spec.surface > MAX_AGGREGATE_REGISTERS:
                raise LimitExceeded("aggregate register ceiling exceeded", limit=MAX_AGGREGATE_REGISTERS)
        self.devices[spec.name] = spec
        return spec

    def replace(self, spec: DeviceSpec) -> dict[str, Any]:
        """Explicitly replace an existing device and return its mandatory surface diff."""
        if not isinstance(spec, DeviceSpec):
            raise DeviceRejected("catalogue entries must be DeviceSpec instances")
        spec = spec.validated()
        old = self.devices.get(spec.name)
        if old is None:
            raise DeviceRejected(f"{spec.name}: cannot replace a device that is not catalogued",
                                 code="INV25_REPLACE_TARGET_ABSENT")
        if old.version == spec.version and old != spec:
            raise DeviceRejected(f"{spec.name}: changed entries require a new version",
                                 code="INV25_VERSION_NOT_CHANGED")
        if self.total_surface() - old.surface + spec.surface > MAX_AGGREGATE_REGISTERS:
            raise LimitExceeded("aggregate register ceiling exceeded", limit=MAX_AGGREGATE_REGISTERS)
        diff = self.diff(old, spec)
        self.devices[spec.name] = spec
        return diff

    def permitted(self) -> set[str]:
        return set(self.devices)

    def total_surface(self) -> int:
        return sum(d.surface for d in self.devices.values())

    def export(self) -> dict[str, Any]:
        out = {
            "schema": "PK_DEVICE_CATALOGUE/1",
            "environment": self.environment,
            "devices": [self.devices[name].as_dict() for name in sorted(self.devices)],
        }
        size = len(canonical_json(out))
        if size > MAX_EXPORT_BYTES:
            raise LimitExceeded(f"serialized catalogue is {size} bytes", limit=MAX_EXPORT_BYTES)
        return out

    def digest(self) -> str:
        """SHA-256 over the canonical export; stable across equivalent catalogues."""
        return "sha256:" + hashlib.sha256(canonical_json(self.export())).hexdigest()

    @staticmethod
    def diff(old: DeviceSpec, new: DeviceSpec) -> dict[str, Any]:
        old = old.validated()
        new = new.validated()
        if old.name != new.name:
            raise ValueError("cannot diff two different devices")
        added = sorted(new.registers - old.registers)
        removed = sorted(old.registers - new.registers)
        return {
            "schema": "PK_DEVICE_SURFACE_DIFF/1",
            "device": new.name,
            "from": old.version,
            "to": new.version,
            "added": added,
            "removed": removed,
            "widened": bool(added),
            "surface": {"before": old.surface, "after": new.surface},
        }


def canonical_json(obj: Any) -> bytes:
    """Canonical serialization used for every digest/signature in INV-25."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def catalogue_from_export(data: Any, *, max_bytes: int = MAX_EXPORT_BYTES) -> DeviceCatalogue:
    """Strictly parse a PK_DEVICE_CATALOGUE/1 document back into a validated catalogue."""
    if isinstance(data, (bytes, str)):
        raw = data.encode("utf-8") if isinstance(data, str) else data
        if len(raw) > max_bytes:
            raise LimitExceeded("catalogue payload too large", limit=max_bytes)
        try:
            data = json.loads(raw.decode("utf-8"), parse_constant=_reject_constant)
        except (ValueError, UnicodeDecodeError, RecursionError) as exc:
            raise DeviceRejected("catalogue payload is not valid JSON", code="INV25_INVALID_FIELD") from exc
    if not isinstance(data, dict) or set(data) != {"schema", "environment", "devices"}:
        raise DeviceRejected("catalogue document has unexpected shape", code="INV25_INVALID_FIELD")
    if data["schema"] != "PK_DEVICE_CATALOGUE/1":
        raise DeviceRejected("unsupported catalogue schema", code="INV25_COMPATIBILITY_MISMATCH")
    devices = data["devices"]
    if not isinstance(devices, list):
        raise DeviceRejected("devices must be an array", code="INV25_INVALID_FIELD")
    if len(devices) > MAX_DEVICES:
        raise LimitExceeded("too many devices", limit=MAX_DEVICES)
    cat = DeviceCatalogue(data["environment"])
    keys = {"name", "device_class", "version", "registers", "rationale", "reviewer"}
    for d in devices:
        if not isinstance(d, dict) or set(d) != keys or not isinstance(d["registers"], list):
            raise DeviceRejected("device entry has unexpected shape", code="INV25_INVALID_FIELD")
        if len(d["registers"]) > MAX_REGISTERS_PER_DEVICE:
            raise LimitExceeded("too many registers", limit=MAX_REGISTERS_PER_DEVICE)
        regs = d["registers"]
        if not all(isinstance(r, str) for r in regs) or len(set(regs)) != len(regs):
            raise DeviceRejected("registers must be unique strings", code="INV25_INVALID_REGISTER")
        spec = DeviceSpec(d["name"], d["device_class"], d["version"], frozenset(regs),
                          d["rationale"], d["reviewer"])
        if spec.validated().name in cat.devices:
            raise DeviceRejected("duplicate device entry", code="INV25_REPLACE_REQUIRED")
        cat.register(spec)
    return cat


def _reject_constant(token: str) -> Any:
    raise ValueError(f"non-finite constant {token} rejected")
