"""GAP02-MC-07 — Virtualization / IOMMU discovery (Linux, macOS, Windows).

Separates *host can virtualize* (extension exposed AND usable: /dev/kvm,
kern.hv_support, Windows HypervisorPresent/VirtualizationFirmwareEnabled) from
*we are a guest* (hypervisor flag / DMI)."""
from __future__ import annotations

from typing import Any

from .errors import Code, Gap02Error
from .evidence import Host, ProbeEvidence, timed


def probe_virt(host: Host | None = None) -> dict[str, Any]:
    host = host or Host()
    out: dict[str, Any] = {}

    def body() -> ProbeEvidence:
        if host.system == "Linux":
            flags = set()
            for line in (host.read("/proc/cpuinfo") or "").splitlines():
                k, _, v = line.partition(":")
                if k.strip() in ("flags", "Features"):
                    flags |= set(v.split())
            kvm = host.exists("/dev/kvm")
            groups = host.listdir("/sys/kernel/iommu_groups")
            nested = None
            for mod in ("kvm_intel", "kvm_amd"):
                v = (host.read(f"/sys/module/{mod}/parameters/nested") or "").strip()
                if v:
                    nested = v in ("Y", "1")
            out.update({
                "cpu_extension": bool({"vmx", "svm"} & flags) if host.machine in ("x86_64", "amd64") else None,
                "slat": bool({"ept", "npt"} & flags) if host.machine in ("x86_64", "amd64") else None,
                "kvm_usable": kvm and host.access("/dev/kvm", 6),
                "iommu_groups": len(groups), "iommu": len(groups) > 0,
                "nested": nested,
                "guest": "hypervisor" in flags or host.exists("/sys/hypervisor/type"),
                "hypervisor_type": (host.read("/sys/hypervisor/type") or "").strip()[:64] or None,
                "container": host.exists("/.dockerenv") or host.exists("/run/.containerenv"),
                "passthrough": bool(host.listdir("/sys/bus/pci/drivers/vfio-pci")),
            })
            return ProbeEvidence("virtualization.host", out["kvm_usable"], "kernel-attribute", "/dev/kvm")
        if host.system == "Darwin":
            rc, o = host.run(("/usr/sbin/sysctl", "-n", "kern.hv_support"))
            if rc != 0 or o.strip() not in ("0", "1"):
                raise Gap02Error(Code.MALFORMED_RESPONSE, "kern.hv_support")
            out.update({"hv_support": o.strip() == "1", "iommu": None})
            return ProbeEvidence("virtualization.host", o.strip() == "1", "api-bit", "kern.hv_support")
        if host.system == "Windows":
            # Win32_Processor.VirtualizationFirmwareEnabled via fixed-path PowerShell CIM (read-only).
            ps = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
            rc, o = host.run((ps, "-NoProfile", "-NonInteractive", "-Command",
                              "(Get-CimInstance Win32_ComputerSystem).HypervisorPresent;"
                              "(Get-CimInstance Win32_Processor | Select-Object -First 1).VirtualizationFirmwareEnabled"),
                             timeout=8.0)
            vals = [x.strip() for x in o.splitlines() if x.strip()]
            if rc != 0 or len(vals) != 2 or any(v not in ("True", "False") for v in vals):
                raise Gap02Error(Code.MALFORMED_RESPONSE, "CIM virtualization")
            out.update({"hypervisor_present": vals[0] == "True", "firmware_enabled": vals[1] == "True"})
            # when Hyper-V is running, firmware bit reads False; hypervisor presence proves usability
            return ProbeEvidence("virtualization.host", vals[0] == "True" or vals[1] == "True", "api-bit", "CIM")
        raise Gap02Error(Code.UNSUPPORTED_PLATFORM, host.system)
    out["evidence"] = timed(body, "virtualization.host", "virt")
    derived = []
    if host.system == "Linux" and out["evidence"].result is not None:
        derived.append(ProbeEvidence("virtualization.iommu", out["iommu"], "kernel-attribute", "/sys/kernel/iommu_groups"))
        if out["nested"] is not None:
            derived.append(ProbeEvidence("virtualization.nested", out["nested"], "kernel-attribute", "kvm module"))
    out["derived"] = derived
    return out
