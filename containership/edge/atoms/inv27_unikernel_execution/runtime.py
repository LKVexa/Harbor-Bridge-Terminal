"""Runtime seal-verification primitives for INV-27.

This module intentionally has no ``pk_core`` dependency so the security-critical
admission logic can be unit-tested in isolation.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import AbstractSet, Mapping

DISQUALIFYING = frozenset({"fork", "exec", "dlopen", "ptrace", "shell"})


class SealInvalid(PermissionError):
    """Raised when an image is not genuinely sealed."""


def _nonempty_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SealInvalid(f"{field} must be a non-empty string")
    return value.strip()


def _name_set(value: object, field: str) -> frozenset[str]:
    if not isinstance(value, (set, frozenset)):
        raise SealInvalid(f"{field} must be a set of names, got {type(value).__name__}")
    normalized: set[str] = set()
    for entry in value:
        if not isinstance(entry, str) or not entry.strip():
            raise SealInvalid(f"{field} entries must be non-empty strings")
        normalized.add(entry.strip())
    return frozenset(normalized)


@dataclass(frozen=True, slots=True)
class UnikernelImage:
    """A unikernel image and the seal it claims."""

    name: str
    toolchain: str
    architecture: str
    declared_syscalls: frozenset[str]
    linked_syscalls: frozenset[str]
    features: frozenset[str] = frozenset()
    single_address_space: bool = True


def verify_seal(
    image: UnikernelImage,
    *,
    permitted: AbstractSet[str],
    architecture: str,
) -> Mapping[str, object]:
    """Verify a seal against binary-observed facts and return immutable evidence.

    Admission is deliberately fail-closed: malformed metadata is rejected before
    set operations, feature comparisons are case-insensitive, and callers cannot
    mutate the returned seal record after admission.
    """
    if not isinstance(image, UnikernelImage):
        raise TypeError("image must be an UnikernelImage")

    image_name = _nonempty_text(image.name, "image.name")
    toolchain = _nonempty_text(image.toolchain, "image.toolchain")
    image_arch = _nonempty_text(image.architecture, "image.architecture")
    site_arch = _nonempty_text(architecture, "architecture")
    declared = _name_set(image.declared_syscalls, "declared_syscalls")
    linked = _name_set(image.linked_syscalls, "linked_syscalls")
    features = _name_set(image.features, "features")
    permitted_names = _name_set(permitted, "permitted")

    if type(image.single_address_space) is not bool:
        raise SealInvalid("single_address_space must be a boolean")
    if not image.single_address_space:
        raise SealInvalid(f"{image_name}: image is not single-address-space")

    disqualifying = {feature.casefold() for feature in features} & DISQUALIFYING
    if disqualifying:
        raise SealInvalid(
            f"{image_name}: image supports {sorted(disqualifying)}, which breaks the seal"
        )

    drift = linked ^ declared
    if drift:
        raise SealInvalid(
            f"{image_name}: syscall manifest drifts from the binary: {sorted(drift)}"
        )

    outside = linked - permitted_names
    if outside:
        raise SealInvalid(
            f"{image_name}: syscalls outside the environment's permitted set: {sorted(outside)}"
        )

    if image_arch != site_arch:
        raise SealInvalid(f"{image_name}: built for {image_arch}, site runs {site_arch}")

    # MappingProxyType prevents post-admission mutation of the evidence attached
    # to a running instance. Lists are avoided so nested values remain immutable.
    return MappingProxyType(
        {
            "schema": "PK_UNIKERNEL_IMAGE/1",
            "image": image_name,
            "toolchain": toolchain,
            "architecture": image_arch,
            "sealed": True,
            "syscalls": tuple(sorted(linked)),
            "syscall_count": len(linked),
        }
    )


@dataclass(slots=True)
class UnikernelInstance:
    name: str
    tenant: str
    seal: Mapping[str, object]
    state: str = "running"

    def stop(self) -> str:
        """Stop an instance idempotently."""
        if self.state not in {"running", "stopped"}:
            raise RuntimeError(f"cannot stop instance in invalid state {self.state!r}")
        self.state = "stopped"
        return self.state


def run(
    image: UnikernelImage,
    *,
    tenant: str,
    permitted: AbstractSet[str],
    architecture: str,
) -> UnikernelInstance:
    tenant_name = _nonempty_text(tenant, "tenant")
    seal = verify_seal(image, permitted=permitted, architecture=architecture)
    return UnikernelInstance(str(seal["image"]), tenant_name, seal)
