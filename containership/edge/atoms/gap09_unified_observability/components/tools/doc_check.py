"""MASTER.md / documentation consistency checker (60).

Checks every local file reference in the package's Markdown files resolves,
and reports -- as a FAIL, not a warning -- any document that claims an
artifact the package does not contain.  The v5.0.0 README's MASTER.md
reference is therefore a standing finding until the authoritative MASTER.md
is recovered (the owner has it, this archive does not)."""
from __future__ import annotations

import os
import re
import sys

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REF = re.compile(r"`([A-Za-z0-9_./-]+\.(?:md|json|py|cmd|sha256|mjs))`")
KNOWN_ABSENT_OK = set()  # nothing is excused
INPUTS = {"components/checklist/GAP09_MISSING_COMPONENTS_CHECKLIST.md"}  # vendored input, not a package doc


def _index(pkg):
    names = set()
    for dp, _, fns in os.walk(pkg):
        names.update(fns)
    return names


def check(pkg=PKG) -> list[dict]:
    findings = []
    names = _index(pkg)
    for dp, _, fns in os.walk(pkg):
        if "__pycache__" in dp:
            continue
        for f in fns:
            if not f.endswith(".md"):
                continue
            p = os.path.join(dp, f)
            if os.path.relpath(p, pkg).replace(os.sep, "/") in INPUTS:
                continue
            text = open(p, encoding="utf-8").read()
            if text.startswith("﻿"):
                findings.append({"file": os.path.relpath(p, pkg), "ref": None, "issue": "UTF-8 BOM"})
            for m in REF.finditer(text):
                ref = m.group(1)
                cands = [os.path.join(dp, ref), os.path.join(pkg, ref), os.path.join(pkg, "components", ref)]
                bare = "/" not in ref and ref in names
                if not any(os.path.exists(c) for c in cands) and not bare and ref not in KNOWN_ABSENT_OK:
                    findings.append({"file": os.path.relpath(p, pkg).replace(os.sep, "/"), "ref": ref, "issue": "missing target"})
    uniq = {(f["file"], f["ref"], f["issue"]): f for f in findings}
    return sorted(uniq.values(), key=lambda x: (x["file"], str(x["ref"])))


if __name__ == "__main__":
    fs = check()
    for f in fs:
        print(f"FAIL {f['file']}: {f['issue']} -> {f['ref']}")
    print("DOC-CHECK", "FAIL" if fs else "PASS", len(fs))
    sys.exit(1 if fs else 0)
