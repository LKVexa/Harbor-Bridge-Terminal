"""Release packaging + unsigned provenance statement (MC-084, MC-036).

    python -B -m inv28_unikernel_implementations.tools.package_release --out DIR

Writes DIR/inv28_unikernel_implementations-<ver>.zip (deterministic: sorted entries, fixed timestamps),
DIR/<zip>.sha256 and DIR/provenance.intoto.json - an in-toto Statement with a SLSA-provenance-shaped
predicate naming the source archive, applied checklist, builder and the SHA256SUMS digest.  The statement
is **not signed** (no signing identity, D-005); verification is by digest only, and the file says so.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

from ._common import CACHE_DIRS, ROOT, read_json

FIXED = (2026, 9, 23, 0, 0, 0)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ver = (ROOT / "VERSION").read_text().strip()
    zpath = out / f"{ROOT.name}-{ver}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(ROOT.rglob("*")):
            rel = p.relative_to(ROOT).as_posix()
            if p.is_file() and not CACHE_DIRS & set(p.parts):
                info = zipfile.ZipInfo(f"{ROOT.name}/{rel}", FIXED)
                info.external_attr = 0o644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, p.read_bytes())
    digest = hashlib.sha256(zpath.read_bytes()).hexdigest()
    (out / (zpath.name + ".sha256")).write_text(f"{digest}  {zpath.name}\n")
    prov = read_json(ROOT / "evidence" / "PROVENANCE.json") if (ROOT / "evidence" / "PROVENANCE.json").exists() else {}
    stmt = {"_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": zpath.name, "digest": {"sha256": digest}}],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {"buildDefinition": {"buildType": "inv28/package_release@1",
                                              "externalParameters": {"version": ver},
                                              "resolvedDependencies": [x for x in (prov.get("source_archive"),
                                                                                   prov.get("applied_package")) if x]},
                          "runDetails": {"builder": {"id": prov.get("builder", "local")},
                                         "metadata": {"sha256sums_digest": hashlib.sha256(
                                             (ROOT / "SHA256SUMS.txt").read_bytes()).hexdigest()
                                             if (ROOT / "SHA256SUMS.txt").exists() else None}}},
            "signature": None, "note": "UNSIGNED - verify by digest only (D-005)"}
    (out / "provenance.intoto.json").write_text(json.dumps(stmt, indent=1) + "\n")
    print("PACKAGE", zpath.name, digest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
