"""MC-044 / MC-045 / MC-046 — pre-exec containment launcher with OS read-back.

Process tree::

    host (caller)            -- owns the gate; reads /proc/<pid> evidence; decides
      └─ supervisor          -- new user/mount/net/ipc/uts ns; PR_SET_CHILD_SUBREAPER;
           │                    forwards SIGTERM/SIGINT; reaps; PDEATHSIG=SIGKILL
           └─ workload       -- PID 1 of a new pid ns; applies every control, then
                                blocks on the gate *after* seccomp is installed

The workload process only calls ``execve`` after the host has read back, from
the kernel, that every mandatory control is active (NoNewPrivs, Seccomp mode 2,
capability sets, uid/gid/groups, namespace inodes, fd table, rlimits, mount
propagation, network interfaces).  Any mismatch -> the whole tree is killed and
``E_NOT_APPLIED`` is raised: fail closed, nothing untrusted ever ran.

Seccomp *rule contents* cannot be read back through /proc (MC-047); they are
bound instead by the compiled program digest reported by the launcher before
installation plus the kernel's ``Seccomp_filters`` count.  Evidence records mark
that fact ``launcher_attested`` rather than ``kernel_read_back``.
"""
from __future__ import annotations

import os
import select
import signal
import struct
import time
from dataclasses import dataclass, field
from typing import Any

from ..errors import SandboxError
from . import primitives as P
from . import landlock, seccomp

HANDOFF_SYSCALLS = frozenset({"read", "execve", "exit_group"})
DEFAULT_RLIMITS = {"core": 0, "nofile": 256, "nproc": 256, "fsize": 64 << 20}
READY_TIMEOUT_S = 10.0


@dataclass(frozen=True)
class LaunchSpec:
    argv: tuple[str, ...]
    syscalls: frozenset[str]
    capabilities: frozenset[str] = frozenset()
    namespaces: frozenset[str] = frozenset({"pid", "mount", "net", "ipc", "uts", "user"})
    env: dict[str, str] = field(default_factory=dict)
    env_allow: frozenset[str] = frozenset()
    rlimits: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_RLIMITS))
    run_as: tuple[int, int] | None = None     # (uid, gid) inside the sandbox
    keep_fds: frozenset[int] = frozenset()    # beyond 0,1,2
    stdio: tuple[int, int, int] | None = None
    deny_action: str = "errno"
    private_tmp_bytes: int = 0                # >0 mounts a private tmpfs on /tmp
    timeout_s: float = 30.0
    landlock_ro: tuple[str, ...] = ()         # MC-038: when either list is non-empty,
    landlock_rw: tuple[str, ...] = ()         # Landlock is mandatory (fail closed)
    cancel: Any = None                        # threading.Event: set -> kill tree, E_CANCELLED

    def validate(self) -> None:
        if not self.argv or not all(isinstance(a, str) and "\0" not in a for a in self.argv):
            raise SandboxError("E_PROFILE_INVALID", "argv must be non-empty NUL-free strings")
        if not os.path.isabs(self.argv[0]):
            raise SandboxError("E_PROFILE_INVALID", "argv[0] must be an absolute path (no PATH search)")
        missing = HANDOFF_SYSCALLS - self.syscalls
        if missing:
            raise SandboxError("E_PROFILE_INVALID", f"allow-list lacks launcher hand-off syscalls {sorted(missing)}")
        if not 0 < self.timeout_s <= 86400:
            raise SandboxError("E_LIMIT_EXCEEDED", "timeout_s out of range")


@dataclass
class LaunchResult:
    pid: int
    exit_code: int | None
    signal: int | None
    timed_out: bool
    evidence: dict[str, Any]
    duration_s: float


def _read_status(pid: int) -> dict[str, str]:
    out = {}
    with open(f"/proc/{pid}/status") as f:
        for line in f:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


def _ns_inode(pid: int | str, ns: str) -> str:
    return os.readlink(f"/proc/{pid}/ns/{ns}")


