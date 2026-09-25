"""MC-103 / MC-093 — production exit gate.

GO requires ALL of: every MC component IMPLEMENTED *and* accepted; no _UNASSIGNED_ role in
docs/OWNERSHIP.md; test suite green with INV39_CERT_TARGET=1 (no skips); release artifact present,
SBOM + provenance present and matching, release signature present; a signed acceptance record
from an independent reviewer (acceptance.json + acceptance.sig verified with INV39_ACCEPT_KEY).
Anything else -> NO_GO with every reason listed.  Writes evidence/exit-gate.json (unsigned
acceptance *bundle* for a reviewer to sign).
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", default=str(HERE.parent / "dist"))
    ap.add_argument("--out", default=str(HERE / "evidence" / "exit-gate.json"))
    ap.add_argument("--skip-tests", action="store_true", help="for unit-testing the gate itself")
    a = ap.parse_args(argv)
    reasons = []
    tr = json.loads((HERE / "TRACEABILITY.json").read_text())
    for c in tr["components"]:
        if c["status"] != "IMPLEMENTED":
            reasons.append(f"{c['id']} {c['status']}: {c['gap']}")
        elif not c["accepted"]:
            reasons.append(f"{c['id']} implemented but not accepted")
    if "_UNASSIGNED_" in (HERE / "docs" / "OWNERSHIP.md").read_text():
        reasons.append("ownership roles unassigned (MC-001)")
    tests = {"ran": False}
    if not a.skip_tests:
        env = dict(os.environ, INV39_CERT_TARGET="1", INV39_FUZZ_ITERS="500")
        p = subprocess.run([sys.executable, "-W", "ignore", str(HERE / "tests" / "run_all.py")],
                           capture_output=True, text=True, env=env)
        tests = {"ran": True, "rc": p.returncode, "tail": p.stderr.strip().splitlines()[-3:]}
        if p.returncode:
            reasons.append("certification-mode test run failed (skips count as failures)")
    dist = pathlib.Path(a.dist)
    arts = sorted(dist.glob("*.zip")) if dist.exists() else []
    art = {}
    if not arts:
        reasons.append("no release artifact")
    else:
        z = arts[-1]
        d = hashlib.sha256(z.read_bytes()).hexdigest()
        stem = z.name[:-4]
        art = {"artifact": z.name, "sha256": d}
        prov = dist / f"{stem}.provenance.json"
        if not (dist / f"{stem}.sbom.json").exists() or not prov.exists():
            reasons.append("SBOM or provenance missing")
        elif json.loads(prov.read_text())["subject"][0]["digest"]["sha256"] != d:
            reasons.append("provenance does not match artifact")
        if not (dist / f"{stem}.sig").exists():
            reasons.append("release artifact unsigned (MC-105)")
    acc, sig = HERE / "evidence" / "acceptance.json", HERE / "evidence" / "acceptance.sig"
    key = os.environ.get("INV39_ACCEPT_KEY", "").encode()
    if not (acc.exists() and sig.exists() and len(key) >= 32 and hmac.compare_digest(
            sig.read_text().strip(), hmac.new(key, acc.read_bytes(), hashlib.sha256).hexdigest())):
        reasons.append("no verified signed acceptance from an independent reviewer (MC-093)")
    verdict = "GO" if not reasons else "NO_GO"
    out = {"schema": "INV39_EXIT_GATE/1", "ts": int(time.time()), "verdict": verdict, "summary": tr["summary"],
           "artifact": art, "tests": tests, "reasons": reasons}
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"verdict": verdict, "reasons": len(reasons)}))
    return 0 if verdict == "GO" else 1


if __name__ == "__main__":
    sys.exit(main())
