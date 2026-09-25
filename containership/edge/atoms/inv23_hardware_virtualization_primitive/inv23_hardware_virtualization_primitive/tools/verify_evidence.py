"""Independent verification of sealed INV-23 gate evidence (MC-14).

Checks: checksums, release-ledger chain, pk_core ledger chain, gate schema, version
consistency, 100 unique requirements, no failures/blocked, no disallowed mandatory skips,
SLO, compatibility evidence, dependency identity, SBOM + provenance presence and digests,
optional wheel hash.  Exit 0 = evidence intact (verdict printed); 1 = evidence broken;
with --require-go also 1 unless the verdict is GO.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import ROOT, canonical, sha256_bytes, sha256_file, version  # noqa: E402


def verify(wheel=None) -> tuple:
    errs = []
    EV, CF = ROOT / "evidence", ROOT / "conformance"
    ck = EV / "checksums.sha256"
    if not ck.exists():
        return ["evidence/checksums.sha256 missing"], None
    for line in ck.read_text().splitlines():
        h, n = line.split("  ", 1)
        if not (ROOT / n).exists() or sha256_file(ROOT / n) != h:
            errs.append(f"checksum mismatch: {n}")
    prev = None
    for i, ln in enumerate((EV / "inv23_release_ledger.jsonl").read_text().splitlines()):
        r = json.loads(ln)
        d = r.pop("digest")
        if sha256_bytes(canonical(r)) != d:
            errs.append(f"release ledger record {i} tampered")
        if r["prev"] != prev or r["seq"] != i:
            errs.append(f"release ledger chain broken at record {i}")
        prev = d
    gate = json.loads((CF / "PK_GATE_RESULTS.json").read_text())
    if prev is None or json.loads((EV / "inv23_release_ledger.jsonl").read_text().splitlines()[-1])["gate_sha256"] != sha256_file(
        CF / "PK_GATE_RESULTS.json"
    ):
        errs.append("gate result is not the ledger head")
    sys.path.insert(0, str(ROOT.parent))
    from importlib import import_module

    try:
        import_module(f"{ROOT.name}.schema").validate(gate, "PK_GATE_RESULTS/1")
    except ValueError as e:
        errs.append(f"gate schema: {e}")
    if gate["version"] != version():
        errs.append("gate version != VERSION")
    pk = gate["environment"]["pk_core"]
    if pk["status"] != "ok" or not pk.get("version"):
        errs.append("dependency identity missing / pk_core not ok (non-certifiable)")
    ids = [c["check_id"] for c in gate["checks"]]
    if len(ids) != 100 or len(set(ids)) != 100:
        errs.append(f"expected 100 unique requirements, found {len(set(ids))}")
    bad = [c["check_id"] for c in gate["checks"] if c["status"] in ("failed", "blocked", "fail")]
    if bad:
        errs.append(f"failing/blocked requirements: {bad[:5]}")
    for name, j in gate["mandatory_jobs"].items():
        if not j["ok"]:
            errs.append(f"mandatory job {name} not ok")
        errs += [f"mandatory job {name} skipped {s['id']}" for s in j["skipped"] if not s.get("allowed")]
    if not gate.get("slo") or not gate["slo"]["pass"]:
        errs.append("SLO evidence missing or failing")
    if not (EV / "compatibility-results.json").exists():
        errs.append("compatibility evidence missing")
    for k in ("sbom", "provenance"):
        a = gate["artifacts"].get(k)
        if not a or not (ROOT / a["path"]).exists() or sha256_file(ROOT / a["path"]) != a["sha256"]:
            errs.append(f"{k} missing or digest mismatch")
    if wheel:
        w = gate["artifacts"].get("wheel")
        if not w or w["sha256"] != sha256_file(wheel):
            errs.append("wheel hash does not match the certified artifact")
    try:
        from pk_core.evidence import EvidenceLedger  # resolved via vendor path below
    except ImportError:
        sys.path.insert(0, str(ROOT / "vendor"))
        from pk_core.evidence import EvidenceLedger
    d = EvidenceLedger(EV / "pk_evidence.jsonl").verify()
    if d:
        errs.append(f"pk_core evidence chain broken: {d[:3]}")
    return errs, gate


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--wheel")
    ap.add_argument("--require-go", action="store_true")
    a = ap.parse_args()
    errs, gate = verify(a.wheel)
    for e in errs:
        print("FAIL", e)
    if gate:
        print(f"verdict: {gate['verdict']}  certifiable={gate['certifiable']}")
        for b in gate.get("blocking_reasons", []):
            print("  BLOCKER", b)
    ok = not errs and (not a.require_go or (gate and gate["verdict"] == "GO"))
    print("evidence intact" if not errs else "evidence BROKEN")
    sys.exit(0 if ok else 1)
