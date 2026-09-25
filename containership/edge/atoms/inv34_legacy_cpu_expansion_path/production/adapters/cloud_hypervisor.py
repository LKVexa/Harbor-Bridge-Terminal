"""Cloud Hypervisor REST adapter (MC-005, MC-007).

SPDX-License-Identifier: NOASSERTION

Pattern source (no code copied): the yard car ``cloud-hypervisor``,
``vmm/src/api/openapi/cloud-hypervisor.yaml`` (``PUT /vm.resize`` with
``VmResize.desired_vcpus``; ``GET /vm.info`` returning ``config.cpus``) and
``vmm/src/cpu.rs`` (ACPI CPU hot-plug through the CPU manager's ``CSCN``/
``_EJ0`` AML; ``max_vcpus`` is a ``u8``).  Donor licence: Apache-2.0 AND
BSD-3-Clause per the SPDX header in ``cpu.rs``.

Important donor behaviour this adapter guards against: Cloud Hypervisor's
``vm.resize`` ALSO shrinks (it ejects CPUs via ``_EJ0``).  INV-34 is hot-add
only, so this adapter re-reads live state and refuses before sending any
target lower than the present count.  ``vm.info``'s ``boot_vcpus`` is what the
hypervisor has *presented*; it is not evidence the guest brought the CPUs
online — that comes from the independent observation path (``observation.py``).
"""
from __future__ import annotations

import http.client
import json
import socket
import time
import uuid
from typing import Any, Callable

from .base import (AdapterError, AdapterErrorCode, EnsureRequest, EnsureResult, FenceRegistry,
                   LiveCpuState, Outcome, validate_request)

API_PREFIX = "/api/v1"
CH_MAX_VCPUS = 255          # vmm/src/cpu.rs: max_vcpus is u8
MAX_RESPONSE_BYTES = 1 << 20


class _UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, path: str, timeout: float) -> None:
        super().__init__("localhost", timeout=timeout)
        self._path = path

    def connect(self) -> None:  # pragma: no cover - exercised only against a real socket
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(self.timeout)
        s.connect(self._path)
        self.sock = s


Transport = Callable[[str, str, bytes | None, float], tuple[int, bytes]]


def unix_socket_transport(socket_path: str) -> Transport:
    def call(method: str, path: str, body: bytes | None, timeout: float) -> tuple[int, bytes]:
        conn = _UnixHTTPConnection(socket_path, timeout)
        try:
            headers = {"Content-Type": "application/json"} if body is not None else {}
            conn.request(method, API_PREFIX + path, body=body, headers=headers)
            resp = conn.getresponse()
            data = resp.read(MAX_RESPONSE_BYTES + 1)
            if len(data) > MAX_RESPONSE_BYTES:
                raise AdapterError(AdapterErrorCode.BACKEND, "response exceeds size limit")
            return resp.status, data
        finally:
            conn.close()
    return call


