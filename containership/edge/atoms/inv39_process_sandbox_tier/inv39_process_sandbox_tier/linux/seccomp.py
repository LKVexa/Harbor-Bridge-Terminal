"""MC-030 / MC-034 / MC-047 — native Linux seccomp-BPF compiler and installer.

Compiles a default-deny syscall allow-list into a classic-BPF program:

    1. load seccomp_data.arch; any architecture other than the compiled one -> KILL_PROCESS
    2. load seccomp_data.nr; on x86_64 any x32 ABI number (>= 0x40000000) -> KILL_PROCESS
    3. one JEQ per allowed syscall -> ALLOW
    4. default -> the profile's deny action (ERRNO(EPERM) or KILL_PROCESS)

Unknown syscall names are refused at compile time (fail closed).  The program
bytes are hashed; that digest is the evidence anchor for the installed filter,
because normal kernel APIs do not expose installed rule contents (MC-047).
Installation requires PR_SET_NO_NEW_PRIVS first (MC-034) and is verified by
reading ``Seccomp:`` / ``NoNewPrivs:`` back from ``/proc/<pid>/status``.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import hashlib
import os
import platform
import struct
from dataclasses import dataclass
from typing import Iterable

from ..errors import SandboxError
from .syscall_tables import AARCH64, X86_64

# BPF opcodes
BPF_LD, BPF_W, BPF_ABS, BPF_JMP, BPF_JEQ, BPF_JGE, BPF_K, BPF_RET = 0x00, 0x00, 0x20, 0x05, 0x10, 0x30, 0x00, 0x06
SECCOMP_RET_KILL_PROCESS = 0x80000000
SECCOMP_RET_ERRNO = 0x00050000
SECCOMP_RET_ALLOW = 0x7FFF0000
SECCOMP_MODE_FILTER = 2
PR_SET_NO_NEW_PRIVS = 38
PR_GET_NO_NEW_PRIVS = 39
PR_SET_SECCOMP = 22
EPERM = 1
X32_SYSCALL_BIT = 0x40000000

ARCHES = {
    "x86_64": (0xC000003E, X86_64),
    "aarch64": (0xC00000B7, AARCH64),
}
MAX_ALLOWED = 1024  # BPF_MAXINSNS is 4096; keep far below it


def host_arch() -> str:
    m = platform.machine().lower()
    return {"amd64": "x86_64", "arm64": "aarch64"}.get(m, m)


@dataclass(frozen=True)
class CompiledFilter:
    arch: str
    allowed: tuple[str, ...]
    deny_action: str
    program: bytes

    @property
    def instructions(self) -> int:
        return len(self.program) // 8

    @property
    def digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.program).hexdigest()


def _ins(code: int, jt: int, jf: int, k: int) -> bytes:
    return struct.pack("=HBBI", code, jt, jf, k & 0xFFFFFFFF)


def compile_filter(syscalls: Iterable[str], *, arch: str | None = None, deny_action: str = "errno") -> CompiledFilter:
    arch = arch or host_arch()
    if arch not in ARCHES:
        raise SandboxError("E_BACKEND_UNSUPPORTED", f"no seccomp syscall table for architecture {arch!r}")
    audit_arch, table = ARCHES[arch]
    names = sorted(set(syscalls))
    if not names:
        raise SandboxError("E_PROFILE_INVALID", "empty syscall allow-list")
    if len(names) > MAX_ALLOWED:
        raise SandboxError("E_LIMIT_EXCEEDED", f"allow-list of {len(names)} exceeds {MAX_ALLOWED}")
    unknown = [n for n in names if n not in table]
    if unknown:
        raise SandboxError("E_PROFILE_INVALID", f"unknown syscalls for {arch}: {unknown[:10]}")
    if deny_action == "errno":
        deny = SECCOMP_RET_ERRNO | EPERM
    elif deny_action == "kill":
        deny = SECCOMP_RET_KILL_PROCESS
    else:
        raise SandboxError("E_PROFILE_INVALID", f"unknown deny action {deny_action!r}")
    nrs = sorted({table[n] for n in names})
    prog = [
        _ins(BPF_LD | BPF_W | BPF_ABS, 0, 0, 4),                       # arch
        _ins(BPF_JMP | BPF_JEQ | BPF_K, 1, 0, audit_arch),
        _ins(BPF_RET | BPF_K, 0, 0, SECCOMP_RET_KILL_PROCESS),
        _ins(BPF_LD | BPF_W | BPF_ABS, 0, 0, 0),                       # nr
    ]
    if arch == "x86_64":
        prog += [
            _ins(BPF_JMP | BPF_JGE | BPF_K, 0, 1, X32_SYSCALL_BIT),
            _ins(BPF_RET | BPF_K, 0, 0, SECCOMP_RET_KILL_PROCESS),
        ]
    n = len(nrs)
    for i, nr in enumerate(nrs):
        # jump-true lands on the ALLOW instruction placed after all comparisons + deny
        prog.append(_ins(BPF_JMP | BPF_JEQ | BPF_K, n - i, 0, nr))
    prog.append(_ins(BPF_RET | BPF_K, 0, 0, deny))
    prog.append(_ins(BPF_RET | BPF_K, 0, 0, SECCOMP_RET_ALLOW))
    return CompiledFilter(arch, tuple(names), deny_action, b"".join(prog))


class _SockFprog(ctypes.Structure):
    _fields_ = [("len", ctypes.c_ushort), ("filter", ctypes.c_void_p)]


_LIBC = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)


def _libc():
    # resolved at import time: after Landlock/mount changes the library path may be unreadable
    return _LIBC


def set_no_new_privs() -> None:
    libc = _libc()
    if libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        e = ctypes.get_errno()
        raise SandboxError("E_APPLY_FAILED", f"PR_SET_NO_NEW_PRIVS failed: {os.strerror(e)}")
    if libc.prctl(PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0) != 1:
        raise SandboxError("E_APPLY_FAILED", "PR_SET_NO_NEW_PRIVS did not read back as set")


def install(filt: CompiledFilter) -> None:
    """Install ``filt`` on the calling thread. Requires NO_NEW_PRIVS (or CAP_SYS_ADMIN)."""
    if filt.arch != host_arch():
        raise SandboxError("E_BACKEND_UNSUPPORTED", "filter compiled for a different architecture")
    libc = _libc()
    buf = ctypes.create_string_buffer(filt.program, len(filt.program))
    fprog = _SockFprog(filt.instructions, ctypes.cast(buf, ctypes.c_void_p))
    if libc.prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, ctypes.byref(fprog), 0, 0) != 0:
        e = ctypes.get_errno()
        raise SandboxError("E_APPLY_FAILED", f"PR_SET_SECCOMP failed: {os.strerror(e)}")
