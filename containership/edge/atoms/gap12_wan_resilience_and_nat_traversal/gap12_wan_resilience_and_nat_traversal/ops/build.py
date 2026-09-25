"""Reproducible source artifact (G12-I102).

Builds ``dist/gap12_wan_resilience_and_nat_traversal-<version>.zip`` from the
package tree with sorted entries, fixed timestamps (SOURCE_DATE_EPOCH, default
2026-09-22T00:00:00Z), fixed permissions, no __pycache__/evidence outputs, and
prints the SHA-256.  Two builds of the same tree are byte-identical; ``--check``
builds twice into temporary files and fails if the digests differ.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.basename(ROOT)
EXCLUDE_DIRS = {"__pycache__", "dist", ".git"}
EXCLUDE_PREFIXES = ("evidence/out/", "evidence/lab/")          # run outputs are not source


def version() -> str:
    with open(os.path.join(ROOT, "VERSION")) as fh:
        return fh.read().strip()


def files() -> list[str]:
    out = []
    for d, dirs, fs in os.walk(ROOT):
        dirs[:] = sorted(x for x in dirs if x not in EXCLUDE_DIRS)
        for f in sorted(fs):
            if f.endswith((".pyc", ".pyo")):
                continue
            rel = os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, "/")
            if rel.startswith(EXCLUDE_PREFIXES) or rel == "MANIFEST.sha256":     # derivative of the tree
                continue
            out.append(rel)
    return sorted(out)


def build(dest: str) -> str:
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "1790035200"))
    import time
    dt = time.gmtime(max(epoch, 315532800))[:6]
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in files():
            info = zipfile.ZipInfo(f"{PKG}/{rel}", date_time=dt)
            info.external_attr = (0o644 << 16)
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(os.path.join(ROOT, rel), "rb") as fh:
                z.writestr(info, fh.read())
    with open(dest, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if a.check:
        d = tempfile.mkdtemp()
        h1, h2 = build(os.path.join(d, "1.zip")), build(os.path.join(d, "2.zip"))
        print(f"build-1 {h1}\nbuild-2 {h2}")
        return 0 if h1 == h2 else 1
    os.makedirs(a.out, exist_ok=True)
    dest = os.path.join(a.out, f"{PKG}-{version()}.zip")
    print(build(dest), dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
