"""Production exit gate (MC-089, C100).  Produces a machine-readable GO/NO_GO
decision bound to the exact release digests.  GO requires *all* of:
CI overall PASS, perf gate PASS, every MC item implemented (reviewed), no
pending/expired waiver, all owners bound, ADR approved, wasmCloud pin verified,
licence present and a PRODUCTION release signature.

    python inv62_edge_topology/tools/exit_gate.py --evidence evidence --dist dist [--out evidence/exit_gate.json]
"""
from __future__ import annotations

import datetime
import json
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]


def load(p: pathlib.Path):
    return json.loads(p.read_text()) if p.exists() else None


def decide(evidence: pathlib.Path, dist: pathlib.Path) -> dict:
    reasons = []
    ci = load(evidence / "ci_report.json")
    if not ci:
        reasons.append("CI report missing")
    elif ci["overall"] != "PASS":
        bad = sorted(k for k, v in ci["lanes"].items() if v["status"] != "PASS")
        reasons.append(f"CI overall {ci['overall']} (lanes not PASS: {', '.join(bad)})")
    perf = load(evidence / "perf_gate.json")
    if not perf or perf.get("status") != "PASS":
        reasons.append(f"perf gate {perf.get('status') if perf else 'missing'}")
    mc = load(PKG / "conformance" / "mc_status.json")
    not_done = [i for i in mc["items"] if i["status"] != "implemented"]
    if not_done:
        reasons.append(f"{len(not_done)}/94 MC items not implemented+reviewed ({mc['summary']})")
    today = datetime.date.today().isoformat()
    waivers = load(PKG / "governance" / "waivers.json")["waivers"]
    pend = [w["id"] for w in waivers if w["status"] != "approved"]
    expired = [w["id"] for w in waivers if w["expires"] < today]
    if pend:
        reasons.append(f"waivers pending approval: {', '.join(pend)}")
    if expired:
        reasons.append(f"waivers expired: {', '.join(expired)}")
    if "UNBOUND" in (PKG / "docs" / "OWNERSHIP.md").read_text():
        reasons.append("accountable owners / release approver UNBOUND (docs/OWNERSHIP.md)")
    if "Status:** PROPOSED" in (PKG / "docs" / "ADR-0001-wasmcloud-lattice.md").read_text():
        reasons.append("ADR-0001 not approved")
    pin = load(PKG / "wasmcloud.pin.json")
    if not pin or not pin.get("verified"):
        reasons.append("wasmCloud pin not verified (MC-021)")
    if not (PKG / "LICENSE").exists():
        reasons.append("no licence (MC-090)")
    sums = (dist / "SHA256SUMS").read_text().split() if (dist / "SHA256SUMS").exists() else []
    import zipfile
    label = None
    zips = sorted(dist.glob("*.zip"))
    if zips:
        with zipfile.ZipFile(zips[-1]) as z:
            label = json.loads(z.read("inv62_edge_topology/RELEASE_MANIFEST.sig.json")).get("label")
    if label != "PRODUCTION":
        reasons.append(f"release signature label {label} (production key required)")
    return {"schema": "INV62_EXIT_GATE/1", "version": (PKG / "VERSION").read_text().strip(),
            "decision": "NO_GO" if reasons else "GO", "reasons": reasons,
            "bound_to": {"zip": zips[-1].name if zips else None, "zip_sha256": sums[0] if sums else None,
                         "source_tree_sha256": ci.get("source_tree_sha256") if ci else None},
            "approvers": [] if reasons else ["<names from OWNERSHIP.md>"], "decided_at": today}


def main(argv: list[str]) -> int:
    arg = lambda k, d: argv[argv.index(k) + 1] if k in argv else d
    res = decide(pathlib.Path(arg("--evidence", "evidence")), pathlib.Path(arg("--dist", "dist")))
    text = json.dumps(res, indent=2)
    out = arg("--out", None)
    if out:
        pathlib.Path(out).write_text(text + "\n")
    print(text)
    return 0 if res["decision"] == "GO" else 4


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
