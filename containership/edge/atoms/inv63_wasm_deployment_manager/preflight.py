"""Machine-checkable architecture assumptions (INV-63-C005, C040).

Each predicate corresponds to an entry ``A-xx`` in docs/architecture/ASSUMPTIONS.md.
``run()`` returns a list of results; ``critical`` failures block readiness
(fail closed); ``preferred`` failures degrade and are reported.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Callable

from .errors import ErrorCode


@dataclass(frozen=True)
class Check:
    id: str
    title: str
    required: bool
    ok: bool
    detail: str
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def run(*, hosts: dict[str, str], state_dir: str | os.PathLike | None, adapter: Any = None,
        reference_time: float | None = None, clock: Callable[[], float] = time.time,
        max_clock_skew_s: float = 30.0, crypto_required: bool = True,
        runtime_capabilities: set[str] | None = None) -> list[Check]:
    out: list[Check] = []

    ok = sys.version_info >= (3, 11)
    out.append(Check("A-01", "Python runtime >= 3.11", True, ok, sys.version.split()[0],
                     None if ok else ErrorCode.PRECONDITION_FAILED.value))

    ok = bool(hosts) and all(isinstance(h, str) and h and isinstance(z, str) and z for h, z in hosts.items())
    out.append(Check("A-02", "Host inventory non-empty with spread labels", True, ok, f"{len(hosts)} hosts",
                     None if ok else ErrorCode.INSUFFICIENT_CAPACITY.value))

    zones = len(set(hosts.values()))
    out.append(Check("A-03", "At least two failure domains for spread", False, zones >= 2, f"{zones} labels"))

    if state_dir is None:
        out.append(Check("A-04", "Durable state directory writable + fsync", True, False, "no state_dir",
                         ErrorCode.DEPENDENCY_UNAVAILABLE.value))
    else:
        try:
            pathlib.Path(state_dir).mkdir(parents=True, exist_ok=True)
            fd, p = tempfile.mkstemp(dir=state_dir, prefix=".probe.")
            os.write(fd, b"x")
            os.fsync(fd)
            os.close(fd)
            os.unlink(p)
            out.append(Check("A-04", "Durable state directory writable + fsync", True, True, str(state_dir)))
        except OSError as exc:
            out.append(Check("A-04", "Durable state directory writable + fsync", True, False, type(exc).__name__,
                             ErrorCode.DEPENDENCY_UNAVAILABLE.value))

    if reference_time is None:
        out.append(Check("A-05", "Clock skew within bound", False, False, "no reference time source"))
    else:
        skew = abs(clock() - reference_time)
        ok = skew <= max_clock_skew_s
        out.append(Check("A-05", "Clock skew within bound", True, ok, f"skew={skew:.3f}s",
                         None if ok else ErrorCode.PRECONDITION_FAILED.value))

    reach = bool(adapter is not None and adapter.ping())
    out.append(Check("A-06", "Lattice/control plane reachable", False, reach,
                     "reachable" if reach else "unreachable: offline mode", None if reach else
                     ErrorCode.CONTROL_PLANE_OFFLINE.value))

    try:
        from . import security
        ok = security.HAVE_CRYPTO
    except Exception:  # pragma: no cover
        ok = False
    out.append(Check("A-07", "Crypto provider present (cryptography pinned)", crypto_required, ok,
                     "available" if ok else "missing", None if ok else ErrorCode.DEPENDENCY_UNAVAILABLE.value))

    need = {"wasi-p2", "component-model"}
    have = runtime_capabilities if runtime_capabilities is not None else set()
    ok = need <= have
    out.append(Check("A-08", "Wasm runtime advertises component-model + WASI P2", False, ok,
                     f"missing={sorted(need - have)}" if not ok else "ok"))
    return out


def ready(checks: list[Check]) -> bool:
    return all(c.ok for c in checks if c.required)
