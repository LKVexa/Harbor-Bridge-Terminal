"""Component 64 - recurring governance review automation (PK_DYN_GOVERNANCE/1).

Review kinds and cadence (days): access 90, policy_config 180, dependency_sbom 30,
architecture_adr 365.  ``status`` computes due/overdue per kind from evidence
records; overdue escalates by level (0 on time, 1 overdue, 2 > 2x grace, 3 >
cadence) mapping to roles in ownership.json.  ``record_review`` validates and
appends an evidence record (reviewer, subject digest, findings) to the audit log.
The dependency/SBOM review binds to the current SBOM digest (component 04) so a
changed SBOM invalidates the last review.  No review has been performed by a
human here: reviewers are UNASSIGNED and every kind is currently overdue.
"""
from __future__ import annotations

from dataclasses import dataclass

DAY = 86400.0
CADENCE_DAYS = {"access": 90, "policy_config": 180, "dependency_sbom": 30, "architecture_adr": 365}
GRACE_DAYS = 7
ESCALATE_TO = {1: "service_owner", 2: "security_owner", 3: "incident_commander"}


@dataclass
class ReviewRecord:
    kind: str
    ts: float
    reviewer: str
    subject_digest: str
    findings: list

    def validate(self) -> list[str]:
        p = []
        if self.kind not in CADENCE_DAYS:
            p.append(f"unknown kind {self.kind}")
        if not self.reviewer or self.reviewer.startswith("UNASSIGNED"):
            p.append("reviewer identity required")
        if not str(self.subject_digest).startswith("sha256:"):
            p.append("subject_digest must be sha256:...")
        if not isinstance(self.findings, list):
            p.append("findings must be a list")
        return p


def record_review(rec: ReviewRecord, audit) -> dict:
    p = rec.validate()
    if p:
        raise ValueError("; ".join(p))
    return audit.append(rec.reviewer, f"review.{rec.kind}", rec.subject_digest, "SUCCESS",
                        {"findings": rec.findings}, ts=rec.ts)


def status(records: list[ReviewRecord], now: float, *, current_subjects: dict | None = None) -> list[dict]:
    out = []
    current_subjects = current_subjects or {}
    for kind, cadence in CADENCE_DAYS.items():
        rs = [r for r in records if r.kind == kind and not r.validate()]
        subj = current_subjects.get(kind)
        if subj:
            rs = [r for r in rs if r.subject_digest == subj]
        last = max((r.ts for r in rs), default=None)
        due = (last + cadence * DAY) if last is not None else None
        if due is None:
            late_days = float("inf")
        else:
            late_days = (now - due) / DAY
        if late_days <= 0:
            level = 0
        elif late_days > cadence:
            level = 3
        elif late_days > 2 * GRACE_DAYS:
            level = 2
        else:
            level = 1
        out.append({"kind": kind, "last": last, "due": due, "overdue": level > 0, "level": level,
                    "escalate_to": ESCALATE_TO.get(level), "never_reviewed": last is None})
    return out