class CloudHypervisorAdapter:
    """One adapter instance per Cloud Hypervisor VMM process (one VM per VMM)."""

    name = "cloud-hypervisor-rest"
    version = "1.0.0"
    api_contract = "cloud-hypervisor OpenAPI /api/v1 (vm.info, vm.resize)"

    def __init__(self, vm_id: str, transport: Transport, *, min_interval_s: float = 0.5,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.vm_id = vm_id
        self._t = transport
        self._fences = FenceRegistry()
        self._min_interval = min_interval_s
        self._last_call = -1e18
        self._clock = clock

    # -- helpers -------------------------------------------------------
    def _call(self, method: str, path: str, payload: dict | None, timeout: float) -> tuple[int, bytes]:
        if timeout <= 0:
            raise AdapterError(AdapterErrorCode.DEADLINE, "no time left for backend call")
        body = json.dumps(payload).encode() if payload is not None else None
        try:
            return self._t(method, path, body, timeout)
        except AdapterError:
            raise
        except (socket.timeout, TimeoutError) as exc:
            raise AdapterError(AdapterErrorCode.TIMEOUT, f"{method} {path} timed out") from exc
        except OSError as exc:
            raise AdapterError(AdapterErrorCode.TRANSPORT, f"{method} {path}: {exc.__class__.__name__}") from exc

    def _check_vm(self, vm_id: str) -> None:
        if vm_id != self.vm_id:
            raise AdapterError(AdapterErrorCode.NOT_FOUND, "adapter bound to a different VM", vm_id=vm_id)

    # -- contract ------------------------------------------------------
    def capabilities(self, vm_id: str) -> dict[str, Any]:
        live = self.read_live(vm_id)
        return {"adapter": self.name, "adapter_version": self.version, "api": self.api_contract,
                "acpi_cpu_hotplug": live.max_vcpus > live.present_vcpus or live.max_vcpus >= 1,
                "hot_add_headroom": live.max_vcpus - live.present_vcpus,
                "max_vcpus": live.max_vcpus, "hot_unplug_exposed": False}

    def read_live(self, vm_id: str, timeout: float = 5.0) -> LiveCpuState:
        self._check_vm(vm_id)
        status, data = self._call("GET", "/vm.info", None, timeout)
        if status == 404:
            raise AdapterError(AdapterErrorCode.NOT_FOUND, "VM not created")
        if status != 200:
            raise AdapterError(AdapterErrorCode.BACKEND, f"vm.info HTTP {status}")
        try:
            info = json.loads(data)
            cpus = info["config"]["cpus"]
            present, mx = cpus["boot_vcpus"], cpus["max_vcpus"]
        except (ValueError, KeyError, TypeError) as exc:
            raise AdapterError(AdapterErrorCode.BACKEND, "vm.info response missing config.cpus") from exc
        for v in (present, mx):
            if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= CH_MAX_VCPUS:
                raise AdapterError(AdapterErrorCode.BACKEND, "vm.info cpu counts out of range")
        return LiveCpuState(vm_id, present, mx, "cloud-hypervisor:vm.info", self._clock())

    def ensure_vcpus(self, req: EnsureRequest) -> EnsureResult:
        validate_request(req)
        self._check_vm(req.vm_id)
        self._fences.check_and_advance(req.vm_id, req.fence_token)
        now = self._clock()
        if now - self._last_call < self._min_interval:
            raise AdapterError(AdapterErrorCode.RATE_LIMITED, "adapter call rate exceeded")
        self._last_call = now
        before = self.read_live(req.vm_id, timeout=min(5.0, req.remaining()))
        if req.target_vcpus > before.max_vcpus or req.target_vcpus > CH_MAX_VCPUS:
            return EnsureResult(Outcome.FAILED, req.vm_id, req.operation_id, req.target_vcpus,
                                before.present_vcpus, before.present_vcpus,
                                error_code=AdapterErrorCode.OVER_MAX.value,
                                error_message=f"target exceeds VM max {before.max_vcpus}")
        if req.target_vcpus < before.present_vcpus:
            # Never send: vm.resize would eject CPUs.
            return EnsureResult(Outcome.FAILED, req.vm_id, req.operation_id, req.target_vcpus,
                                before.present_vcpus, before.present_vcpus,
                                error_code=AdapterErrorCode.SHRINK_REFUSED.value,
                                error_message="live count above target; INV-34 never hot-unplugs")
        if req.target_vcpus == before.present_vcpus:
            return EnsureResult(Outcome.NOOP, req.vm_id, req.operation_id, req.target_vcpus,
                                before.present_vcpus, before.present_vcpus)
        backend_op = f"ch-{uuid.uuid4().hex[:16]}"
        try:
            status, data = self._call("PUT", "/vm.resize", {"desired_vcpus": req.target_vcpus},
                                      min(30.0, req.remaining()))
        except AdapterError as exc:
            if exc.code in (AdapterErrorCode.TIMEOUT, AdapterErrorCode.TRANSPORT, AdapterErrorCode.DEADLINE):
                return EnsureResult(Outcome.UNKNOWN, req.vm_id, req.operation_id, req.target_vcpus,
                                    before.present_vcpus, None, backend_op, exc.code.value, str(exc), True)
            raise
        if status == 404:
            return EnsureResult(Outcome.FAILED, req.vm_id, req.operation_id, req.target_vcpus,
                                before.present_vcpus, before.present_vcpus, backend_op,
                                AdapterErrorCode.NOT_FOUND.value, "VM not created")
        if status not in (200, 204):
            return EnsureResult(Outcome.UNKNOWN if status >= 500 else Outcome.FAILED, req.vm_id,
                                req.operation_id, req.target_vcpus, before.present_vcpus, None, backend_op,
                                AdapterErrorCode.BACKEND.value, f"vm.resize HTTP {status}", status >= 500)
        try:
            after = self.read_live(req.vm_id, timeout=min(5.0, max(req.remaining(), 0.1)))
        except AdapterError as exc:
            return EnsureResult(Outcome.SUBMITTED, req.vm_id, req.operation_id, req.target_vcpus,
                                before.present_vcpus, None, backend_op, exc.code.value,
                                "resize accepted; post-read failed", True)
        outcome = (Outcome.ACKNOWLEDGED if after.present_vcpus >= req.target_vcpus
                   else Outcome.PARTIAL if after.present_vcpus > before.present_vcpus else Outcome.SUBMITTED)
        return EnsureResult(outcome, req.vm_id, req.operation_id, req.target_vcpus,
                            before.present_vcpus, after.present_vcpus, backend_op)
