import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv19_os_asynchronous_analogues.hostio import capabilities as capmod  # noqa: E402

CAPS = capmod.detect()
AVAILABLE = set(CAPS.available())
LINUX_URING = "io_uring" in AVAILABLE
HAS_EPOLL = "epoll" in AVAILABLE
HAS_KQUEUE = "kqueue" in AVAILABLE
IS_WINDOWS = os.name == "nt"


def pipe_nb():
    r, w = os.pipe()
    os.set_blocking(r, False)
    os.set_blocking(w, False)
    return r, w


def platform_blocked(reason: str):
    """Platform-specific tests that cannot run here are recorded as BLOCKED by
    the gate (tools/run_gate.py reads skip reasons prefixed 'BLOCKED:'), never
    counted as passes."""
    import unittest
    return unittest.skip("BLOCKED: " + reason)
