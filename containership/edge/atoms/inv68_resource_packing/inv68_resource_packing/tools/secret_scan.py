"""Repository secret scan (INV-68 MC-11, MC-16; C039, C075).

    python -m inv68_resource_packing.tools.secret_scan [--out evidence/]

Scans every text file in the package with the same detector the runtime uses
(:func:`redaction.classify_text`), line by line.  Hits are FAIL unless the
exact ``(path, pattern)`` pair is in ``ops/secret_scan_allowlist.json`` with a
reason (deliberate *fake* credentials in negative tests).  Reports locations
and pattern classes only -- never the matched text.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common import PKG, write

from inv68_resource_packing.redaction import classify_text  # noqa: E402

SKIP_DIRS = {"__pycache__", ".git", "evidence", "dist", "build", "release"}
TEXT = {".py", ".md", ".json", ".txt", ".toml", ".yml", ".yaml", ".sh", ".ps1", ".cfg", ".ini", ".wit", ""}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PKG / "evidence"))
    a = ap.parse_args(argv)
    allow = {(e["path"], e["pattern"]): e["reason"]
             for e in json.loads((PKG / "ops" / "secret_scan_allowlist.json").read_text())["entries"]}
    hits, allowed, files = [], [], 0
    for p in sorted(PKG.rglob("*")):
        rel = p.relative_to(PKG)
        if not p.is_file() or SKIP_DIRS & set(rel.parts) or p.suffix not in TEXT or p.stat().st_size > 2_000_000:
            continue
        files += 1
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for no, line in enumerate(lines, 1):
            cls = classify_text(line)
            if cls:
                entry = {"path": rel.as_posix(), "line": no, "pattern": cls}
                (allowed if (rel.as_posix(), cls) in allow else hits).append(entry)
    write(Path(a.out) / "SECRET_SCAN.json", {"schema": "PK_PACK_SECRET_SCAN/1", "files_scanned": files,
                                             "findings": hits, "allowlisted": allowed,
                                             "result": "PASS" if not hits else "FAIL"})
    print(f"SECRET_SCAN {'PASS' if not hits else 'FAIL'}: {files} files, {len(hits)} findings, {len(allowed)} allowlisted")
    for h in hits:
        print("  ", h)
    return 0 if not hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
