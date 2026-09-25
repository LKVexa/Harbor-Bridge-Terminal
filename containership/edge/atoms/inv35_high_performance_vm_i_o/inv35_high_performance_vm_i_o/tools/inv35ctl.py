"""Reference operator CLI for INV-35 (runbooks). Operates on an in-process runtime for
drills/smoke tests; production tooling calls the same ControlPlane API remotely.

  python tools/inv35ctl.py config-check FILE
  python tools/inv35ctl.py smoke
  python tools/inv35ctl.py explain
  python tools/inv35ctl.py status
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
rt = importlib.import_module(PKG.name + ".runtime")
config = importlib.import_module(PKG.name + ".runtime.config")
wire = importlib.import_module(PKG.name + ".runtime.wire")
pkg = importlib.import_module(PKG.name)


def smoke() -> tuple[int, rt.Runtime]:
    failures = 0
    last = None
    for f in sorted((PKG / "fixtures").rglob("*.json")):
        fx = json.loads(f.read_text())
        r = rt.Runtime()
        cp, dp = rt.ControlPlane(r), rt.Datapath(r)
        ctl = r.authority.mint("smoke", "t1", {"q0"}, {"register_memory", "read_status"})
        bulk = r.authority.mint("smoke", "t1", {"q0"}, {"submit", "complete"})
        cp.register_queue(ctl, tenant="t1", queue="q0",
                          regions=tuple(pkg.MemoryRegion(b, l) for b, l in fx["setup"]["regions"]))
        try:
            req = wire.decode_submit(fx["request"])
            dp.submit(bulk, tenant="t1", queue="q0", chain=req["chain"], head=req["head"])
            got = "INV35-E000"
        except rt.Inv35Error as exc:
            got = exc.code
        ok = got == fx["expect"]
        failures += not ok
        print(f"{'OK  ' if ok else 'FAIL'} {f.parent.name}/{f.stem}: expect {fx['expect']} got {got}")
        last = r
    return failures, last


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "config-check":
        values, prov = config.load_file(argv[1])
        print(f"CONFIG=OK digest={prov['digest']} profile={values['profile']}")
        return 0
    if cmd == "smoke":
        failures, _ = smoke()
        print(f"SMOKE={'PASS' if not failures else 'FAIL'} failures={failures}")
        return 1 if failures else 0
    if cmd in ("explain", "status"):
        _, r = smoke()
        print(r.explain() if cmd == "explain" else json.dumps(r.status(), indent=2))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
