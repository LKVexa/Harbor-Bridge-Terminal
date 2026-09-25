"""Dependency-free reference model for INV-45 software fault isolation.

This module models the security invariants exercised by the INV-45 component.  It
is deliberately dependency-free so the core checks can be tested even when the
external ``pk_core`` orchestration package is not installed.

It is a reference/verifier model, not a native-code rewriter or a process
security boundary.  A production SFI implementation still needs a trusted
rewriter/validator and loader at the machine-code or Wasm layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any

MODULE_SCHEMA = "PK_SFI_MODULE/1"
MASK_SCHEMA = "PK_SFI_MASK/1"


def _plain_int(value: object) -> bool:
    """Return True for ordinary integer values but not bools."""
    return isinstance(value, int) and not isinstance(value, bool)


class SfiSecurityError(PermissionError):
    """Base class for fail-closed SFI policy violations."""

    code = "SFI_SECURITY_ERROR"

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.details = dict(details)

    def as_dict(self) -> dict[str, Any]:
        """Return a stable, machine-readable error representation."""
        return {"code": self.code, "message": str(self), "details": dict(self.details)}


class UnmaskedAccess(SfiSecurityError):
    """Raised when a module contains a memory access that was not rewritten."""

    code = "SFI_UNMASKED_ACCESS"


class ModuleNotVerified(UnmaskedAccess):
    """Raised when execution is attempted without a current verification seal."""

    code = "SFI_NOT_VERIFIED"


class BranchOutsideTargets(SfiSecurityError):
    """Raised when an indirect branch would leave the permitted target set."""

    code = "SFI_BRANCH_OUTSIDE_TARGETS"


@dataclass(frozen=True)
class Access:
    """One memory access in a module, and whether the rewriter masked it."""

    offset: int
    masked: bool

    def __post_init__(self) -> None:
        if not _plain_int(self.offset) or self.offset < 0:
            raise ValueError("access offset must be a non-negative integer")
        if type(self.masked) is not bool:
            raise TypeError("access masked flag must be bool")


@dataclass(frozen=True)
class SandboxRegion:
    """An immutable power-of-two sandbox region."""

    base: int
    size: int

    def __post_init__(self) -> None:
        if not _plain_int(self.base) or self.base < 0:
            raise ValueError("region base must be a non-negative integer")
        if not _plain_int(self.size) or self.size <= 0:
            raise ValueError("region size must be a positive integer")
        if self.size & (self.size - 1):
            raise ValueError(f"region size {self.size} must be a positive power of two")

    @property
    def mask(self) -> int:
        return self.size - 1

    def confine(self, address: int) -> int:
        """Map any integer address into this region using low-bit masking."""
        if not _plain_int(address):
            raise TypeError("address must be an integer")
        return self.base + (address & self.mask)

    def contains(self, address: int) -> bool:
        if not _plain_int(address):
            return False
        return self.base <= address < self.base + self.size


@dataclass
class SfiModule:
    """A module confined by masking and gated by a verification seal.

    Security-sensitive input collections are copied into immutable containers at
    construction/verification time.  A successful verification seals the exact
    region, access manifest, and indirect-target policy.  Replacing any of those
    values invalidates the seal and execution fails closed until re-verification.
    """

    name: str
    region: SandboxRegion
    accesses: tuple[Access, ...]
    indirect_targets: frozenset[int]
    overhead_percent: float = 0.0
    _verified_snapshot: tuple[SandboxRegion, tuple[Access, ...], frozenset[int]] | None = field(
        default=None, init=False, repr=False
    )

    def __post_init__(self) -> None:
        self._normalise_security_state()
        self._validate_metadata()

    @property
    def verified(self) -> bool:
        """Whether the current security-sensitive state matches the verified seal."""
        return self._verified_snapshot is not None and self._verified_snapshot == self._snapshot()

    def _invalidate(self) -> None:
        self._verified_snapshot = None

    def _normalise_security_state(self) -> None:
        """Copy caller-owned collections so later external mutation cannot widen policy."""
        try:
            self.accesses = tuple(self.accesses)
        except TypeError as exc:
            raise TypeError("accesses must be an iterable of Access objects") from exc
        try:
            self.indirect_targets = frozenset(self.indirect_targets)
        except TypeError as exc:
            raise TypeError("indirect_targets must be an iterable of integers") from exc
        self._validate_security_state()

    def _validate_security_state(self) -> None:
        if type(self.region) is not SandboxRegion:
            raise TypeError("region must be a SandboxRegion")
        if type(self.accesses) is not tuple or any(type(a) is not Access for a in self.accesses):
            raise TypeError("accesses must contain only Access objects")
        if type(self.indirect_targets) is not frozenset:
            raise TypeError("indirect_targets must be a frozenset after normalization")
        if any(not _plain_int(target) or target < 0 for target in self.indirect_targets):
            raise ValueError("indirect branch targets must be non-negative integers")

    def _validate_metadata(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("module name must be a non-empty string")
        if isinstance(self.overhead_percent, bool) or not isinstance(self.overhead_percent, (int, float)):
            raise TypeError("overhead_percent must be a finite non-negative number")
        if not isfinite(float(self.overhead_percent)) or self.overhead_percent < 0:
            raise ValueError("overhead_percent must be a finite non-negative number")

    def _snapshot(self) -> tuple[SandboxRegion, tuple[Access, ...], frozenset[int]]:
        return self.region, self.accesses, self.indirect_targets

    def verify(self) -> dict[str, Any]:
        """Verify the complete access manifest and seal the current security policy."""
        # A failed re-verification must never leave an older successful seal active.
        self._invalidate()
        self._normalise_security_state()
        self._validate_metadata()

        unmasked = [a.offset for a in self.accesses if not a.masked]
        if unmasked:
            raise UnmaskedAccess(
                f"{self.name}: {len(unmasked)} unmasked access(es) at offsets {unmasked[:5]}",
                module=self.name,
                unmasked_count=len(unmasked),
                sample_offsets=unmasked[:5],
            )

        self._verified_snapshot = self._snapshot()
        return {
            "schema": MODULE_SCHEMA,
            "module": self.name,
            "accesses": len(self.accesses),
            "all_masked": True,
            "region": {"base": self.region.base, "size": self.region.size},
            "permitted_targets": len(self.indirect_targets),
            "overhead_percent": float(self.overhead_percent),
        }

    def _require_verified(self) -> None:
        try:
            self._validate_security_state()
        except (TypeError, ValueError) as exc:
            raise ModuleNotVerified(
                f"{self.name}: security state is invalid and must be re-verified",
                module=self.name,
            ) from exc
        if not self.verified:
            raise ModuleNotVerified(
                f"{self.name}: module was not verified for its current security state",
                module=self.name,
            )

    def access(self, address: int) -> dict[str, Any]:
        self._require_verified()
        confined = self.region.confine(address)
        return {
            "schema": MASK_SCHEMA,
            "requested": address,
            "effective": confined,
            "inside_region": self.region.contains(confined),
        }

    def branch(self, target: int) -> int:
        self._require_verified()
        if not _plain_int(target) or target not in self.indirect_targets:
            raise BranchOutsideTargets(
                f"{self.name}: indirect branch to {target!r} is outside the permitted target set",
                module=self.name,
                target=repr(target),
            )
        return target
