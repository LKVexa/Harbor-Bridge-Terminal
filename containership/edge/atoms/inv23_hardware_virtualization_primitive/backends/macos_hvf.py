"""macOS Hypervisor.framework backend (MC-03): sysctl kern.hv_support == 1 is the
kernel's own statement that HVF is usable by an entitled process.  Entitlement
(com.apple.security.hypervisor) is checked at hv_vm_create time and is reported as
a limitation, not verified here.  Hardware-backed validation outstanding."""

from __future__ import annotations

import platform as _platform
import time
from typing import Any, Callable, Dict, Optional

from .base import ABSENT, INDETERMINATE, USABLE, ProbeResult


def _default_sysctl(name: str) -> Optional[int]:
    import ctypes
    import ctypes.util

    lib = ctypes.CDLL(ctypes.util.find_library("c"))
    val = ctypes.c_int(0)
    size = ctypes.c_size_t(ctypes.sizeof(val))
    rc = lib.sysctlbyname(name.encode(), ctypes.byref(val), ctypes.byref(size), None, 0)
    return None if rc != 0 else val.value


class MacosHvfBackend:
    name = "macos-hvf"
    version = "1.0.0"

    def __init__(self, *, sysctl: Optional[Callable[[str], Optional[int]]] = None) -> None:
        self._sysctl = sysctl or _default_sysctl

    def supports(self, platform: str, architecture: str) -> bool:
        return platform == "darwin" and architecture in ("arm64", "x86_64")

    def probe(self, host: str) -> ProbeResult:
        t0 = time.monotonic_ns()
        arch = _platform.machine().lower()
        ev: dict = {}
        hv = self._sysctl("kern.hv_support")
        vmm = self._sysctl("kern.hv_vmm_present")
        ev.update(kern_hv_support=hv, kern_hv_vmm_present=vmm)
        virt = None if vmm is None else bool(vmm)
        kw: Dict[str, Any] = dict(
            host=host,
            backend=self.name,
            backend_version=self.version,
            platform="darwin",
            architecture=arch,
            evidence=ev,
            virtualized=virt,
            nesting_depth=(0 if virt is False else None),
        )
        if hv == 1:
            return ProbeResult(
                state=USABLE,
                reason="ok",
                cpu_capable=True,
                facility_usable=True,
                firmware_enabled=True,
                probe_ns=time.monotonic_ns() - t0,
                **kw,
            )
        if hv == 0:
            return ProbeResult(state=ABSENT, reason="capability_absent", cpu_capable=False, probe_ns=time.monotonic_ns() - t0, **kw)
        return ProbeResult(state=INDETERMINATE, reason="kernel_api_unavailable", probe_ns=time.monotonic_ns() - t0, **kw)
