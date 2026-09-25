"""Linux / KVM probe backend (MC-03).

Evidence sources: /proc/cpuinfo flags (vmx/svm, ept/npt, hypervisor), /dev/kvm opened
O_RDWR|O_CLOEXEC and KVM_GET_API_VERSION ioctl (must be 12), and
/sys/module/kvm_{intel,amd}/parameters/nested.  /dev/kvm is *not* exclusive in the
KVM API -- many VMMs may open it concurrently -- so exclusivity is a project policy
enforced by ``ownership`` providers, never claimed here.
"""

from __future__ import annotations

import errno
import os
import platform as _platform
import time
from typing import Any, Callable, Optional

from .base import ABSENT, INDETERMINATE, PRESENT_DISABLED, USABLE, ProbeError, ProbeResult

KVM_GET_API_VERSION = 0xAE00
KVM_API_VERSION = 12
X86 = ("x86_64", "amd64", "i686", "i386")


def parse_cpuinfo(text: str) -> dict:
    """Parse /proc/cpuinfo; raises ProbeError('malformed_probe_response') on garbage."""
    if not isinstance(text, str):
        raise ProbeError("malformed_probe_response", "cpuinfo is not text")
    vendor, flags = None, None
    for line in text.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        k = k.strip()
        if k == "vendor_id" and vendor is None:
            vendor = v.strip() or None
        elif k == "flags" and flags is None:
            flags = set(v.split())
    if flags is None:
        raise ProbeError("malformed_probe_response", "no flags line in cpuinfo")
    return {"vendor": vendor, "flags": flags}


def _default_ioctl(fd: int) -> int:
    import fcntl

    return fcntl.ioctl(fd, KVM_GET_API_VERSION)


class LinuxKvmBackend:
    name = "linux-kvm"
    version = "1.0.0"

    def __init__(self, root: str = "/", *, ioctl: Optional[Callable[[int], int]] = None, opener: Callable[..., int] = os.open) -> None:
        self.root = root
        self._ioctl = ioctl or _default_ioctl
        self._open = opener

    def _p(self, path: str) -> str:
        return os.path.join(self.root, path.lstrip("/"))

    def supports(self, platform: str, architecture: str) -> bool:
        return platform == "linux" and architecture in X86

    def _read(self, path: str) -> Optional[str]:
        try:
            with open(self._p(path), encoding="ascii", errors="replace") as fh:
                return fh.read(1 << 20)
        except FileNotFoundError:
            return None
        except PermissionError:
            return None

    def probe(self, host: str) -> ProbeResult:
        t0 = time.monotonic_ns()
        arch = _platform.machine().lower()
        ev: dict = {}

        def result(state: str, reason: str, **kw: Any) -> ProbeResult:
            return ProbeResult(
                host=host,
                backend=self.name,
                backend_version=self.version,
                platform="linux",
                architecture=arch,
                state=state,
                reason=reason,
                evidence=ev,
                probe_ns=time.monotonic_ns() - t0,
                **kw,
            )

        if arch not in X86:
            return result(INDETERMINATE, "unsupported_architecture")
        cpuinfo = self._read("/proc/cpuinfo")
        if cpuinfo is None:
            return result(INDETERMINATE, "kernel_api_unavailable")
        info = parse_cpuinfo(cpuinfo)
        flags, vendor = info["flags"], info["vendor"]
        vmx, svm = "vmx" in flags, "svm" in flags
        slat = ("ept" in flags) if vmx else (("npt" in flags) if svm else None)
        guest = "hypervisor" in flags
        ev.update(cpu_flags=sorted(flags & {"vmx", "svm", "ept", "npt", "hypervisor"}))
        nested = None
        for mod in ("kvm_intel", "kvm_amd"):
            raw = self._read(f"/sys/module/{mod}/parameters/nested")
            if raw is not None:
                nested = raw.strip() in ("1", "Y", "y")
                ev["nested_param"] = f"{mod}={raw.strip()}"
        # Depth: we can observe "guest vs not"; exact depth > 1 is not observable.
        depth = None if guest else 0
        common = dict(cpu_vendor=vendor, cpu_capable=vmx or svm, slat=slat, virtualized=guest, nesting_depth=depth, nested_enabled=nested)
        if not (vmx or svm):
            # vmx/svm missing from cpuinfo: either the CPU lacks it or (in a guest)
            # the hypervisor does not expose it.  Both mean this OS instance cannot use it.
            ev["capability"] = "vmx/svm flag absent"
            return result(ABSENT, "capability_absent", **common)
        try:
            fd = self._open(self._p("/dev/kvm"), os.O_RDWR | getattr(os, "O_CLOEXEC", 0))
        except FileNotFoundError:
            ev["dev_kvm"] = "absent"
            # CPU capable but no device: module not loaded or firmware-disabled
            # (kvm_intel refuses to load with "disabled by bios").
            return result(PRESENT_DISABLED, "device_absent", firmware_enabled=None, **common)
        except PermissionError:
            ev["dev_kvm"] = "EACCES"
            return result(PRESENT_DISABLED, "permission_denied", firmware_enabled=True, **common)
        except OSError as exc:
            ev["dev_kvm"] = errno.errorcode.get(exc.errno or 0, str(exc.errno))
            reason = "device_busy" if exc.errno == errno.EBUSY else "transient_io_failure"
            return result(PRESENT_DISABLED if reason == "device_busy" else INDETERMINATE, reason, **common)
        try:
            try:
                api = self._ioctl(fd)
            except OSError as exc:
                ev["kvm_api"] = f"ioctl failed: {errno.errorcode.get(exc.errno or 0, exc.errno)}"
                return result(PRESENT_DISABLED, "kernel_api_unavailable", firmware_enabled=True, **common)
        finally:
            try:
                os.close(fd)
            except OSError:
                pass
        if type(api) is not int:
            ev["kvm_api"] = repr(api)[:64]
            return result(INDETERMINATE, "malformed_probe_response", **common)
        ev["kvm_api"] = api
        if api != KVM_API_VERSION:
            return result(PRESENT_DISABLED, "kernel_api_unavailable", firmware_enabled=True, **common)
        return result(USABLE, "ok", firmware_enabled=True, facility_usable=True, **common)
