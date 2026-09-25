"""GAP02-MC-04 — NUMA and memory-topology discovery (Linux sysfs; others unprobed)."""
from __future__ import annotations

from typing import Any

from .errors import Code, Gap02Error
from .evidence import Host, ProbeEvidence, timed

NODE = "/sys/devices/system/node"


def _kb(text: str | None, key: str) -> int | None:
    for line in (text or "").splitlines():
        if key in line:
            parts = line.split()
            try:
                return int(parts[parts.index(key.rstrip(":") + ":") + 1]) * 1024
            except (ValueError, IndexError):
                return None
    return None


def probe_numa(host: Host | None = None) -> dict[str, Any]:
    host = host or Host()
    out: dict[str, Any] = {"nodes": [], "hugepages": {}, "ecc": None}

    def body() -> ProbeEvidence:
        if host.system != "Linux":
            raise Gap02Error(Code.UNSUPPORTED_PLATFORM, host.system)
        names = [n for n in host.listdir(NODE) if n.startswith("node") and n[4:].isdigit()]
        if not names:
            raise Gap02Error(Code.PROBE_UNAVAILABLE, "no NUMA sysfs")
        for n in names[:1024]:
            mi = host.read(f"{NODE}/{n}/meminfo")
            dist = (host.read(f"{NODE}/{n}/distance") or "").split()
            out["nodes"].append({
                "id": int(n[4:]), "cpulist": (host.read(f"{NODE}/{n}/cpulist") or "").strip()[:256],
                "mem_total_bytes": _kb(mi, "MemTotal:"), "mem_free_bytes": _kb(mi, "MemFree:"),
                "distance": [int(x) for x in dist if x.isdigit()][:1024],
                "online": True})
        for hp in host.listdir("/sys/kernel/mm/hugepages"):
            nr = (host.read(f"/sys/kernel/mm/hugepages/{hp}/nr_hugepages") or "").strip()
            out["hugepages"][hp.replace("hugepages-", "")] = int(nr) if nr.isdigit() else None
        mcs = host.listdir("/sys/devices/system/edac/mc")
        out["ecc"] = True if any(m.startswith("mc") for m in mcs) else None  # absence ≠ proof of no ECC
        out["memory_hotplug"] = host.exists("/sys/devices/system/memory/auto_online_blocks")
        return ProbeEvidence("memory.numa", len(names) > 1, "kernel-attribute", NODE,
                             {"nodes": len(names)})
    out["evidence"] = timed(body, "memory.numa", NODE)
    ecc = out["ecc"]
    out["ecc_evidence"] = ProbeEvidence("memory.ecc", True, "kernel-attribute", "edac") if ecc else \
        ProbeEvidence("memory.ecc", None, "observation", "edac", error="GAP02-E001")
    hp = any((v or 0) > 0 for v in out["hugepages"].values())
    out["hugepage_evidence"] = ProbeEvidence("memory.hugepages", hp, "kernel-attribute", "hugepages") \
        if out["hugepages"] else ProbeEvidence("memory.hugepages", None, "observation", "hugepages", error="GAP02-E001")
    return out
