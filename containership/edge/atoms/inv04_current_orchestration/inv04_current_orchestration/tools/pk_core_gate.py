#!/usr/bin/env python3
"""pk_core integration gate (component 78).

  python tools/pk_core_gate.py

Runs the 100-item estate conformance suite (tests/test_component.py) and
FAILS when pk_core is not importable - absence is a failed gate, never a
silent skip.  Set ``INV04_PK_CORE=not_applicable`` together with
``INV04_PK_CORE_WAIVER=<waiver id>`` to record an explicit, owned waiver;
the gate then exits 0 but prints WAIVED so release evidence shows it.
Set ``PK_CORE_PATH`` to the pinned checkout (pyproject extra ``pk-core``).
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import subprocess  # noqa: S404
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
PINNED = "4.0"


def main() -> int:
    if os.environ.get("PK_CORE_PATH"):
        sys.path.insert(0, os.environ["PK_CORE_PATH"])
    spec = importlib.util.find_spec("pk_core")
    if spec is None:
        if os.environ.get("INV04_PK_CORE") == "not_applicable" and os.environ.get("INV04_PK_CORE_WAIVER"):
            print(f"PK_CORE GATE: WAIVED ({os.environ['INV04_PK_CORE_WAIVER']})")
            return 0
        print("PK_CORE GATE: FAIL - pk_core is not importable; the 100-item conformance suite cannot run. "
              "Install the pinned pk_core (extra 'pk-core') or record a waiver.")
        return 1
    import pk_core  # type: ignore[import-not-found]
    version = getattr(pk_core, "__version__", "unknown")
    if not str(version).startswith(PINNED):
        print(f"PK_CORE GATE: FAIL - pk_core {version} does not match pin {PINNED}.*")
        return 1
    env = dict(os.environ, INV04_REQUIRE_PK_CORE="1")
    rc = 0
    for flags in ([], ["-O"]):
        proc = subprocess.run([sys.executable, *flags, str(PKG / "tests" / "test_component.py")], env=env)  # noqa: S603
        rc |= proc.returncode
    print("PK_CORE GATE:", "OK" if rc == 0 else "FAIL")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
