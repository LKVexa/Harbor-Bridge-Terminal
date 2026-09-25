"""GAP02-MC-01 GPU compute probes and GAP02-MC-02 NPU probes.

Backend adapter contract: ``probe(host, cfg) -> list[AcceleratorDevice]`` plus a
per-backend ``ProbeEvidence``. A device is compute-*present* only when:
  1. a vendor runtime/management API answered (runtime-call proof),
  2. runtime↔driver compatibility is proven by the vendor rule table, and
  3. the health API answered healthy.
Display-adapter/PCI/driver presence never promotes (see evidence.promote).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from typing import Any

from .errors import Code, Gap02Error
from .evidence import Host, ProbeEvidence, timed, unknown

SCHEMA = "PK_ACCELERATOR_DEVICE/1"

# NVIDIA published minimum Linux driver per CUDA toolkit major.minor (forward-compat
# excluded). Source: CUDA Toolkit release notes, "CUDA Toolkit and Minimum Required
# Driver Version". Unknown runtime version → compatibility unproven.
NVIDIA_MIN_DRIVER = {
    (11, 0): (450, 80, 2), (11, 8): (450, 80, 2),
    (12, 0): (525, 60, 13), (12, 4): (525, 60, 13), (12, 8): (525, 60, 13),
    (13, 0): (580, 65, 6),
}


def _ver(text: str) -> tuple[int, ...]:
    parts = []
    for p in str(text).strip().split("."):
        if not p.isdigit():
            raise Gap02Error(Code.MALFORMED_RESPONSE, f"version {text!r}")
        parts.append(int(p))
    return tuple(parts)


def nvidia_compatible(runtime: str | None, driver: str) -> tuple[bool | None, str]:
    if not runtime:
        return None, "cuda runtime version not configured; compatibility unproven"
    r = _ver(runtime)[:2]
    rule = NVIDIA_MIN_DRIVER.get(r) or NVIDIA_MIN_DRIVER.get((r[0], 0))
    if rule is None:
        return None, f"no vendor rule for CUDA {runtime}"
    ok = _ver(driver) >= rule
    return ok, "" if ok else f"driver {driver} < minimum {'.'.join(map(str, rule))} for CUDA {runtime}"


@dataclass
class AcceleratorDevice:
    backend: str
    kind: str                       # gpu | npu | gpu-partition
    stable_id: str | None           # durable identity (UUID) — scheduling key
    enum_index: int | None          # ephemeral; never a scheduling identity
    runtime_version: str | None = None
    driver_version: str | None = None
    compute_api: bool | None = None
    memory_total_bytes: int | None = None
    memory_free_bytes: int | None = None
    health: str = "unknown"         # healthy | unhealthy | unknown
    compatible: bool | None = None
    incompatibility: str = ""
    parent_id: str | None = None
    partition_mode: str | None = None
    children: list[str] = field(default_factory=list)

    @property
    def schedulable(self) -> bool:
        return bool(self.stable_id and self.compute_api is True and self.compatible is True
                    and self.health == "healthy"
                    and not (self.kind == "gpu" and self.partition_mode == "enabled"))

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["schema"] = SCHEMA
        d["schedulable"] = self.schedulable
        return d


# --------------------------------------------------------------------- NVIDIA
NVSMI = "/usr/bin/nvidia-smi"
NV_QUERY = (NVSMI, "--query-gpu=uuid,index,driver_version,memory.total,memory.free,"
            "mig.mode.current,ecc.errors.uncorrected.volatile.total",
            "--format=csv,noheader,nounits")
NV_LIST = (NVSMI, "-L")
MIB = 1024 * 1024


def _nvidia(host: Host, cfg: dict[str, Any]) -> tuple[list[AcceleratorDevice], ProbeEvidence]:
    devices: list[AcceleratorDevice] = []

    def body() -> ProbeEvidence:
        if host.system not in ("Linux", "Windows"):
            raise Gap02Error(Code.UNSUPPORTED_PLATFORM, host.system)
        rc, out = host.run(NV_QUERY, timeout=cfg.get("timeout", 3.0))
        if rc == 9 or "couldn't communicate" in out.lower():
            raise Gap02Error(Code.DRIVER_ERROR, "NVML cannot reach driver")
        if rc != 0:
            raise Gap02Error(Code.DRIVER_ERROR, f"nvidia-smi rc={rc}")
        for line in out.strip().splitlines()[:64]:
            f = [x.strip() for x in line.split(",")]
            if len(f) != 7 or not f[0].startswith("GPU-"):
                raise Gap02Error(Code.MALFORMED_RESPONSE, line[:120])
            ok, why = nvidia_compatible(cfg.get("cuda_runtime_version"), f[2])
            ecc = f[6]
            health = "unknown" if ecc in ("[N/A]", "N/A", "") else ("healthy" if ecc == "0" else "unhealthy")
            devices.append(AcceleratorDevice(
                "nvidia-nvml", "gpu", f[0], int(f[1]), cfg.get("cuda_runtime_version"), f[2],
                True, int(f[3]) * MIB, int(f[4]) * MIB, health, ok, why,
                partition_mode={"Enabled": "enabled", "Disabled": "disabled"}.get(f[5])))
        if any(d.partition_mode == "enabled" for d in devices):
            _, lst = host.run(NV_LIST, timeout=cfg.get("timeout", 3.0))
            parent = None
            for line in lst.splitlines()[:512]:
                s = line.strip()
                if s.startswith("GPU ") and "UUID: GPU-" in s:
                    parent = s.split("UUID: ")[1].rstrip(")")
                elif s.startswith("MIG ") and "UUID: MIG-" in s and parent:
                    uid = s.split("UUID: ")[1].rstrip(")")
                    p = next(d for d in devices if d.stable_id == parent)
                    p.children.append(uid)
                    devices.append(AcceleratorDevice(
                        "nvidia-nvml", "gpu-partition", uid, None, p.runtime_version,
                        p.driver_version, True, None, None, p.health, p.compatible,
                        p.incompatibility, parent_id=parent, partition_mode="mig"))
        proven = any(d.schedulable for d in devices)
        return ProbeEvidence("gpu.compute.nvidia", proven if devices else False, "runtime-call",
                             "nvml:nvidia-smi", {"devices": len(devices)})
    return devices, timed(body, "gpu.compute.nvidia", "nvml:nvidia-smi")


# ------------------------------------------------------------------------ AMD
KFD = "/sys/class/kfd/kfd/topology/nodes"
ROCM_SMI = "/opt/rocm/bin/rocm-smi"


def _amd(host: Host, cfg: dict[str, Any]) -> tuple[list[AcceleratorDevice], ProbeEvidence]:
    devices: list[AcceleratorDevice] = []

    def body() -> ProbeEvidence:
        if host.system != "Linux":
            raise Gap02Error(Code.UNSUPPORTED_PLATFORM, host.system)
        nodes = host.listdir(KFD)
        if not nodes:
            raise Gap02Error(Code.PROBE_UNAVAILABLE, "no KFD topology (amdgpu compute driver absent)")
        rocm = (host.read("/opt/rocm/.info/version") or "").strip() or None
        health_map: dict[str, str] = {}
        try:
            rc, out = host.run((ROCM_SMI, "--showuniqueid", "--showhealth", "--json"))
            if rc == 0:
                for card, v in json.loads(out).items():
                    uid = str(v.get("Unique ID", "")).strip()
                    h = str(v.get("Health", "")).lower()
                    if uid:
                        health_map[uid] = "healthy" if h in ("ok", "good", "healthy") else "unhealthy"
        except (Gap02Error, ValueError, AttributeError):
            pass  # health unknown → fail closed below
        for n in nodes:
            props = host.read(f"{KFD}/{n}/properties") or ""
            kv = dict(l.split()[:2] for l in props.splitlines() if len(l.split()) >= 2)
            if int(kv.get("simd_count", "0") or 0) <= 0:
                continue  # CPU node
            uid = kv.get("unique_id")
            dev = AcceleratorDevice("amd-kfd", "gpu", f"AMD-{uid}" if uid and uid != "0" else None,
                                    int(n) if n.isdigit() else None, rocm, None,
                                    True if rocm else None, health=health_map.get(uid or "", "unknown"),
                                    compatible=True if rocm else None,
                                    incompatibility="" if rocm else "ROCm runtime not installed")
            devices.append(dev)
        return ProbeEvidence("gpu.compute.amd", any(d.schedulable for d in devices), "kernel-attribute",
                             "kfd-topology+rocm-smi", {"devices": len(devices)})
    return devices, timed(body, "gpu.compute.amd", "kfd-topology")


# ---------------------------------------------------------------------- Intel
CLINFO = "/usr/bin/clinfo"


def _intel(host: Host, cfg: dict[str, Any]) -> tuple[list[AcceleratorDevice], ProbeEvidence]:
    devices: list[AcceleratorDevice] = []

    def body() -> ProbeEvidence:
        if host.system not in ("Linux", "Windows"):
            raise Gap02Error(Code.UNSUPPORTED_PLATFORM, host.system)
        rc, out = host.run((CLINFO, "--json"))
        if rc != 0:
            raise Gap02Error(Code.DRIVER_ERROR, f"clinfo rc={rc}")
        data = json.loads(out)
        for pi, plat in enumerate(data.get("devices", [])[:16]):
            for di, d in enumerate(plat.get("online", [])[:16]):
                if "intel" not in str(d.get("CL_DEVICE_VENDOR", "")).lower():
                    continue
                if "GPU" not in str(d.get("CL_DEVICE_TYPE", "")):
                    continue
                devices.append(AcceleratorDevice(
                    "intel-opencl", "gpu", d.get("CL_DEVICE_UUID_KHR") or None, di,
                    str(d.get("CL_DEVICE_VERSION", "")) or None, str(d.get("CL_DRIVER_VERSION", "")) or None,
                    bool(d.get("CL_DEVICE_AVAILABLE")) and bool(d.get("CL_DEVICE_COMPILER_AVAILABLE")),
                    int(d.get("CL_DEVICE_GLOBAL_MEM_SIZE", 0)) or None, None, "unknown", True))
        return ProbeEvidence("gpu.compute.intel", any(d.schedulable for d in devices), "runtime-call",
                             "opencl:clinfo", {"devices": len(devices), "health_api": "none"})
    return devices, timed(body, "gpu.compute.intel", "opencl:clinfo")


# ---------------------------------------------------------------------- Apple
SYSPROF = "/usr/sbin/system_profiler"


def _apple(host: Host, cfg: dict[str, Any]) -> tuple[list[AcceleratorDevice], ProbeEvidence]:
    devices: list[AcceleratorDevice] = []

    def body() -> ProbeEvidence:
        if host.system != "Darwin":
            raise Gap02Error(Code.UNSUPPORTED_PLATFORM, host.system)
        rc, out = host.run((SYSPROF, "SPDisplaysDataType", "-json"), timeout=cfg.get("timeout", 8.0))
        if rc != 0:
            raise Gap02Error(Code.DRIVER_ERROR, f"system_profiler rc={rc}")
        for i, g in enumerate(json.loads(out).get("SPDisplaysDataType", [])[:8]):
            fam = g.get("spdisplays_mtlgpufamilysupport")
            devices.append(AcceleratorDevice("apple-metal", "gpu", None, i, None, None,
                                             bool(fam), None, None, "unknown", bool(fam)))
        # Metal exposes no stable device UUID or health API → never schedulable.
        return ProbeEvidence("gpu.compute.apple", any(d.schedulable for d in devices), "api-bit",
                             "metal:system_profiler", {"devices": len(devices),
                                                       "limitation": "no stable id / health API"})
    return devices, timed(body, "gpu.compute.apple", "metal:system_profiler")


GPU_BACKENDS = {"nvidia": _nvidia, "amd": _amd, "intel": _intel, "apple": _apple}


# ------------------------------------------------------------------------ NPU
NPU_DRIVERS = {"intel_vpu": "intel", "amdxdna": "amd", "qcom_fastrpc": "qualcomm"}


def _npu(host: Host, cfg: dict[str, Any]) -> tuple[list[AcceleratorDevice], ProbeEvidence]:
    """NPU presence requires a configured vendor runtime usability check
    (absolute-path command printing JSON ``{"usable": bool, "device_id": str,
    "runtime_version": str, "health": str}``). Driver/model names never promote."""
    devices: list[AcceleratorDevice] = []

    def body() -> ProbeEvidence:
        observed = []
        if host.system == "Linux":
            for a in host.listdir("/sys/class/accel"):
                drv = (host.read(f"/sys/class/accel/{a}/device/driver_name") or "").strip()
                if drv:
                    observed.append((a, NPU_DRIVERS.get(drv, drv)))
        elif host.system == "Darwin":
            raise Gap02Error(Code.UNSUPPORTED_PLATFORM, "Apple Neural Engine has no public usability API")
        checks = cfg.get("npu_runtime_checks", {})
        for vendor, argv in sorted(checks.items()):
            rc, out = host.run(tuple(argv), timeout=cfg.get("timeout", 5.0))
            if rc != 0:
                continue
            j = json.loads(out)
            if not isinstance(j.get("usable"), bool):
                raise Gap02Error(Code.MALFORMED_RESPONSE, "usable must be bool")
            devices.append(AcceleratorDevice(
                f"npu-{vendor}", "npu", j.get("device_id") or None, None, j.get("runtime_version"),
                j.get("driver_version"), j["usable"], health=str(j.get("health", "unknown")),
                compatible=j["usable"]))
        if not checks:
            raise Gap02Error(Code.PROBE_UNAVAILABLE,
                             f"no NPU runtime check configured; observed={observed}")
        return ProbeEvidence("npu.compute", any(d.schedulable for d in devices), "runtime-call",
                             "npu-runtime-check", {"observed_drivers": observed, "devices": len(devices)})
    return devices, timed(body, "npu.compute", "npu-runtime-check")


def probe_accelerators(host: Host | None = None, cfg: dict[str, Any] | None = None):
    host = host or Host()
    cfg = cfg or {}
    out: dict[str, Any] = {"devices": [], "evidence": []}
    for name, fn in GPU_BACKENDS.items():
        if name in cfg.get("disabled_backends", ()):
            continue
        devs, ev = fn(host, cfg)
        out["devices"] += devs
        out["evidence"].append(ev)
    devs, ev = _npu(host, cfg)
    out["devices"] += devs
    out["evidence"].append(ev)
    return out
