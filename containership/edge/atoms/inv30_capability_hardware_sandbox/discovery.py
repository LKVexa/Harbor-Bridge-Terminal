# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Local CHERI hardware discovery feeding GAP-02 (GAP-002).

Probes are read-only and side-effect free. A probe that cannot run yields
``unprobed`` — never ``absent`` and never ``present``. Only a positive,
specific signal yields ``present``:

* Arm Morello: ``/proc/cpuinfo`` CPU implementer 0x41 with part 0xd0f? — not a
  reliable public signal, so Morello is recognised only via CheriBSD's
  ``kern.features.cheri`` sysctl or the ``aarch64c`` machine string.
* CHERI-RISC-V: machine string ``riscv64c``/``riscv64cheri`` or the same sysctl.

Anything else is ``absent`` on Linux/Windows/macOS (no CHERI kernel exists
there), and ``unprobed`` when the probe itself errors.
"""
from __future__ import annotations

import os
import platform
import subprocess

PRESENT, ABSENT, UNPROBED = "present", "absent", "unprobed"
CHERI_MACHINES = {"aarch64c", "arm64c", "riscv64c", "riscv64cheri", "morello"}


def _sysctl_cheri() -> bool | None:
    try:
        out = subprocess.run(["sysctl", "-n", "kern.features.cheri"], capture_output=True,
                             text=True, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return False if platform.system() == "FreeBSD" else None
    return out.stdout.strip() == "1"


def probe_cheri(*, machine: str | None = None, system: str | None = None, sysctl=_sysctl_cheri) -> dict:
    """Return {'state', 'signal', 'machine', 'system'} for CHERI capability hardware."""
    try:
        machine = (machine if machine is not None else platform.machine()).lower()
        system = system if system is not None else platform.system()
    except Exception:  # pragma: no cover - platform module failure
        return {"state": UNPROBED, "signal": "platform probe failed", "machine": None, "system": None}
    if machine in CHERI_MACHINES:
        return {"state": PRESENT, "signal": f"machine={machine}", "machine": machine, "system": system}
    if system == "FreeBSD":  # CheriBSD reports FreeBSD
        s = sysctl()
        if s is None:
            return {"state": UNPROBED, "signal": "sysctl unavailable", "machine": machine, "system": system}
        return {"state": PRESENT if s else ABSENT, "signal": f"kern.features.cheri={int(bool(s))}",
                "machine": machine, "system": system}
    if system in ("Linux", "Windows", "Darwin"):
        return {"state": ABSENT, "signal": f"{system} has no CHERI kernel support", "machine": machine,
                "system": system}
    return {"state": UNPROBED, "signal": f"unknown system {system!r}", "machine": machine, "system": system}


def publish_to_gap02(node: str, now: int, result: dict | None = None):
    """Publish the probe through the real GAP-02 CapabilityReport when installed; else None."""
    try:
        from pk_core.integration import resolve
    except ModuleNotFoundError:
        return None
    gap02 = resolve("GAP-02")
    if gap02 is None:
        return None
    result = result or probe_cheri()
    report = gap02.CapabilityReport(node)

    def prober():
        if result["state"] == UNPROBED:
            raise gap02.ProbeUnavailable(result["signal"])
        return result["state"] == PRESENT

    gap02.probe(report, "cheri", prober, now)
    return report


def environment_report() -> dict:
    """Deterministic (sorted-key) environment discovery for CI and operators."""
    from . import deps
    from .backend import available_backends
    return {
        "schema": "INV30_ENVIRONMENT/1",
        "python": deps.python_status(),
        "pk_core": deps.pk_core_status(),
        "siblings": deps.sibling_status(),
        "cheri": probe_cheri(),
        "backends": available_backends(),
        "env_overrides": sorted(k for k in os.environ if k.startswith("INV30_")),
    }
