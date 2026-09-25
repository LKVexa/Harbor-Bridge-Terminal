"""Probe backend protocol and immutable result model (MC-03).

Classification rules (authoritative):

* ``usable``           -- positive evidence that the OS virtualization facility can be
                          opened/used by this process (e.g. /dev/kvm opened and
                          KVM_GET_API_VERSION == 12; WHvGetCapability reports the
                          hypervisor present; kern.hv_support == 1).  Never inferred from
                          the absence of an error.
* ``present-disabled`` -- CPU capability seen, but firmware, permission, kernel or a
                          conflicting hypervisor prevents use.
* ``absent``           -- positive evidence the CPU lacks the extension.
* ``indeterminate``    -- the probe could not decide (unsupported platform or
                          architecture, malformed evidence, timeout, unexpected error).
                          Introduced by PK_VIRT_PRIMITIVE/2; never treated as usable.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable

USABLE = "usable"
PRESENT_DISABLED = "present-disabled"
ABSENT = "absent"
INDETERMINATE = "indeterminate"
STATES = (USABLE, PRESENT_DISABLED, ABSENT, INDETERMINATE)

# Stable reason codes (bounded set; also the only telemetry label values allowed).
REASONS = (
    "ok",
    "unsupported_platform",
    "unsupported_architecture",
    "permission_denied",
    "kernel_api_unavailable",
    "device_absent",
    "device_busy",
    "firmware_disabled",
    "capability_absent",
    "conflicting_hypervisor",
    "transient_io_failure",
    "malformed_probe_response",
    "probe_timeout",
    "backend_error",
)


class ProbeError(Exception):
    """Structured probe failure; ``reason`` is one of ``REASONS``."""

    def __init__(self, reason: str, detail: str = "") -> None:
        if reason not in REASONS:
            raise ValueError(f"unknown probe reason {reason!r}")
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class ProbeResult:
    host: str
    backend: str
    backend_version: str
    platform: str
    architecture: str
    state: str
    reason: str
    cpu_vendor: Optional[str] = None
    cpu_capable: Optional[bool] = None  # VMX/SVM (or HVF-capable CPU) seen
    slat: Optional[bool] = None  # EPT / NPT seen
    firmware_enabled: Optional[bool] = None
    facility_usable: bool = False  # positive open/use evidence
    virtualized: Optional[bool] = None  # running as a guest?
    nesting_depth: Optional[int] = None  # None = unknown (never fabricated)
    nested_enabled: Optional[bool] = None  # host allows nested guests (KVM param)
    evidence: Mapping[str, Any] = field(default_factory=dict)
    probed_at: float = field(default_factory=time.time)  # wall clock, audit only
    probe_ns: int = 0  # monotonic duration

    def __post_init__(self) -> None:
        if self.state not in STATES:
            raise ValueError(f"invalid state {self.state!r}")
        if self.reason not in REASONS:
            raise ValueError(f"invalid reason {self.reason!r}")
        if self.state == USABLE and not self.facility_usable:
            raise ValueError("usable requires positive facility evidence")
        if self.state == USABLE and self.reason != "ok":
            raise ValueError("usable must carry reason 'ok'")
        if self.nesting_depth is not None and (type(self.nesting_depth) is not int or self.nesting_depth < 0):
            raise ValueError("nesting_depth must be None or a non-negative int")
        if self.virtualized and self.nesting_depth == 0:
            raise ValueError("a virtualized host cannot report nesting depth 0")

    @property
    def bare_metal(self) -> Optional[bool]:
        if self.virtualized is None:
            return None
        return (not self.virtualized) and self.nesting_depth == 0

    def to_report(self) -> dict:
        """Serialise as PK_VIRT_PRIMITIVE/2 (see schemas/)."""
        return {
            "schema": "PK_VIRT_PRIMITIVE/2",
            "host": self.host,
            "state": self.state,
            "reason": self.reason,
            "nesting_depth": self.nesting_depth,
            "bare_metal": bool(self.bare_metal) and self.state == USABLE,
            "virtualized": self.virtualized,
            "backend": self.backend,
            "backend_version": self.backend_version,
            "platform": self.platform,
            "architecture": self.architecture,
            "probed_at": round(self.probed_at, 6),
            "capability": {
                "cpu_vendor": self.cpu_vendor,
                "cpu_capable": self.cpu_capable,
                "slat": self.slat,
                "firmware_enabled": self.firmware_enabled,
                "nested_enabled": self.nested_enabled,
            },
            "evidence": dict(self.evidence),
        }


@runtime_checkable
class VirtualizationProbeBackend(Protocol):
    name: str
    version: str

    def supports(self, platform: str, architecture: str) -> bool: ...

    def probe(self, host: str) -> ProbeResult: ...
