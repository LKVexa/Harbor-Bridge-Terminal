"""Component 57 - environment compatibility matrix and qualification (PK_DYN_ENVMATRIX/1).

``DECLARED`` is the supported matrix.  ``observe`` captures the *current*
interpreter / implementation / machine / OS.  ``qualify`` runs the deterministic
smoke suite (pool semantics + canonical encoding + protocol schema ids) in the
current environment only; every other declared cell is reported ``NOT_RUN`` (no
other interpreters, architectures or hypervisors are available here) and
provider cells are ``BLOCKED`` (no provider integration exists).
"""
from __future__ import annotations

import platform
import sys

from .core import canonical, digest

DECLARED = {
    "python": ["3.10", "3.11", "3.12", "3.13"],
    "implementation": ["CPython"],
    "arch": ["x86_64", "aarch64"],
    "os": ["Linux", "Darwin", "Windows"],
    "hypervisor": ["none", "kvm", "firecracker"],
    "provider": ["none"],        # no provider adapters exist yet -> other providers BLOCKED
    "protocol": ["PK_DYN_LEASE/1", "PK_DYN_SCALE/1", "PK_DYN_COST/1", "PK_DYN_RESULT/1"],
}
_ARCH_ALIASES = {"amd64": "x86_64", "x64": "x86_64", "arm64": "aarch64"}


def observe(*, sys_mod=sys, platform_mod=platform) -> dict:
    return {"python": f"{sys_mod.version_info[0]}.{sys_mod.version_info[1]}",
            "implementation": platform_mod.python_implementation(),
            "arch": _ARCH_ALIASES.get(platform_mod.machine().lower(), platform_mod.machine().lower()),
            "os": platform_mod.system(),
            "hypervisor": "unknown", "provider": "none"}


def smoke() -> list[tuple[str, bool, str]]:
    from ..model import Pool
    from .core import RESULT_CODE_POLICY
    out = []
    p = Pool(min_nodes=1, max_nodes=10)
    sizes = [p.tick(t, d)["size"] for t, d in enumerate([4, 16, 40, 8, 0, 0])]
    out.append(("pool_sequence", sizes == [1, 4, 10, 2, 1, 1], str(sizes)))
    out.append(("canonical_encoding", canonical({"b": 1, "a": [1.5, "é"]}) == '{"a":[1.5,"é"],"b":1}'.encode(), ""))
    out.append(("digest_stable", digest({"x": 1}).startswith("sha256:"), ""))
    out.append(("result_protocol", RESULT_CODE_POLICY["version"] == "PK_DYN_RESULT/1", ""))
    return out


def qualify(observed: dict | None = None, *, declared: dict = DECLARED) -> dict:
    observed = observe() if observed is None else observed
    checks = smoke()
    passed = all(ok for _, ok, _ in checks)
    cells = []
    for dim, values in declared.items():
        for v in values:
            if dim == "provider" and v != "none":
                state = "BLOCKED"
            elif dim == "protocol":
                state = "PASS" if passed else "FAIL"
            elif observed.get(dim) == v:
                state = "PASS" if passed else "FAIL"
            else:
                state = "NOT_RUN"
            cells.append({"dimension": dim, "value": v, "state": state})
    unsupported = [d for d in ("python", "arch", "os", "implementation")
                   if observed.get(d) not in declared.get(d, [])]
    if observed.get("python") and tuple(map(int, observed["python"].split("."))) < (3, 10):
        unsupported.append("python<3.10")
    report = {"schema": "PK_DYN_ENVMATRIX/1", "observed": observed,
              "smoke": [{"name": n, "ok": ok, "detail": d} for n, ok, d in checks],
              "cells": cells, "unsupported_observed": unsupported,
              "certified": False,
              "certification_blocker": "only the current environment was executed; other cells NOT_RUN"}
    report["digest"] = digest({k: v for k, v in report.items() if k != "digest"})
    return report
