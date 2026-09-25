"""Verify an INV11_EVIDENCE/1 bundle: digests, subject consistency, and the
no-false-green rules.  `--self-test` proves tampering is detected."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile


def check(path: str) -> list[str]:
    errs = []
    b = json.load(open(path))
    base = os.path.dirname(os.path.abspath(path))
    claimed = b.pop("bundle_sha256", None)
    if claimed != hashlib.sha256(json.dumps(b, indent=1, sort_keys=True).encode()).hexdigest():
        errs.append("bundle digest mismatch")
    if b.get("schema") != "INV11_EVIDENCE/1":
        errs.append("unknown schema")
    for rel, digest in sorted(b.get("artifacts", {}).items()):
        p = os.path.join(base, rel)
        if not os.path.isfile(p):
            errs.append(f"missing artifact {rel}")
        elif hashlib.sha256(open(p, "rb").read()).hexdigest() != digest:
            errs.append(f"artifact digest mismatch {rel}")
    arc = os.path.join(base, "release", b["subject"]["archive"])
    if os.path.isfile(arc) and hashlib.sha256(open(arc, "rb").read()).hexdigest() != b["subject"]["sha256"]:
        errs.append("subject archive digest mismatch")
    comps: dict = {}
    for it in b["items"]:
        if it["status"] == "PASS" and not it["id"].endswith("GATE") and not it.get("evidence"):
            errs.append(f"{it['id']}: PASS without evidence")
        comps.setdefault(it["component"], []).append(it)
    for c, rows in comps.items():
        gate = next((r for r in rows if r["id"].endswith("GATE")), None)
        if gate and gate["status"] == "PASS" and any(r["status"] != "PASS" for r in rows if r is not gate):
            errs.append(f"component {c}: gate PASS with open items")
    if len(comps) != 40:
        errs.append(f"expected 40 components, found {len(comps)}")
    if b["runs"]["pk_core"]["status"] != "OK" and any(p["id"] == "INV11-PROGRAM-009" and p["status"] in ("PASS", "MET") for p in b["program_gates"]):
        errs.append("PROGRAM-009 passed without pk_core")
    return errs


def self_test(path: str) -> int:
    base = os.path.dirname(os.path.abspath(path))
    with tempfile.TemporaryDirectory() as td:
        copy_dir = os.path.join(td, "e")
        shutil.copytree(base, copy_dir)
        bp = os.path.join(copy_dir, os.path.basename(path))
        assert check(bp) == [], check(bp)
        b = json.load(open(bp))
        # 1 tamper an artifact
        rel = sorted(b["artifacts"])[0]
        open(os.path.join(copy_dir, rel), "ab").write(b"x")
        assert any("artifact digest mismatch" in e for e in check(bp))
        shutil.rmtree(copy_dir)
        shutil.copytree(base, copy_dir)
        # 2 flip a gate to PASS (bundle digest and gate rule both catch it)
        b2 = copy.deepcopy(b)
        g = next(i for i in b2["items"] if i["id"].endswith("GATE"))
        g["status"] = "PASS"
        json.dump(b2, open(bp, "w"), indent=1, sort_keys=True)
        e = check(bp)
        assert any("bundle digest" in x for x in e) and any("gate PASS with open items" in x for x in e), e
        # 3 missing evidence file
        shutil.rmtree(copy_dir)
        shutil.copytree(base, copy_dir)
        os.unlink(os.path.join(copy_dir, "perf.json"))
        assert any("missing artifact perf.json" in x for x in check(bp))
    print("self-test: tamper, gate-forgery and missing-evidence all detected")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "--self-test":
        sys.exit(self_test(sys.argv[1]))
    errs = check(sys.argv[1])
    print("\n".join(errs) if errs else "evidence bundle verified")
    sys.exit(1 if errs else 0)