def _read_limits(pid: int) -> dict[str, int | None]:
    names = {"Max cpu time": "cpu", "Max file size": "fsize", "Max processes": "nproc",
             "Max open files": "nofile", "Max address space": "as", "Max core file size": "core"}
    out: dict[str, int | None] = {}
    with open(f"/proc/{pid}/limits") as f:
        for line in f.readlines()[1:]:
            for label, key in names.items():
                if line.startswith(label):
                    soft = line[len(label):].split()[0]
                    out[key] = None if soft == "unlimited" else int(soft)
    return out


def read_back(pid: int, host_ns: dict[str, str]) -> dict[str, Any]:
    """Collect kernel-reported state for ``pid`` (MC-046)."""
    st = _read_status(pid)
    ns = {n: _ns_inode(pid, p) for n, p in P.NS_PROC.items()}
    try:
        with open(f"/proc/{pid}/net/dev") as f:
            ifaces = sorted(l.split(":")[0].strip() for l in f.readlines()[2:])
    except OSError:
        ifaces = None
    with open(f"/proc/{pid}/mountinfo") as f:
        shared_mounts = sum(1 for l in f if " shared:" in l.split(" - ")[0])
    return {
        "no_new_privs": st.get("NoNewPrivs") == "1",
        "seccomp_mode": int(st.get("Seccomp", "0")),
        "seccomp_filters": int(st.get("Seccomp_filters", "0")),
        "cap_eff": int(st["CapEff"], 16), "cap_prm": int(st["CapPrm"], 16),
        "cap_inh": int(st["CapInh"], 16), "cap_bnd": int(st["CapBnd"], 16),
        "cap_amb": int(st.get("CapAmb", "0"), 16),
        "uid": [int(x) for x in st["Uid"].split()], "gid": [int(x) for x in st["Gid"].split()],
        "groups": [int(x) for x in st.get("Groups", "").split()],
        "namespaces_new": sorted(n for n in ns if ns[n] != host_ns[n]),
        "fds": sorted(int(x) for x in os.listdir(f"/proc/{pid}/fd")),
        "rlimits": _read_limits(pid),
        "net_interfaces": ifaces,
        "shared_mount_propagation": shared_mounts,
    }


