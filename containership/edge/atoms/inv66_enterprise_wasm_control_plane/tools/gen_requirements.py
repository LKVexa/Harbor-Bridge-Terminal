"""Generate the normative SHALL specification (MC-006) from CHECKLIST.json + tools/control_map.py.

    python tools/gen_requirements.py [--check]
Every C001-C100 control becomes REQ-INV66-Cxxx; security invariants add REQ-INV66-S1..S6.
Rationale/notes are kept in separate fields so certification cannot be satisfied by prose.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from control_map import CONTROLS  # noqa: E402

VERSION = "1.0.0"
INVARIANTS = [
    ("S1", "INV-66 SHALL NOT forward any manifest to INV-63 unless an admitted decision for it is durably journaled.", ["tests.fault.test_faults.FaultTest.test_journal_failure_admits_nothing_and_degrades", "tests.security.test_threats.ThreatTest.test_T01_attacker_registry_never_forwarded"]),
    ("S2", "INV-66 SHALL fail closed (no admission) when the audit journal cannot durably record the decision.", ["tests.fault.test_faults.FaultTest.test_journal_failure_admits_nothing_and_degrades"]),
    ("S3", "INV-66 SHALL derive the acting principal only from a verified credential and SHALL NOT accept a caller-supplied identity field.", ["tests.security.test_threats.ThreatTest.test_T04_spoofed_identity_and_forged_token"]),
    ("S4", "INV-66 SHALL NOT disclose inventory, audit or explain data outside the scopes for which the principal holds the corresponding read capability.", ["tests.unit.test_additions.AdditionsTest.test_audit_cursor_pagination_and_filters", "tests.contract.test_contracts.SchemaContractTest.test_audit_api_contract"]),
    ("S5", "INV-66 SHALL require the configured number of distinct approvers, excluding the author, before activating a configuration generation.", ["tests.unit.test_units.ConfigTest.test_dual_authorization_and_author_exclusion", "tests.security.test_threats.ThreatTest.test_T15_config_change_needs_two_other_people"]),
    ("S6", "INV-66 SHALL make journal tampering, truncation and full-chain recomputation detectable to any holder of the trusted anchor public keys.", ["tests.unit.test_units.JournalTest.test_recomputed_chain_detected_by_anchor", "tests.unit.test_units.JournalTest.test_truncation_detected_by_anchor"]),
]


def build() -> dict:
    items = json.loads((ROOT / "CHECKLIST.json").read_text())["items"]
    reqs = []
    for it in items:
        cid = it["check_id"].split("-")[-1]
        m = CONTROLS[cid]
        text = it["requirement"].rstrip(".")
        verb = text[0].lower() + text[1:]
        reqs.append({
            "id": f"REQ-INV66-{cid}", "level": "SHALL", "source": it["check_id"], "dimension": it["dimension"],
            "statement": f"INV-66 SHALL {verb}.",
            "acceptance": {"artifacts_exist": m["artifacts"], "tests_pass": m["tests"],
                           "independent_review": "required (release/reviews.jsonl)"},
            "evidence_type": "automated" if m["tests"] else "document",
            "owner_role": "service_owner", "failure_disposition": "release-blocking" if m["status"] != "NA_PROPOSED" else "waiver W-10",
            "engineering_status": m["status"], "note": m.get("gap", "")})
    for sid, text, tests in INVARIANTS:
        reqs.append({"id": f"REQ-INV66-{sid}", "level": "SHALL", "source": "THREAT_MODEL invariants", "dimension": "Security invariant",
                     "statement": text, "acceptance": {"artifacts_exist": ["docs/THREAT_MODEL.md"], "tests_pass": tests,
                                                       "independent_review": "required"},
                     "evidence_type": "automated", "owner_role": "security_owner", "failure_disposition": "release-blocking",
                     "engineering_status": "ENGINEERED", "note": ""})
    return {"schema": "PK_ECP_REQUIREMENTS/1", "document_id": "INV66-REQ", "version": VERSION,
            "normative_language": "RFC 2119 / RFC 8174 (SHALL, SHOULD, MAY in capitals)",
            "change_control": "a change to any statement requires a version bump, an impact note in history, and security-owner review",
            "history": [{"version": "1.0.0", "date": "2026-09-22", "change": "initial generation from CHECKLIST.json (4.3.0)"}],
            "requirements": reqs}


def main() -> int:
    doc = json.dumps(build(), indent=1, ensure_ascii=False) + "\n"
    p = ROOT / "requirements" / "requirements.json"
    if "--check" in sys.argv:
        ok = p.exists() and p.read_text() == doc
        print("requirements up to date" if ok else "requirements drift")
        return 0 if ok else 1
    p.parent.mkdir(exist_ok=True)
    p.write_text(doc)
    print(f"wrote {len(json.loads(doc)['requirements'])} requirements")
    return 0


if __name__ == "__main__":
    sys.exit(main())
