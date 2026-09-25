"""Production exit gate and traceability (components 11, 78, 86-88).

``evaluate()`` aggregates, for the *exact* source tree being promoted:

* the component register ``governance/COMPONENTS.json`` (all 96 audit gaps),
* the CI evidence ``evidence/CI_EVIDENCE.json`` (must be bound to the current
  source digest; stale evidence is refused),
* role ownership ``governance/owners.json``,
* approvals ``governance/approvals/*.json`` – only counted when an external
  verifier (bound by the owner; none ships with this package) confirms them,
* the waiver register ``governance/WAIVERS.json`` (expired waivers block),
* performance thresholds ``perf/THRESHOLDS.json`` (must be APPROVED and met).

GO requires every component COMPLETE, every role bound, every approval verified,
all CI lanes PASS, and approved perf thresholds met.  Anything else is NO_GO with
named blockers.  A register that *claims* evidence the CI run does not contain is
an error, not a blocker: the gate refuses to evaluate a dishonest register.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any, Callable, Mapping

PKG = Path(__file__).resolve().parent
STATUSES = ("COMPLETE", "IMPLEMENTED_LOCAL", "PARTIAL", "BLOCKED", "MISSING")
REQUIRED_ROLES = ("service_owner", "technical_owner", "security_owner", "operations_owner", "qa_owner", "release_approver")
REQUIRED_LANES = ("compile", "lint", "schemas", "unit", "optimized", "pk_core", "perf", "reproducible", "tree_stable")
WAIVABLE = ("IMPLEMENTED_LOCAL", "PARTIAL")      # a waiver never turns BLOCKED/MISSING work into GO
EXCLUDE_DIRS = {"__pycache__", "evidence", "approvals", ".git", "build", "dist"}


class RegisterError(ValueError):
    pass


def source_digest(root: Path = PKG) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if p.is_dir() or any(part in EXCLUDE_DIRS or part.endswith(".egg-info") for part in rel.parts) \
                or p.suffix in (".pyc", ".pyo"):
            continue
        h.update(rel.as_posix().encode() + b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def _load(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def check_register(register: Mapping[str, Any], evidence: Mapping[str, Any] | None, root: Path) -> list[str]:
    """Return register-honesty errors: claims that the tree or the CI run does not support."""
    errors = []
    comps = register.get("components", [])
    if len(comps) != register.get("expected_count", 96):
        errors.append(f"register lists {len(comps)} components, expected {register.get('expected_count', 96)}")
    ids = [c["id"] for c in comps]
    if len(set(ids)) != len(ids):
        errors.append("duplicate component ids")
    passed = {t for t, r in (evidence or {}).get("tests", {}).items() if r == "pass"}
    for c in comps:
        if c["status"] not in STATUSES:
            errors.append(f"{c['id']}: unknown status {c['status']}")
        for a in c.get("artifacts", []):
            if not (root / a).exists():
                errors.append(f"{c['id']}: artifact {a} does not exist")
        if c["status"] in ("COMPLETE", "IMPLEMENTED_LOCAL", "PARTIAL") and evidence is not None:
            for t in c.get("tests", []):
                if t not in passed:
                    errors.append(f"{c['id']}: test {t} is not a passing test in the CI evidence")
        if c["status"] in ("COMPLETE", "IMPLEMENTED_LOCAL") and not (c.get("tests") or c.get("artifacts")):
            errors.append(f"{c['id']}: {c['status']} without any evidence")
        if c["status"] in ("PARTIAL", "BLOCKED", "MISSING") and not c.get("blockers"):
            errors.append(f"{c['id']}: {c['status']} must name its blocker(s)")
    return errors


def evaluate(*, root: Path = PKG, evidence_path: str | Path | None = None,
             approval_verifier: Callable[[Mapping[str, Any]], bool] | None = None,
             today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    register = _load(root / "governance" / "COMPONENTS.json", {"components": []})
    ev_path = Path(evidence_path) if evidence_path else root / "evidence" / "CI_EVIDENCE.json"
    evidence = _load(ev_path)
    owners = _load(root / "governance" / "owners.json", {})
    waivers = _load(root / "governance" / "WAIVERS.json", {"waivers": []})
    thresholds = _load(root / "perf" / "THRESHOLDS.json", {})
    blockers: list[str] = []

    errors = check_register(register, evidence, root)
    if errors:
        return {"schema": "inv53.exitgate/1", "verdict": "ERROR", "register_errors": errors}

    digest = source_digest(root)
    if evidence is None:
        blockers.append("no CI evidence")
    else:
        if evidence.get("source_digest") != digest:
            blockers.append("CI evidence is stale: it was produced for a different source tree")
        lanes = evidence.get("lanes") or {}
        for lane in REQUIRED_LANES:
            if lane not in lanes:
                blockers.append(f"CI lane {lane}: absent from the evidence")
        for lane, res in lanes.items():
            if res.get("status") != "PASS":
                blockers.append(f"CI lane {lane}: {res.get('status')} ({res.get('reason', '')})")
        if not any(r == "pass" for r in (evidence.get("tests") or {}).values()):
            blockers.append("CI evidence records no passing tests")

    for role in REQUIRED_ROLES:
        if not (owners.get("roles", {}).get(role) or {}).get("name"):
            blockers.append(f"role {role} is UNASSIGNED")

    approvals_dir = root / "governance" / "approvals"
    approved_roles = set()
    for p in sorted(approvals_dir.glob("*.json")) if approvals_dir.exists() else []:
        rec = _load(p)
        if approval_verifier is None:
            blockers.append(f"approval {p.name} cannot be verified: no approval verifier is bound")
        elif approval_verifier(rec) and rec.get("decision") == "APPROVE" and rec.get("source_digest") == digest:
            approved_roles.add(rec.get("role"))
    for role in REQUIRED_ROLES:
        if role not in approved_roles:
            blockers.append(f"no verified release approval from {role}")

    counts = {s: 0 for s in STATUSES}
    for c in register["components"]:
        counts[c["status"]] += 1
        if c["status"] != "COMPLETE":
            waived = [w for w in waivers.get("waivers", []) if w.get("component") == c["id"]]
            live = [w for w in waived if c["status"] in WAIVABLE and w.get("expires")
                    and date.fromisoformat(w["expires"]) >= today and w.get("approved_by")
                    and approval_verifier is not None and approval_verifier(w)]
            if not live:
                blockers.append(f"{c['id']} {c['title']}: {c['status']}")
    for w in waivers.get("waivers", []):
        if w.get("expires") and date.fromisoformat(w["expires"]) < today:
            blockers.append(f"waiver {w.get('id')} expired {w['expires']}")

    if thresholds.get("status") != "APPROVED":
        blockers.append(f"performance thresholds are {thresholds.get('status', 'ABSENT')}, not APPROVED")
    elif evidence is not None and (evidence.get("perf_gate") or {}).get("verdict") != "PASS":
        blockers.append("performance regression gate did not PASS")

    return {"schema": "inv53.exitgate/1", "verdict": "NO_GO" if blockers else "GO", "source_digest": digest,
            "component_counts": counts, "blocker_count": len(blockers), "blockers": blockers,
            "evaluated_on": today.isoformat()}


def traceability_markdown(root: Path = PKG) -> str:
    reg = _load(root / "governance" / "COMPONENTS.json", {"components": []})
    out = ["# INV-53 requirements traceability matrix", "",
           "Generated by `python -m inv53_message_reliability traceability` from `governance/COMPONENTS.json`.",
           "Requirement → design artifact → implementation → verification → status. Do not edit by hand.", "",
           "| # | Component | Checklist | Severity | Status | Design / artifacts | Implementation | Verification | Blockers |",
           "|---:|---|---|---|---|---|---|---|---|"]
    for c in reg["components"]:
        out.append("| {n} | {t} | {cl} | {sev} | {st} | {a} | {i} | {v} | {b} |".format(
            n=c["id"], t=c["title"], cl=c.get("checklist", ""), sev=c.get("severity", ""), st=c["status"],
            a="<br>".join(f"`{x}`" for x in c.get("artifacts", []) if not x.endswith(".py")) or "—",
            i="<br>".join(f"`{x}`" for x in c.get("artifacts", []) if x.endswith(".py")) or "—",
            v=f"{len(c.get('tests', []))} test(s)" if c.get("tests") else "—",
            b="; ".join(c.get("blockers", [])) or "—"))
    return "\n".join(out) + "\n"