def _kill_tree(pid: int) -> None:
    for p in (pid,):
        try:
            os.kill(p, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _workload(spec: LaunchSpec, filt: seccomp.CompiledFilter, env: dict[str, str],
              gate_r: int, report_w: int) -> None:
    """Runs as PID 1 of the new pid namespace. Never returns."""
    try:
        P.prctl(P.PR_SET_PDEATHSIG, signal.SIGKILL)
        if "mount" in spec.namespaces:
            P.make_mounts_private()
            if "pid" in spec.namespaces:
                P.mount_fresh_proc()           # MC-040: workload sees only its own pid namespace
            if spec.private_tmp_bytes:
                P.mount_private_tmpfs("/tmp", spec.private_tmp_bytes)
        P.apply_rlimits(spec.rlimits)
        if spec.stdio:
            for i, fd in enumerate(spec.stdio):
                os.dup2(fd, i)
        P.close_fds_except({0, 1, 2, gate_r, report_w} | set(spec.keep_fds))
        for fd in (gate_r, report_w):
            os.set_inheritable(fd, False)
        # capability bounding/ambient first (needs CAP_SETPCAP), then securebits, ids, capset
        keep = P.cap_mask(spec.capabilities)
        for i in range(P.last_cap() + 1):
            if not keep & (1 << i):
                P.prctl(P.PR_CAPBSET_DROP, i)
        P.lock_securebits()
        if spec.run_as is not None:
            P.switch_ids(*spec.run_as)
        P.drop_capabilities(spec.capabilities)
        seccomp.set_no_new_privs()
        if spec.landlock_ro or spec.landlock_rw:
            landlock.restrict(spec.landlock_ro, spec.landlock_rw)
        argv = list(spec.argv)
        path = spec.argv[0]
        os.write(report_w, b"R" + filt.digest.encode())
        seccomp.install(filt)
        # ---- from here only read/execve/exit_group are guaranteed to be permitted ----
        go = os.read(gate_r, 1)
        if go == b"G":
            os.execve(path, argv, env)
        os._exit(126)
    except BaseException as exc:  # noqa: BLE001 - report and die; never continue unconfined
        try:
            os.write(report_w, b"F" + repr(exc).encode()[:512])
        finally:
            os._exit(125)


def _supervisor(spec: LaunchSpec, filt, env, gate_r, report_w, uid, gid) -> None:
    try:
        P.prctl(P.PR_SET_PDEATHSIG, signal.SIGKILL)
        if "user" in spec.namespaces:
            P.unshare(P.CLONE_NEWUSER)
            inner = spec.run_as or (0, 0)
            P.write_id_maps(uid, gid, inner[0], inner[1])
        other = P.ns_flags(spec.namespaces - {"user"})
        if other:
            P.unshare(other)
        P.prctl(P.PR_SET_CHILD_SUBREAPER, 1)
        child = os.fork()
        if child == 0:
            _workload(spec, filt, env, gate_r, report_w)
        os.write(report_w, b"P" + struct.pack("=i", child))
        os.close(report_w)
        os.close(gate_r)

        def fwd(sig, _frm):
            try:
                os.kill(child, sig)
            except ProcessLookupError:
                pass
        for s in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            signal.signal(s, fwd)
        code = 0
        while True:  # reap everything re-parented to us
            try:
                pid, status = os.waitpid(-1, 0)
            except ChildProcessError:
                break
            if pid == child:
                code = os.waitstatus_to_exitcode(status)
        os._exit(code & 0xFF if code >= 0 else 128 + (-code))
    except BaseException as exc:  # noqa: BLE001
        try:
            os.write(report_w, b"F" + repr(exc).encode()[:512])
        finally:
            os._exit(125)


def expected_state(spec: LaunchSpec, host_uid: int) -> dict[str, Any]:
    keep = P.cap_mask(spec.capabilities)
    return {"no_new_privs": True, "seccomp_mode": 2, "cap_eff": keep, "cap_prm": keep,
            "cap_inh": 0, "cap_amb": 0, "namespaces_new": sorted(spec.namespaces)}


def verify(spec: LaunchSpec, rb: dict[str, Any], internal_fds: set[int]) -> list[str]:
    defects = []
    exp = expected_state(spec, os.getuid())
    for k in ("no_new_privs", "seccomp_mode", "cap_eff", "cap_prm", "cap_inh", "cap_amb", "namespaces_new"):
        if rb[k] != exp[k]:
            defects.append(f"{k}: kernel reports {rb[k]!r}, required {exp[k]!r}")
    if rb["cap_bnd"] & ~exp["cap_prm"]:
        defects.append(f"cap_bnd retains 0x{rb['cap_bnd'] & ~exp['cap_prm']:x}")
    if rb["seccomp_filters"] < 1:
        defects.append("no seccomp filter attached")
    if spec.run_as is not None:
        uid, gid = spec.run_as
        # values are reported in the reader's (host) user namespace; only check uniformity
        if len(set(rb["uid"])) != 1 or len(set(rb["gid"])) != 1:
            defects.append(f"uid/gid not uniform: {rb['uid']} {rb['gid']}")
    allowed = {0, 1, 2} | set(spec.keep_fds) | internal_fds
    extra = set(rb["fds"]) - allowed
    if extra:
        defects.append(f"unexpected inherited fds {sorted(extra)}")
    for k, v in spec.rlimits.items():
        if rb["rlimits"].get(k) != v:
            defects.append(f"rlimit {k}: kernel reports {rb['rlimits'].get(k)}, required {v}")
    if "net" in spec.namespaces and rb["net_interfaces"] not in (["lo"], None):
        defects.append(f"network namespace exposes {rb['net_interfaces']}")
    if "mount" in spec.namespaces and rb["shared_mount_propagation"]:
        defects.append(f"{rb['shared_mount_propagation']} mounts still have shared propagation")
    return defects


def launch(spec: LaunchSpec, *, on_ready=None) -> LaunchResult:
    """Launch ``spec`` with every control verified before exec. Fail closed."""
    spec.validate()
    filt = seccomp.compile_filter(spec.syscalls, deny_action=spec.deny_action)
    env = P.sanitize_env(spec.env, spec.env_allow)
    host_ns = {n: _ns_inode("self", p) for n, p in P.NS_PROC.items()}
    gate_r, gate_w = os.pipe()
    report_r, report_w = os.pipe()
    t0 = time.monotonic()
    sup = os.fork()
    if sup == 0:
        os.close(gate_w)
        os.close(report_r)
        _supervisor(spec, filt, env, gate_r, report_w, os.getuid(), os.getgid())
    os.close(gate_r)
    os.close(report_w)
    evidence: dict[str, Any] = {"seccomp_program_digest": filt.digest, "seccomp_instructions": filt.instructions}
    workload_pid = None
    released = False
    try:
        buf = b""
        deadline = time.monotonic() + READY_TIMEOUT_S
        ready_digest = None
        while ready_digest is None or workload_pid is None:
            r, _, _ = select.select([report_r], [], [], max(0.0, deadline - time.monotonic()))
            if not r:
                raise SandboxError("E_TIMEOUT", "launcher did not reach the gate in time")
            chunk = os.read(report_r, 4096)
            if not chunk:
                raise SandboxError("E_APPLY_FAILED", f"launcher exited before the gate: {buf!r}")
            buf += chunk
            while buf:
                tag = buf[:1]
                if tag == b"P" and len(buf) >= 5:
                    workload_pid = struct.unpack("=i", buf[1:5])[0]
                    buf = buf[5:]
                elif tag == b"F":
                    raise SandboxError("E_APPLY_FAILED", buf[1:].decode(errors="replace"))
                elif tag == b"R" and len(buf) >= 1 + 71:
                    ready_digest = buf[1:72].decode()
                    buf = buf[72:]
                else:
                    break
        if ready_digest != filt.digest:
            raise SandboxError("E_NOT_APPLIED", "launcher reported a different seccomp program")
        # wait until the kernel shows the filter installed (the workload is then blocked in read)
        rb = None
        while time.monotonic() < deadline:
            try:
                rb = read_back(workload_pid, host_ns)
            except FileNotFoundError:
                tail = buf
                r, _, _ = select.select([report_r], [], [], 0.5)
                if r:
                    tail += os.read(report_r, 4096)
                raise SandboxError("E_APPLY_FAILED", "workload died before the gate: "
                                   + tail.decode(errors="replace")[:512]) from None
            if rb["seccomp_mode"] == 2:
                break
            time.sleep(0.002)
        if rb is None:
            raise SandboxError("E_TIMEOUT", "no read-back obtained")
        # launcher-internal fds (gate + report) are CLOEXEC and vanish at exec
        internal = {gate_r, report_w}
        defects = verify(spec, rb, internal)
        evidence.update({"kernel_read_back": rb, "defects": defects})
        if defects:
            raise SandboxError("E_NOT_APPLIED", "; ".join(defects), details={"defects": defects})
        if on_ready is not None:
            on_ready(workload_pid, evidence)
        os.write(gate_w, b"G")
        released = True
        os.close(gate_w)
        # wait with timeout (MC-045)
        timed_out = False
        end = time.monotonic() + spec.timeout_s
        status = None
        while status is None:
            pid, st = os.waitpid(sup, os.WNOHANG)
            if pid:
                status = st
                break
            if spec.cancel is not None and spec.cancel.is_set():
                _kill_tree(workload_pid)
                if _alive(sup):
                    os.kill(sup, signal.SIGKILL)
                os.waitpid(sup, 0)
                raise SandboxError("E_CANCELLED", "launch cancelled by caller; sandbox tree killed")
            if time.monotonic() > end:
                timed_out = True
                _kill_tree(workload_pid)   # PID 1 of the pid ns: kernel kills the whole ns
                os.kill(sup, signal.SIGKILL) if _alive(sup) else None
                _, status = os.waitpid(sup, 0)
                break
            time.sleep(0.005)
        code = os.waitstatus_to_exitcode(status)
        return LaunchResult(workload_pid, code if code >= 0 else None, -code if code < 0 else None,
                            timed_out, evidence, time.monotonic() - t0)
    except BaseException:
        if not released:
            try:
                os.close(gate_w)       # EOF -> workload _exit(126) even if kill races
            except OSError:
                pass
        if workload_pid:
            _kill_tree(workload_pid)
        if _alive(sup):
            os.kill(sup, signal.SIGKILL)
        try:
            os.waitpid(sup, 0)
        except ChildProcessError:
            pass
        raise
    finally:
        os.close(report_r)


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
