"""MC-24 - Cross-platform compatibility certification matrix.

A cell is FULLY_SUPPORTED only when ``evidence/platform/<cell>.json`` holds a
passing test run from this exact source revision on that platform.  Cells with
no current evidence are UNVERIFIED (never "supported"); combinations outside
the claim set are UNSUPPORTED and select the portable fallback or fail cleanly.

    python tools/certify.py record   # run the suite here and record this cell
    python tools/certify.py matrix   # rebuild evidence/compat_matrix.json
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import platform
import subprocess
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
from inv19_os_asynchronous_analogues.tools.supply_chain import source_revision  # noqa: E402

CLAIMS = [  # (cell id, os, arch, expected fast path, claim level)
    ("linux-x86_64", "Linux", "x86_64", "io_uring", "claimed"),
    ("linux-aarch64", "Linux", "aarch64", "io_uring", "claimed"),
    ("linux-x86_64-restricted", "Linux", "x86_64", "epoll", "claimed"),   # io_uring admin-disabled / seccomp-denied
    ("linux-x86_64-lowres", "Linux", "x86_64", "io_uring", "claimed"),     # 1 CPU, 256 fds
    ("windows-x86_64", "Windows", "AMD64", "iocp", "claimed"),
    ("windows-arm64", "Windows", "ARM64", "iocp", "best-effort"),
    ("macos-arm64", "Darwin", "arm64", "kqueue", "claimed"),
    ("macos-x86_64", "Darwin", "x86_64", "kqueue", "best-effort"),
    ("freebsd-x86_64", "FreeBSD", "amd64", "kqueue", "best-effort"),
]
LIMITS = {
    "linux-aarch64": "io_uring ring memory ordering relies on the syscall boundary; unverified on arm64",
    "windows-x86_64": "IOCP adapter implemented but never executed; handle-association path not wired into AsyncHost",
    "windows-arm64": "as windows-x86_64",
    "macos-arm64": "kqueue adapter implemented but never executed",
    "freebsd-x86_64": "kqueue EV_EOF fflags semantics differ from macOS; unverified",
}


def this_cell() -> str:
    osn, m = platform.system(), platform.machine()
    base = {("Linux", "x86_64"): "linux-x86_64", ("Linux", "aarch64"): "linux-aarch64",
            ("Windows", "AMD64"): "windows-x86_64", ("Windows", "ARM64"): "windows-arm64",
            ("Darwin", "arm64"): "macos-arm64", ("Darwin", "x86_64"): "macos-x86_64",
            ("FreeBSD", "amd64"): "freebsd-x86_64"}.get((osn, m), f"{osn}-{m}".lower())
    return base


def record(cell: str | None = None) -> dict:
    from inv19_os_asynchronous_analogues.hostio import capabilities as capmod
    caps = capmod.detect()
    r = subprocess.run([sys.executable, str(PKG / "tools" / "_collect.py")],
                       capture_output=True, text=True, cwd=str(PKG / "tests"), timeout=1800)
    rows = json.loads(r.stdout)["rows"]
    real_fail = [x[0] for x in rows if x[1] in ("fail", "error") and "DEPENDENCY_UNAVAILABLE" not in x[2]]
    dep = [x[0] for x in rows if x[1] in ("fail", "error") and "DEPENDENCY_UNAVAILABLE" in x[2]]
    tail = {"pass": sum(1 for x in rows if x[1] == "pass"), "fail": real_fail,
            "dependency_blocked": dep, "blocked_skips": sum(1 for x in rows if x[1] == "skip")}
    rec = {"cell": cell or this_cell(), "cpu_affinity": len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
           "fd_limit": __import__("resource").getrlimit(__import__("resource").RLIMIT_NOFILE)[0],
           "io_uring_disabled_sysctl": pathlib.Path("/proc/sys/kernel/io_uring_disabled").read_text().strip()
           if pathlib.Path("/proc/sys/kernel/io_uring_disabled").exists() else None, "source_revision": source_revision(), "date": dt.date.today().isoformat(),
           "python": platform.python_version(), "kernel": platform.release(), "cpus": os.cpu_count(),
           "container": os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv"),
           "backends_available": caps.available(), "selected": capmod.choose(caps).backend,
           "suite_rc": 0 if not real_fail else 1, "suite": tail}
    d = PKG / "evidence" / "platform"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{rec['cell']}.json").write_text(json.dumps(rec, indent=1))
    return rec


def matrix() -> dict:
    rev = source_revision()
    cells = []
    for cid, osn, arch, fast, level in CLAIMS:
        p = PKG / "evidence" / "platform" / f"{cid}.json"
        ev = json.loads(p.read_text()) if p.exists() else None
        if ev and ev["source_revision"] == rev and ev["suite_rc"] == 0:
            status = "FULLY_SUPPORTED" if level == "claimed" else "BEST_EFFORT_VERIFIED"
        elif ev and ev["source_revision"] != rev:
            status = "UNVERIFIED (stale evidence from another revision)"
        else:
            status = "UNVERIFIED (no automated evidence)"
        cells.append({"cell": cid, "os": osn, "arch": arch, "expected_fast_path": fast, "claim": level,
                      "status": status, "evidence": p.name if ev else None,
                      "backends_observed": ev and ev["backends_available"], "tested": ev and ev["date"],
                      "limitations": LIMITS.get(cid, "")})
    out = {"schema": "PK_COMPAT_MATRIX/1", "source_revision": rev, "cells": cells,
           "unsupported_policy": "any platform not listed: portable fallback if selectors works, else NoBackend at start-up",
           "rule": "a cell is supported only with current automated evidence from this revision"}
    (PKG / "evidence" / "compat_matrix.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "matrix"
    cell = sys.argv[2] if len(sys.argv) > 2 else None
    print(json.dumps(record(cell) if cmd == "record" else matrix(), indent=1)[:3000])
