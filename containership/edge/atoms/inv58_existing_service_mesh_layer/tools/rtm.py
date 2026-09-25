"""Generate and verify the requirements traceability matrix (MC-004, INV-58-C020).

    python -B tools/rtm.py          # writes governance/RTM.json
    python -B tools/rtm.py --check  # exit 1 on dangling refs or drift

Sources: CHECKLIST.json (C001..C100), MISSING_COMPONENTS.json (4.2.0 audit
status + MC id), governance/rtm_map.json (4.3.0 closure), governance/OWNERSHIP.json.
Every implementation symbol, file, test id and doc path is resolved; a
dangling reference is an error, never a warning.
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text().strip()
RULES = {
    "VERIFIED_LOCAL": lambda r: bool(r["tests"]) and bool(r["implementation"]),
    "DEFINED": lambda r: bool(r["docs"] or r["implementation"]),
    "PARTIAL": lambda r: bool(r["blocker"]) and bool(r["implementation"] or r["docs"]),
    "BLOCKED": lambda r: bool(r["blocker"]),
}


def _sha(p: pathlib.Path) -> str:
    if p.is_dir():
        h = hashlib.sha256()
        for f in sorted(x for x in p.rglob("*") if x.is_file() and "__pycache__" not in x.parts):
            h.update(f.relative_to(ROOT).as_posix().encode() + b"\0" + f.read_bytes())
        return "sha256:" + h.hexdigest()
    return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()


def _symbols(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text())
    out = set()
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            out.add(n.name)
            if isinstance(n, ast.ClassDef):
                for m in n.body:
                    if isinstance(m, (ast.FunctionDef, ast.AnnAssign)):
                        name = m.name if isinstance(m, ast.FunctionDef) else getattr(m.target, "id", None)
                        if name:
                            out.add(f"{n.name}.{name}")
        elif isinstance(n, (ast.Assign, ast.AnnAssign)):
            for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                if isinstance(t, ast.Name):
                    out.add(t.id)
    return out


def _tests() -> set[str]:
    names = set()
    for p in (ROOT / "tests").glob("test_*.py"):
        for cls in [n for n in ast.parse(p.read_text()).body if isinstance(n, ast.ClassDef)]:
            for fn in cls.body:
                if isinstance(fn, ast.FunctionDef) and fn.name.startswith("test"):
                    names.add(f"{p.stem}.{cls.name}.{fn.name}")
    return names


def resolve_ref(ref: str, problems: list, where: str) -> dict:
    base = re.split(r"\s[\(\[]|\[", ref)[0].strip()
    file_part, _, sym = base.partition("::")
    path_part, _, anchor = file_part.partition("#")
    p = ROOT / path_part
    if not p.exists():
        problems.append(f"{where}: missing path {path_part}")
        return {"ref": ref, "resolved": False}
    if anchor:
        slugs = {re.sub(r"[^a-z0-9 -]", "", h.strip("# ").lower()).replace(" ", "-")
                 for h in p.read_text().splitlines() if h.startswith("#")}
        if anchor not in slugs:
            problems.append(f"{where}: anchor #{anchor} not found in {path_part}")
            return {"ref": ref, "resolved": False}
    if sym:
        sym = sym.split(" ")[0]
        if p.suffix != ".py" or sym not in _symbols(p):
            problems.append(f"{where}: symbol {sym} not found in {file_part}")
            return {"ref": ref, "resolved": False}
    return {"ref": ref, "resolved": True, "digest": _sha(p)}


def build():
    checklist = json.loads((ROOT / "CHECKLIST.json").read_text())["items"]
    audit = json.loads((ROOT / "MISSING_COMPONENTS.json").read_text())
    prior = {}
    for c in audit["components"]:
        for r in c["requirements"]:
            prior[r["check_id"]] = (r["status"], c["id"])
    rmap = json.loads((ROOT / "governance" / "rtm_map.json").read_text())["rows"]
    owners = json.loads((ROOT / "governance" / "OWNERSHIP.json").read_text())
    tests = _tests()
    problems, rows = [], []
    for item in checklist:
        cid = item["check_id"]
        m = rmap.get(cid)
        if m is None:
            problems.append(f"{cid}: no RTM mapping (dangling requirement)")
            continue
        if m["status"] not in RULES or not RULES[m["status"]](m):
            problems.append(f"{cid}: status {m['status']} not supported by its evidence fields")
        for t in m["tests"]:
            if t not in tests:
                problems.append(f"{cid}: test {t} does not exist")
        impl = [resolve_ref(x, problems, cid) for x in m["implementation"]]
        docs = [resolve_ref(x, problems, cid) for x in m["docs"]]
        st, mc = prior.get(cid, ("implemented", None))
        rows.append({
            "check_id": cid, "dimension": item["dimension"], "requirement": item["requirement"],
            "audit_4_2_0": st, "work_package": mc, "status": m["status"], "implementation": impl,
            "tests": m["tests"], "docs": docs, "blocker": m["blocker"],
            "owner": owners["accountable_owner"]["name"], "release": VERSION,
        })
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"schema": "PK_MESH_RTM/1", "element": "INV-58", "version": VERSION, "row_count": len(rows),
            "counts": counts, "rows": rows}, problems


def main(argv):
    rtm, problems = build()
    out = ROOT / "governance" / "RTM.json"
    text = json.dumps(rtm, indent=1, sort_keys=True) + "\n"
    if problems:
        print("\n".join(problems))
        return 1
    if "--check" in argv:
        if not out.exists() or out.read_text() != text:
            print("RTM.json is stale; regenerate with tools/rtm.py")
            return 1
        print(f"RTM verified: {rtm['row_count']} rows {rtm['counts']}")
        return 0
    out.write_text(text)
    print(f"RTM written: {rtm['row_count']} rows {rtm['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
