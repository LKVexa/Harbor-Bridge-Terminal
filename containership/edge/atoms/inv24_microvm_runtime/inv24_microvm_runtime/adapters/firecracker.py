"""Typed Firecracker adapter (MC-001).

The adapter is the only place that knows Firecracker's REST API.  It
translates a validated :class:`~inv24_microvm_runtime.runtime.MicroVM` plus
typed device specs into an ordered, whitelisted API plan, then drives the
plan over a bounded Unix-domain socket with per-call deadlines.  Launch is
refused (fail closed) unless, *before any side effect*:

1. the Firecracker binary, kernel and rootfs match the approved manifest pins,
2. the KVM preflight returns a usable host profile, and
3. every device is declared, in the minimal model and ownership-claimable.

The pure ``MicroVM`` state machine stays framework- and runtime-agnostic.
"""
from __future__ import annotations

import http.client
import json
import os
import socket
import time
from dataclasses import dataclass, field
from typing import Callable, Final, Protocol

from ..devices.specs import BlockSpec, NetSpec, OwnershipRegistry, VsockSpec, order_and_check
from ..errors import Inv24Error
from ..runtime import BOOT_BUDGET_MS, MicroVM
from ..security.artifacts import ArtifactManifest
from ..supervision.vmm_process import VmmProcess
from ..virtualization.kvm import HostProfile, KvmPreflight

#: Only these API paths and body fields may ever be sent.
ALLOWED_FIELDS: Final[dict[str, frozenset[str]]] = {
    "/machine-config": frozenset({"vcpu_count", "mem_size_mib", "smt"}),
    "/boot-source": frozenset({"kernel_image_path", "boot_args"}),
    "/drives/": frozenset({"drive_id", "path_on_host", "is_root_device", "is_read_only"}),
    "/network-interfaces/": frozenset({"iface_id", "host_dev_name", "guest_mac"}),
    "/vsock": frozenset({"vsock_id", "guest_cid", "uds_path"}),
    "/actions": frozenset({"action_type"}),
    "/vm": frozenset({"state"}),
}
ALLOWED_ACTIONS: Final[frozenset[str]] = frozenset({"InstanceStart", "SendCtrlAltDel"})
DEFAULT_BOOT_ARGS: Final[str] = "console=ttyS0 reboot=k panic=1 pci=off"
MAX_RESPONSE: Final[int] = 64 * 1024


@dataclass(frozen=True, slots=True)
class ApiCall:
    method: str
    path: str
    body: dict[str, object]


class Transport(Protocol):
    def request(self, call: ApiCall, timeout_s: float) -> tuple[int, dict]: ...


class UdsTransport:
    """HTTP/1.1 over a Unix socket with a per-request deadline and bounded body."""

    def __init__(self, socket_path: str) -> None:
        self.socket_path = socket_path

    def request(self, call: ApiCall, timeout_s: float) -> tuple[int, dict]:
        class _Conn(http.client.HTTPConnection):
            def connect(inner):  # noqa: N805
                inner.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                inner.sock.settimeout(timeout_s)
                inner.sock.connect(self.socket_path)
        conn = _Conn("localhost", timeout=timeout_s)
        try:
            conn.request(call.method, call.path, body=json.dumps(call.body),
                         headers={"Content-Type": "application/json", "Accept": "application/json"})
            resp = conn.getresponse()
            raw = resp.read(MAX_RESPONSE + 1)[:MAX_RESPONSE]
            try:
                payload = json.loads(raw) if raw else {}
            except ValueError:
                payload = {"fault_message": raw[:256].decode("utf-8", "replace")}
            return resp.status, payload
        except socket.timeout:
            raise Inv24Error("TIMEOUT", f"{call.method} {call.path} exceeded {timeout_s}s") from None
        except OSError as exc:
            raise Inv24Error("PROCESS_CRASHED", f"API socket error: {exc}") from None
        finally:
            conn.close()


def _check_fields(call: ApiCall) -> None:
    key = next((k for k in ALLOWED_FIELDS if call.path == k or (k.endswith("/") and call.path.startswith(k))), None)
    if key is None:
        raise Inv24Error("UNSUPPORTED_FIELD", f"API path {call.path} not permitted")
    extra = set(call.body) - ALLOWED_FIELDS[key]
    if extra:
        raise Inv24Error("UNSUPPORTED_FIELD", f"{call.path}: fields {sorted(extra)} not permitted")
    if call.path == "/actions" and call.body.get("action_type") not in ALLOWED_ACTIONS:
        raise Inv24Error("UNSUPPORTED_FIELD", "action not permitted")


def build_plan(vm: MicroVM, specs: list, *, kernel_path: str, boot_args: str = DEFAULT_BOOT_ARGS,
               tenant_root: str | None = None) -> list[ApiCall]:
    """Pure translation; raises before any side effect on any disallowed input."""
    if vm.state != "created" or vm.destroyed:
        raise Inv24Error("CONFIG_REJECTED", "only pristine instances can be planned")
    if "\n" in boot_args or len(boot_args) > 2048 or "init=" in boot_args:
        raise Inv24Error("CONFIG_REJECTED", "boot_args contain forbidden content")
    ordered = order_and_check(specs, declared=vm.devices, tenant_root=tenant_root)
    if "serial" not in vm.devices:
        boot_args = " ".join(a for a in boot_args.split() if not a.startswith("console=")) + " 8250.nr_uarts=0"
    plan = [
        ApiCall("PUT", "/machine-config", {"vcpu_count": vm.vcpus, "mem_size_mib": vm.memory_mib, "smt": False}),
        ApiCall("PUT", "/boot-source", {"kernel_image_path": kernel_path, "boot_args": boot_args.strip()}),
    ]
    for s in ordered:
        if isinstance(s, BlockSpec):
            plan.append(ApiCall("PUT", f"/drives/{s.device_id}", s.api()))
        elif isinstance(s, NetSpec):
            plan.append(ApiCall("PUT", f"/network-interfaces/{s.device_id}", s.api()))
        elif isinstance(s, VsockSpec):
            plan.append(ApiCall("PUT", "/vsock", s.api()))
    plan.append(ApiCall("PUT", "/actions", {"action_type": "InstanceStart"}))
    for call in plan:
        _check_fields(call)
    return plan


