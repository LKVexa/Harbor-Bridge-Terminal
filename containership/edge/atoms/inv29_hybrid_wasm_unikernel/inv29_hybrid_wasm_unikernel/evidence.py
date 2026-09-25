"""Evidence ledger, waiver register and machine-derived production gate
(MC040, MC041, MC100, MC101, MC103).

The gate verdict is *computed* from control outcomes - it cannot be set by
prose.  Inputs:

* ``MISSING_COMPONENTS_STATUS.json`` - one record per INV29-MCxxx with status
* ``governance/WAIVERS.json``        - time-boxed waivers (never for P0)
* the test-run summary and the release manifest (source digest binding)

Status vocabulary:

* ``CLOSED``            - implemented and evidenced in the certification environment
* ``IMPLEMENTED_LOCAL`` - implemented and evidenced in this archive; the item's
                          Definition of Done still needs an external environment
* ``OWNER_ACTION``      - needs a decision only the owner can make (licence, named on-call)
* ``BLOCKED_EXTERNAL``  - needs an external dependency, lab or estate not present
* ``NOT_APPLICABLE``    - owner-approved non-applicability with evidence

Only CLOSED and NOT_APPLICABLE count as closed for Production-GO.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import pathlib
import threading
from typing import Iterable, Optional

from .records import canonical

GENESIS = "0" * 64
CLOSED_STATES = {"CLOSED", "NOT_APPLICABLE"}
ALL_STATES = {"CLOSED", "IMPLEMENTED_LOCAL", "OWNER_ACTION", "BLOCKED_EXTERNAL", "NOT_APPLICABLE"}


class EvidenceInvalid(ValueError):
    code = "INV29-E-EVIDENCE"


class Ledger:
    """Append-only, hash-chained JSON-lines evidence ledger."""

    def __init__(self, path: pathlib.Path):
        self.path = pathlib.Path(path)
        self._lock = threading.Lock()

    def head(self) -> str:
        if not self.path.exists():
            return GENESIS
        last = GENESIS
        for line in self.path.read_text("utf-8").splitlines():
            if line.strip():
                last = json.loads(line)["hash"]
        return last

    def append(self, kind: str, body: dict) -> dict:
        with self._lock:
            prev = self.head()
            entry = {"seq": sum(1 for _ in self._lines()), "kind": kind, "prev": prev, "body": body}
            entry["hash"] = hashlib.sha256(canonical(entry)).hexdigest()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, sort_keys=True) + "\n")
            return entry

    def _lines(self):
        if self.path.exists():
            for line in self.path.read_text("utf-8").splitlines():
                if line.strip():
                    yield line

    def verify(self, *, expected_head: Optional[str] = None, min_entries: int = 0) -> dict:
        """Verify the chain.  Truncation is only detectable against an external anchor, so
        callers pass the head/length recorded in the gate artifact or release manifest."""
        prev, n = GENESIS, 0
        for i, line in enumerate(self._lines()):
            e = json.loads(line)
            h = e.pop("hash")
            if e["prev"] != prev or e["seq"] != i:
                raise EvidenceInvalid(f"ledger chain broken at seq {i}")
            if hashlib.sha256(canonical(e)).hexdigest() != h:
                raise EvidenceInvalid(f"ledger entry {i} was modified")
            prev, n = h, i + 1
        if n < min_entries:
            raise EvidenceInvalid(f"ledger has {n} entries, anchor expects at least {min_entries} (truncated?)")
        if expected_head is not None and prev != expected_head:
            raise EvidenceInvalid("ledger head does not match the recorded anchor (truncated or rewritten)")
        return {"intact": True, "entries": n, "head": prev}


# ------------------------------------------------------------------ waivers
WAIVER_FIELDS = {"id", "component", "requirements", "rationale", "risk", "compensating_controls",
                 "owner", "approvers", "created", "expires", "remediation", "status",
                 "applies_to_version", "applies_to_environment"}


def validate_waivers(waivers: list, *, today: _dt.date, version: str, environment: str,
                     priorities: dict) -> dict:
    """Return {component: waiver} for waivers that are valid *now* for this release."""
    valid = {}
    for w in waivers:
        missing = WAIVER_FIELDS - set(w)
        if missing:
            raise EvidenceInvalid(f"waiver {w.get('id')!r} missing fields {sorted(missing)}")
        if priorities.get(w["component"]) == "P0":
            raise EvidenceInvalid(f"waiver {w['id']}: P0 components cannot be waived")
        if not w["approvers"]:
            raise EvidenceInvalid(f"waiver {w['id']}: no approvers")
        if w["status"] != "approved":
            continue
        if _dt.date.fromisoformat(w["expires"]) < today:
            continue
        if w["applies_to_version"] != version or w["applies_to_environment"] != environment:
            continue
        valid[w["component"]] = w
    return valid


# ------------------------------------------------------------------ gate
def derive_gate(status: dict, *, tests: dict, manifest: Optional[dict], source_digest: str,
                waivers: Iterable[dict] = (), today: Optional[_dt.date] = None,
                version: str, environment: str = "production") -> dict:
    """Compute GO / CONDITIONAL_GO / NO_GO from control outcomes.  Pure function."""
    today = today or _dt.date.today()
    comps = status.get("components")
    if not isinstance(comps, list) or not comps:
        raise EvidenceInvalid("status file has no components")
    priorities = {c["id"]: c["priority"] for c in comps}
    bad = [c["id"] for c in comps if c.get("status") not in ALL_STATES]
    if bad:
        raise EvidenceInvalid(f"unknown status on {bad}")
    valid_waivers = validate_waivers(list(waivers), today=today, version=version,
                                     environment=environment, priorities=priorities)
    blockers, conditions = [], []
    for c in comps:
        if c["status"] in CLOSED_STATES:
            continue
        if c["priority"] == "P2" and c["id"] in valid_waivers:
            conditions.append({"id": c["id"], "waiver": valid_waivers[c["id"]]["id"]})
        elif c["priority"] == "P1" and c["id"] in valid_waivers:
            conditions.append({"id": c["id"], "waiver": valid_waivers[c["id"]]["id"]})
        else:
            blockers.append({"id": c["id"], "priority": c["priority"], "status": c["status"],
                             "reason": c.get("blocker", "")[:300]})
    if tests.get("failed", 1) or tests.get("errors", 1) or not tests.get("passed"):
        blockers.append({"id": "TESTS", "priority": "P0", "status": "FAILED", "reason": json.dumps(tests)})
    if tests.get("certification_critical_skips", 0):
        blockers.append({"id": "TESTS", "priority": "P0", "status": "SKIPPED",
                         "reason": f"{tests['certification_critical_skips']} certification-critical tests skipped"})
    if manifest is None:
        blockers.append({"id": "MANIFEST", "priority": "P0", "status": "ABSENT", "reason": "no release manifest"})
    elif manifest.get("source_digest") != source_digest:
        blockers.append({"id": "MANIFEST", "priority": "P0", "status": "STALE",
                         "reason": "release manifest was produced for a different source tree"})
    counts = {}
    for c in comps:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    verdict = "NO_GO" if blockers else ("CONDITIONAL_GO" if conditions else "GO")
    return {
        "schema": "PK_GATE_RESULT/1",
        "element": "INV-29",
        "version": version,
        "environment": environment,
        "source_digest": source_digest,
        "evaluated_on": today.isoformat(),
        "verdict": verdict,
        "status_counts": dict(sorted(counts.items())),
        "p0_open": sum(1 for b in blockers if b["priority"] == "P0"),
        "blockers": blockers,
        "conditions": conditions,
        "tests": tests,
        "derivation": "machine-derived by evidence.derive_gate; prose approval cannot override",
    }


def tree_digest(root: pathlib.Path, *, exclude: Iterable[str] = ()) -> str:
    """Deterministic digest of the source tree (paths + contents)."""
    root = pathlib.Path(root)
    ex = tuple(exclude)
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if not p.is_file() or "__pycache__" in rel or rel.startswith(ex):
            continue
        h.update(rel.encode() + b"\0" + hashlib.sha256(p.read_bytes()).digest())
    return "sha256:" + h.hexdigest()
