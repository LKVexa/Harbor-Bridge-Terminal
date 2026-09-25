"""Hardened, dependency-free sandbox policy model for INV-39.

This module deliberately does **not** claim to install kernel enforcement.  It
validates a requested policy, verifies an externally supplied read-back state,
and provides a bounded behavioural model used by the INV-39 component tests.
A production backend (seccomp/bubblewrap/Seatbelt) must supply the real applied
state; see ``MISSING_COMPONENTS.md``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import re
from typing import Any, Iterable

REQUIRED_NAMESPACES = frozenset({"pid", "mount", "net", "ipc", "uts", "user"})
FORBIDDEN_CAPABILITIES = frozenset(
    {
        "CAP_SYS_ADMIN",
        "CAP_SYS_MODULE",
        "CAP_SYS_PTRACE",
        "CAP_DAC_READ_SEARCH",
        "CAP_BPF",
    }
)
SYSCALL_BUDGET = 60
MAX_PROFILE_ITEMS = 4096
MAX_DENIAL_LOG = 1024
MAX_TOKEN_LENGTH = 128
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.:+-]+$")


class ProfileInvalid(PermissionError):
    """Raised when a sandbox profile may not be applied as written."""


class ProfileNotApplied(RuntimeError):
    """Raised when verified applied state is absent or differs from the request."""


class SandboxStateError(RuntimeError):
    """Raised when sandbox lifecycle methods are used out of order."""


def _normalise_tokens(
    values: Iterable[str], *, field_name: str, case: str | None = None
) -> frozenset[str]:
    """Return a bounded, canonical token set or raise ``ProfileInvalid``.

    Strings are rejected as iterables to avoid accidentally turning ``"read"``
    into ``{"r", "e", "a", "d"}``.  Whitespace and case tricks are normalised
    before policy checks so forbidden capabilities cannot be bypassed by casing.
    """
    if isinstance(values, (str, bytes)):
        raise ProfileInvalid(f"{field_name} must be an iterable of tokens, not a string")
    try:
        raw = list(values)
    except TypeError as exc:
        raise ProfileInvalid(f"{field_name} must be iterable") from exc
    if len(raw) > MAX_PROFILE_ITEMS:
        raise ProfileInvalid(
            f"{field_name} has {len(raw)} entries; maximum is {MAX_PROFILE_ITEMS}"
        )
    out: set[str] = set()
    for value in raw:
        if not isinstance(value, str):
            raise ProfileInvalid(f"{field_name} contains non-string token: {value!r}")
        token = value.strip()
        if not token:
            raise ProfileInvalid(f"{field_name} contains an empty token")
        if len(token) > MAX_TOKEN_LENGTH or not _TOKEN_RE.fullmatch(token):
            raise ProfileInvalid(f"{field_name} contains invalid token: {value!r}")
        if case == "upper":
            token = token.upper()
        elif case == "lower":
            token = token.lower()
        out.add(token)
    return frozenset(out)


@dataclass(frozen=True)
class SandboxProfile:
    """A canonical, default-deny process sandbox policy request."""

    name: str
    syscalls: frozenset[str]
    capabilities: frozenset[str] = frozenset()
    namespaces: frozenset[str] = REQUIRED_NAMESPACES

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ProfileInvalid("profile name must be a non-empty string")
        name = self.name.strip()
        if len(name) > MAX_TOKEN_LENGTH or not _TOKEN_RE.fullmatch(name):
            raise ProfileInvalid(f"invalid profile name: {self.name!r}")
        object.__setattr__(self, "name", name)
        object.__setattr__(
            self, "syscalls", _normalise_tokens(self.syscalls, field_name="syscalls", case="lower")
        )
        object.__setattr__(
            self,
            "capabilities",
            _normalise_tokens(self.capabilities, field_name="capabilities", case="upper"),
        )
        object.__setattr__(
            self,
            "namespaces",
            _normalise_tokens(self.namespaces, field_name="namespaces", case="lower"),
        )

    def validate(self) -> list[str]:
        defects: list[str] = []
        forbidden = self.capabilities & FORBIDDEN_CAPABILITIES
        if forbidden:
            defects.append(f"forbidden capabilities retained: {sorted(forbidden)}")
        missing = REQUIRED_NAMESPACES - self.namespaces
        if missing:
            defects.append(f"required namespaces omitted: {sorted(missing)}")
        return defects

    @property
    def digest(self) -> str:
        payload = {
            "schema": "PK_SANDBOX_PROFILE/1",
            "name": self.name,
            "syscalls": sorted(self.syscalls),
            "capabilities": sorted(self.capabilities),
            "namespaces": sorted(self.namespaces),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return "sha256:" + sha256(canonical).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "PK_SANDBOX_PROFILE/1",
            "name": self.name,
            "syscalls": sorted(self.syscalls),
            "capabilities": sorted(self.capabilities),
            "namespaces": sorted(self.namespaces),
            "digest": self.digest,
        }


@dataclass
class Sandbox:
    """Verified policy state for one process.

    ``start`` is intentionally verification-only.  It requires a read-back from
    an external enforcer and fails closed when none is supplied.  That prevents
    the old behaviour where the requested policy was silently treated as if it
    had been applied by the kernel.
    """

    process: str
    profile: SandboxProfile
    applied_syscalls: frozenset[str] = frozenset()
    applied_capabilities: frozenset[str] = frozenset()
    applied_namespaces: frozenset[str] = frozenset()
    denials: list[str] = field(default_factory=list)
    denials_dropped: int = 0
    _started: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.process, str) or not self.process.strip():
            raise ProfileInvalid("process identifier must be a non-empty string")
        self.process = self.process.strip()
        if len(self.process) > MAX_TOKEN_LENGTH:
            raise ProfileInvalid("process identifier is too long")

    def requested_state(self) -> dict[str, frozenset[str]]:
        """Return the exact state an OS backend must apply and read back."""
        return {
            "syscalls": self.profile.syscalls,
            "capabilities": self.profile.capabilities,
            "namespaces": self.profile.namespaces,
        }

    @staticmethod
    def _read_set(state: dict[str, Any], key: str, *, case: str | None = None) -> frozenset[str]:
        if key not in state:
            raise ProfileNotApplied(f"read-back is missing required field: {key}")
        try:
            return _normalise_tokens(state[key], field_name=f"readback.{key}", case=case)
        except ProfileInvalid as exc:
            raise ProfileNotApplied(str(exc)) from exc

    def start(self, *, readback: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._started:
            raise SandboxStateError(f"{self.process}: sandbox has already been verified as started")
        defects = self.profile.validate()
        if defects:
            raise ProfileInvalid(f"{self.profile.name}: {'; '.join(defects)}")
        if readback is None:
            raise ProfileNotApplied(
                f"{self.process}: no applied-state read-back supplied; refusing to claim enforcement"
            )
        if not isinstance(readback, dict):
            raise ProfileNotApplied(f"{self.process}: applied-state read-back must be a mapping")

        applied_syscalls = self._read_set(readback, "syscalls", case="lower")
        applied_capabilities = self._read_set(readback, "capabilities", case="upper")
        applied_namespaces = self._read_set(readback, "namespaces", case="lower")

        if (
            applied_syscalls != self.profile.syscalls
            or applied_capabilities != self.profile.capabilities
            or applied_namespaces != self.profile.namespaces
        ):
            raise ProfileNotApplied(
                f"{self.process}: applied state differs from the requested profile"
            )
        # Publish applied state only after the entire read-back has been verified.
        self.applied_syscalls = applied_syscalls
        self.applied_capabilities = applied_capabilities
        self.applied_namespaces = applied_namespaces
        self._started = True
        return {
            "schema": "PK_SANDBOX_APPLIED/1",
            "process": self.process,
            "profile": self.profile.name,
            "profile_digest": self.profile.digest,
            "verified": True,
            "verification_scope": "readback_matches_profile",
            "evidence_source": "caller_supplied",
            "os_enforcement_proven": False,
            "default_deny": True,
            "residual_syscalls": len(self.applied_syscalls),
            "within_budget": len(self.applied_syscalls) <= SYSCALL_BUDGET,
            "capabilities_retained": sorted(self.applied_capabilities),
            "namespaces": sorted(self.applied_namespaces),
            "shares_kernel": True,
            "isolation_note": (
                "process-level only: a kernel bug reached through any of the "
                f"{len(self.applied_syscalls)} allowed syscalls defeats this tier"
            ),
        }

    def call(self, syscall: str) -> bool:
        """Model default-deny behavior with a bounded denial log."""
        if not self._started:
            raise SandboxStateError(f"{self.process}: sandbox has not been verified as started")
        token_set = _normalise_tokens([syscall], field_name="syscall", case="lower")
        token = next(iter(token_set))
        if token not in self.applied_syscalls:
            if len(self.denials) < MAX_DENIAL_LOG:
                self.denials.append(token)
            else:
                self.denials_dropped += 1
            return False
        return True
