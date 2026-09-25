"""Conservative host-hardware discovery for GAP-02.

The implementation deliberately prefers ``unprobed`` over inference. It uses
read-only OS facilities and standard-library APIs, never shells user input, and
never collects MAC addresses, IP addresses, serial numbers, or disk contents.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import ctypes
import glob
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
from typing import Any

from .capabilities import (
    ABSENT,
    PRESENT,
    UNPROBED,
    CapabilityReport,
    ProbeUnavailable,
    probe,
)

INVENTORY_SCHEMA = "PK_HARDWARE_INVENTORY/1"
_MAX_COMMAND_OUTPUT = 1_000_000
_COMMAND_TIMEOUT_SECONDS = 2.0


@dataclass
class HardwareInventory:
    """Privacy-minimized local hardware facts used to drive capability probes."""

    node: str
    collected_at: int
    os: dict[str, Any] = field(default_factory=dict)
    cpu: dict[str, Any] = field(default_factory=dict)
    memory: dict[str, Any] = field(default_factory=dict)
    storage: dict[str, Any] = field(default_factory=dict)
    network: dict[str, Any] = field(default_factory=dict)
    accelerators: dict[str, Any] = field(default_factory=dict)
    virtualization: dict[str, Any] = field(default_factory=dict)
    security_devices: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema"] = INVENTORY_SCHEMA
        return payload


def _safe_text(path: Path, *, limit: int = 131_072) -> str | None:
    try:
        if not path.is_file():
            return None
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return handle.read(limit)
    except (OSError, PermissionError):
        return None


def _safe_command(argv: list[str]) -> str | None:
    """Run a fixed, caller-constructed system command without a shell."""
    if not argv or not os.path.isabs(argv[0]) or not os.path.isfile(argv[0]):
        return None
    try:
        completed = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=_COMMAND_TIMEOUT_SECONDS,
            shell=False,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout[:_MAX_COMMAND_OUTPUT]


def _physical_memory_bytes() -> int | None:
    system = platform.system()
    if system == "Windows":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        try:
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullTotalPhys)
        except (AttributeError, OSError):
            return None
        return None

    if system == "Darwin":
        for binary in ("/usr/sbin/sysctl", "/usr/bin/sysctl"):
            output = _safe_command([binary, "-n", "hw.memsize"])
            if output:
                try:
                    return int(output.strip())
                except ValueError:
                    return None
        return None

    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        if isinstance(pages, int) and isinstance(page_size, int) and pages > 0 and page_size > 0:
            return pages * page_size
    except (AttributeError, OSError, ValueError):
        pass

    meminfo = _safe_text(Path("/proc/meminfo"))
    if meminfo:
        for line in meminfo.splitlines():
            if line.startswith("MemTotal:"):
                parts = line.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    return int(parts[1]) * 1024
    return None


def _storage_root() -> str:
    anchor = Path.cwd().anchor
    return anchor or os.path.sep


def _network_interfaces() -> list[str] | None:
    try:
        items = socket.if_nameindex()
    except (AttributeError, OSError):
        return None
    # Interface names are included for operator usefulness; addresses and MACs are not.
    return sorted({name for _, name in items if isinstance(name, str) and name})


def _linux_cpu_flags() -> set[str] | None:
    text = _safe_text(Path("/proc/cpuinfo"))
    if not text:
        return None
    flags: set[str] = set()
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip().lower() in {"flags", "features"}:
            flags.update(value.strip().lower().split())
    return flags or None


def _virtualization_info() -> dict[str, Any]:
    system = platform.system()
    info: dict[str, Any] = {"cpu_extension": None, "hypervisor_detected": None, "source": None}
    if system == "Linux":
        flags = _linux_cpu_flags()
        machine = (platform.machine() or "").lower()
        if flags is not None:
            if machine in {"x86_64", "amd64", "i386", "i686", "x86"}:
                info["cpu_extension"] = bool({"vmx", "svm"}.intersection(flags))
            info["hypervisor_detected"] = "hypervisor" in flags
            info["source"] = "/proc/cpuinfo"
        hypervisor_type = _safe_text(Path("/sys/hypervisor/type"), limit=4096)
        if hypervisor_type:
            info["hypervisor_detected"] = True
            info["hypervisor_type"] = hypervisor_type.strip()[:128]
            info["source"] = "/sys/hypervisor/type"
        return info

    if system == "Darwin":
        for binary in ("/usr/sbin/sysctl", "/usr/bin/sysctl"):
            output = _safe_command([binary, "-n", "kern.hv_support"])
            if output is not None:
                value = output.strip()
                info["cpu_extension"] = value == "1"
                info["source"] = "sysctl kern.hv_support"
                break
        return info

    # Windows has multiple architecture- and SKU-dependent virtualization APIs.
    # Do not map an ambiguous API bit to a scheduling capability.
    return info


def _windows_display_adapters() -> list[str] | None:
    if platform.system() != "Windows":
        return None

    class DISPLAY_DEVICEW(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("DeviceName", ctypes.c_wchar * 32),
            ("DeviceString", ctypes.c_wchar * 128),
            ("StateFlags", ctypes.c_ulong),
            ("DeviceID", ctypes.c_wchar * 128),
            ("DeviceKey", ctypes.c_wchar * 128),
        ]

    adapters: list[str] = []
    try:
        enum = ctypes.windll.user32.EnumDisplayDevicesW
    except (AttributeError, OSError):
        return None
    index = 0
    while index < 64:  # hard upper bound against pathological API behavior
        dev = DISPLAY_DEVICEW()
        dev.cb = ctypes.sizeof(DISPLAY_DEVICEW)
        try:
            ok = enum(None, index, ctypes.byref(dev), 0)
        except OSError:
            return None
        if not ok:
            break
        name = dev.DeviceString.strip()
        if name:
            adapters.append(name[:128])
        index += 1
    return sorted(set(adapters))


def _gpu_info() -> dict[str, Any]:
    """Return GPU observations without claiming a schedulable compute accelerator.

    Display/DRM enumeration proves that an adapter is exposed, but not that a
    usable CUDA/ROCm/Level-Zero/Metal compute stack is present. Therefore the
    scheduling-level ``detected`` field remains ``None`` until a vendor/runtime
    probe is supplied.
    """
    system = platform.system()
    if system == "Windows":
        adapters = _windows_display_adapters()
        return {
            "detected": None,
            "observed_adapter_count": None if adapters is None else len(adapters),
            "adapters": adapters or [],
            "source": "EnumDisplayDevicesW" if adapters is not None else None,
        }
    if system == "Linux":
        cards = sorted(path for path in glob.glob("/sys/class/drm/card*") if "-" not in Path(path).name)
        return {
            "detected": None,
            "observed_adapter_count": len(cards),
            "source": "/sys/class/drm/card*",
        }
    if system == "Darwin":
        return {"detected": None, "observed_adapter_count": None, "source": None}
    return {"detected": None, "observed_adapter_count": None, "source": None}


def _tpm_info() -> dict[str, Any]:
    if platform.system() == "Linux":
        paths = [Path("/dev/tpmrm0"), Path("/dev/tpm0")]
        exposed = [path for path in paths if path.exists()]
        usable = [path for path in exposed if os.access(path, os.R_OK | os.W_OK)]
        return {
            "detected": bool(exposed),
            "usable": bool(usable) if exposed else False,
            "device_count": len(exposed),
            "source": "/dev/tpm*",
        }
    return {"detected": None, "usable": None, "source": None}


def collect_inventory(node: str, now: int) -> HardwareInventory:
    """Collect read-only, privacy-minimized host facts."""
    CapabilityReport(node)  # validates the externally supplied node identifier
    if isinstance(now, bool) or not isinstance(now, int) or now < 0:
        raise ValueError(f"now must be a non-negative integer; got {now!r}")
    inventory = HardwareInventory(node=node, collected_at=now)
    inventory.os = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python_bits": 64 if sys.maxsize > 2**32 else 32,
    }
    inventory.cpu = {
        "architecture": platform.machine() or None,
        "logical_processors": os.cpu_count(),
        "processor": (platform.processor() or None),
    }
    memory_bytes = _physical_memory_bytes()
    inventory.memory = {"physical_bytes": memory_bytes}

    root = _storage_root()
    try:
        disk = shutil.disk_usage(root)
        inventory.storage = {
            "root": root,
            "total_bytes": int(disk.total),
            "free_bytes": int(disk.free),
        }
    except OSError as exc:
        inventory.storage = {"root": root, "total_bytes": None, "free_bytes": None}
        inventory.warnings.append(f"storage probe failed: {type(exc).__name__}")

    interfaces = _network_interfaces()
    inventory.network = {
        "interface_count": None if interfaces is None else len(interfaces),
        "interfaces": interfaces or [],
        "addresses_collected": False,
    }
    inventory.accelerators = {
        "gpu": _gpu_info(),
        # No portable, privilege-safe standard API proves that an NPU is exposed.
        "npu": {"detected": None, "source": None},
    }
    inventory.virtualization = _virtualization_info()
    inventory.security_devices = {"tpm": _tpm_info()}
    return inventory


def report_from_inventory(inventory: HardwareInventory) -> CapabilityReport:
    """Convert discovered host facts to the conservative three-valued report."""
    report = CapabilityReport(inventory.node)
    now = inventory.collected_at

    def known_bool(value: Any, label: str):
        def _probe() -> bool:
            if isinstance(value, bool):
                return value
            raise ProbeUnavailable(f"{label} has no reliable probe on this platform")
        return _probe

    def positive_number(value: Any, label: str):
        def _probe() -> bool:
            if isinstance(value, bool) or not isinstance(value, int):
                raise ProbeUnavailable(f"{label} value unavailable")
            return value > 0
        return _probe

    probe(report, "cpu", positive_number(inventory.cpu.get("logical_processors"), "cpu"), now)
    probe(report, "memory", positive_number(inventory.memory.get("physical_bytes"), "memory"), now)
    probe(report, "storage", positive_number(inventory.storage.get("total_bytes"), "storage"), now)
    def network_probe() -> bool:
        count = inventory.network.get("interface_count")
        if count is None:
            raise ProbeUnavailable("network interface API unavailable")
        return bool(count)

    probe(report, "network", network_probe, now)
    probe(report, "gpu", known_bool(inventory.accelerators["gpu"].get("detected"), "gpu"), now)
    probe(report, "npu", known_bool(inventory.accelerators["npu"].get("detected"), "npu"), now)
    probe(
        report,
        "virtualization.cpu-extension",
        known_bool(inventory.virtualization.get("cpu_extension"), "virtualization.cpu-extension"),
        now,
    )
    probe(report, "tpm", known_bool(inventory.security_devices["tpm"].get("usable"), "tpm"), now)
    return report


def discover(node: str, now: int) -> tuple[HardwareInventory, CapabilityReport]:
    """Collect hardware inventory and produce its fail-closed capability report."""
    inventory = collect_inventory(node, now)
    return inventory, report_from_inventory(inventory)
