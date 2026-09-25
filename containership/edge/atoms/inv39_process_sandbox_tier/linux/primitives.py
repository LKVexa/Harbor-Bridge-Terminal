"""Linux containment primitives used by the pre-exec launcher.

MC-035 uid/gid/groups + user-namespace mapping + SECBIT_NOROOT (no regain on exec)
MC-036 capability sets: bounding drop, ambient clear, capset(eff/prm/inh)
MC-037 mount namespace: recursive MS_PRIVATE propagation, private tmpfs
MC-039 network namespace: fresh empty netns (loopback only, down)
MC-040 fresh /proc (hidepid=2) inside pid+mount ns; no device nodes created; /sys and /dev read-only views delegated to bwrap
MC-041 fd closure to an explicit allow-list
MC-042 environment allow-list with loader/interpreter variable stripping
MC-043 rlimits (NPROC, AS, CPU, NOFILE, FSIZE, CORE=0)
"""
from __future__ import annotations

import ctypes
import ctypes.util
import os
import resource

from ..errors import SandboxError

CAPS = [
    "CAP_CHOWN", "CAP_DAC_OVERRIDE", "CAP_DAC_READ_SEARCH", "CAP_FOWNER", "CAP_FSETID",
    "CAP_KILL", "CAP_SETGID", "CAP_SETUID", "CAP_SETPCAP", "CAP_LINUX_IMMUTABLE",
    "CAP_NET_BIND_SERVICE", "CAP_NET_BROADCAST", "CAP_NET_ADMIN", "CAP_NET_RAW",
    "CAP_IPC_LOCK", "CAP_IPC_OWNER", "CAP_SYS_MODULE", "CAP_SYS_RAWIO", "CAP_SYS_CHROOT",
    "CAP_SYS_PTRACE", "CAP_SYS_PACCT", "CAP_SYS_ADMIN", "CAP_SYS_BOOT", "CAP_SYS_NICE",
    "CAP_SYS_RESOURCE", "CAP_SYS_TIME", "CAP_SYS_TTY_CONFIG", "CAP_MKNOD", "CAP_LEASE",
    "CAP_AUDIT_WRITE", "CAP_AUDIT_CONTROL", "CAP_SETFCAP", "CAP_MAC_OVERRIDE",
    "CAP_MAC_ADMIN", "CAP_SYSLOG", "CAP_WAKE_ALARM", "CAP_BLOCK_SUSPEND", "CAP_AUDIT_READ",
    "CAP_PERFMON", "CAP_BPF", "CAP_CHECKPOINT_RESTORE",
]
CAP_INDEX = {n: i for i, n in enumerate(CAPS)}

CLONE_NEWNS, CLONE_NEWUTS, CLONE_NEWIPC = 0x00020000, 0x04000000, 0x08000000
CLONE_NEWUSER, CLONE_NEWPID, CLONE_NEWNET = 0x10000000, 0x20000000, 0x40000000
NS_FLAGS = {"mount": CLONE_NEWNS, "uts": CLONE_NEWUTS, "ipc": CLONE_NEWIPC,
            "user": CLONE_NEWUSER, "pid": CLONE_NEWPID, "net": CLONE_NEWNET}
NS_PROC = {"mount": "mnt", "uts": "uts", "ipc": "ipc", "user": "user", "pid": "pid", "net": "net"}

PR_CAPBSET_DROP, PR_SET_SECUREBITS, PR_CAP_AMBIENT, PR_CAP_AMBIENT_CLEAR_ALL = 24, 28, 47, 4
PR_SET_PDEATHSIG, PR_SET_CHILD_SUBREAPER, PR_SET_DUMPABLE = 1, 36, 4
SECBIT_NOROOT, SECBIT_NOROOT_LOCKED = 1 << 0, 1 << 1
SECBIT_NO_SETUID_FIXUP, SECBIT_NO_SETUID_FIXUP_LOCKED = 1 << 2, 1 << 3
SECBIT_KEEP_CAPS_LOCKED, SECBIT_NO_CAP_AMBIENT_RAISE, SECBIT_NO_CAP_AMBIENT_RAISE_LOCKED = 1 << 5, 1 << 6, 1 << 7
MS_REC, MS_PRIVATE, MS_NOSUID, MS_NODEV, MS_NOEXEC = 0x4000, 1 << 18, 2, 4, 8

# MC-042: variables that change loader/interpreter behaviour are never passed through
DANGEROUS_ENV_PREFIXES = ("LD_", "DYLD_", "PYTHON", "PERL5", "PERLLIB", "RUBYOPT", "RUBYLIB",
                          "NODE_OPTIONS", "JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "BASH_ENV", "ENV",
                          "IFS", "GCONV_PATH", "MALLOC_", "GLIBC_TUNABLES", "HOSTALIASES", "LOCALDOMAIN",
                          "RES_OPTIONS", "TMPDIR", "NLSPATH", "GETCONF_DIR", "SHELLOPTS", "PS4")
SAFE_DEFAULT_ENV = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}

_libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)


def _check(rc: int, what: str) -> None:
    if rc != 0:
        e = ctypes.get_errno()
        raise SandboxError("E_APPLY_FAILED", f"{what} failed: {os.strerror(e)}")


def prctl(opt: int, a: int = 0, b: int = 0, c: int = 0, d: int = 0) -> int:
    return _libc.prctl(opt, ctypes.c_ulong(a), ctypes.c_ulong(b), ctypes.c_ulong(c), ctypes.c_ulong(d))


def unshare(flags: int) -> None:
    _check(_libc.unshare(flags), f"unshare(0x{flags:x})")


