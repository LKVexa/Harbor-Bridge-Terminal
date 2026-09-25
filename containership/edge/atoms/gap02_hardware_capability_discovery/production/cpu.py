"""GAP02-MC-03 — Cross-platform CPU feature engine.

Sources (all authoritative kernel/OS reports, never model-name inference):
  Linux  : /proc/cpuinfo flags/Features (kernel-filtered CPUID/HWCAP view),
           /sys/devices/system/cpu topology
  macOS  : sysctl hw.optional.* API bits
  Windows: IsProcessorFeaturePresent API bits
Normalised feature vocabulary is arch-scoped: ``cpu.x86.avx2``, ``cpu.arm64.sve``.
"""
from __future__ import annotations

from typing import Any

from .errors import Code, Gap02Error
from .evidence import Host, ProbeEvidence, timed

ARCH = {"x86_64": "x86", "amd64": "x86", "i686": "x86", "i386": "x86",
        "aarch64": "arm64", "arm64": "arm64", "riscv64": "riscv64"}

# kernel flag → normalised name
X86 = {"sse4_2": "sse4.2", "avx": "avx", "avx2": "avx2", "avx512f": "avx512f", "avx512bw": "avx512bw",
       "avx512_vnni": "avx512vnni", "amx_tile": "amx", "aes": "aes", "sha_ni": "sha", "pclmulqdq": "pclmul",
       "vmx": "virt.vmx", "svm": "virt.svm", "sev": "sev", "sgx": "sgx", "rdrand": "rdrand",
       "bmi2": "bmi2", "fma": "fma", "hypervisor": "hypervisor-guest",
       "ept": "virt.slat", "npt": "virt.slat"}
ARM = {"asimd": "neon", "sve": "sve", "sve2": "sve2", "aes": "aes", "sha2": "sha2", "sha3": "sha3",
       "pmull": "pmull", "atomics": "lse", "asimddp": "dotprod", "bf16": "bf16", "i8mm": "i8mm", "sme": "sme"}
RISCV_EXT = {"v": "rvv", "f": "f", "d": "d", "c": "c", "a": "a", "m": "m"}
DARWIN = {"hw.optional.arm.FEAT_SVE": "sve", "hw.optional.neon": "neon", "hw.optional.arm.FEAT_AES": "aes",
          "hw.optional.arm.FEAT_SHA256": "sha2", "hw.optional.arm.FEAT_SME": "sme",
          "hw.optional.arm.FEAT_BF16": "bf16", "hw.optional.arm.FEAT_I8MM": "i8mm",
          "hw.optional.avx2_0": "avx2", "hw.optional.avx512f": "avx512f", "hw.optional.aes": "aes"}
WIN_PF = {17: ("x86", "sse4.2"), 39: ("x86", "avx2"), 41: ("x86", "avx512f"),
          21: ("x86", "virt.slat"), 30: ("arm64", "aes"), 43: ("arm64", "dotprod"), 34: ("arm64", "lse")}
KNOWN = {"x86": set(X86.values()), "arm64": set(ARM.values()), "riscv64": set(RISCV_EXT.values())}


def _topology(host: Host) -> dict[str, Any]:
    cpus = [c for c in host.listdir("/sys/devices/system/cpu") if c[3:].isdigit() and c.startswith("cpu")]
    pkgs, cores = set(), set()
    for c in cpus[:4096]:
        p = (host.read(f"/sys/devices/system/cpu/{c}/topology/physical_package_id") or "").strip()
        k = (host.read(f"/sys/devices/system/cpu/{c}/topology/core_id") or "").strip()
        if p:
            pkgs.add(p)
            if k:
                cores.add((p, k))
    return {"logical": len(cpus) or None, "packages": len(pkgs) or None, "cores": len(cores) or None}


def probe_cpu(host: Host | None = None) -> dict[str, Any]:
    host = host or Host()
    arch = ARCH.get(host.machine)
    features: set[str] = set()
    info: dict[str, Any] = {"arch": arch, "features": [], "topology": {}, "microarch": {}}

    def body() -> ProbeEvidence:
        if arch is None:
            raise Gap02Error(Code.UNSUPPORTED_PLATFORM, f"arch {host.machine!r}")
        if host.system == "Linux":
            text = host.read("/proc/cpuinfo")
            if not text:
                raise Gap02Error(Code.PROBE_UNAVAILABLE, "/proc/cpuinfo")
            for line in text.splitlines():
                k, _, v = line.partition(":")
                k = k.strip().lower()
                if k in ("flags", "features"):
                    table = X86 if arch == "x86" else ARM
                    features.update(table[f] for f in v.split() if f in table)
                elif k == "isa" and arch == "riscv64":
                    isa = v.strip().lower()
                    base = isa[4:].split("_")[0] if isa.startswith("rv64") else ""
                    features.update(RISCV_EXT[c] for c in base if c in RISCV_EXT)
                elif k in ("vendor_id", "cpu family", "model", "cpu implementer", "cpu part", "stepping"):
                    info["microarch"].setdefault(k.replace(" ", "_"), v.strip()[:32])
            info["topology"] = _topology(host)
            src = "/proc/cpuinfo"
        elif host.system == "Darwin":
            for key, name in DARWIN.items():
                try:
                    rc, out = host.run(("/usr/sbin/sysctl", "-n", key))
                except Gap02Error:
                    continue
                if rc == 0 and out.strip() == "1":
                    features.add(name)
            src = "sysctl hw.optional"
        elif host.system == "Windows":
            import ctypes
            fn = ctypes.windll.kernel32.IsProcessorFeaturePresent  # type: ignore[attr-defined]
            for pf, (a, name) in WIN_PF.items():
                if a == arch and fn(pf):
                    features.add(name)
            src = "IsProcessorFeaturePresent"
        else:
            raise Gap02Error(Code.UNSUPPORTED_PLATFORM, host.system)
        info["features"] = sorted(features)
        return ProbeEvidence("cpu.features", True, "kernel-attribute" if host.system == "Linux" else "api-bit",
                             src, {"count": len(features)})
    ev = timed(body, "cpu.features", "cpu")
    info["evidence"] = ev
    return info


def feature_evidence(info: dict[str, Any]) -> list[ProbeEvidence]:
    """Per-feature evidence. Features the source could not report stay unprobed
    (absence in an allow-listed source table is proof of absence only on Linux,
    where the kernel reports the full flag set)."""
    base: ProbeEvidence = info["evidence"]
    arch = info["arch"]
    out = []
    if base.result is not True or arch is None:
        return out
    full_set = base.source == "/proc/cpuinfo"
    for f in sorted(KNOWN.get(arch, ())):
        cap = f"cpu.{arch}.{f}"
        if f in info["features"]:
            out.append(ProbeEvidence(cap, True, base.kind, base.source))
        elif full_set:
            out.append(ProbeEvidence(cap, False, base.kind, base.source))
    return out
