"""Portable verification entry point for the GAP-01 component package."""
from __future__ import annotations

import compileall
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent


def main() -> int:
    print("GAP-01 Edge Node Supervisor verification")
    print("Python:", sys.version.split()[0])
    if not compileall.compile_dir(ROOT, quiet=1):
        print("FAIL: Python compilation")
        return 1
    print("PASS: Python compilation")

    sys.path.insert(0, str(ROOT.parent))
    sys.path.insert(0, str(ROOT / "tests"))
    for pattern, label in (("test_supervisor.py", "dependency-free lifecycle model suite"),
                           ("test_production.py", "production component unit suite"),
                           ("test_controller.py", "controller/property/concurrency/fuzz suite"),
                           ("test_bootstrap_inventory.py", "bootstrap/inventory/schema-fixture suite"),
                           ("test_integration.py", "socket/process integration + SIGKILL chaos suite")):
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern=pattern)
        result = unittest.TextTestRunner(verbosity=0).run(suite)
        if not result.wasSuccessful():
            print(f"FAIL: {label}")
            return 1
        print(f"PASS: {label}")

    code = (
        "import pathlib,sys; "
        f"sys.path.insert(0,{str(ROOT.parent)!r}); "
        "from gap01_edge_node_supervisor import NodeSupervisor; "
        "s=NodeSupervisor('verify'); s.transition('ready'); s.report_health('runtime',1); "
        "s.admit('w','trusted'); r=s.drain(now=2,deadline=3); "
        "raise SystemExit(0 if r['complete'] and s.state=='stopped' else 2)"
    )
    proc = subprocess.run([sys.executable, "-O", "-c", code], cwd=str(ROOT.parent))
    if proc.returncode:
        print("FAIL: optimized-mode behavioral smoke test")
        return proc.returncode
    print("PASS: optimized-mode behavioral smoke test")

    try:
        import pk_core  # noqa: F401
    except ModuleNotFoundError:
        print("INFO: pk_core unavailable; external 100-check integration gate not executed")
    else:
        proc = subprocess.run([sys.executable, str(ROOT / "tests" / "test_component.py")],
                              cwd=str(ROOT.parent))
        if proc.returncode:
            print("FAIL: pk_core integration suite")
            return proc.returncode
        print("PASS: pk_core integration suite")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