def classify_api_error(status: int, payload: dict, path: str) -> Inv24Error:
    msg = str(payload.get("fault_message", ""))[:256]
    if status == 400:
        return Inv24Error("CONFIG_REJECTED", f"Firecracker rejected {path}: {msg}")
    if path == "/actions":
        return Inv24Error("GUEST_BOOT_FAILED", f"InstanceStart failed ({status}): {msg}")
    return Inv24Error("PROCESS_CRASHED", f"{path} returned {status}: {msg}")


@dataclass
class LaunchResult:
    instance: str
    host: HostProfile
    boot: dict[str, object]
    api_calls: int
    firecracker_version: str
    durations_ms: dict[str, float] = field(default_factory=dict)


class FirecrackerAdapter:
    """Fail-closed launcher. Dependencies are injectable for deterministic tests."""

    def __init__(self, manifest: ArtifactManifest, *, firecracker_path: str, kernel_path: str,
                 rootfs_path: str | None = None, registry: OwnershipRegistry | None = None,
                 kvm: KvmPreflight | None = None,
                 transport_factory: Callable[[str], Transport] = UdsTransport,
                 process_factory: Callable[..., VmmProcess] = VmmProcess,
                 run_dir: str = "/run/inv24", call_timeout_s: float = 1.0,
                 on_event: Callable[[str, dict], None] | None = None) -> None:
        self.manifest, self.fc_path, self.kernel_path, self.rootfs_path = manifest, firecracker_path, kernel_path, rootfs_path
        self.registry = registry or OwnershipRegistry()
        self.kvm = kvm or KvmPreflight()
        self.transport_factory, self.process_factory = transport_factory, process_factory
        self.run_dir, self.call_timeout_s = run_dir, call_timeout_s
        self.on_event = on_event or (lambda name, data: None)
        self.processes: dict[str, VmmProcess] = {}

    def preconditions(self) -> tuple[str, HostProfile]:
        fc = self.manifest.verify("firecracker", self.fc_path)
        self.manifest.verify("guest-kernel", self.kernel_path)
        if self.rootfs_path:
            self.manifest.verify("guest-rootfs", self.rootfs_path)
        return fc.version, self.kvm.run()

    def launch(self, vm: MicroVM, specs: list, *, budget_ms: int = BOOT_BUDGET_MS,
               tenant_root: str | None = None) -> LaunchResult:
        t0 = time.monotonic()
        version, host = self.preconditions()                      # integrity + host gates
        plan = build_plan(vm, specs, kernel_path=self.kernel_path, tenant_root=tenant_root)
        self.registry.claim_specs(specs, vm.tenant, vm.name)       # ownership gate
        sock = os.path.join(self.run_dir, f"{vm.tenant}-{vm.name}.sock")
        proc = self.process_factory([self.fc_path, "--api-sock", sock, "--level", "Warning"],
                                    socket_path=sock, version=version)
        durations: dict[str, float] = {"preflight": (time.monotonic() - t0) * 1000}
        try:
            proc.start()
            proc.wait_ready()
            transport = self.transport_factory(sock)
            boot_start = time.monotonic()
            for call in plan:
                status, payload = transport.request(call, self.call_timeout_s)
                if not 200 <= status < 300:
                    raise classify_api_error(status, payload, call.path)
            elapsed = int((time.monotonic() - boot_start) * 1000)
            durations["boot"] = float(elapsed)
            boot = vm.boot(elapsed_ms=elapsed, budget_ms=budget_ms)
        except BaseException as exc:
            self._teardown(vm, proc)
            self.on_event("launch_failed", {"instance": vm.name, "error": getattr(exc, "code", type(exc).__name__)})
            raise
        self.processes[vm.name] = proc
        self.on_event("launched", {"instance": vm.name, "boot_ms": boot["boot_ms"]})
        return LaunchResult(vm.name, host, boot, len(plan), version, durations)

    def _teardown(self, vm: MicroVM, proc: VmmProcess) -> dict[str, object]:
        released = self.registry.release_instance(vm.tenant, vm.name)
        try:
            cleanup = proc.cleanup()
        except Inv24Error:
            cleanup = {"ok": False}
            raise
        finally:
            self.processes.pop(vm.name, None)
        return {"released": released, **cleanup}

    def destroy(self, vm: MicroVM) -> dict[str, object]:
        proc = self.processes.get(vm.name)
        record = vm.stop()
        if proc is not None:
            record = {**record, "cleanup": self._teardown(vm, proc)}
        else:
            self.registry.release_instance(vm.tenant, vm.name)
        self.on_event("destroyed", {"instance": vm.name})
        return record
