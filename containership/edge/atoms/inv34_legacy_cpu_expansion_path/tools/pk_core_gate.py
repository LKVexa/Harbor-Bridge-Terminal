"""pk_core certification gate (MC-001, MC-061). Hard-fails production certification unless
pk_core is importable AND matches the digest pinned in governance/DEPENDENCIES.lock.json.
Local unit tests are unaffected (they run without pk_core by design)."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys

from _common import PKG, write_json


def main() -> int:
    lock = json.loads((PKG / "governance/DEPENDENCIES.lock.json").read_text())
    pin = lock["dependencies"]["pk_core"]
    spec = importlib.util.find_spec("pk_core")
    res = {"schema": "INV34_PK_CORE_GATE/1", "pin": pin}
    if spec is None or not spec.submodule_search_locations:
        res.update(verdict="FAIL", reason="pk_core not importable in this environment")
    elif pin.get("sha256") in (None, "UNRESOLVED"):
        res.update(verdict="FAIL", reason="pk_core present but no approved digest is pinned")
    else:
        root = pathlib.Path(list(spec.submodule_search_locations)[0])
        h = hashlib.sha256()
        for f in sorted(root.rglob("*.py")):
            h.update(f.relative_to(root).as_posix().encode() + hashlib.sha256(f.read_bytes()).digest())
        got = h.hexdigest()
        res.update(observed_sha256=got, verdict="PASS_PIN_ONLY" if got == pin["sha256"] else "FAIL",
                   reason="digest matches; framework gate itself must still be run" if got == pin["sha256"]
                   else "pk_core digest does not match the pin")
    write_json("governance/PK_CORE_GATE.json", res)
    print(json.dumps(res))
    return 0 if res["verdict"].startswith("PASS") else 2


if __name__ == "__main__":
    sys.exit(main())