def ns_flags(names) -> int:
    f = 0
    for n in names:
        if n not in NS_FLAGS:
            raise SandboxError("E_PROFILE_INVALID", f"unknown namespace {n!r}")
        f |= NS_FLAGS[n]
    return f


def write_id_maps(uid: int, gid: int, inner_uid: int = 0, inner_gid: int = 0) -> None:
    """Map exactly one id each into the new user namespace (deny setgroups first)."""
    with open("/proc/self/setgroups", "w") as f:
        f.write("deny")
    with open("/proc/self/uid_map", "w") as f:
        f.write(f"{inner_uid} {uid} 1")
    with open("/proc/self/gid_map", "w") as f:
        f.write(f"{inner_gid} {gid} 1")


def make_mounts_private() -> None:
    _check(_libc.mount(None, b"/", None, ctypes.c_ulong(MS_REC | MS_PRIVATE), None), "mount(MS_PRIVATE)")


def mount_private_tmpfs(path: str, size_bytes: int) -> None:
    opts = f"size={int(size_bytes)},mode=1777".encode()
    _check(_libc.mount(b"tmpfs", path.encode(), b"tmpfs",
                       ctypes.c_ulong(MS_NOSUID | MS_NODEV), opts), f"mount tmpfs {path}")


def mount_fresh_proc() -> None:
    _check(_libc.mount(b"proc", b"/proc", b"proc", ctypes.c_ulong(MS_NOSUID | MS_NODEV | MS_NOEXEC),
                       b"hidepid=2"), "mount /proc")


def switch_ids(uid: int, gid: int) -> None:
    try:
        os.setgroups([])
    except PermissionError:
        # inside a user namespace with setgroups=deny the group list is already fixed and empty/overflow
        with open("/proc/self/setgroups") as f:
            if f.read().strip() != "deny":
                raise
    os.setresgid(gid, gid, gid)
    os.setresuid(uid, uid, uid)
    if os.getresuid() != (uid, uid, uid) or os.getresgid() != (gid, gid, gid):
        raise SandboxError("E_APPLY_FAILED", "uid/gid switch did not read back")


def lock_securebits() -> None:
    bits = (SECBIT_NOROOT | SECBIT_NOROOT_LOCKED | SECBIT_NO_SETUID_FIXUP | SECBIT_NO_SETUID_FIXUP_LOCKED
            | SECBIT_KEEP_CAPS_LOCKED | SECBIT_NO_CAP_AMBIENT_RAISE | SECBIT_NO_CAP_AMBIENT_RAISE_LOCKED)
    _check(prctl(PR_SET_SECUREBITS, bits), "PR_SET_SECUREBITS")


class _CapHeader(ctypes.Structure):
    _fields_ = [("version", ctypes.c_uint32), ("pid", ctypes.c_int)]


class _CapData(ctypes.Structure):
    _fields_ = [("effective", ctypes.c_uint32), ("permitted", ctypes.c_uint32), ("inheritable", ctypes.c_uint32)]


def cap_mask(names) -> int:
    m = 0
    for n in names:
        if n not in CAP_INDEX:
            raise SandboxError("E_PROFILE_INVALID", f"unknown capability {n!r}")
        m |= 1 << CAP_INDEX[n]
    return m


def last_cap() -> int:
    try:
        with open("/proc/sys/kernel/cap_last_cap") as f:
            return int(f.read())
    except OSError:
        return len(CAPS) - 1


def drop_capabilities(retained) -> None:
    keep = cap_mask(retained)
    for i in range(last_cap() + 1):
        if not keep & (1 << i):
            rc = prctl(PR_CAPBSET_DROP, i)
            if rc != 0 and ctypes.get_errno() != 22:  # EINVAL: cap unknown to kernel
                _check(rc, f"PR_CAPBSET_DROP({i})")
    _check(prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_CLEAR_ALL), "PR_CAP_AMBIENT_CLEAR_ALL")
    hdr = _CapHeader(0x20080522, 0)  # _LINUX_CAPABILITY_VERSION_3
    data = (_CapData * 2)()
    for word in (0, 1):
        part = (keep >> (32 * word)) & 0xFFFFFFFF
        data[word].effective = part
        data[word].permitted = part
        data[word].inheritable = 0
    _check(_libc.capset(ctypes.byref(hdr), data), "capset")


def apply_rlimits(limits: dict[str, int]) -> None:
    names = {"nproc": resource.RLIMIT_NPROC, "as": resource.RLIMIT_AS, "cpu": resource.RLIMIT_CPU,
             "nofile": resource.RLIMIT_NOFILE, "fsize": resource.RLIMIT_FSIZE, "core": resource.RLIMIT_CORE}
    for k, v in limits.items():
        if k not in names:
            raise SandboxError("E_PROFILE_INVALID", f"unknown rlimit {k!r}")
        resource.setrlimit(names[k], (int(v), int(v)))


def sanitize_env(env: dict[str, str] | None, allow: frozenset[str]) -> dict[str, str]:
    out = dict(SAFE_DEFAULT_ENV)
    for k, v in (env or {}).items():
        if k not in allow:
            continue
        if any(k.startswith(p) for p in DANGEROUS_ENV_PREFIXES) or "\0" in k or "\0" in v or "=" in k:
            continue
        out[k] = v[:4096]
    return out


def close_fds_except(keep: set[int]) -> None:
    try:
        fds = [int(x) for x in os.listdir("/proc/self/fd")]
    except OSError:
        fds = list(range(3, 4096))
    for fd in fds:
        if fd not in keep:
            try:
                os.close(fd)
            except OSError:
                pass
