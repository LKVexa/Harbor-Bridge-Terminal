"""MC-07 - Host capability detection and backend selection (PK_ASYNC_CAPS/1).

Selection is derived from *operational* probes, never from the platform name.
Priority is fixed: io_uring > iocp > epoll > kqueue > portable.  An
administratively disabled backend is rejected with ADMIN_DISABLED; an explicit
override may select an unavailable backend only in diagnostic mode.  Every
rejected higher-priority backend is recorded with its reason code, and
fallback engagement is recorded with why.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from dataclasses import asdict, dataclass, field

from . import iocp, iouring, readiness

PROBE_VERSION = "caps-probe/1.0"
PRIORITY = ("io_uring", "iocp", "epoll", "kqueue", "portable")
SEMANTICS = {"io_uring": "completion", "iocp": "completion", "epoll": "readiness",
             "kqueue": "readiness", "portable": "readiness"}


@dataclass
class HostCapabilities:
    probe_version: str
    os_family: str
    os_release: str
    kernel: str
    arch: str
    python: str
    backends: dict[str, dict] = field(default_factory=dict)

    def available(self) -> list[str]:
        return [b for b in PRIORITY if self.backends.get(b, {}).get("available")]

    def to_dict(self) -> dict:
        return asdict(self)

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()


PROBES = {"io_uring": iouring.probe, "iocp": iocp.probe, "epoll": readiness.probe_epoll,
          "kqueue": readiness.probe_kqueue, "portable": readiness.probe_portable}


def detect(probes: dict | None = None) -> HostCapabilities:
    probes = probes or PROBES
    caps = HostCapabilities(
        probe_version=PROBE_VERSION, os_family=platform.system(),
        os_release=platform.release().split("+")[0][:32],  # no hostname / serials
        kernel=platform.release().split("-")[0][:16], arch=platform.machine(),
        python=platform.python_version())
    for name in PRIORITY:
        try:
            caps.backends[name] = probes[name]()
        except OSError as exc:  # host refused the probe (EMFILE, ENOMEM, EPERM...)
            from .errors import translate
            caps.backends[name] = {"backend": name, "available": False,
                                   "reason": f"PROBE_FAILED:{translate(name, exc.errno).code}"}
        except Exception as exc:  # a probe crash is a rejection, never a selection
            caps.backends[name] = {"backend": name, "available": False,
                                   "reason": f"PROBE_CRASH:{type(exc).__name__}"}
    return caps


@dataclass
class Selection:
    backend: str
    semantics: str
    fallback: bool
    rejected: dict[str, str]
    reason: str
    diagnostic: bool
    probe_version: str
    caps_digest: str

    def to_dict(self) -> dict:
        return asdict(self)


class SelectionError(RuntimeError):
    pass


def choose(caps: HostCapabilities, *, disabled: list[str] | tuple = (), override: str = "",
           diagnostic: bool = False, fast_path_expected: bool = False) -> Selection:
    rejected: dict[str, str] = {}
    if override:
        if override not in PRIORITY:
            raise SelectionError(f"unknown override {override!r}")
        avail = caps.backends.get(override, {}).get("available")
        if not avail and not diagnostic:
            raise SelectionError(f"override {override} unavailable "
                                 f"({caps.backends.get(override, {}).get('reason')}); diagnostic mode required")
        if override in disabled and not diagnostic:
            raise SelectionError(f"override {override} is administratively disabled")
        return Selection(override, SEMANTICS[override], override == "portable", {},
                         "DIAGNOSTIC_OVERRIDE" if not avail or diagnostic else "OPERATOR_OVERRIDE",
                         diagnostic, caps.probe_version, caps.digest())
    for name in PRIORITY:
        info = caps.backends.get(name, {})
        if name in disabled and name != "portable":
            rejected[name] = "ADMIN_DISABLED"
            continue
        if not info.get("available"):
            rejected[name] = str(info.get("reason") or "UNAVAILABLE")
            continue
        fb = name == "portable"
        reason = "HIGHEST_PRIORITY_AVAILABLE"
        if fb:
            reason = "FALLBACK:" + ";".join(f"{k}={v}" for k, v in rejected.items())
        return Selection(name, SEMANTICS[name], fb, rejected, reason, False,
                         caps.probe_version, caps.digest())
    raise SelectionError("no backend available, including portable")


def snapshot(caps: HostCapabilities, sel: Selection) -> dict:
    return {"schema": "PK_ASYNC_CAPS/1", "probe_version": caps.probe_version,
            "capabilities": caps.to_dict(), "selection": sel.to_dict(),
            "python_impl": sys.implementation.name}
