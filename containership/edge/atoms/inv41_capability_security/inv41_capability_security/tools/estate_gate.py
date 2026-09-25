"""Estate integration gate for C030/C083/C090/C100 (Section 6, REQ-EST-001).

Replaces skip-as-success with explicit states.  PASS requires pk_core to be
importable AND its provenance to match ``estate/pk_core.pin.json`` AND the
conformance suite to pass.  Anything else is FAIL or BLOCKED — never PASS.
``--profile production`` exits non-zero unless every item is PASS;
``--profile development`` records BLOCKED and exits 0.
Output: evidence/estate_gate.json (hash-chained records).
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import pathlib
import platform
import subprocess
import sys
import time

PKG = pathlib.Path(__file__).resolve().parents[1]
ITEMS = ("INV-41-C030", "INV-41-C083", "INV-41-C090", "INV-41-C100")


def _pk_core_state(pin: dict):
    for p in filter(None, [os.environ.get("PK_CORE_PATH"), str(PKG.parent.parent), str(PKG.parent)]):
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        mod = importlib.import_module("pk_core")
    except ModuleNotFoundError:
        return "BLOCKED", "pk_core not importable", None
    root = pathlib.Path(mod.__file__).parent
    h = hashlib.sha256()
    for f in sorted(root.rglob("*.py")):
        h.update(f.relative_to(root).as_posix().encode() + b"\0" + f.read_bytes())
    digest = h.hexdigest()
    if not pin.get("tree_sha256"):
        return "BLOCKED", "pk_core found but no approved pin in estate/pk_core.pin.json", digest
    if digest != pin["tree_sha256"]:
        return "FAIL", "pk_core provenance mismatch against pin", digest
    return "READY", "pk_core pinned and verified", digest


def main() -> int:
    profile = sys.argv[sys.argv.index("--profile") + 1] if "--profile" in sys.argv else "development"
    pin = json.loads((PKG / "estate" / "pk_core.pin.json").read_text())
    state, detail, digest = _pk_core_state(pin)
    results = []
    if state == "READY":
        p = subprocess.run([sys.executable, "-B", str(PKG / "tests" / "test_component.py")], capture_output=True, text=True,
                           env=dict(os.environ, INV41_PROFILE="production"))
        state = "PASS" if p.returncode == 0 else "FAIL"
        detail = p.stderr[-2000:]
    prev = "0" * 64
    for item in ITEMS:
        rec = {"check_id": item, "state": state, "detail": detail, "pk_core_tree_sha256": digest,
               "pin": pin, "profile": profile, "python": platform.python_version(), "at": time.time(), "prev": prev}
        rec["digest"] = hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()
        prev = rec["digest"]
        results.append(rec)
    out = {"schema": "INV41_ESTATE_GATE/1", "profile": profile, "head": prev, "results": results,
           "production_ok": all(r["state"] == "PASS" for r in results)}
    (PKG / "evidence").mkdir(exist_ok=True)
    (PKG / "evidence" / "estate_gate.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({i["check_id"]: i["state"] for i in results}))
    if profile == "production" and not out["production_ok"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
