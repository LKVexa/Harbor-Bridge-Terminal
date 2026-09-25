"""Dependency-free capability semantics for INV-30.

This module is intentionally independent of ``pk_core`` so the security-critical
bounds, attenuation, and invalidation rules can be tested even when the wider
Post-Kubernetes framework is not installed.

It is a semantic model, not a replacement for CHERI hardware enforcement.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Iterable

ACCESS_SCHEMA = "PK_CAPABILITY_ACCESS/1"
CAPABILITY_SCHEMA = "PK_CAPABILITY/1"
PERMISSIONS: FrozenSet[str] = frozenset({"read", "write", "execute"})


class CapabilityError(PermissionError):
    """Base class for capability policy refusals with a stable machine code."""

    code = "CAPABILITY_ERROR"

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self)}


class BoundsViolation(CapabilityError):
    """Raised when an access falls outside a capability's bounds."""

    code = "BOUNDS_VIOLATION"


class PermissionViolation(CapabilityError):
    """Raised when an operation needs a permission the capability does not carry."""

    code = "PERMISSION_VIOLATION"


class Amplification(CapabilityError):
    """Raised when a derivation would widen bounds or permissions."""

    code = "AMPLIFICATION"


class Invalidated(CapabilityError):
    """Raised when an invalidated capability is used or resurrected."""

    code = "INVALIDATED"


def _require_int(name: str, value: object) -> int:
    """Require an actual integer, rejecting bool (a subclass of int in Python)."""
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer")
    return value


def _normalise_permissions(value: Iterable[str]) -> FrozenSet[str]:
    if isinstance(value, (str, bytes, bytearray)):
        raise TypeError("permissions must be a collection of permission names, not a string/bytes value")
    try:
        permissions = frozenset(value)
    except TypeError as exc:
        raise TypeError("permissions must be an iterable of permission names") from exc
    if not all(isinstance(item, str) for item in permissions):
        raise TypeError("every permission must be a string")
    unknown = permissions - PERMISSIONS
    if unknown:
        raise ValueError(f"unknown permissions: {sorted(unknown)}")
    return permissions


@dataclass
class Capability:
    """A CHERI-shaped memory capability with attenuation-only derivation.

    Bounds and permissions become immutable after construction. Validity may
    transition only from ``True`` to ``False``. The public constructor models a
    capability already minted by a trusted authority; this Python object itself
    is not an unforgeable hardware token.
    """

    base: int
    length: int
    permissions: FrozenSet[str]
    valid: bool = True

    def __post_init__(self) -> None:
        base = _require_int("base", self.base)
        length = _require_int("length", self.length)
        if base < 0:
            raise ValueError("capability base may not be negative")
        if length < 0:
            raise ValueError("capability length may not be negative")
        if type(self.valid) is not bool:
            raise TypeError("valid must be a boolean")
        object.__setattr__(self, "base", base)
        object.__setattr__(self, "length", length)
        object.__setattr__(self, "permissions", _normalise_permissions(self.permissions))
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            if name in ("base", "length", "permissions"):
                raise Amplification(f"capability {name} is immutable once minted")
            if name == "valid":
                if type(value) is not bool:
                    raise TypeError("valid must be a boolean")
                if value and not self.valid:
                    raise Invalidated("an invalidated capability cannot be made valid again")
        object.__setattr__(self, name, value)

    @property
    def limit(self) -> int:
        return self.base + self.length

    def derive(
        self,
        *,
        base: int,
        length: int,
        permissions: Iterable[str] | None = None,
    ) -> "Capability":
        """Derive a capability that is no broader than this capability."""
        if not self.valid:
            raise Invalidated("cannot derive from an invalidated capability")
        base = _require_int("base", base)
        length = _require_int("length", length)
        if length < 0:
            raise Amplification(f"derived length {length} is negative")
        perms = self.permissions if permissions is None else _normalise_permissions(permissions)
        if base < self.base or base + length > self.limit:
            raise Amplification(
                f"derived bounds [{base}, {base + length}) escape [{self.base}, {self.limit})"
            )
        if not perms <= self.permissions:
            raise Amplification(
                f"derived permissions {sorted(perms - self.permissions)} exceed the held set"
            )
        return Capability(base, length, perms)

    def check(self, *, address: int, size: int, operation: str) -> dict[str, object]:
        """Validate one access and return a versioned success record."""
        if not self.valid:
            raise Invalidated("capability has been invalidated")
        address = _require_int("address", address)
        size = _require_int("size", size)
        if not isinstance(operation, str):
            raise TypeError("operation must be a string")
        if operation not in self.permissions:
            raise PermissionViolation(
                f"{operation!r} not permitted by this capability ({sorted(self.permissions)})"
            )
        if size <= 0 or address < self.base or address + size > self.limit:
            raise BoundsViolation(
                f"access [{address}, {address + size}) escapes [{self.base}, {self.limit})"
            )
        return {
            "schema": ACCESS_SCHEMA,
            "address": address,
            "size": size,
            "operation": operation,
            "permitted": True,
        }

    def invalidate(self) -> None:
        """Permanently invalidate this model capability."""
        self.valid = False
