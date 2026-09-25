"""MC-019 -- interface/version negotiation and compatibility matrix."""
from __future__ import annotations

import datetime as _dt
from typing import Any

from .errors import ErrorCode, Inv13Error

MATRIX: dict[str, Any] = {
    "schema": "INV13_COMPAT/1",
    "host_release": "4.3.0",
    "interfaces": {
        # package version -> support status + EOL (ISO date). Additive minor changes only.
        "inv13:system-interface@4.3.0": {"status": "supported", "eol": "2027-09-30"},
        "inv13:system-interface@4.2.0": {"status": "deprecated", "eol": "2026-12-31",
                                         "note": "4.2.0 had no WIT; guests declared worlds by name only"},
    },
    "engines": {"v8-node": {"min": "18.0.0", "tested": ["22.22.2"], "abi": "core-wasm"},
                "wasmtime": {"status": "not-integrated", "abi": "component-model"}},
    "python": {"min": "3.10", "tested": ["3.11.15"]},
    "platforms": {"linux-x86_64": "tested", "linux-aarch64": "untested",
                  "darwin-arm64": "untested", "windows-x86_64": "fs-unsupported"},
}


def _v(s: str) -> tuple[int, int, int]:
    parts = s.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise Inv13Error(ErrorCode.UNSUPPORTED_VERSION, s)
    return tuple(int(p) for p in parts)  # type: ignore[return-value]


def negotiate(requested: list[str], *, today: _dt.date | None = None) -> str:
    """Pick the highest mutually supported package the guest requested.

    Accepts same-major, requested-minor <= host-minor (host is additive-compatible).
    Past-EOL versions are refused; deprecated versions are allowed until EOL.
    """
    today = today or _dt.date.today()
    best = None
    for req in requested:
        if not isinstance(req, str) or "@" not in req:
            continue
        pkg, ver = req.rsplit("@", 1)
        rv = _v(ver)
        for known, meta in MATRIX["interfaces"].items():
            kpkg, kver = known.rsplit("@", 1)
            kv = _v(kver)
            if kpkg != pkg or kv[0] != rv[0] or rv[1] > kv[1]:
                continue
            if _dt.date.fromisoformat(meta["eol"]) < today:
                continue
            if rv[1] == kv[1] and rv[2] > kv[2]:
                continue
            if best is None or kv > _v(best.rsplit("@", 1)[1]):
                best = known
    if best is None:
        raise Inv13Error(ErrorCode.UNSUPPORTED_VERSION, requested)
    return best
