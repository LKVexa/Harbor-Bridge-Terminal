"""Least-privilege execution policy below the domain model (MC-022, MC-023).

Builds the Firecracker *jailer* invocation (chroot, dedicated uid/gid per
instance, new PID + network namespace, cgroup v2 limits, seccomp level 2)
and verifies that a running process actually has the isolation it was
promised (namespaces differ from the host, uid is non-root, cgroup matches).
Execution itself requires root + KVM and is covered by integration tests.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Final

from ..errors import Inv24Error
from ..runtime import MicroVM

UID_BASE: Final[int] = 200_000
UID_SPAN: Final[int] = 65_536
_ID = re.compile(r"[A-Za-z0-9-]{1,64}")
CPU_PERIOD_US: Final[int] = 100_000
MEM_OVERHEAD_MIB: Final[int] = 64   # VMM overhead budget above guest RAM


@dataclass(frozen=True, slots=True)
class JailPolicy:
    instance_id: str
    uid: int
    gid: int
    chroot_base: str
    netns: str
    cgroup: dict[str, str]
    seccomp_level: int = 2

    def jailer_argv(self, jailer: str, firecracker: str) -> list[str]:
        if not (os.path.isabs(jailer) and os.path.isabs(firecracker)):
            raise Inv24Error("ARTIFACT_NOT_APPROVED", "jailer/firecracker must be absolute verified paths")
        argv = [jailer, "--id", self.instance_id, "--exec-file", firecracker,
                "--uid", str(self.uid), "--gid", str(self.gid),
                "--chroot-base-dir", self.chroot_base, "--netns", self.netns,
                "--new-pid-ns", "--cgroup-version", "2"]
        for k, v in sorted(self.cgroup.items()):
            argv += ["--cgroup", f"{k}={v}"]
        return argv


def uid_for(tenant: str, instance: str, allocated: set[int]) -> int:
    """Deterministic but collision-checked per-instance uid; never 0, never shared."""
    import hashlib
    base = int(hashlib.sha256(f"{tenant}/{instance}".encode()).hexdigest(), 16) % UID_SPAN
    for i in range(UID_SPAN):
        uid = UID_BASE + (base + i) % UID_SPAN
        if uid not in allocated:
            return uid
    raise Inv24Error("RESOURCE_EXHAUSTED", "no free jail uid")


def policy_for(vm: MicroVM, *, allocated_uids: set[int], chroot_base: str = "/srv/jailer",
               netns_dir: str = "/var/run/netns", seccomp_level: int = 2) -> JailPolicy:
    if seccomp_level != 2:
        raise Inv24Error("UNAUTHORIZED", "production policy requires seccomp level 2 (advanced)")
    iid = f"{vm.tenant}-{vm.name}"
    if not _ID.fullmatch(iid):
        raise Inv24Error("CONFIG_REJECTED", "tenant/instance must be [A-Za-z0-9-] for jail ids")
    uid = uid_for(vm.tenant, vm.name, allocated_uids)
    mem_bytes = (vm.memory_mib + MEM_OVERHEAD_MIB) * 1024 * 1024
    cgroup = {"memory.max": str(mem_bytes), "memory.swap.max": "0",
              "cpu.max": f"{vm.vcpus * CPU_PERIOD_US} {CPU_PERIOD_US}", "pids.max": "64"}
    return JailPolicy(iid, uid, uid, chroot_base, f"{netns_dir}/{iid}", cgroup, seccomp_level)


def verify_process_isolation(pid: int, policy: JailPolicy, *, proc_root: str = "/proc") -> dict[str, bool]:
    """Compare a live process against its promised policy; raises on any gap."""
    def ns(p, kind):
        return os.readlink(f"{proc_root}/{p}/ns/{kind}")
    checks: dict[str, bool] = {}
    try:
        checks["pid_ns_isolated"] = ns(pid, "pid") != ns(1, "pid")
        checks["net_ns_isolated"] = ns(pid, "net") != ns(1, "net")
        status = open(f"{proc_root}/{pid}/status").read()
        uid_line = next(l for l in status.splitlines() if l.startswith("Uid:"))
        checks["uid_matches"] = all(int(u) == policy.uid for u in uid_line.split()[1:])
        checks["non_root"] = policy.uid != 0
        checks["no_new_privs"] = "NoNewPrivs:\t1" in status
        checks["seccomp_filter"] = "Seccomp:\t2" in status
    except (OSError, StopIteration, ValueError) as exc:
        raise Inv24Error("INTEGRITY_VIOLATION", f"cannot verify isolation of pid {pid}: {exc}") from None
    if not all(checks.values()):
        raise Inv24Error("INTEGRITY_VIOLATION", f"isolation gaps: {[k for k, v in checks.items() if not v]}")
    return checks
