"""Deterministic hypervisor + guest emulator for CI fault scenarios (MC-005, MC-038).

SPDX-License-Identifier: NOASSERTION

It is NOT a hypervisor and its results are never production evidence.  It
implements the same adapter contract so the reconciler can be driven through
timeouts, lost acknowledgements, partial presentation, hypervisor restart and
stale observation deterministically.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .base import (AdapterError, AdapterErrorCode, EnsureRequest, EnsureResult, FenceRegistry,
                   LiveCpuState, Outcome, validate_request)


@dataclass
class FaultPlan:
    """Faults consumed in order; each entry applies to the next ensure call."""
    queue: list[str] = field(default_factory=list)
    # "timeout_before" -> nothing done, UNKNOWN; "timeout_after" -> action done, UNKNOWN
    # "partial:<n>" -> only n vCPUs presented; "backend_error" -> FAILED retryable
    # "restart" -> hypervisor restarts, keeps present count (hot-added CPUs persist)

    def next(self) -> str | None:
        return self.queue.pop(0) if self.queue else None


class EmulatedHypervisor:
    name = "emulator"
    version = "1.0.0"

    def __init__(self, vms: dict[str, tuple[int, int]], faults: FaultPlan | None = None,
                 guest_online_lag: int = 0) -> None:
        self.present: dict[str, int] = {k: v[0] for k, v in vms.items()}
        self.max: dict[str, int] = {k: v[1] for k, v in vms.items()}
        self.guest_online: dict[str, int] = dict(self.present)
        self.faults = faults or FaultPlan()
        self.guest_online_lag = guest_online_lag
        self.calls: list[dict[str, Any]] = []
        self.hotadd_actions = 0
        self._fences = FenceRegistry()
        self.restarts = 0

    def capabilities(self, vm_id: str) -> dict[str, Any]:
        self._vm(vm_id)
        return {"adapter": self.name, "acpi_cpu_hotplug": True, "hot_unplug_exposed": False,
                "max_vcpus": self.max[vm_id]}

    def _vm(self, vm_id: str) -> None:
        if vm_id not in self.present:
            raise AdapterError(AdapterErrorCode.NOT_FOUND, "unknown VM")

    def read_live(self, vm_id: str) -> LiveCpuState:
        self._vm(vm_id)
        return LiveCpuState(vm_id, self.present[vm_id], self.max[vm_id], "emulator", time.monotonic())

    def guest_tick(self, vm_id: str) -> int:
        """Guest onlines presented CPUs, lagging by ``guest_online_lag``."""
        target = max(self.guest_online[vm_id], self.present[vm_id] - self.guest_online_lag)
        self.guest_online[vm_id] = target
        return target

    def ensure_vcpus(self, req: EnsureRequest) -> EnsureResult:
        validate_request(req)
        self._vm(req.vm_id)
        self._fences.check_and_advance(req.vm_id, req.fence_token)
        self.calls.append({"op": req.operation_id, "target": req.target_vcpus, "fence": req.fence_token})
        before = self.present[req.vm_id]
        if req.target_vcpus > self.max[req.vm_id]:
            return EnsureResult(Outcome.FAILED, req.vm_id, req.operation_id, req.target_vcpus, before, before,
                                error_code=AdapterErrorCode.OVER_MAX.value)
        if req.target_vcpus < before:
            return EnsureResult(Outcome.FAILED, req.vm_id, req.operation_id, req.target_vcpus, before, before,
                                error_code=AdapterErrorCode.SHRINK_REFUSED.value)
        if req.target_vcpus == before:
            return EnsureResult(Outcome.NOOP, req.vm_id, req.operation_id, req.target_vcpus, before, before)
        fault = self.faults.next()
        if fault == "timeout_before":
            return EnsureResult(Outcome.UNKNOWN, req.vm_id, req.operation_id, req.target_vcpus, before, None,
                                error_code=AdapterErrorCode.TIMEOUT.value, retryable=True)
        if fault == "backend_error":
            return EnsureResult(Outcome.FAILED, req.vm_id, req.operation_id, req.target_vcpus, before, before,
                                error_code=AdapterErrorCode.BACKEND.value, retryable=True)
        self.hotadd_actions += 1
        if fault and fault.startswith("partial:"):
            self.present[req.vm_id] = max(before, min(req.target_vcpus, int(fault.split(":")[1])))
            return EnsureResult(Outcome.PARTIAL, req.vm_id, req.operation_id, req.target_vcpus, before,
                                self.present[req.vm_id], f"emu-{len(self.calls)}")
        self.present[req.vm_id] = req.target_vcpus
        if fault == "timeout_after":
            return EnsureResult(Outcome.UNKNOWN, req.vm_id, req.operation_id, req.target_vcpus, before, None,
                                f"emu-{len(self.calls)}", AdapterErrorCode.TIMEOUT.value, retryable=True)
        if fault == "restart":
            self.restarts += 1
            self._fences = FenceRegistry()   # restarted process forgets fences; state reconciliation must cover it
        return EnsureResult(Outcome.ACKNOWLEDGED, req.vm_id, req.operation_id, req.target_vcpus, before,
                            self.present[req.vm_id], f"emu-{len(self.calls)}")
