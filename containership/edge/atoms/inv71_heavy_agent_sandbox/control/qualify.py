"""Node qualification and deployment profiles (C012, C040-IMP-04, C031-IMP-02).

``qualify(facts, profile)`` turns host facts into a machine-readable capability
report and an ADMIT/REJECT verdict.  ``probe_local()`` gathers the facts it can
read from the current Linux host without privilege (it is how the evidence
bundle records the *audit environment*; this container is not a Firecracker
host and qualifies as REJECT, which is the correct answer).
"""
from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Any, Mapping

PROFILES: Mapping[str, Mapping[str, Any]] = {
    "cloud":      {"min_kernel": (5, 10), "min_mem_mib": 65536, "kvm": True, "cgroup2": True, "nested_ok": False,
                   "offline_grace_s": 0, "telemetry_buffer_mib": 256},
    "datacenter": {"min_kernel": (5, 10), "min_mem_mib": 131072, "kvm": True, "cgroup2": True, "nested_ok": False,
                   "offline_grace_s": 300, "telemetry_buffer_mib": 512},
    "near-edge":  {"min_kernel": (5, 10), "min_mem_mib": 16384, "kvm": True, "cgroup2": True, "nested_ok": False,
                   "offline_grace_s": 3600, "telemetry_buffer_mib": 1024},
    "far-edge":   {"min_kernel": (5, 10), "min_mem_mib": 8192, "kvm": True, "cgroup2": True, "nested_ok": False,
                   "offline_grace_s": 86400, "telemetry_buffer_mib": 2048},
}
REQUIRED_CPU_FLAGS = {"x86_64": ("vmx|svm",), "aarch64": ()}


def probe_local() -> dict[str, Any]:
    f: dict[str, Any] = {"arch": platform.machine(), "kernel": platform.release(), "python": platform.python_version()}
    f["kvm"] = os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK)
    f["cgroup2"] = Path("/sys/fs/cgroup/cgroup.controllers").exists()
    try:
        meminfo = Path("/proc/meminfo").read_text()
        f["mem_mib"] = int(next(l for l in meminfo.splitlines() if l.startswith("MemTotal")).split()[1]) // 1024
    except Exception:
        f["mem_mib"] = 0
    try:
        cpu = Path("/proc/cpuinfo").read_text()
        flags = next((l for l in cpu.splitlines() if l.startswith(("flags", "Features"))), "")
        f["cpu_flags"] = sorted(set(flags.split(":", 1)[-1].split()) & {"vmx", "svm", "hypervisor", "aes", "sha_ni"})
        f["cpu_model"] = next((l.split(":", 1)[1].strip() for l in cpu.splitlines() if l.startswith("model name")), "")
        f["microcode"] = next((l.split(":", 1)[1].strip() for l in cpu.splitlines() if l.startswith("microcode")), "")
    except Exception:
        f["cpu_flags"], f["cpu_model"], f["microcode"] = [], "", ""
    f["nested"] = "hypervisor" in f.get("cpu_flags", [])
    f["time_sync"] = Path("/run/systemd/timesync/synchronized").exists()
    return f


def _kver(s: str) -> tuple[int, int]:
    try:
        a, b = s.split(".")[:2]
        return int(a), int("".join(ch for ch in b if ch.isdigit()) or 0)
    except Exception:
        return (0, 0)


def qualify(facts: Mapping[str, Any], profile: str) -> dict[str, Any]:
    p = PROFILES[profile]
    checks = []

    def chk(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})
    chk("kernel", _kver(str(facts.get("kernel", ""))) >= p["min_kernel"], f"{facts.get('kernel')} >= {p['min_kernel']}")
    chk("kvm", bool(facts.get("kvm")) or not p["kvm"], f"/dev/kvm usable={facts.get('kvm')}")
    chk("cgroup2", bool(facts.get("cgroup2")), f"unified cgroup={facts.get('cgroup2')}")
    chk("memory", int(facts.get("mem_mib", 0)) >= p["min_mem_mib"], f"{facts.get('mem_mib')} MiB >= {p['min_mem_mib']}")
    chk("nested_virtualization", p["nested_ok"] or not facts.get("nested"), f"nested={facts.get('nested')}")
    arch = facts.get("arch", "")
    flags = set(facts.get("cpu_flags", []))
    need = REQUIRED_CPU_FLAGS.get(arch)
    chk("cpu_virt_flags", need is not None and all(any(x in flags for x in n.split("|")) for n in need),
        f"arch={arch} flags={sorted(flags)}")
    chk("time_sync", bool(facts.get("time_sync")), f"synchronized={facts.get('time_sync')}")
    verdict = "ADMIT" if all(c["status"] == "PASS" for c in checks) else "REJECT"
    return {"schema": "PK_HEAVYBOX_NODE_QUALIFICATION/1", "profile": profile, "facts": dict(facts),
            "checks": checks, "verdict": verdict}
