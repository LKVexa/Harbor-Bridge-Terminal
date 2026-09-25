"""Startup/preflight checks for programmatically detectable assumptions
(Section 3, REQ-ASM-*).  ``run(profile)`` fails closed: any mandatory check
that fails makes ``ok`` False and callers must refuse to start.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import platform
import secrets
import sys
import time
from typing import Final

SUPPORTED_PYTHON: Final[tuple] = ((3, 10), (3, 13))  # inclusive range, see COMPATIBILITY.md
SUPPORTED_IMPLEMENTATIONS: Final[frozenset] = frozenset({"CPython"})


def _check(name, fn, mandatory=True):
    try:
        ok, detail = fn()
    except Exception as exc:  # a crashing check is a failing check
        ok, detail = False, f"check raised {type(exc).__name__}"
    return {"check": name, "ok": bool(ok), "mandatory": mandatory, "detail": detail}


def run(profile: str = "workstation", *, version_info=None, implementation=None) -> dict:
    vi = version_info or sys.version_info
    impl = implementation or platform.python_implementation()
    checks = [
        _check("python.version", lambda: (SUPPORTED_PYTHON[0] <= tuple(vi[:2]) <= SUPPORTED_PYTHON[1], f"{vi[0]}.{vi[1]}")),
        _check("python.implementation", lambda: (impl in SUPPORTED_IMPLEMENTATIONS, impl)),
        _check("entropy.os_urandom", lambda: (len(os.urandom(32)) == 32 and len(set(secrets.token_bytes(32))) > 8, "os.urandom ok")),
        _check("crypto.hmac_sha256", lambda: (hmac.new(b"Jefe", b"what do ya want for nothing?", hashlib.sha256).hexdigest()
                                             == "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843", "RFC 4231 case 2")),
        _check("crypto.compare_digest", lambda: (hmac.compare_digest("a", "a") and not hmac.compare_digest("a", "b"), "ok")),
        _check("clock.monotonic", lambda: (time.monotonic() <= time.monotonic(), "non-decreasing")),
        _check("security.not_optimized_asserts_irrelevant", lambda: (True, f"optimize={sys.flags.optimize}"), mandatory=False),
        _check("profile.known", lambda: (profile in ("cloud", "near-edge", "far-edge", "workstation", "test"), profile)),
    ]
    ok = all(c["ok"] for c in checks if c["mandatory"])
    return {"schema": "INV41_PREFLIGHT/1", "profile": profile, "ok": ok, "checks": checks}


if __name__ == "__main__":
    import json
    r = run(sys.argv[1] if len(sys.argv) > 1 else "workstation")
    print(json.dumps(r, indent=1))
    raise SystemExit(0 if r["ok"] else 2)
