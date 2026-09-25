"""Clean-node smoke test (C040): activate config, capture, restore with grant, verify audit chain."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    from ..tests.harness import Rig
    r = Rig(str(Path(a.root) / "smoke"))
    snap = r.capture("smoke")
    st, body = r.restore(snap)
    rep = r.svc.reconcile()
    doc = {"schema": "PK_SNAPSHOT_SMOKE/1", "capture": snap["state"], "restore_status": st,
           "restore_state": body.get("state"), "ready": r.svc.health()["ready"], "audit_records": r.audit.verify(),
           "reconcile": {k: len(v) for k, v in rep.items() if isinstance(v, list)},
           "profile": "reference", "note": "reference VMM; a production smoke needs KVM + Firecracker"}
    doc["result"] = "PASS" if st == 200 and doc["ready"] else "FAIL"
    if a.out:
        Path(a.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps(doc))
    return 0 if doc["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
