"""CI gate decision (G12-I105, G12-H085 no-skip, G12-I116): a mandatory job counts
only when it PASSed.  SKIP / UNKNOWN / NOT-RUN / missing are NOT-EVIDENCED, never PASS."""
from __future__ import annotations


def decide(jobs: list[dict]) -> dict:
    mandatory = [j for j in jobs if j.get("mandatory")]
    failed = [j["job"] for j in mandatory if j.get("status") == "FAIL"]
    missing = [j["job"] for j in mandatory if j.get("status") not in ("PASS", "FAIL")]
    decision = "FAIL" if failed else "NOT-EVIDENCED" if missing else "PASS"
    return {"decision": decision, "failed": failed, "not_evidenced": missing,
            "optional_skipped": [j["job"] for j in jobs if not j.get("mandatory") and j.get("status") != "PASS"]}
