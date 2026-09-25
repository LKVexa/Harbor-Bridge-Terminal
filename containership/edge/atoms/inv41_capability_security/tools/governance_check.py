"""Governance checks: owners, CODEOWNERS two-reviewer rule, stale owners,
waiver expiry and stdlib-only imports (Sections 1, 7, 23, 24).

``check_*`` functions return (errors, warnings).  Placeholder/unconfirmed
owners are *errors in production mode* and warnings in development mode.
"""
from __future__ import annotations

import ast
import datetime as dt
import json
import pathlib
import re
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
STDLIB = set(sys.stdlib_module_names) | {"__future__"}
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I)
REQUIRED_ROLES = ("accountable_owner", "backup_owner", "technical_owner", "security_approver", "release_approver",
                  "incident_commander", "policy_approver")


def check_owners(owners: dict, codeowners: str, *, today: dt.date, production: bool):
    errs, warns = [], []
    for k in ("component_id", "roles", "escalation", "review_cadence_days", "last_reviewed", "security_critical_paths",
              "human_only_roles", "decision_authority", "transfer_procedure"):
        if k not in owners:
            errs.append(f"OWNERS.json missing {k}")
    roles = owners.get("roles", {})
    for role in REQUIRED_ROLES:
        r = roles.get(role)
        if r is None:
            errs.append(f"role {role} missing")
            continue
        placeholder = r.get("name") in (None, "", "UNASSIGNED")
        bad_contact = not (isinstance(r.get("contact"), str) and EMAIL.match(r["contact"]))
        if role in owners.get("human_only_roles", []) and r.get("kind") != "human":
            errs.append(f"role {role} must be human")
        if placeholder or bad_contact or not r.get("confirmed"):
            (errs if production else warns).append(f"role {role} unassigned/unconfirmed/invalid contact")
    if roles.get("accountable_owner", {}).get("name") == roles.get("backup_owner", {}).get("name"):
        errs.append("backup owner must differ from accountable owner")
    for tier in owners.get("escalation", []):
        for k in ("severity", "first", "then", "ack_minutes", "decision_minutes"):
            if k not in tier:
                errs.append(f"escalation tier missing {k}")
    try:
        last = dt.date.fromisoformat(owners["last_reviewed"])
        if (today - last).days > owners["review_cadence_days"]:
            (errs if production else warns).append("owner review is stale")
    except Exception:
        errs.append("last_reviewed invalid")
    rules = {}
    for line in codeowners.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            path, *who = line.split()
            rules[path.lstrip("/")] = who
    for crit in owners.get("security_critical_paths", []):
        who = rules.get(crit)
        if who is None or len(set(who)) < 2:
            errs.append(f"CODEOWNERS: {crit} lacks two reviewers")
        elif any("UNASSIGNED" in w for w in who):
            (errs if production else warns).append(f"CODEOWNERS: {crit} has a placeholder reviewer")
    return errs, warns


def check_waivers(exc: dict, *, today: dt.date, production: bool):
    errs, warns = [], []
    for e in exc.get("entries", []):
        for k in ("id", "requirement_id", "risk", "rationale", "compensating_control", "owner", "created", "expires"):
            if not e.get(k):
                errs.append(f"{e.get('id')}: missing {k}")
        try:
            created = dt.date.fromisoformat(e["created"])
            expires = dt.date.fromisoformat(e["expires"])
        except Exception:
            errs.append(f"{e.get('id')}: bad dates")
            continue
        if e.get("risk") in ("high", "critical") and (expires - created).days > 90:
            errs.append(f"{e['id']}: high-risk waiver exceeds 90 days")
        if expires < today:
            errs.append(f"{e['id']}: EXPIRED on {expires}")
        elif (expires - today).days <= 14:
            warns.append(f"{e['id']}: expires in {(expires - today).days} days")
        if e.get("approval") is None:
            (errs if production else warns).append(f"{e['id']}: not approved")
    return errs, warns


def check_imports():
    errs = []
    local = {p.stem for p in (PKG / "tools").glob("*.py")} | {p.stem for p in (PKG / "tests").glob("*.py")}
    for f in sorted(PKG.rglob("*.py")):
        if "dist" in f.parts:
            continue
        for node in ast.walk(ast.parse(f.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for n in names:
                top = n.split(".")[0]
                if top in STDLIB or top == "inv41_capability_security" or top in local:
                    continue
                if top == "pk_core" and f.name in ("component.py", "contract.py", "test_component.py", "estate_gate.py"):
                    continue  # optional estate integration, gated by tools/estate_gate.py
                errs.append(f"{f.relative_to(PKG)}: non-stdlib import {n}")
    return errs


def run(production: bool = False, today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    owners = json.loads((PKG / "OWNERS.json").read_text())
    oe, ow = check_owners(owners, (PKG / "CODEOWNERS").read_text(), today=today, production=production)
    we, ww = check_waivers(json.loads((PKG / "EXCEPTIONS.json").read_text()), today=today, production=production)
    ie = check_imports()
    errs = oe + we + ie
    return {"schema": "INV41_GOVERNANCE/1", "mode": "production" if production else "development",
            "errors": errs, "warnings": ow + ww, "ok": not errs,
            "ownership": {"component_id": owners["component_id"], "accountable_owner": owners["roles"]["accountable_owner"]["name"],
                          "status": owners["status"]}}


def main() -> int:
    prod = "--production" in sys.argv
    r = run(production=prod)
    (PKG / "evidence").mkdir(exist_ok=True)
    (PKG / "evidence" / f"governance_{r['mode']}.json").write_text(json.dumps(r, indent=1))
    print(json.dumps({"mode": r["mode"], "errors": len(r["errors"]), "warnings": len(r["warnings"])}))
    for e in r["errors"]:
        print("GOV-ERROR", e)
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
