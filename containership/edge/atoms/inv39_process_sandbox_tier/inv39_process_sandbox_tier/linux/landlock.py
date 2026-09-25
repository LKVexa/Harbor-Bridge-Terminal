"""MC-038 — optional Landlock filesystem policy backend.

Builds a ruleset handling all filesystem access rights known to the running
ABI, then grants only the listed read-only / read-write path beneath rights.
Must run after PR_SET_NO_NEW_PRIVS and before seccomp (the launcher's order).
``abi_version()`` returns 0 when Landlock is unavailable; a profile that
*requires* Landlock then fails closed (E_BACKEND_UNSUPPORTED).
"""
from __future__ import annotations

import ctypes
import ctypes.util
import os

from ..errors import SandboxError

NR = {"x86_64": (444, 445, 446), "aarch64": (444, 445, 446)}
LANDLOCK_CREATE_RULESET_VERSION = 1
LANDLOCK_RULE_PATH_BENEATH = 1

EXECUTE, WRITE_FILE, READ_FILE, READ_DIR = 1 << 0, 1 << 1, 1 << 2, 1 << 3
REMOVE_DIR, REMOVE_FILE, MAKE_CHAR, MAKE_DIR, MAKE_REG = 1 << 4, 1 << 5, 1 << 6, 1 << 7, 1 << 8
MAKE_SOCK, MAKE_FIFO, MAKE_BLOCK, MAKE_SYM = 1 << 9, 1 << 10, 1 << 11, 1 << 12
REFER, TRUNCATE, IOCTL_DEV = 1 << 13, 1 << 14, 1 << 15
ABI_MASK = {1: (1 << 13) - 1, 2: (1 << 14) - 1, 3: (1 << 15) - 1, 4: (1 << 15) - 1, 5: (1 << 16) - 1}
RO = EXECUTE | READ_FILE | READ_DIR

_libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)
_libc.syscall.restype = ctypes.c_long


class _Attr(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class _PathBeneath(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int32)]


def _nrs():
    import platform
    return NR.get(platform.machine().lower().replace("amd64", "x86_64").replace("arm64", "aarch64"))


def abi_version() -> int:
    nrs = _nrs()
    if not nrs:
        return 0
    v = _libc.syscall(nrs[0], None, ctypes.c_size_t(0), ctypes.c_uint32(LANDLOCK_CREATE_RULESET_VERSION))
    return int(v) if v > 0 else 0


def restrict(ro_paths=(), rw_paths=()) -> int:
    abi = abi_version()
    if abi == 0:
        raise SandboxError("E_BACKEND_UNSUPPORTED", "Landlock is not available on this kernel")
    create, add, restrict_self = _nrs()
    handled = ABI_MASK.get(abi, ABI_MASK[5])
    attr = _Attr(handled)
    rfd = _libc.syscall(create, ctypes.byref(attr), ctypes.c_size_t(ctypes.sizeof(attr)), ctypes.c_uint32(0))
    if rfd < 0:
        raise SandboxError("E_APPLY_FAILED", f"landlock_create_ruleset: {os.strerror(ctypes.get_errno())}")
    try:
        for paths, rights in ((ro_paths, RO), (rw_paths, handled)):
            for p in paths:
                fd = os.open(p, os.O_PATH | os.O_CLOEXEC)
                try:
                    allowed = rights & handled
                    if not os.path.isdir(p):
                        allowed &= EXECUTE | WRITE_FILE | READ_FILE | TRUNCATE | IOCTL_DEV
                    pb = _PathBeneath(allowed, fd)
                    if _libc.syscall(add, ctypes.c_int(rfd), ctypes.c_int(LANDLOCK_RULE_PATH_BENEATH),
                                     ctypes.byref(pb), ctypes.c_uint32(0)) != 0:
                        raise SandboxError("E_APPLY_FAILED", f"landlock_add_rule {p}: {os.strerror(ctypes.get_errno())}")
                finally:
                    os.close(fd)
        if _libc.syscall(restrict_self, ctypes.c_int(rfd), ctypes.c_uint32(0)) != 0:
            raise SandboxError("E_APPLY_FAILED", f"landlock_restrict_self: {os.strerror(ctypes.get_errno())}")
    finally:
        os.close(rfd)
    return abi
