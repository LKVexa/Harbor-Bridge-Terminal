"""MC-01: verify MASTER.md provenance. Never reconstructs the source.  Exit 0 VERIFIED, 3 EVIDENCE_GAP, 1 MISMATCH."""
from _common import PKG, dump, sha
import json, sys

def main() -> int:
    rec_p = PKG / "evidence/master_provenance.json"
    master = PKG / "MASTER.md"
    rec = json.loads(rec_p.read_text()) if rec_p.exists() else None
    if not master.exists():
        out = {"schema": "PK_MASTER_PROVENANCE/1", "status": "EVIDENCE_GAP", "master_present": False,
               "checklist_sha256": sha(PKG / "CHECKLIST.json"),
               "reason": "MASTER.md not in the supplied archive; not reconstructed. Needs the canonical source or an approved waiver.",
               "waiver": None}
        dump(rec_p, out); print(json.dumps(out)); return 3
    if not rec or rec.get("master_sha256") != sha(master):
        print("MISMATCH: MASTER.md digest does not match provenance record"); return 1
    print("VERIFIED"); return 0

if __name__ == "__main__": sys.exit(main())
