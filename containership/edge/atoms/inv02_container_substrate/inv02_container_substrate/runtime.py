"""Runtime-side components.

MC05 runtime integration (OCI runtime-spec bundle + runc/crun/runsc CLI adapter)
MC06 lifecycle controller (durable state machine)
MC07 namespace manager            MC08 cgroups v2 manager
MC10 networking modes             MC11 volumes          MC12 process supervision
MC22 seccomp default-deny         MC23 capability policy
MC24 user-namespace / rootless    MC25 MAC (AppArmor / SELinux labels)
MC26 no-new-privileges            MC27 device broker    MC28 secrets isolation
MC33 sandboxed runtime classes

Spec generation is pure and fully testable.  Execution paths call a real OCI runtime
binary and are exercised by the privileged integration suite (``tests/integration``),
which skips with an explicit reason when the host cannot run containers.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable

from .registry import IntegrityError, ValidationError
from .rootfs import DEFAULT_MOUNTS, validate_bind_mount
from .store import atomic_write
from .timeutil import Clock, SystemClock

OCI_RUNTIME_SPEC_VERSION = "1.1.0"

# --- MC23 capabilities -------------------------------------------------------------------
DEFAULT_CAPS = ("CAP_CHOWN", "CAP_DAC_OVERRIDE", "CAP_FSETID", "CAP_FOWNER", "CAP_MKNOD", "CAP_NET_RAW",
                "CAP_SETGID", "CAP_SETUID", "CAP_SETFCAP", "CAP_SETPCAP", "CAP_NET_BIND_SERVICE",
                "CAP_SYS_CHROOT", "CAP_KILL", "CAP_AUDIT_WRITE")
NEVER_WITHOUT_PRIVILEGED = frozenset({"CAP_SYS_ADMIN", "CAP_SYS_MODULE", "CAP_SYS_RAWIO", "CAP_SYS_PTRACE",
                                      "CAP_SYS_BOOT", "CAP_MAC_ADMIN", "CAP_MAC_OVERRIDE", "CAP_BPF",
                                      "CAP_PERFMON", "CAP_SYSLOG", "CAP_DAC_READ_SEARCH", "CAP_NET_ADMIN"})
_CAP_RE = re.compile(r"CAP_[A-Z_]+\Z")


def capability_set(add: list[str] = (), drop: list[str] = (), *, baseline: str = "restricted",
                   granted_sensitive: frozenset[str] = frozenset()) -> list[str]:
    """Compute the effective capability list.  ``restricted`` baseline is empty (drop ALL);
    ``default`` is the Docker-compatible set.  Sensitive caps need an explicit grant."""
    norm = lambda c: c.upper() if c.upper().startswith("CAP_") else "CAP_" + c.upper()
    add_n, drop_n = {norm(c) for c in add}, {norm(c) for c in drop}
    for c in add_n | drop_n:
        if c != "CAP_ALL" and not _CAP_RE.fullmatch(c):
            raise ValidationError(f"invalid capability {c}")
    base = set() if baseline == "restricted" or "CAP_ALL" in drop_n else set(DEFAULT_CAPS)
    ungranted = (add_n & NEVER_WITHOUT_PRIVILEGED) - granted_sensitive
    if ungranted:
        raise ValidationError(f"sensitive capabilities require an explicit grant: {sorted(ungranted)}")
    return sorted((base | add_n) - drop_n - {"CAP_ALL"})


# --- MC22 seccomp -----------------------------------------------------------------------
_SECCOMP_ALLOW = """accept accept4 access alarm bind brk capget capset chdir chmod chown clock_getres clock_gettime
clock_nanosleep close close_range connect copy_file_range creat dup dup2 dup3 epoll_create epoll_create1 epoll_ctl
epoll_pwait epoll_pwait2 epoll_wait eventfd eventfd2 execve execveat exit exit_group faccessat faccessat2 fadvise64
fallocate fchdir fchmod fchmodat fchown fchownat fcntl fdatasync fgetxattr flistxattr flock fork fremovexattr
fsetxattr fstat fstatfs fsync ftruncate futex futex_waitv getcpu getcwd getdents getdents64 getegid geteuid getgid
getgroups getitimer getpeername getpgid getpgrp getpid getppid getpriority getrandom getresgid getresuid getrlimit
get_robust_list getrusage getsid getsockname getsockopt gettid gettimeofday getuid getxattr inotify_add_watch
inotify_init inotify_init1 inotify_rm_watch io_cancel ioctl io_destroy io_getevents io_setup io_submit ioprio_get
ioprio_set kill lchown lgetxattr link linkat listen listxattr llistxattr lremovexattr lseek lsetxattr lstat madvise
membarrier memfd_create mincore mkdir mkdirat mknod mknodat mlock mlock2 mlockall mmap mprotect mq_getsetattr
mq_notify mq_open mq_timedreceive mq_timedsend mq_unlink mremap msgctl msgget msgrcv msgsnd msync munlock munlockall
munmap nanosleep newfstatat open openat openat2 pause pipe pipe2 poll ppoll prctl pread64 preadv preadv2 prlimit64
pselect6 pwrite64 pwritev pwritev2 read readahead readlink readlinkat readv recvfrom recvmmsg recvmsg remap_file_pages
removexattr rename renameat renameat2 restart_syscall rmdir rseq rt_sigaction rt_sigpending rt_sigprocmask
rt_sigqueueinfo rt_sigreturn rt_sigsuspend rt_sigtimedwait rt_tgsigqueueinfo sched_getaffinity sched_getattr
sched_getparam sched_get_priority_max sched_get_priority_min sched_getscheduler sched_rr_get_interval
sched_setaffinity sched_setattr sched_setparam sched_setscheduler sched_yield select semctl semget semop semtimedop
sendfile sendmmsg sendmsg sendto setfsgid setfsuid setgid setgroups setitimer setpgid setpriority setregid setresgid
setresuid setreuid setrlimit set_robust_list setsid setsockopt set_tid_address setuid setxattr shmat shmctl shmdt
shmget shutdown sigaltstack signalfd signalfd4 socket socketpair splice stat statfs statx symlink symlinkat sync
sync_file_range syncfs sysinfo tee tgkill time timer_create timer_delete timer_getoverrun timer_gettime
timer_settime timerfd_create timerfd_gettime timerfd_settime times tkill truncate umask uname unlink unlinkat
utime utimensat utimes vfork wait4 waitid waitpid write writev arch_prctl""".split()
# Explicitly never allowed even if a profile extension asks (escape-relevant).
SECCOMP_DENY_ALWAYS = frozenset({"kexec_load", "kexec_file_load", "init_module", "finit_module", "delete_module",
                                 "open_by_handle_at", "bpf", "perf_event_open", "userfaultfd", "keyctl", "add_key",
                                 "request_key", "ptrace", "mount", "umount2", "pivot_root", "swapon", "swapoff",
                                 "reboot", "setns", "unshare", "iopl", "ioperm", "quotactl", "acct",
                                 "lookup_dcookie", "name_to_handle_at", "fsopen", "fsmount", "move_mount",
                                 "open_tree", "fspick", "process_vm_readv", "process_vm_writev"})


def seccomp_profile(extra_allow: list[str] = (), arches: tuple[str, ...] = ("SCMP_ARCH_X86_64", "SCMP_ARCH_AARCH64")) -> dict:
    bad = set(extra_allow) & SECCOMP_DENY_ALWAYS
    if bad:
        raise ValidationError(f"seccomp: syscalls cannot be allowed: {sorted(bad)}")
    names = sorted(set(_SECCOMP_ALLOW) | set(extra_allow))
    return {"defaultAction": "SCMP_ACT_ERRNO", "defaultErrnoRet": 1, "architectures": list(arches),
            "syscalls": [{"names": names, "action": "SCMP_ACT_ALLOW"},
                         # clone only without namespace-creating flags (CLONE_NEW* mask 0x7E020000)
                         {"names": ["clone"], "action": "SCMP_ACT_ALLOW",
                          "args": [{"index": 0, "value": 0x7E020000, "valueTwo": 0, "op": "SCMP_CMP_MASKED_EQ"}]},
                         # clone3 flags live in a struct seccomp cannot inspect: return ENOSYS so
                         # libc falls back to the filtered clone(2).
                         {"names": ["clone3"], "action": "SCMP_ACT_ERRNO", "errnoRet": 38}]}


# --- MC24 user namespaces ------------------------------------------------------------------
@dataclass(frozen=True)
class IDMap:
    container_id: int
    host_id: int
    size: int


def subid_range(user: str, path: str = "/etc/subuid") -> IDMap:
    """Read the first subordinate id range for ``user`` (rootless mapping)."""
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                parts = line.strip().split(":")
                if len(parts) == 3 and parts[0] == user:
                    start, count = int(parts[1]), int(parts[2])
                    if count < 65536:
                        raise ValidationError(f"{path}: {user} needs >= 65536 subordinate ids")
                    return IDMap(0, start, 65536)
    except FileNotFoundError:
        pass
    raise ValidationError(f"{path}: no subordinate id range for {user!r}")


# --- MC27 devices ---------------------------------------------------------------------------
DEFAULT_DEVICE_RULES = [
    {"allow": False, "access": "rwm"},
    *[{k: v for k, v in {"allow": True, "type": "c", "major": maj, "minor": mnr, "access": "rwm"}.items() if v is not None}
      for maj, mnr in ((1, 3), (1, 5), (1, 7), (1, 8), (1, 9), (5, 0), (5, 1), (5, 2), (136, None))],
]


# --- MC08 cgroups v2 --------------------------------------------------------------------------
@dataclass(frozen=True)
class Resources:
    cpu_quota_us: int | None = None
    cpu_period_us: int = 100_000
    cpu_weight: int | None = None
    memory_max: int | None = None
    memory_high: int | None = None
    swap_max: int | None = 0
    pids_max: int | None = 4096
    io_weight: int | None = None

    def validate(self) -> None:
        if self.memory_max is not None and self.memory_max < 6 * 1024 * 1024:
            raise ValidationError("memory_max below 6MiB is not schedulable")
        if self.pids_max is not None and not (1 <= self.pids_max <= 4_194_304):
            raise ValidationError("pids_max out of range")
        if self.cpu_weight is not None and not (1 <= self.cpu_weight <= 10000):
            raise ValidationError("cpu_weight out of range")
        if self.cpu_quota_us is not None and self.cpu_quota_us < 1000:
            raise ValidationError("cpu quota below 1ms")

    def to_oci(self) -> dict:
        self.validate()
        r: dict = {"devices": DEFAULT_DEVICE_RULES}
        if self.memory_max is not None:
            r["memory"] = {"limit": self.memory_max, "swap": self.memory_max + (self.swap_max or 0)}
        if self.cpu_quota_us or self.cpu_weight:
            r["cpu"] = {k: v for k, v in (("quota", self.cpu_quota_us), ("period", self.cpu_period_us),
                                          ("shares", self.cpu_weight)) if v}
        if self.pids_max:
            r["pids"] = {"limit": self.pids_max}
        return r


class CgroupV2Manager:
    """Direct cgroup v2 filesystem manager (used when the runtime delegates cgroup
    creation, or for supervisor-owned processes).  ``root`` defaults to the unified
    hierarchy; tests pass a temporary directory laid out like cgroupfs."""

    NAME_RE = re.compile(r"[A-Za-z0-9_.-]{1,128}\Z")

    def __init__(self, root: str = "/sys/fs/cgroup", parent: str = "inv02.slice") -> None:
        self.root = Path(root)
        self.parent = self.root / parent

    @staticmethod
    def available(root: str = "/sys/fs/cgroup") -> bool:
        return Path(root, "cgroup.controllers").is_file()

    def create(self, name: str, res: Resources) -> Path:
        if not self.NAME_RE.fullmatch(name):
            raise ValidationError("invalid cgroup name")
        res.validate()
        self.parent.mkdir(exist_ok=True)
        ctrl = (self.root / "cgroup.controllers").read_text().split() if (self.root / "cgroup.controllers").exists() else []
        want = [c for c in ("cpu", "memory", "pids", "io") if c in ctrl]
        if want and (self.parent / "cgroup.subtree_control").exists():
            (self.parent / "cgroup.subtree_control").write_text(" ".join("+" + c for c in want))
        cg = self.parent / name
        cg.mkdir(exist_ok=False)
        writes = {"memory.max": res.memory_max, "memory.high": res.memory_high, "memory.swap.max": res.swap_max,
                  "pids.max": res.pids_max, "cpu.weight": res.cpu_weight, "io.weight": res.io_weight}
        if res.cpu_quota_us:
            writes["cpu.max"] = f"{res.cpu_quota_us} {res.cpu_period_us}"
        for f, v in writes.items():
            if v is not None:
                (cg / f).write_text(str(v))
        return cg

    def add_process(self, name: str, pid: int) -> None:
        (self.parent / name / "cgroup.procs").write_text(str(pid))

    def stats(self, name: str) -> dict:
        cg, out = self.parent / name, {}
        for f in ("memory.current", "pids.current", "memory.events", "cpu.stat"):
            p = cg / f
            if p.exists():
                txt = p.read_text().strip()
                out[f] = int(txt) if txt.isdigit() else dict(l.split() for l in txt.splitlines() if " " in l)
        return out

    def destroy(self, name: str) -> None:
        cg = self.parent / name
        if (cg / "cgroup.kill").exists():
            (cg / "cgroup.kill").write_text("1")
        for child in sorted(cg.glob("*/"), reverse=True):
            if child.is_dir():
                child.rmdir()
        try:
            cg.rmdir()
        except OSError:
            # On a real cgroupfs the interface files vanish with rmdir; in test trees
            # they are regular files and must be removed first.
            for f in cg.iterdir():
                f.unlink()
            cg.rmdir()


# --- spec builder --------------------------------------------------------------------------
@dataclass
class ContainerConfig:
    """Workload request.  Security-relevant defaults fail closed."""
    args: list[str]
    env: dict[str, str] = field(default_factory=dict)
    cwd: str = "/"
    user: tuple[int, int] = (65534, 65534)
    hostname: str = "container"
    readonly_rootfs: bool = True
    cap_add: list[str] = field(default_factory=list)
    cap_baseline: str = "restricted"
    privileged: bool = False
    no_new_privileges: bool = True
    network: str = "none"  # none | loopback | netns:<path>
    rootless: bool = True
    uid_map: IDMap | None = None
    gid_map: IDMap | None = None
    resources: Resources = field(default_factory=Resources)
    binds: list[dict] = field(default_factory=list)  # {source, destination, options}
    volumes: list[dict] = field(default_factory=list)  # {name, destination, readonly}
    secrets: dict[str, bytes] = field(default_factory=dict)  # name -> value (mounted, never env)
    devices: list[str] = field(default_factory=list)
    apparmor_profile: str | None = "inv02-default"
    selinux_label: str | None = None
    seccomp_extra: list[str] = field(default_factory=list)
    runtime_class: str = "runc"
    nofile: int = 65536


RUNTIME_CLASSES = {"runc": "runc", "crun": "crun", "gvisor": "runsc", "kata": "kata-runtime"}
SANDBOXED_CLASSES = frozenset({"gvisor", "kata"})
_ENV_KEY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_SECRET_NAME_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,62}\Z")


def build_spec(cfg: ContainerConfig, *, rootfs: str = "rootfs", secrets_dir: str | None = None,
               volume_root: str | None = None, bind_prefixes: tuple[str, ...] = (),
               granted: frozenset[str] = frozenset()) -> dict:
    """Produce an OCI runtime-spec ``config.json`` document."""
    if not cfg.args or not all(isinstance(a, str) for a in cfg.args):
        raise ValidationError("args must be a non-empty list of strings")
    for k, v in cfg.env.items():
        if not _ENV_KEY_RE.fullmatch(k) or "\x00" in v:
            raise ValidationError(f"invalid env var {k!r}")
        if re.search(r"(PASSWORD|SECRET|TOKEN|PRIVATE_KEY)", k, re.I):
            raise ValidationError(f"secret-like env var {k!r}: deliver secrets as mounted files (MC28)")
    if cfg.privileged and "privileged" not in granted:
        raise ValidationError("privileged containers require an explicit grant")
    if cfg.runtime_class not in RUNTIME_CLASSES:
        raise ValidationError(f"unknown runtime class {cfg.runtime_class!r}")
    caps = capability_set(cfg.cap_add, baseline=cfg.cap_baseline,
                          granted_sensitive=frozenset("CAP_" + c[4:].upper().removeprefix("CAP_")
                                                    for c in granted if c.startswith("cap:")))
    ns = [{"type": t} for t in ("pid", "ipc", "uts", "mount", "cgroup")]
    if cfg.network == "none" or cfg.network == "loopback":
        ns.append({"type": "network"})
    elif cfg.network.startswith("netns:"):
        path = cfg.network[6:]
        if not path.startswith(("/var/run/netns/", "/run/netns/", "/proc/")):
            raise ValidationError("network namespace path not allowed")
        ns.append({"type": "network", "path": path})
    elif cfg.network == "host":
        if "host_network" not in granted:
            raise ValidationError("host networking requires an explicit grant")
    else:
        raise ValidationError(f"unknown network mode {cfg.network!r}")
    linux: dict = {"namespaces": ns, "resources": json.loads(json.dumps(cfg.resources.to_oci())),
                   "maskedPaths": ["/proc/acpi", "/proc/asound", "/proc/kcore", "/proc/keys", "/proc/latency_stats",
                                   "/proc/timer_list", "/proc/timer_stats", "/proc/sched_debug", "/proc/scsi",
                                   "/sys/firmware", "/sys/devices/virtual/powercap"],
                   "readonlyPaths": ["/proc/bus", "/proc/fs", "/proc/irq", "/proc/sys", "/proc/sysrq-trigger"]}
    if not cfg.privileged:
        linux["seccomp"] = seccomp_profile(cfg.seccomp_extra)
    if cfg.rootless or cfg.uid_map:
        ns.append({"type": "user"})
        um = cfg.uid_map or IDMap(0, 100000, 65536)
        gm = cfg.gid_map or um
        linux["uidMappings"] = [{"containerID": um.container_id, "hostID": um.host_id, "size": um.size}]
        linux["gidMappings"] = [{"containerID": gm.container_id, "hostID": gm.host_id, "size": gm.size}]
    if cfg.selinux_label:
        linux["mountLabel"] = cfg.selinux_label
    mounts = [dict(m) for m in DEFAULT_MOUNTS]
    for b in cfg.binds:
        mounts.append({"destination": b["destination"], "type": "bind", "source": os.path.realpath(b["source"]),
                       "options": validate_bind_mount(b["source"], b["destination"], b.get("options", []), bind_prefixes)})
    for v in cfg.volumes:  # MC11 named volumes
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,62}", v["name"]) or not volume_root:
            raise ValidationError("invalid volume or no volume root")
        src = os.path.join(volume_root, v["name"])
        mounts.append({"destination": v["destination"], "type": "bind", "source": src,
                       "options": ["rbind", "nosuid", "nodev", "rprivate", "ro" if v.get("readonly") else "rw"]})
    if cfg.secrets:  # MC28 secrets: tmpfs-backed dir, files 0400, read-only mount
        if not secrets_dir:
            raise ValidationError("secrets require a secrets_dir (tmpfs recommended)")
        for name in cfg.secrets:
            if not _SECRET_NAME_RE.fullmatch(name):
                raise ValidationError(f"invalid secret name {name!r}")
        mounts.append({"destination": "/run/secrets", "type": "bind", "source": secrets_dir,
                       "options": ["rbind", "ro", "nosuid", "nodev", "noexec", "rprivate"]})
    for dev in cfg.devices:  # MC27
        if f"device:{dev}" not in granted:
            raise ValidationError(f"device {dev} requires an explicit grant")
        st = os.stat(dev)
        linux.setdefault("devices", []).append({"path": dev, "type": "c", "major": os.major(st.st_rdev),
                                                "minor": os.minor(st.st_rdev), "fileMode": 0o660})
        linux["resources"]["devices"].append({"allow": True, "type": "c", "major": os.major(st.st_rdev),
                                              "minor": os.minor(st.st_rdev), "access": "rw"})
    process = {"terminal": False, "user": {"uid": cfg.user[0], "gid": cfg.user[1]}, "args": list(cfg.args),
               "env": ["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"]
                      + [f"{k}={v}" for k, v in sorted(cfg.env.items())],
               "cwd": cfg.cwd, "noNewPrivileges": bool(cfg.no_new_privileges or not cfg.privileged),
               "capabilities": {k: caps for k in ("bounding", "effective", "permitted")} | {"ambient": [], "inheritable": []},
               "rlimits": [{"type": "RLIMIT_NOFILE", "hard": cfg.nofile, "soft": cfg.nofile}]}
    if cfg.apparmor_profile:
        process["apparmorProfile"] = cfg.apparmor_profile
    if cfg.selinux_label:
        process["selinuxLabel"] = cfg.selinux_label
    return {"ociVersion": OCI_RUNTIME_SPEC_VERSION, "process": process,
            "root": {"path": rootfs, "readonly": cfg.readonly_rootfs}, "hostname": cfg.hostname,
            "mounts": mounts, "linux": linux}


def write_secrets(secrets_dir: str, secrets: dict[str, bytes]) -> None:
    os.makedirs(secrets_dir, mode=0o700, exist_ok=True)
    for name, value in secrets.items():
        if not _SECRET_NAME_RE.fullmatch(name):
            raise ValidationError(f"invalid secret name {name!r}")
        atomic_write(Path(secrets_dir) / name, value, 0o400)


# --- MC06 lifecycle -------------------------------------------------------------------------
class State(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    DELETED = "deleted"
    FAILED = "failed"


TRANSITIONS = {
    State.CREATED: {State.RUNNING, State.DELETED, State.FAILED},
    State.RUNNING: {State.PAUSED, State.STOPPED, State.FAILED},
    State.PAUSED: {State.RUNNING, State.STOPPED, State.FAILED},
    State.STOPPED: {State.DELETED, State.RUNNING},
    State.FAILED: {State.DELETED},
    State.DELETED: set(),
}


class IllegalTransition(IntegrityError):
    code = "LIFECYCLE_ILLEGAL_TRANSITION"


class LifecycleStore:
    """Durable per-container state records with monotonic generation (MC06 / MC15)."""

    def __init__(self, root: str | os.PathLike, clock: Clock | None = None) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.clock = clock or SystemClock()
        self._lock = threading.Lock()

    def _p(self, cid: str) -> Path:
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}", cid):
            raise ValidationError("invalid container id")
        return self.root / f"{cid}.json"

    def get(self, cid: str) -> dict | None:
        p = self._p(cid)
        return json.loads(p.read_text()) if p.exists() else None

    def create(self, cid: str, spec_digest: str, image_digest: str) -> dict:
        with self._lock:
            if self._p(cid).exists():
                raise ValidationError(f"container {cid} exists")
            rec = {"id": cid, "state": State.CREATED.value, "generation": 1, "spec_digest": spec_digest,
                   "image_digest": image_digest, "history": [[self.clock.now(), State.CREATED.value, "create"]]}
            atomic_write(self._p(cid), json.dumps(rec).encode())
            return rec

    def transition(self, cid: str, to: State, reason: str, *, expected_generation: int | None = None) -> dict:
        with self._lock:
            rec = self.get(cid)
            if rec is None:
                raise ValidationError(f"no container {cid}")
            cur = State(rec["state"])
            if expected_generation is not None and rec["generation"] != expected_generation:
                raise IllegalTransition("stale generation (concurrent update)")
            if to not in TRANSITIONS[cur]:
                raise IllegalTransition(f"{cur.value} -> {to.value} not allowed")
            rec["state"] = to.value
            rec["generation"] += 1
            rec["history"] = (rec["history"] + [[self.clock.now(), to.value, reason]])[-64:]
            atomic_write(self._p(cid), json.dumps(rec).encode())
            return rec

    def list(self) -> list[dict]:
        return [json.loads(p.read_text()) for p in sorted(self.root.glob("*.json"))]


# --- MC05 OCI runtime adapter ---------------------------------------------------------------
class RuntimeUnavailable(RuntimeError):
    code = "RUNTIME_UNAVAILABLE"


class OCIRuntime:
    """Thin, argument-safe adapter over an OCI runtime CLI (runc/crun/runsc/kata)."""

    def __init__(self, runtime_class: str = "runc", *, state_root: str | None = None, rootless: bool | None = None,
                 timeout_s: float = 30.0) -> None:
        binary = RUNTIME_CLASSES.get(runtime_class)
        if binary is None:
            raise ValidationError(f"unknown runtime class {runtime_class}")
        self.path = shutil.which(binary)
        if not self.path:
            raise RuntimeUnavailable(f"{binary} not found on PATH")
        self.cls = runtime_class
        self.state_root = state_root
        self.rootless = rootless
        self.timeout = timeout_s

    def _cmd(self, *args: str) -> list[str]:
        cmd = [self.path]
        if self.state_root:
            cmd += ["--root", self.state_root]
        if self.rootless is not None and self.cls in ("runc", "crun"):
            cmd += [f"--rootless={'true' if self.rootless else 'false'}"]
        return cmd + list(args)

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(self._cmd(*args), capture_output=True, text=True, timeout=self.timeout, check=check)

    def version(self) -> str:
        return self._run("--version").stdout.strip()

    def run(self, cid: str, bundle: str) -> subprocess.CompletedProcess:
        """Create+start+wait (foreground) — used by integration tests and one-shot jobs."""
        return self._run("run", "--bundle", bundle, cid, check=False)

    def create(self, cid: str, bundle: str) -> None:
        self._run("create", "--bundle", bundle, cid)

    def start(self, cid: str) -> None:
        self._run("start", cid)

    def state(self, cid: str) -> dict:
        return json.loads(self._run("state", cid).stdout)

    def kill(self, cid: str, sig: str = "TERM") -> None:
        self._run("kill", cid, sig, check=False)

    def delete(self, cid: str, force: bool = False) -> None:
        self._run("delete", *(["--force"] if force else []), cid, check=False)


# --- MC12 process supervision ---------------------------------------------------------------
@dataclass
class SupervisorPolicy:
    restart: str = "on-failure"  # never | on-failure | always
    max_restarts: int = 5
    backoff_base_s: float = 0.5
    backoff_max_s: float = 30.0
    stop_grace_s: float = 10.0


class Supervisor:
    """Supervise a child process: restart with exponential backoff, graceful stop
    (SIGTERM → grace → SIGKILL), and exit-status reporting."""

    def __init__(self, argv: list[str], policy: SupervisorPolicy | None = None, *,
                 on_event: Callable[[str, dict], None] | None = None, clock: Clock | None = None) -> None:
        self.argv, self.policy = argv, policy or SupervisorPolicy()
        self.on_event = on_event or (lambda e, f: None)
        self.clock = clock or SystemClock()
        self.proc: subprocess.Popen | None = None
        self.restarts = 0
        self.exits: list[int] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.proc = subprocess.Popen(self.argv, start_new_session=True)
            self.on_event("process.start", {"pid": self.proc.pid})
            rc = self.proc.wait()
            self.exits.append(rc)
            self.on_event("process.exit", {"rc": rc})
            if self._stop.is_set():
                break
            want = self.policy.restart == "always" or (self.policy.restart == "on-failure" and rc != 0)
            if not want or self.restarts >= self.policy.max_restarts:
                self.on_event("process.gave_up" if want else "process.done", {"restarts": self.restarts})
                break
            self.restarts += 1
            delay = min(self.policy.backoff_max_s, self.policy.backoff_base_s * 2 ** (self.restarts - 1))
            if self._stop.wait(delay):
                break

    def stop(self) -> int | None:
        self._stop.set()
        p = self.proc
        if p and p.poll() is None:
            with _suppress():
                os.killpg(p.pid, signal.SIGTERM)
            try:
                p.wait(self.policy.stop_grace_s)
            except subprocess.TimeoutExpired:
                with _suppress():
                    os.killpg(p.pid, signal.SIGKILL)
                p.wait()
        if self._thread:
            self._thread.join(self.policy.stop_grace_s + 5)
        return p.returncode if p else None

    def wait_done(self, timeout: float) -> bool:
        if self._thread:
            self._thread.join(timeout)
            return not self._thread.is_alive()
        return True


class _suppress:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return exc[0] is not None and issubclass(exc[0], ProcessLookupError)
