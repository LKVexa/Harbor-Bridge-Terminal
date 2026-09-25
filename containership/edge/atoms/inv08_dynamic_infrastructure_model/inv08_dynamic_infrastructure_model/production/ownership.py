"""Component 08 - ownership/escalation metadata loader (PK_DYN_OWNERSHIP/1).

Validates the RACI (exactly one Accountable per activity), escalation chains that
reference defined roles, and reports every UNASSIGNED person/contact as a
production blocker.  ``query`` / CLI make the data queryable from tooling::

  python -m inv08_dynamic_infrastructure_model.production.ownership [role]

No people are invented: every identity in ownership.json is UNASSIGNED, so
``blockers()`` is non-empty and ``ready`` is False until an owner fills it in.
"""
from __future__ import annotations

import json
from pathlib import Path

PATH = Path(__file__).resolve().parent / "ownership.json"
ACTIVITIES = ("design", "release", "operate", "security")
UNASSIGNED = "UNASSIGNED"


def load(path: Path = PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(doc: dict) -> list[str]:
    p = []
    if doc.get("schema") != "PK_DYN_OWNERSHIP/1":
        p.append("schema mismatch")
    roles = {r["role"]: r for r in doc.get("roles", [])}
    for act in ACTIVITIES:
        acc = [r for r, d in roles.items() if d.get("raci", {}).get(act) == "A"]
        if len(acc) != 1:
            p.append(f"activity {act} needs exactly one Accountable role, has {acc}")
    for r, d in roles.items():
        for act, v in d.get("raci", {}).items():
            if v not in {"R", "A", "C", "I"}:
                p.append(f"{r}.{act}: bad RACI letter {v!r}")
    for chain in ("escalation_chain", "security_chain"):
        for r in doc.get(chain, []):
            if r not in roles:
                p.append(f"{chain} references undefined role {r}")
        if not doc.get(chain):
            p.append(f"{chain} empty")
    return p


def _unassigned(v) -> bool:
    return not v or str(v).startswith(UNASSIGNED)


def blockers(doc: dict) -> list[str]:
    out = []
    for r in doc.get("roles", []):
        for k in ("primary", "secondary", "contact", "rotation"):
            if k in r and _unassigned(r[k]):
                out.append(f"{r['role']}.{k} UNASSIGNED")
    for v in doc.get("vendors", []):
        if _unassigned(v.get("contact")):
            out.append(f"vendor {v.get('provider', '?')[:40]} contact UNASSIGNED")
    if _unassigned(doc.get("repository", {}).get("team")):
        out.append("repository.team UNASSIGNED")
    return out


def query(doc: dict, role: str) -> dict:
    for r in doc.get("roles", []):
        if r["role"] == role:
            return r
    raise KeyError(role)


def report(doc: dict) -> dict:
    b = blockers(doc)
    errs = validate(doc)
    return {"valid": not errs, "errors": errs, "blockers": b, "ready": not errs and not b}


def main(argv: list[str] | None = None) -> int:
    import sys
    argv = sys.argv[1:] if argv is None else argv
    doc = load()
    if argv:
        print(json.dumps(query(doc, argv[0]), sort_keys=True))
        return 0
    r = report(doc)
    print(json.dumps(r, indent=1, sort_keys=True))
    return 0 if r["ready"] else 3


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
