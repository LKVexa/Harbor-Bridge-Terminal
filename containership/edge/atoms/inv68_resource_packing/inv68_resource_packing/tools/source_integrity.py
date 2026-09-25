"""Master-source provenance check (INV-68 MC-01).

    python -m inv68_resource_packing.tools.source_integrity [--out evidence/]

* Every source recorded in ``provenance/master-source.json`` that has a
  ``path`` must exist and match its SHA-256 (tamper detection).
* ``MASTER.md`` is required once ``expected_sha256`` is set; then presence and
  digest are enforced.  While the record says ``UNVERIFIED`` the result is FAIL
  -- 4.3.0 does not synthesize an authoritative master source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .common import PKG, write


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PKG / "evidence"))
    a = ap.parse_args(argv)
    rec = json.loads((PKG / "provenance" / "master-source.json").read_text())
    checks = []
    for s in rec["sources"]:
        if "path" not in s:
            continue
        p = PKG / s["path"]
        ok = p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == s["sha256"]
        checks.append({"check": f"digest {s['path']}", "result": "PASS" if ok else "FAIL"})
    master = PKG / "MASTER.md"
    if rec.get("expected_sha256"):
        ok = master.is_file() and hashlib.sha256(master.read_bytes()).hexdigest() == rec["expected_sha256"]
        checks.append({"check": "MASTER.md present with approved digest", "result": "PASS" if ok else "FAIL"})
    else:
        checks.append({"check": "MASTER.md provenance", "result": "FAIL",
                       "reason": f"status {rec['status']}: authoritative source not supplied; not synthesized"})
    checks.append({"check": "no unverified MASTER.md shipped", "result": "PASS" if not master.exists() or
                   rec.get("expected_sha256") else "FAIL"})
    res = "PASS" if all(c["result"] == "PASS" for c in checks) else "FAIL"
    write(Path(a.out) / "SOURCE_CHECK.json", {"schema": "PK_PACK_SOURCE_CHECK/1", "status": rec["status"],
                                              "checks": checks, "result": res})
    print(f"SOURCE {res}: {[(c['check'], c['result']) for c in checks]}")
    return 0 if res == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
