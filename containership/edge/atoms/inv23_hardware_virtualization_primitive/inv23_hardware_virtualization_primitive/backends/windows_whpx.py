"""Windows probe backend: IsProcessorFeaturePresent + WHvGetCapability (MC-03).

PF_VIRT_FIRMWARE_ENABLED (21) reports firmware-enabled virtualization; when Hyper-V
is running the root partition sees it as False, so WHvGetCapability
(WHvCapabilityCodeHypervisorPresent) is the positive usability evidence.
Hardware-backed validation is still outstanding (see COMPATIBILITY.md).
"""

from __future__ import annotations

import platform as _platform
import time
from typing import Any, Callable, Optional

from .base import ABSENT, INDETERMINATE, PRESENT_DISABLED, USABLE, ProbeResult

PF_VIRT_FIRMWARE_ENABLED = 21
PF_SECOND_LEVEL_ADDRESS_TRANSLATION = 20
WHV_CAP_HYPERVISOR_PRESENT = 0


def _default_feature(pf: int) -> bool:
    import ctypes

    return bool(ctypes.windll.kernel32.IsProcessorFeaturePresent(pf))  # type: ignore[attr-defined]


def _default_whv() -> Optional[bool]:
    """Return True/False from WHvGetCapability, None if WinHvPlatform.dll is unavailable."""
    import ctypes

    try:
        dll = ctypes.WinDLL("WinHvPlatform.dll")  # type: ignore[attr-defined]
    except OSError:
        return None
    buf = ctypes.c_uint32(0)
    written = ctypes.c_uint32(0)
    hr = dll.WHvGetCapability(WHV_CAP_HYPERVISOR_PRESENT, ctypes.byref(buf), 4, ctypes.byref(written))
    if hr != 0:
        return None
    return bool(buf.value)


class WindowsWhpxBackend:
    name = "windows-whpx"
    version = "1.0.0"

    def __init__(
        self,
        *,
        feature: Optional[Callable[[int], bool]] = None,
        whv: Optional[Callable[[], Optional[bool]]] = None,
        cpu_capable: Optional[Callable[[], Optional[bool]]] = None,
    ) -> None:
        self._feature = feature or _default_feature
        self._whv = whv or _default_whv
        self._cpu = cpu_capable

    def supports(self, platform: str, architecture: str) -> bool:
        return platform == "windows" and architecture in ("amd64", "x86_64")

    def probe(self, host: str) -> ProbeResult:
        t0 = time.monotonic_ns()
        arch = _platform.machine().lower()
        ev: dict = {}

        def result(state: str, reason: str, **kw: Any) -> ProbeResult:
            return ProbeResult(
                host=host,
                backend=self.name,
                backend_version=self.version,
                platform="windows",
                architecture=arch,
                state=state,
                reason=reason,
                evidence=ev,
                probe_ns=time.monotonic_ns() - t0,
                **kw,
            )

        try:
            fw = self._feature(PF_VIRT_FIRMWARE_ENABLED)
            slat = self._feature(PF_SECOND_LEVEL_ADDRESS_TRANSLATION)
            hv = self._whv()
        except OSError as exc:
            ev["error"] = type(exc).__name__
            return result(INDETERMINATE, "kernel_api_unavailable")
        ev.update(pf_virt_firmware_enabled=fw, pf_slat=slat, whv_hypervisor_present=hv)
        cpu = self._cpu() if self._cpu else None
        if hv is True:
            # Hyper-V root partition: depth relative to the physical host is unknowable
            # from inside the root without additional attestation.
            return result(
                USABLE, "ok", cpu_capable=True, slat=slat, firmware_enabled=True, facility_usable=True, virtualized=None, nesting_depth=None
            )
        if fw:
            return result(PRESENT_DISABLED, "kernel_api_unavailable", cpu_capable=True, slat=slat, firmware_enabled=True, virtualized=None)
        if cpu is False:
            return result(ABSENT, "capability_absent", cpu_capable=False)
        # Firmware flag False with no hypervisor: either BIOS-disabled or absent; the
        # public API cannot distinguish them without CPUID, so do not guess.
        return result(INDETERMINATE, "firmware_disabled", cpu_capable=cpu, firmware_enabled=False)
