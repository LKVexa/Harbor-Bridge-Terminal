"""Fail-closed validation policy kernel for INV-09.

This module intentionally has no ``pk_core`` dependency so its security-critical
validation rules can be unit-tested in isolation.  It validates a *decoded
module descriptor*; the byte-level decoder/type validator
(M01-M03) now lives in ``prod/`` and must be the only source of ``used_features``.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Final

#: Features that can make results diverge between hosts or executions.
NON_DETERMINISTIC: Final[frozenset[str]] = frozenset(
    {"float-relaxed", "simd-relaxed", "threads", "wall-clock"}
)

#: Profiles: the complete feature ceiling each profile permits.
#: Wasm 2.0 standard features that are deterministic and certified by prod/typecheck.
_STD_2_0: Final[frozenset[str]] = frozenset({"mutable-globals-import", "sign-ext", "sat-float-to-int"})

PROFILES: Final[dict[str, frozenset[str]]] = {
    "deterministic": frozenset({"core", "bulk-memory", "reference-types", "multi-value"}) | _STD_2_0,
    "extended": frozenset({"core", "bulk-memory", "reference-types", "multi-value", "simd"}) | _STD_2_0,
    "permissive": _STD_2_0 | frozenset(
        {
            "core",
            "bulk-memory",
            "reference-types",
            "multi-value",
            "simd",
            "simd-relaxed",
            "threads",
            "float-relaxed",
            "wall-clock",
        }
    ),
}
KNOWN_FEATURES: Final[frozenset[str]] = frozenset().union(*PROFILES.values())

MAX_SECTIONS: Final[int] = 64
MAX_BYTES: Final[int] = 4 * 1024 * 1024
MAX_FEATURES: Final[int] = 64
MAX_MODULE_NAME_CHARS: Final[int] = 256
MAX_FEATURE_NAME_CHARS: Final[int] = 64
_FEATURE_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")


class ValidationFailed(ValueError):
    """Raised when a module descriptor fails structural/policy validation."""

    code = "VALIDATION_FAILED"


class FeatureRefused(PermissionError):
    """Raised when a module declares or uses a feature the profile forbids."""

    code = "FEATURE_REFUSED"


@dataclass(frozen=True)
class Module:
    """Decoded compute-module facts consumed by the policy validator.

    ``used_features`` must be derived from validated module bytes by the binary
    parser/type validator.  It is not safe to populate it from an untrusted
    manifest or module header in production.
    """

    name: str
    declared_features: frozenset[str] | set[str]
    used_features: frozenset[str] | set[str]
    sections: int = 8
    size_bytes: int = 1024
    well_formed: bool = True


def _clean_module_name(name: object) -> str:
    if not isinstance(name, str):
        raise ValidationFailed(f"module name must be a string, got {type(name).__name__}")
    if not name or name != name.strip():
        raise ValidationFailed("module name must be non-empty and have no leading/trailing whitespace")
    if len(name) > MAX_MODULE_NAME_CHARS:
        raise ValidationFailed(
            f"module name exceeds {MAX_MODULE_NAME_CHARS} characters"
        )
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
        raise ValidationFailed("module name must not contain control characters")
    return name


def _snapshot_features(value: object, *, field_name: str, module_name: str) -> frozenset[str]:
    if not isinstance(value, (set, frozenset)):
        raise ValidationFailed(f"{module_name}: {field_name} must be a set of feature names")
    if len(value) > MAX_FEATURES:
        raise ValidationFailed(
            f"{module_name}: {field_name} exceeds the {MAX_FEATURES}-feature limit"
        )
    try:
        features = frozenset(value)
    except (RuntimeError, TypeError) as exc:
        raise ValidationFailed(f"{module_name}: could not snapshot {field_name}: {exc}") from exc
    for feature in features:
        if not isinstance(feature, str):
            raise ValidationFailed(
                f"{module_name}: {field_name} contains non-string feature {feature!r}"
            )
        if not feature or len(feature) > MAX_FEATURE_NAME_CHARS or not _FEATURE_NAME_RE.fullmatch(feature):
            raise ValidationFailed(
                f"{module_name}: invalid feature name {feature!r} in {field_name}"
            )
    return features


def validate(module: Module, *, profile: str) -> dict[str, object]:
    """Validate a decoded module descriptor using fail-closed profile rules.

    Successful return values conform to ``PK_MODULE_VALIDATION/1``.  Invalid
    structure/metadata raises :class:`ValidationFailed`; valid features that
    are not permitted by the selected profile raise :class:`FeatureRefused`.
    """
    if not isinstance(profile, str) or profile not in PROFILES:
        raise ValueError(f"unknown ISA profile: {profile!r}")
    if not isinstance(module, Module):
        raise ValidationFailed(f"expected a Module, got {type(module).__name__}")

    module_name = _clean_module_name(module.name)
    declared = _snapshot_features(
        module.declared_features, field_name="declared_features", module_name=module_name
    )
    used = _snapshot_features(
        module.used_features, field_name="used_features", module_name=module_name
    )

    if type(module.well_formed) is not bool:
        raise ValidationFailed(
            f"{module_name}: well_formed must be bool, got {type(module.well_formed).__name__}"
        )
    for field_name in ("sections", "size_bytes"):
        value = getattr(module, field_name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValidationFailed(
                f"{module_name}: {field_name} must be a non-negative int, got {value!r}"
            )

    if not module.well_formed:
        raise ValidationFailed(f"{module_name}: structural validation failed")
    if module.sections > MAX_SECTIONS:
        raise ValidationFailed(
            f"{module_name}: {module.sections} sections exceeds the {MAX_SECTIONS} limit"
        )
    if module.size_bytes > MAX_BYTES:
        raise ValidationFailed(
            f"{module_name}: {module.size_bytes} bytes exceeds the {MAX_BYTES} limit"
        )

    unknown_declared = declared - KNOWN_FEATURES
    unknown_used = used - KNOWN_FEATURES
    if unknown_declared or unknown_used:
        unknown = sorted(unknown_declared | unknown_used)
        raise ValidationFailed(f"{module_name}: unknown/unregistered features {unknown}")

    # Used-but-undeclared is dangerous: it can bypass declaration-only gates.
    undeclared = used - declared
    if undeclared:
        raise ValidationFailed(f"{module_name}: uses undeclared features {sorted(undeclared)}")

    permitted = PROFILES[profile]
    used_outside_profile = used - permitted
    if used_outside_profile:
        raise FeatureRefused(
            f"{module_name}: uses features outside the {profile!r} profile: "
            f"{sorted(used_outside_profile)}"
        )

    # A declaration is a requested capability.  Fail closed even when an
    # unsupported capability happens to be unused in this particular module.
    declared_outside_profile = declared - permitted
    if declared_outside_profile:
        raise FeatureRefused(
            f"{module_name}: declares features outside the {profile!r} profile: "
            f"{sorted(declared_outside_profile)}"
        )

    unused = declared - used
    deterministic = not bool(used & NON_DETERMINISTIC)
    return {
        "schema": "PK_MODULE_VALIDATION/1",
        "module": module_name,
        "profile": profile,
        "valid": True,
        "used": sorted(used),
        "declared_unused": sorted(unused),
        "declared_unsupported": [],
        "deterministic": deterministic,
    }
