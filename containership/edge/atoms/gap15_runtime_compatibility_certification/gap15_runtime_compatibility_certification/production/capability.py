"""Typed runtime capability model (component 17).

A ``RuntimeProfile`` is a set of typed ``Capability`` facts. Each fact records
its layer (hardware / measured-security / runtime-advertised / operator-label
/ dynamic) and provenance strength (measured > attested > discovered >
configured > inferred > claimed) so certification rules can demand a minimum
strength (MC-17-02, MC-17-04). Core fields use closed registries; vendor
extensions live under ``x-<vendor>.`` and are untrusted until policy
recognises them (MC-17-03). ``UNKNOWN`` is an explicit value, never a
wildcard (MC-17-08). Profile identity is a digest over normalised trusted
fields only (MC-17-07).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .canonical import digest

MODEL_VERSION = "GAP15-CAPABILITY-MODEL/1"
UNKNOWN = "__unknown__"

PROVENANCE_RANK = {"measured": 6, "attested": 5, "discovered": 4, "configured": 3, "inferred": 2, "claimed": 1}
LAYERS = {"hardware", "security", "runtime", "operator", "dynamic"}

REGISTRY: dict[str, set] = {
    "cpu.arch": {"x86_64", "aarch64", "riscv64", "armv7"},
    "cpu.isa_level": {"x86-64-v1", "x86-64-v2", "x86-64-v3", "x86-64-v4", "armv8.0", "armv8.2", "armv9.0", "rv64gc"},
    "os.family": {"linux", "windows", "freebsd", "none"},
    "isolation": {"process", "container", "microvm", "vm", "sev-snp", "tdx", "cca", "none"},
    "runtime.name": {"wasmtime", "wamr", "wasmedge", "wasmer", "jco", "none"},
    "wasi.preview": {"preview1", "preview2", "preview3"},
    "component_model": {"none", "0.2"},
    "abi": {"wasm32", "wasm64"},
    "fs": {"none", "ro", "rw"},
    "net": {"none", "outbound", "full"},
    "threads": {"none", "wasi-threads", "shared-memory"},
    "accelerator": {"none", "gpu", "npu", "fpga"},
}
# Deterministic alias normalisation (MC-17-06); anything not listed is rejected.
ALIASES = {
    "cpu.arch": {"amd64": "x86_64", "x64": "x86_64", "arm64": "aarch64"},
    "isolation": {"sev": "sev-snp", "intel-tdx": "tdx"},
    "wasi.preview": {"p1": "preview1", "p2": "preview2", "p3": "preview3", "wasip1": "preview1", "wasip2": "preview2"},
}
CORE_FIELDS_FOR_IDENTITY = ("cpu.arch", "cpu.isa_level", "os.family", "isolation", "runtime.name",
                            "runtime.version", "wasi.preview", "component_model", "abi")


class CapabilityError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


@dataclass(frozen=True)
class Capability:
    name: str
    value: str
    layer: str
    provenance: str
    #: optional parameterised limits, e.g. {"max_memory_pages": 65536}
    params: tuple = ()

    @property
    def is_extension(self) -> bool:
        return self.name.startswith("x-")


def normalize(name: str, value: str) -> str:
    if value == UNKNOWN:
        return UNKNOWN
    if not isinstance(value, str) or not value or value != value.strip():
        raise CapabilityError("E_CAP_VALUE", f"{name}: invalid value")
    value = ALIASES.get(name, {}).get(value, value)
    if name in REGISTRY and value not in REGISTRY[name]:
        raise CapabilityError("E_CAP_UNKNOWN_CORE_VALUE", f"{name}={value!r} is not in the registry")
    return value


def capability(name: str, value: str, *, layer: str, provenance: str, **params) -> Capability:
    if layer not in LAYERS:
        raise CapabilityError("E_CAP_LAYER", layer)
    if provenance not in PROVENANCE_RANK:
        raise CapabilityError("E_CAP_PROVENANCE", provenance)
    if not name.startswith("x-") and name not in REGISTRY and name not in ("runtime.version", "wit.world", "wit.interface"):
        raise CapabilityError("E_CAP_UNKNOWN_FIELD", name)
    for k, v in params.items():
        if isinstance(v, bool) or not isinstance(v, (int, str)):
            raise CapabilityError("E_CAP_PARAM", f"{name}.{k}")
    return Capability(name, normalize(name, value), layer, provenance, tuple(sorted(params.items())))


@dataclass
class RuntimeProfile:
    capabilities: list = field(default_factory=list)
    model_version: str = MODEL_VERSION

    def __post_init__(self) -> None:
        single_valued = set(REGISTRY) | {"runtime.version", "wit.world"}
        seen: dict[str, str] = {}
        for cap in self.capabilities:
            if cap.name in single_valued:
                if cap.name in seen and seen[cap.name] != cap.value:
                    raise CapabilityError("E_CAP_CONTRADICTION",
                                          f"{cap.name} advertised as both {seen[cap.name]!r} and {cap.value!r}")
                seen[cap.name] = cap.value

    def get(self, name: str, *, min_provenance: Optional[str] = None) -> str:
        for cap in self.capabilities:
            if cap.name == name:
                if min_provenance and PROVENANCE_RANK[cap.provenance] < PROVENANCE_RANK[min_provenance]:
                    return UNKNOWN
                return cap.value
        return UNKNOWN

    def values(self, name: str) -> set:
        return {c.value for c in self.capabilities if c.name == name}

    def trusted_extensions(self, recognised: set) -> list:
        return [c for c in self.capabilities if c.is_extension and c.name in recognised]

    def identity(self, *, min_provenance: str = "attested") -> str:
        """Stable profile id over normalised fields at >= ``min_provenance``.

        Claimed/inferred facts never change the identity, so a caller cannot
        mint a new 'profile' by asserting capabilities.
        """
        body = {name: self.get(name, min_provenance=min_provenance) for name in CORE_FIELDS_FOR_IDENTITY}
        return "profile:" + digest({"model": self.model_version, "fields": body})[7:39]

    def migrate_missing(self, new_mandatory: list) -> "RuntimeProfile":
        """Schema growth: older profiles get explicit UNKNOWN for new mandatory fields (MC-17-09)."""
        have = {c.name for c in self.capabilities}
        extra = [Capability(n, UNKNOWN, "runtime", "claimed") for n in new_mandatory if n not in have]
        return RuntimeProfile(self.capabilities + extra, self.model_version)
