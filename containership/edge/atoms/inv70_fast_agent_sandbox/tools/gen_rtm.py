"""Generate requirements/RTM.yaml covering all 100 INV-70 requirements (C020)."""
import json
import pathlib

import yaml

from .remediation_status import OWNER, S

ROOT = pathlib.Path(__file__).resolve().parents[1]


def build():
    base = json.loads((ROOT / "AUDIT_MATRIX_4.2.0.json").read_text())
    rows = []
    for it in base["items"]:
        cid = it["check_id"]
        if cid in S:
            st, impl, tests, gap = S[cid]
            ev = ["RELEASE_EVIDENCE.json"] if st != "BLOCKED" else []
        else:
            st, impl, tests, gap, ev = it["status"], [it["evidence"]] if it["evidence"] else [], [], it["remaining_gap"], []
        rows.append({"id": cid, "dimension": it["dimension"], "requirement": it["requirement"], "status": st,
                     "implementation": impl, "tests": tests, "evidence": ev, "owner": OWNER,
                     "remaining_gap": gap, "source": "4.3.0 remediation" if cid in S else "carried from 4.2.0 audit"})
    return {"element": "INV-70", "version": "4.3.0", "rows": rows}


if __name__ == "__main__":
    (ROOT / "requirements" / "RTM.yaml").write_text(yaml.safe_dump(build(), sort_keys=False, width=110))
    print("wrote requirements/RTM.yaml")
