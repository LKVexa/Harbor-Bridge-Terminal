"""Deterministic crash-point injection for crash/restart qualification (GAP04-C31).

Set ``GAP04_CRASHPOINT=<name>[:<nth>]`` and the process ``os._exit(137)``s the
nth time execution reaches that point - equivalent to kill -9/power loss at an
exact persistence transition. Inert (a dict lookup) when the variable is unset.
"""
import os

POINTS = ("journal.before_write", "journal.partial_write", "journal.after_fsync", "decide.after_wal",
          "decide.after_effect", "reconcile.after_begin", "reconcile.after_batch_ack", "reconcile.before_compact",
          "compact.before_replace", "atomic.before_rename", "lease.before_commit")
_spec = os.environ.get("GAP04_CRASHPOINT", "")
_name, _, _nth = _spec.partition(":")
_count = {"n": 0}


def crashpoint(name: str) -> None:
    if name == _name:
        _count["n"] += 1
        if _count["n"] >= int(_nth or 1):
            os._exit(137)


def will_fire(name: str) -> bool:
    """True if the *next* crashpoint(name) call will terminate the process (used to
    stage a torn write immediately before the simulated power cut)."""
    return name == _name and _count["n"] + 1 >= int(_nth or 1)
