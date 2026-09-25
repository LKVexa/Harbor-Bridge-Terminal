"""MC-036/037/039/044 governance checks used by CI and the exit gate."""
from __future__ import annotations

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh) if rel.endswith(".json") else fh.read()


def ownership_blockers() -> list[str]:
    o = _load("governance/OWNERS.json")
    out = []
    if o.get("service_owner") in (None, "", "UNASSIGNED"):
        out.append("no accountable service owner")
    if o.get("owning_team") in (None, "", "UNASSIGNED"):
        out.append("no owning team")
    if not o["oncall"].get("primary_rotation") or not o["oncall"].get("secondary_rotation"):
        out.append("no on-call rotations")
    for area, r in o["raci"].items():
        if r.get("A") in (None, "", "UNASSIGNED"):
            out.append(f"RACI {area}: no accountable")
    if "UNASSIGNED" in _load("governance/CODEOWNERS").split("\n", 1)[1]:
        out.append("CODEOWNERS uses placeholder handles")
    if not o.get("last_escalation_drill"):
        out.append("escalation path never drilled")
    for rb in ("runbooks/incident-response.md",):
        if not os.path.exists(os.path.join(ROOT, rb)):
            out.append(f"missing {rb}")
    return out


ADR_SECTIONS = ("## Context and problem", "## Decision", "## Alternatives considered", "## Invariants and assumptions",
                "## Trade-offs", "## Diagrams", "## Links", "## Approvals", "## Review triggers")


def adr_status(path="docs/adr/ADR-0001-gap03-control-plane.md") -> dict:
    text = _load(path)
    missing = [s for s in ADR_SECTIONS if s not in text]
    m = re.search(r"\*\*Status:\*\* (\w+)", text)
    approvals = re.findall(r"^\| (Accountable engineering|Operations / SRE|Security architecture) \| (\S+) \|", text, re.M)
    return {"missing_sections": missing, "status": m.group(1) if m else None,
            "approved": bool(m and m.group(1) == "Accepted") and all(n != "UNASSIGNED" for _, n in approvals),
            "has_supersession_rule": "Supersession rule" in text, "has_mermaid": "```mermaid" in text}


def provenance_status() -> dict:
    return _load("governance/MC-039_MASTER_md_provenance.json")


def support_policy() -> dict:
    return _load("policy/support_policy.json")


def validate_provenance(rec: dict) -> list[str]:
    """A provenance record may claim VERIFIED only with location, authority, digest and signature."""
    p = []
    if rec.get("status") not in ("BLOCKED", "VERIFIED"):
        p.append("unknown status")
    if rec.get("status") == "VERIFIED":
        for k in ("source", "authority", "sha256", "signature", "acquired_at", "owner"):
            if not rec.get(k):
                p.append(f"VERIFIED without {k}")
    if rec.get("status") == "BLOCKED" and not rec.get("required_to_unblock"):
        p.append("BLOCKED without unblock requirements")
    return p


def validate_policy(policy: dict, matrix: dict) -> list[str]:
    p = []
    for k in ("minor_support_months", "major_support_months", "vuln_sla_hours", "runtime_eol", "eol_notice_days", "backport"):
        if k not in policy:
            p.append(f"missing {k}")
    sla = policy.get("vuln_sla_hours", {})
    if sla and not (sla.get("critical") or 0) <= (sla.get("high") or 10**9) <= (sla.get("medium") or 10**9):
        p.append("SLA ordering violated")
    for py, eol in policy.get("runtime_eol", {}).items():
        if matrix["python"]["eol"].get(py) != eol:
            p.append(f"EOL mismatch for {py}")
    return p


def validate_adr_text(text: str) -> dict:
    missing = [s for s in ADR_SECTIONS if s not in text]
    return {"missing_sections": missing, "complete": not missing}
