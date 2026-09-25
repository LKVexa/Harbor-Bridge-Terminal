"""INV-23 hardware-virtualization boundary: real /dev/kvm preflight (MC-002).

The probe opens ``/dev/kvm``, issues ``KVM_GET_API_VERSION`` and
``KVM_CHECK_EXTENSION`` ioctls, and classifies every failure into a stable
error code.  CPU flags alone are never treated as proof of usability.  The
opener/ioctl functions are injectable so no-device, permission-denied,
unsupported-capability and revoked-device paths are deterministically
testable without a KVM host.
"""
from __future__ import annotations

import errno
import os
import platform
import time
from dataclasses import dataclass, field
from typing import Callable, Final

from ..errors import Inv24Error

KVMIO: Final[int] = 0xAE
KVM_GET_API_VERSION: Final[int] = (KVMIO << 8) | 0x00
KVM_CHECK_EXTENSION: Final[int] = (KVMIO << 8) | 0x03
KVM_API_VERSION: Final[int] = 12
#: capabilities Firecracker depends on (numbers from linux/kvm.h)
REQUIRED_CAPS: Final[dict[str, int]] = {
    "KVM_CAP_IRQCHIP": 0, "KVM_CAP_USER_MEMORY": 3, "KVM_CAP_IOEVENTFD": 36,
    "KVM_CAP_IRQFD": 32, "KVM_CAP_MP_STATE": 14,
}
ARCH_CAPS: Final[dict[str, dict[str, int]]] = {
    "x86_64": {"KVM_CAP_EXT_CPUID": 7, "KVM_CAP_TSC_DEADLINE_TIMER": 72},
    "aarch64": {"KVM_CAP_ARM_PSCI_0_2": 102},
}
SUPPORTED_ARCHES: Final[frozenset[str]] = frozenset(ARCH_CAPS)


@dataclass(frozen=True, slots=True)
class HostProfile:
    arch: str
    api_version: int
    capabilities: dict[str, bool]
    nested: bool | None
    in_container: bool
    probed_at: float
    probe_ms: float
    usable: bool
    notes: tuple[str, ...] = field(default=())

    def to_dict(self) -> dict[str, object]:
        return {"schema": "PK_MICROVM_HOST/1", "arch": self.arch, "api_version": self.api_version,
                "capabilities": dict(self.capabilities), "nested": self.nested,
                "in_container": self.in_container, "usable": self.usable,
                "probe_ms": round(self.probe_ms, 3), "notes": list(self.notes)}


def _default_ioctl(fd: int, req: int, arg: int = 0) -> int:
    import fcntl
    return fcntl.ioctl(fd, req, arg)


def _detect_container() -> bool:
    try:
        return os.path.exists("/.dockerenv") or "container" in open("/proc/1/environ", "rb").read().decode("latin1")
    except OSError:
        return False


def _detect_nested(arch: str) -> bool | None:
    for path in ("/sys/module/kvm_intel/parameters/nested", "/sys/module/kvm_amd/parameters/nested"):
        try:
            return open(path).read().strip() in {"Y", "1"}
        except OSError:
            continue
    return None


class KvmPreflight:
    """Injectable KVM preflight; ``run`` either returns a usable profile or raises."""

    def __init__(self, device: str = "/dev/kvm", *,
                 opener: Callable[[str, int], int] = os.open,
                 closer: Callable[[int], None] = os.close,
                 ioctl: Callable[..., int] = _default_ioctl,
                 arch: str | None = None,
                 deadline_s: float = 2.0) -> None:
        self.device, self.opener, self.closer, self.ioctl = device, opener, closer, ioctl
        self.arch = arch or platform.machine()
        self.deadline_s = deadline_s

    def run(self) -> HostProfile:
        start = time.monotonic()
        if self.arch not in SUPPORTED_ARCHES:
            raise Inv24Error("HOST_KVM_INCOMPATIBLE", f"architecture {self.arch!r} not supported")
        try:
            fd = self.opener(self.device, os.O_RDWR | getattr(os, "O_CLOEXEC", 0))
        except FileNotFoundError:
            raise Inv24Error("HOST_KVM_UNAVAILABLE", f"{self.device} does not exist (module not loaded or no passthrough)") from None
        except PermissionError:
            raise Inv24Error("HOST_KVM_PERMISSION", f"{self.device} not openable; add runtime user to the kvm group") from None
        except OSError as exc:
            code = "HOST_KVM_TRANSIENT" if exc.errno in (errno.EINTR, errno.EAGAIN, errno.EBUSY) else "HOST_KVM_UNAVAILABLE"
            raise Inv24Error(code, f"open {self.device}: {exc.strerror}") from None
        try:
            try:
                api = int(self.ioctl(fd, KVM_GET_API_VERSION, 0))
            except OSError as exc:
                raise Inv24Error("HOST_KVM_UNAVAILABLE", f"KVM_GET_API_VERSION failed (device revoked?): {exc}") from None
            if api != KVM_API_VERSION:
                raise Inv24Error("HOST_KVM_INCOMPATIBLE", f"KVM API {api} != {KVM_API_VERSION}")
            caps: dict[str, bool] = {}
            for name, num in {**REQUIRED_CAPS, **ARCH_CAPS[self.arch]}.items():
                if time.monotonic() - start > self.deadline_s:
                    raise Inv24Error("TIMEOUT", "KVM preflight exceeded its deadline")
                try:
                    caps[name] = int(self.ioctl(fd, KVM_CHECK_EXTENSION, num)) > 0
                except OSError:
                    caps[name] = False
            missing = sorted(k for k, v in caps.items() if not v)
            if missing:
                raise Inv24Error("HOST_KVM_INCOMPATIBLE", f"missing KVM capabilities: {missing}")
        finally:
            try:
                self.closer(fd)
            except OSError:
                pass
        nested = _detect_nested(self.arch)
        notes = ("nested virtualization detected; certify separately",) if nested else ()
        return HostProfile(self.arch, api, caps, nested, _detect_container(), time.time(),
                           (time.monotonic() - start) * 1000, True, notes)


def preflight(**kwargs) -> HostProfile:
    return KvmPreflight(**kwargs).run()
