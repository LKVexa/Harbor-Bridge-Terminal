"""MC-49 machine-readable release evidence bundle: digests of every artifact + gate inputs.
Unsigned: signing requires a release authority key that is not present."""
from _common import PKG, dump, files, sha
import json, sys

if __name__ == "__main__":
    ev = lambda p: json.loads((PKG / p).read_text()) if (PKG / p).exists() else None
    doc = {"schema": "PK_RELEASE_EVIDENCE/1", "version": (PKG / "VERSION").read_text().strip(),
           "artifacts": {p.relative_to(PKG).as_posix(): sha(p) for p in files()
                         if not p.relative_to(PKG).as_posix().startswith("evidence/RELEASE_EVIDENCE")},
           "ci": ev("evidence/ci_result.json"), "bench_gate": ev("evidence/bench_gate.json"),
           "exit_gate": (ev("evidence/EXIT_GATE.json") or {}).get("verdict"),
           "checklist_counts": (ev("evidence/CHECKLIST_STATUS.json") or {}).get("counts"),
           "signature": None, "signature_status": "UNSIGNED - no release authority key bound"}
    dump(PKG / "evidence/RELEASE_EVIDENCE.json", doc); print(json.dumps({"artifacts": len(doc["artifacts"]), "exit_gate": doc["exit_gate"]}))
