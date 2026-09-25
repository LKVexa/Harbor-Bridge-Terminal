"""Host probe entry point (MC-03): backend selection, timeout, cache, telemetry.

``probe_host()`` is the production path; it never returns ``usable`` from a backend
exception, a timeout, or an unsupported platform.
"""

from __future__ import annotations

import platform as _platform
import socket
import sys
import threading
import time
from collections.abc import Iterable
from typing import Optional

from .backends.base import INDETERMINATE, USABLE, ProbeError, ProbeResult, VirtualizationProbeBackend
from .backends.linux_kvm import LinuxKvmBackend
from .backends.macos_hvf import MacosHvfBackend
from .backends.windows_whpx import WindowsWhpxBackend
from .telemetry import Telemetry, label_arch, label_platform

DEFAULT_TIMEOUT_S = 2.0
DEFAULT_CACHE_TTL_S = 5.0


def current_platform() -> str:
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform in ("win32", "cygwin"):
        return "windows"
    if sys.platform == "darwin":
        return "darwin"
    return sys.platform


def default_backends() -> list:
    return [LinuxKvmBackend(), WindowsWhpxBackend(), MacosHvfBackend()]


def select_backend(backends: Iterable[VirtualizationProbeBackend], plat: str, arch: str):
    for b in backends:
        if b.supports(plat, arch):
            return b
    return None


def _indeterminate(host, plat, arch, reason, backend="none", detail=""):
    return ProbeResult(
        host=host,
        backend=backend,
        backend_version="0",
        platform=plat,
        architecture=arch,
        state=INDETERMINATE,
        reason=reason,
        evidence={"detail": detail} if detail else {},
    )


class Prober:
    """Caching prober.  Cache is time-bounded (monotonic TTL) and explicitly invalidatable,
    so a firmware/device change is observed at most ``cache_ttl_s`` later."""

    def __init__(
        self,
        backends=None,
        *,
        host: Optional[str] = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        cache_ttl_s: float = DEFAULT_CACHE_TTL_S,
        telemetry: Optional[Telemetry] = None,
        platform: Optional[str] = None,
        architecture: Optional[str] = None,
    ) -> None:
        self.backends = list(backends) if backends is not None else default_backends()
        self.host = (host or socket.gethostname() or "localhost").strip() or "localhost"
        self.timeout_s = timeout_s
        self.cache_ttl_s = cache_ttl_s
        self.telemetry = telemetry or Telemetry()
        self.platform = platform or current_platform()
        self.architecture = (architecture or _platform.machine()).lower()
        self._lock = threading.Lock()
        self._cached: Optional[ProbeResult] = None
        self._cached_at = 0.0

    def invalidate(self) -> None:
        with self._lock:
            self._cached = None

    def probe(self, *, use_cache: bool = True) -> ProbeResult:
        with self._lock:
            if use_cache and self._cached is not None and time.monotonic() - self._cached_at < self.cache_ttl_s:
                return self._cached
        res = self._probe_uncached()
        with self._lock:
            self._cached, self._cached_at = res, time.monotonic()
        return res

    def _probe_uncached(self) -> ProbeResult:
        t0 = time.monotonic_ns()
        backend = select_backend(self.backends, self.platform, self.architecture)
        tel = self.telemetry
        with tel.span("inv23.probe", platform=label_platform(self.platform)) as sp:
            if backend is None:
                tel.count(
                    "inv23_unsupported_platform_total", platform=label_platform(self.platform), architecture=label_arch(self.architecture)
                )
                res = _indeterminate(
                    self.host,
                    self.platform,
                    self.architecture,
                    "unsupported_platform" if self.platform not in ("linux", "windows", "darwin") else "unsupported_architecture",
                )
            else:
                res = self._run(backend)
            sp.update(backend=res.backend, state=res.state, reason=res.reason)
        secs = (time.monotonic_ns() - t0) / 1e9
        bl = res.backend if res.backend in ("linux-kvm", "windows-whpx", "macos-hvf") else "none"
        tel.observe("inv23_probe_latency_seconds", secs, backend=bl)
        tel.gauge("inv23_virt_primitive", 1, state=res.state, backend=bl, platform=label_platform(res.platform))
        if res.nesting_depth is not None:
            tel.gauge("inv23_nesting_depth", res.nesting_depth, backend=bl)
        if res.state == USABLE:
            tel.last_success = time.time()
            tel.event("INV23-E001", backend=res.backend, state=res.state)
        else:
            tel.last_failure_reason = res.reason
            tel.count("inv23_probe_failures_total", reason=res.reason, backend=bl)
            tel.event("INV23-E002", backend=res.backend, state=res.state, reason=res.reason)
        return res

    def _run(self, backend) -> ProbeResult:
        box: dict = {}

        def target():
            try:
                box["r"] = backend.probe(self.host)
            except ProbeError as exc:
                box["e"] = (exc.reason, exc.detail)
            except Exception as exc:  # noqa: BLE001 - never collapse into absent/usable
                box["e"] = ("backend_error", type(exc).__name__)

        th = threading.Thread(target=target, name="inv23-probe", daemon=True)
        th.start()
        th.join(self.timeout_s)
        if th.is_alive():
            return _indeterminate(self.host, self.platform, self.architecture, "probe_timeout", backend.name)
        if "e" in box:
            return _indeterminate(self.host, self.platform, self.architecture, box["e"][0], backend.name, box["e"][1])
        r = box.get("r")
        if not isinstance(r, ProbeResult):
            return _indeterminate(self.host, self.platform, self.architecture, "malformed_probe_response", backend.name)
        return r


def probe_host(**kw) -> ProbeResult:
    return Prober(**kw).probe(use_cache=False)
