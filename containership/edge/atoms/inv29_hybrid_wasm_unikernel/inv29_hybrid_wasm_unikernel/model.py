"""Standalone hybrid Wasm/unikernel composition model.

This module intentionally has no ``pk_core`` dependency so the security-critical
composition rules can be unit tested in an isolated checkout.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet

COMPOSITION_SCHEMA = "PK_HYBRID_COMPOSITION/1"
VERIFICATION_SCHEMA = "PK_HYBRID_VERIFICATION/1"
SUPPORTED_WASM_ARCHITECTURES = frozenset({"wasm32", "wasm64"})
SUPPORTED_HOST_ARCHITECTURES = frozenset({"x86_64", "aarch64"})
MAX_NAME_LENGTH = 256
MAX_CAPABILITIES = 4096
MAX_CAPABILITY_LENGTH = 256


class LayerMissing(PermissionError):
    """Raised when a composition does not carry the required sound layers."""


class ImportUnsatisfied(PermissionError):
    """Raised when a Wasm module imports a capability the host does not expose."""


@dataclass(frozen=True, slots=True)
class WasmModule:
    name: str
    imports: FrozenSet[str]
    hardened: bool = True
    architecture: str = "wasm32"


@dataclass(frozen=True, slots=True)
class HostImage:
    """The sealed unikernel image hosting the Wasm runtime."""

    name: str
    exposes: FrozenSet[str]
    sealed: bool = True
    architecture: str = "x86_64"


def _require_name(label: str, value: object) -> str:
    # exact type: a str subclass could override __eq__/__hash__ and lie to set/dict operations
    if type(value) is not str or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    if len(value) > MAX_NAME_LENGTH:
        raise ValueError(f"{label} exceeds {MAX_NAME_LENGTH} characters")
    return value


def _require_capabilities(label: str, value: object) -> FrozenSet[str]:
    # exact type: a frozenset subclass could override __sub__/__and__ and defeat import closure
    if type(value) is not frozenset:
        raise TypeError(f"{label} must be a frozenset[str] (not a subclass), got {type(value).__name__}")
    if len(value) > MAX_CAPABILITIES:
        raise ValueError(f"{label} exceeds the {MAX_CAPABILITIES}-capability limit")
    bad = [item for item in value if type(item) is not str or not item.strip()]
    if bad:
        raise TypeError(f"{label} must contain only non-empty strings")
    if any(len(item) > MAX_CAPABILITY_LENGTH for item in value):
        raise ValueError(f"{label} contains a capability longer than {MAX_CAPABILITY_LENGTH} characters")
    return value


def verify(module: WasmModule, host: HostImage) -> dict:
    """Verify each isolation layer independently plus import closure.

    Returns a machine-readable verification record and does not silently coerce
    malformed inputs.  Unsupported architectures are reported as failed layer
    verification rather than being treated as a valid layer.
    """
    # exact types: a subclass could turn fields into properties that answer differently
    # on each read (validate one value, then record/compare another)
    if type(module) is not WasmModule:
        raise TypeError(f"module must be WasmModule, got {type(module).__name__}")
    if type(host) is not HostImage:
        raise TypeError(f"host must be HostImage, got {type(host).__name__}")

    _require_name("module.name", module.name)
    _require_name("host.name", host.name)
    imports = _require_capabilities("module.imports", module.imports)
    exposes = _require_capabilities("host.exposes", host.exposes)
    if type(module.hardened) is not bool:
        raise TypeError("module.hardened must be bool")
    if type(host.sealed) is not bool:
        raise TypeError("host.sealed must be bool")
    if type(module.architecture) is not str or type(host.architecture) is not str:
        raise TypeError("architecture must be a plain str")

    host_ok = host.sealed and host.architecture in SUPPORTED_HOST_ARCHITECTURES
    wasm_ok = module.hardened and module.architecture in SUPPORTED_WASM_ARCHITECTURES
    unsatisfied = tuple(sorted(imports - exposes))

    return {
        "schema": VERIFICATION_SCHEMA,
        "module": module.name,
        "host": host.name,
        "layers": {
            "unikernel": {
                "verified": host_ok,
                "sealed": host.sealed,
                "architecture": host.architecture,
                "guarantee": "hardware-backed address-space isolation",
            },
            "wasm": {
                "verified": wasm_ok,
                "hardened": module.hardened,
                "architecture": module.architecture,
                "guarantee": "software fault isolation and typed imports",
            },
        },
        "import_closure": {"verified": not unsatisfied, "unsatisfied": unsatisfied},
        "verified": host_ok and wasm_ok and not unsatisfied,
    }


def compose(module: WasmModule, host: HostImage, *, required_layers: int = 2) -> dict:
    """Compose the layers after independent verification.

    ``required_layers`` may raise the environmental bar, but may never lower the
    hybrid tier below its mandatory two isolation layers.
    """
    if type(required_layers) is not int or required_layers < 2:
        raise ValueError(
            f"required_layers must be an integer >= 2 for a hybrid composition, got {required_layers!r}"
        )

    result = verify(module, host)
    layers = []
    failures = []
    for layer_name in ("unikernel", "wasm"):
        layer = result["layers"][layer_name]
        if layer["verified"]:
            layers.append({"layer": layer_name, "guarantee": layer["guarantee"]})
        else:
            failures.append(
                f"{layer_name}: verification failed (architecture={layer['architecture']!r})"
            )

    if failures or len(layers) < required_layers:
        detail = "; ".join(failures) or "environment requires more verified layers than this composition provides"
        raise LayerMissing(
            f"{module.name}: {len(layers)} sound layer(s), {required_layers} required ({detail})"
        )

    unsatisfied = result["import_closure"]["unsatisfied"]
    if unsatisfied:
        raise ImportUnsatisfied(
            f"{module.name}: imports not exposed by {host.name}: {list(unsatisfied)}"
        )

    return {
        "schema": COMPOSITION_SCHEMA,
        "module": module.name,
        "host": host.name,
        "layers": layers,
        "layer_count": len(layers),
        "imports": sorted(module.imports),
        "defence_in_depth": len(layers) >= 2,
        "verification": result,
    }
