"""Third-party verification of the local evidence bundle (closure #41).

    python tools/verify_evidence.py [evidence_dir]

Checks: every ledger record's hash, the prev-hash chain, every artifact digest,
that every record binds the same release SHA256SUMS digest, that the gate's
ledger head matches, and that no checklist item is claimed PASS.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys


def verify(ev: pathlib.Path) -> list[str]:
    errs = []
    prev = "0" * 64
    sums = hashlib.sha256((ev / "release" / "SHA256SUMS").read_bytes()).hexdigest()
    for i, line in enumerate((ev / "inv16_local_evidence.jsonl").read_text().splitlines(), 1):
        rec = json.loads(line)
        h = rec.pop("hash")
        if hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest() != h:
            errs.append(f"record {i}: hash mismatch")
        if rec["prev"] != prev:
            errs.append(f"record {i}: chain broken")
        art = ev / rec["path"]
        if not art.exists() or hashlib.sha256(art.read_bytes()).hexdigest() != rec["sha256"]:
            errs.append(f"record {i}: artifact {rec['path']} digest mismatch")
        if rec["release_sha256sums"] != sums:
            errs.append(f"record {i}: not bound to this release")
        prev = h
    gate = json.loads((ev / "INV16_LOCAL_GATE.json").read_text())
    if gate["ledger_head"] != prev:
        errs.append("gate ledger_head does not match chain head")
    items = json.loads((ev / "checklist_items.json").read_text())
    if items["count"] != 100 or any(x["status"] == "PASS" for x in items["items"]):
        errs.append("checklist representation invalid or PASS claimed without pk_core")
    return errs


if __name__ == "__main__":
    ev = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[1] / "evidence"
    e = verify(ev)
    print("EVIDENCE OK" if not e else "\n".join(e))
    raise SystemExit(0 if not e else 1)
