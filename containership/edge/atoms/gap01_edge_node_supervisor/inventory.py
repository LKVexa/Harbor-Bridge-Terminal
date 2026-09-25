"""Hardware/resource inventory adapter (2) and resource-pressure sampling (22).

Read-only, best-effort snapshot from the host (Linux /proc and /sys, with
portable fallbacks).  Authoritative capability discovery remains delegated to
GAP-02; this adapter provides the supervisor's *local view* so it can bound
admission and detect pressure.  Every field records its source so consumers
can distinguish measured values from unknowns (``None``).
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import platform
import shutil


def _read(path: str) -> str | None:
    try:
        return pathlib.Path(path).read_text(errors="replace")
    except OSError:
        return None


def _meminfo() -> dict:
    txt = _read("/proc/meminfo")
    if not txt:
        return {"total_kb": None, "available_kb": None, "source": "unavailable"}
    vals = {}
    for ln in txt.splitlines():
        k, _, v = ln.partition(":")
        parts = v.split()
        if parts and parts[0].isdigit():
            vals[k] = int(parts[0])
    return {"total_kb": vals.get("MemTotal"), "available_kb": vals.get("MemAvailable"),
            "source": "/proc/meminfo"}


def _numa() -> list[str]:
    base = pathlib.Path("/sys/devices/system/node")
    return sorted(p.name for p in base.glob("node[0-9]*")) if base.exists() else []


def _nics() -> list[dict]:
    base = pathlib.Path("/sys/class/net")
    out = []
    if base.exists():
        for p in sorted(base.iterdir()):
            out.append({"name": p.name, "mac": (_read(str(p / "address")) or "").strip() or None,
                        "mtu": int((_read(str(p / "mtu")) or "0").strip() or 0)})
    return out


def _accelerators() -> list[str]:
    found = []
    for pattern in ("/dev/nvidia[0-9]*", "/dev/dri/renderD*", "/dev/accel/accel*", "/dev/kfd"):
        found += sorted(str(p) for p in pathlib.Path("/").glob(pattern.lstrip("/")))
    return found


def snapshot(disk_paths: tuple[str, ...] = ("/",)) -> dict:
    disks = []
    for d in disk_paths:
        try:
            u = shutil.disk_usage(d)
            disks.append({"path": d, "total": u.total, "used": u.used, "free": u.free})
        except OSError:
            disks.append({"path": d, "total": None, "used": None, "free": None})
    fw = (_read("/sys/class/dmi/id/bios_version") or "").strip() or None
    snap = {
        "schema": "GAP01_INVENTORY/1",
        "platform": {"system": platform.system(), "release": platform.release(),
                     "machine": platform.machine(), "python": platform.python_version()},
        "cpu": {"logical": os.cpu_count(), "model": _cpu_model()},
        "memory": _meminfo(),
        "numa_nodes": _numa(),
        "accelerators": _accelerators(),
        "disks": disks,
        "nics": _nics(),
        "firmware": {"bios_version": fw},
        "authority": "local-view; authoritative discovery delegated to GAP-02",
    }
    snap["digest"] = hashlib.sha256(json.dumps(snap, sort_keys=True).encode()).hexdigest()
    return snap


def _cpu_model() -> str | None:
    txt = _read("/proc/cpuinfo") or ""
    for ln in txt.splitlines():
        if ln.lower().startswith("model name"):
            return ln.split(":", 1)[1].strip()
    return platform.processor() or None


def pressure(mem_threshold_pct: int, disk_threshold_pct: int, disk_path: str = "/") -> dict:
    mem = _meminfo()
    mem_pct = None
    if mem["total_kb"] and mem["available_kb"] is not None:
        mem_pct = round(100 * (1 - mem["available_kb"] / mem["total_kb"]), 1)
    try:
        u = shutil.disk_usage(disk_path)
        disk_pct = round(100 * u.used / u.total, 1) if u.total else None
    except OSError:
        disk_pct = None
    reasons = []
    if mem_pct is not None and mem_pct >= mem_threshold_pct:
        reasons.append(f"memory {mem_pct}% >= {mem_threshold_pct}%")
    if disk_pct is not None and disk_pct >= disk_threshold_pct:
        reasons.append(f"disk {disk_pct}% >= {disk_threshold_pct}%")
    return {"memory_pct": mem_pct, "disk_pct": disk_pct, "under_pressure": bool(reasons),
            "reasons": reasons}
