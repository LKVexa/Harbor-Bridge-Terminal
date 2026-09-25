"""Process identity helpers: PID liveness, process start identity, host boot id."""

from __future__ import annotations

import os
import sys
from typing import Optional


def boot_id() -> Optional[str]:
    try:
        with open("/proc/sys/kernel/random/boot_id", encoding="ascii") as fh:
            return fh.read().strip() or None
    except OSError:
        return None


def start_identity(pid: int) -> Optional[str]:
    """Linux: starttime (field 22 of /proc/<pid>/stat, clock ticks since boot).
    Windows: process creation FILETIME via GetProcessTimes.  Else None."""
    if sys.platform.startswith("linux"):
        try:
            with open(f"/proc/{pid}/stat", "rb") as fh:
                data = fh.read()
            rest = data[data.rindex(b")") + 2 :].split()
            return "linux:" + rest[19].decode()
        except (OSError, ValueError, IndexError):
            return None
    if sys.platform == "win32":  # pragma: no cover - platform specific
        import ctypes
        from ctypes import wintypes

        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return None
        try:
            c, e, k, u = (wintypes.FILETIME() for _ in range(4))
            if not k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(k), ctypes.byref(u)):
                return None
            return f"win:{(c.dwHighDateTime << 32) | c.dwLowDateTime}"
        finally:
            k32.CloseHandle(h)
    return None


def pid_alive(pid: int) -> Optional[bool]:
    if sys.platform == "win32":  # pragma: no cover
        import ctypes

        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x1000, False, pid)
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = k32.GetExitCodeProcess(h, ctypes.byref(code))
        k32.CloseHandle(h)
        return None if not ok else code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return None
    if sys.platform.startswith("linux"):
        try:  # zombies count as dead
            with open(f"/proc/{pid}/stat", "rb") as fh:
                data = fh.read()
            if data[data.rindex(b")") + 2 : data.rindex(b")") + 3] == b"Z":
                return False
        except (OSError, ValueError):
            pass
    return True
