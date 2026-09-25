"""GAP02-MC-40 — Resource ceilings for the agent process (POSIX rlimits) and
per-sweep budgets. On platforms without ``resource`` the ceilings are reported
as unenforced rather than silently assumed."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Ceilings:
    max_rss_bytes: int = 256 * 1024 * 1024
    max_open_files: int = 256
    max_cpu_seconds_per_sweep: float = 5.0
    max_threads: int = 8


def apply(c: Ceilings) -> dict:
    try:
        import resource
    except ImportError:
        return {"enforced": False, "reason": "resource module unavailable on this OS"}
    applied = {}
    for name, lim, val in (("RLIMIT_AS", getattr(resource, "RLIMIT_AS", None), c.max_rss_bytes * 4),
                           ("RLIMIT_NOFILE", resource.RLIMIT_NOFILE, c.max_open_files)):
        if lim is None:
            continue
        soft, hard = resource.getrlimit(lim)
        new = val if hard == resource.RLIM_INFINITY else min(val, hard)
        if soft == resource.RLIM_INFINITY or soft > new:
            resource.setrlimit(lim, (new, hard))
        applied[name] = resource.getrlimit(lim)[0]
    return {"enforced": True, "applied": applied}


def sweep_cpu_ok(cpu_seconds: float, c: Ceilings) -> bool:
    return cpu_seconds <= c.max_cpu_seconds_per_sweep
