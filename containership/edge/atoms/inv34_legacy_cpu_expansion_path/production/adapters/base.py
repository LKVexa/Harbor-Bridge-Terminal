"""Hypervisor CPU hot-add adapter contract (MC-005, MC-013).

SPDX-License-Identifier: NOASSERTION

An adapter translates an accepted desired vCPU count into the hypervisor's
documented ACPI CPU hot-add primitive.  The contract is hot-add only: an
adapter MUST refuse any call whose target is below the live count, and no
adapter in this package exposes a shrink primitive.

Outcomes are deliberately five-valued.  ``UNKNOWN`` exists because a timeout
or a dropped connection does not tell us whether the hypervisor acted; the
reconciler must re-read live state before it may retry.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Protocol

ADAPTER_CONTRACT = "INV34_HOTPLUG_ADAPTER/1"


class Outcome(str, Enum):
    NOOP = "noop"                    # already at (or above) target
    SUBMITTED = "submitted"          # request sent, hypervisor acknowledged receipt only
    ACKNOWLEDGED = "acknowledged"    # hypervisor reports the vCPUs were presented
    PARTIAL = "partial"              # some but not all vCPUs presented
    FAILED = "failed"                # hypervisor definitively refused; nothing changed
    UNKNOWN = "unknown"              # ambiguous: timeout / transport loss / cancel


class AdapterErrorCode(str, Enum):
    UNSUPPORTED = "ADAPTER_UNSUPPORTED"
    SHRINK_REFUSED = "ADAPTER_SHRINK_REFUSED"
    OVER_MAX = "ADAPTER_OVER_MAX"
    STALE_FENCE = "ADAPTER_STALE_FENCE"
    TIMEOUT = "ADAPTER_TIMEOUT"
    TRANSPORT = "ADAPTER_TRANSPORT"
    BACKEND = "ADAPTER_BACKEND"
    NOT_FOUND = "ADAPTER_VM_NOT_FOUND"
    DEADLINE = "ADAPTER_DEADLINE_EXCEEDED"
    RATE_LIMITED = "ADAPTER_RATE_LIMITED"


RETRYABLE_CODES = frozenset({AdapterErrorCode.TIMEOUT, AdapterErrorCode.TRANSPORT,
                             AdapterErrorCode.RATE_LIMITED, AdapterErrorCode.BACKEND})


@dataclass(frozen=True)
class LiveCpuState:
    """What the hypervisor itself reports right now."""
    vm_id: str
    present_vcpus: int
    max_vcpus: int
    source: str
    read_at: float


@dataclass(frozen=True)
class EnsureRequest:
    vm_id: str
    target_vcpus: int
    generation: int
    operation_id: str
    fence_token: int
    deadline: float                  # absolute monotonic-clock deadline
    trace_id: str = ""
    request_id: str = ""

    def remaining(self, now: float | None = None) -> float:
        return self.deadline - (time.monotonic() if now is None else now)


@dataclass(frozen=True)
class EnsureResult:
    outcome: Outcome
    vm_id: str
    operation_id: str
    target_vcpus: int
    present_before: int | None
    present_after: int | None
    backend_operation_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False
    contract: str = ADAPTER_CONTRACT
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["outcome"] = self.outcome.value
        return d


class AdapterError(RuntimeError):
    def __init__(self, code: AdapterErrorCode, message: str, **ctx: Any) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = code in RETRYABLE_CODES
        self.context = ctx


class HotplugAdapter(Protocol):
    name: str
    version: str

    def capabilities(self, vm_id: str) -> dict[str, Any]: ...
    def read_live(self, vm_id: str) -> LiveCpuState: ...
    def ensure_vcpus(self, req: EnsureRequest) -> EnsureResult: ...


class FenceRegistry:
    """Per-VM highest fence token seen by an adapter instance.

    A controller that lost its lease holds an older token; the adapter refuses
    it before any side effect, so a stale writer cannot repeat or supersede a
    newer operation (MC-005 fencing, MC-021/024)."""

    def __init__(self) -> None:
        self._seen: dict[str, int] = {}

    def check_and_advance(self, vm_id: str, token: int) -> None:
        if isinstance(token, bool) or not isinstance(token, int) or token < 1:
            raise AdapterError(AdapterErrorCode.STALE_FENCE, "fence token must be a positive integer")
        last = self._seen.get(vm_id, 0)
        if token < last:
            raise AdapterError(AdapterErrorCode.STALE_FENCE,
                               f"fence token {token} is older than {last}", vm_id=vm_id)
        self._seen[vm_id] = token


def validate_request(req: EnsureRequest) -> None:
    from ..validation import require_identifier, require_int
    require_identifier(req.vm_id, "vm_id")
    require_identifier(req.operation_id, "operation_id")
    require_int(req.target_vcpus, "target_vcpus", minimum=1, maximum=65_536)
    require_int(req.generation, "generation", minimum=0)
    require_int(req.fence_token, "fence_token", minimum=1)
    if req.remaining() <= 0:
        raise AdapterError(AdapterErrorCode.DEADLINE, "deadline already passed before side effect")
