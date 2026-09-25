"""MC-031 / MC-032 / MC-033 — bubblewrap adapter, Seatbelt compiler, capability probe.

* ``probe()`` discovers what this node can actually enforce (kernel seccomp,
  NNP, user/pid/net namespaces, Landlock ABI, bwrap, sandbox-exec).  Probing
  never raises; ``require()`` turns a missing mandatory feature into
  E_BACKEND_UNSUPPORTED (fail closed).
* ``bwrap_argv()`` renders a launch spec to a bubblewrap command line.  The
  seccomp program from ``linux.seccomp`` is passed via ``--seccomp FD``;
  bwrap adds read-only binds, a fresh /proc, a minimal /dev and pivot_root
  (MC-037/MC-040).  The native launcher is the default backend; bwrap is used
  when the node policy prefers it and ``probe()['bwrap']`` is true.
* ``seatbelt_profile()`` compiles a default-deny SBPL profile for macOS and
  ``seatbelt_argv()`` the ``sandbox-exec`` invocation.  macOS has no read-back
  API for an applied Seatbelt profile; evidence for this backend is therefore
  ``launcher_attested`` and certification on macOS remains BLOCKED until run on
  a real macOS target (see TRACEABILITY.json).
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess

from .errors import SandboxError


def _ns_ok(flag: str) -> bool:
    unshare = shutil.which("unshare")
    if not unshare:
        return False
    try:
        return subprocess.run([unshare, flag, "true"], capture_output=True, timeout=5).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def probe() -> dict:
    sysname = platform.system()
    out = {"os": sysname, "arch": platform.machine(), "kernel": platform.release(),
           "seccomp": False, "no_new_privs": False, "userns": False, "landlock_abi": 0,
           "bwrap": bool(shutil.which("bwrap")), "sandbox_exec": bool(shutil.which("sandbox-exec")),
           "cgroup_v2": os.path.exists("/sys/fs/cgroup/cgroup.controllers")}
    if sysname == "Linux":
        try:
            with open("/proc/self/status") as f:
                st = f.read()
            out["seccomp"] = "Seccomp:" in st
            out["no_new_privs"] = "NoNewPrivs:" in st
        except OSError:
            pass
        out["userns"] = _ns_ok("-Ur")
        try:
            from .linux import landlock
            out["landlock_abi"] = landlock.abi_version()
        except Exception:  # noqa: BLE001
            out["landlock_abi"] = 0
    return out


MANDATORY = {"Linux": ("seccomp", "no_new_privs"), "Darwin": ("sandbox_exec",)}


def require(p: dict | None = None, *, need_userns: bool = True, need_landlock: bool = False) -> dict:
    p = p or probe()
    missing = [k for k in MANDATORY.get(p["os"], ("__unsupported_os__",)) if not p.get(k)]
    if p["os"] == "Linux" and need_userns and not p["userns"] and os.geteuid() != 0:
        missing.append("userns")
    if need_landlock and not p.get("landlock_abi"):
        missing.append("landlock")
    if missing:
        raise SandboxError("E_BACKEND_UNSUPPORTED", f"node lacks mandatory features: {missing}", details=p)
    return p


def bwrap_argv(spec, seccomp_fd: int, *, ro_binds=("/usr", "/bin", "/lib", "/lib64", "/etc/ld.so.cache")) -> list[str]:
    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise SandboxError("E_BACKEND_UNSUPPORTED", "bubblewrap (bwrap) not installed")
    a = [bwrap, "--die-with-parent", "--new-session", "--unshare-all", "--clearenv",
         "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--cap-drop", "ALL"]
    if "net" not in spec.namespaces:
        a.append("--share-net")
    for c in sorted(spec.capabilities):
        a += ["--cap-add", c]
    for p in ro_binds:
        if os.path.exists(p):
            a += ["--ro-bind", p, p]
    for k, v in sorted(spec.env.items()):
        a += ["--setenv", k, v]
    if spec.run_as:
        a += ["--uid", str(spec.run_as[0]), "--gid", str(spec.run_as[1])]
    a += ["--seccomp", str(seccomp_fd), "--"] + list(spec.argv)
    return a


def _sbpl_str(s: str) -> str:
    if any(c in s for c in '"\\\n\0'):
        raise SandboxError("E_PROFILE_INVALID", f"illegal character in Seatbelt path {s!r}")
    return f'"{s}"'


def seatbelt_profile(*, read_paths=(), write_paths=(), allow_network=False, allow_exec=()) -> str:
    lines = ["(version 1)", "(deny default)", "(allow process-fork)", "(allow signal (target self))",
             "(allow sysctl-read)", "(allow file-read-metadata)",
             '(allow file-read* (subpath "/usr/lib") (subpath "/System/Library"))']
    for p in allow_exec:
        lines.append(f"(allow process-exec (literal {_sbpl_str(p)}))")
    for p in read_paths:
        lines.append(f"(allow file-read* (subpath {_sbpl_str(p)}))")
    for p in write_paths:
        lines.append(f"(allow file-read* file-write* (subpath {_sbpl_str(p)}))")
    if allow_network:
        lines.append("(allow network-outbound)")
    return "\n".join(lines) + "\n"


def seatbelt_argv(profile: str, argv) -> list[str]:
    se = shutil.which("sandbox-exec")
    if not se:
        raise SandboxError("E_BACKEND_UNSUPPORTED", "sandbox-exec not available (macOS only)")
    return [se, "-p", profile, "--"] + list(argv)
