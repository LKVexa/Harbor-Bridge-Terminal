"""Mutation testing of the safety/refusal branches (MC-054), stdlib only.

    python -B -m inv28_unikernel_implementations.tools.mutation [--max N] [--threshold 80]

Operators (one per mutant): comparison flips (in<->not in, ==<->!=, <<->=, >-> >=, <-> <=, is<->is not),
boolean flips (and<->or), `not x` -> `x`, and `raise` -> `pass` inside the targeted functions only.
Each mutant is written into a scratch copy of the package and the focused suite is run in a subprocess;
a mutant is *killed* when the suite fails.  Survivors are listed with file:line so they can be triaged
(an equivalent mutant is recorded, never silently dropped).  evidence/MUTATION.json.
"""
from __future__ import annotations

import argparse
import ast
import os
import shutil
import subprocess
import sys
import tempfile
import time

from ._common import EVIDENCE, ROOT, write_json

TARGETS = {
    "selection.py": ("_codes", "_evaluate", "_check_deadline", "select"),
    "policy.py": ("__post_init__", "approver_ok", "active", "covers", "rule"),
    "registry.py": ("_cas", "check", "register", "update", "remove", "emergency_disable", "verify_snapshot", "load"),
    "binding.py": ("verify",),
    "model.py": ("stale", "eol_passed", "token", "token_set", "parse_utc"),
    "certification.py": ("ingest", "lookup", "valid_at"),
    "trust.py": ("verify",),
}
SUITE = ["test_selection", "test_registry", "test_integration", "test_security", "test_model", "test_ops",
         "test_boundaries"]
#: Mutants proven unreachable by an earlier check.  Listed in the evidence, excluded from the score denominator.
EQUIVALENT = {
    ("binding.py", "toolchain is"): "lifecycle is part of the record digest, so a disabled/quarantined/retired entry "
                                    "always fails the record_digest check first; kept as defence in depth",
    ("binding.py", "binds no artifact digest"): "an empty bound digest can never equal sha256(bytes), so the next "
                                                "check raises BIND_ARTIFACT_MISMATCH anyway; kept for a clearer reason",
}
FLIP = {ast.In: ast.NotIn, ast.NotIn: ast.In, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.LtE,
        ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Is: ast.IsNot, ast.IsNot: ast.Is}


def sites(tree, funcs):
    out: list = []
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name in funcs:
            for node in ast.walk(fn):
                if isinstance(node, ast.Compare):
                    for i, op in enumerate(node.ops):
                        if type(op) in FLIP:
                            out.append(("cmp", node, i))
                elif isinstance(node, ast.BoolOp):
                    out.append(("bool", node, 0))
                elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
                    out.append(("not", node, 0))
                elif isinstance(node, ast.Raise):
                    out.append(("raise", node, 0))
    return out


def mutate(src: str, funcs, k: int):
    tree = ast.parse(src)
    kind, node, i = sites(tree, funcs)[k]
    line = node.lineno
    if kind == "cmp":
        node.ops[i] = FLIP[type(node.ops[i])]()
        desc = "comparison flip"
    elif kind == "bool":
        node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
        desc = "and/or flip"
    elif kind == "not":
        # replace `not x` by `x` via parent rewrite
        class DropNot(ast.NodeTransformer):
            def visit_UnaryOp(self, n):
                return n.operand if n is node else self.generic_visit(n)
        tree = DropNot().visit(tree)
        desc = "drop not"
    else:
        class RaiseToPass(ast.NodeTransformer):
            def visit_Raise(self, n):
                return ast.Pass() if n is node else n
        tree = RaiseToPass().visit(tree)
        desc = "raise -> pass"
    ast.fix_missing_locations(tree)
    return ast.unparse(tree), line, desc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=0, help="cap per file (0 = all)")
    ap.add_argument("--threshold", type=float, default=80.0)
    a = ap.parse_args(argv)
    results, t0 = [], time.time()
    with tempfile.TemporaryDirectory() as tmp:
        pkg = os.path.join(tmp, ROOT.name)
        shutil.copytree(ROOT, pkg, ignore=shutil.ignore_patterns("__pycache__", ".mypy_cache", ".ruff_cache", "evidence", "*.zip"))
        env = dict(os.environ, PYTHONPATH=tmp, PYTHONDONTWRITEBYTECODE="1", INV28_FUZZ_N="40", INV28_SOAK_N="300")
        base = subprocess.run([sys.executable, "-B", "-W", "ignore", "-m", "unittest", "-q", *SUITE],
                              cwd=os.path.join(pkg, "tests"), env=env, capture_output=True, text=True, timeout=600)
        if base.returncode != 0:
            print(base.stderr[-2000:])
            raise SystemExit("baseline suite fails; mutation testing meaningless")
        for fname, funcs in TARGETS.items():
            original = (ROOT / fname).read_text(encoding="utf-8")
            n = len(sites(ast.parse(original), funcs))
            idx = range(n) if not a.max else range(0, n, max(1, n // a.max))
            for k in idx:
                mutated, line, desc = mutate(original, funcs, k)
                with open(os.path.join(pkg, fname), "w", encoding="utf-8") as fh:
                    fh.write(mutated)
                try:
                    p = subprocess.run([sys.executable, "-B", "-W", "ignore", "-m", "unittest", "-q", "-f", *SUITE],
                                       cwd=os.path.join(pkg, "tests"), env=env, capture_output=True, text=True, timeout=300)
                    killed = p.returncode != 0
                except subprocess.TimeoutExpired:
                    killed = True
                src_line = original.splitlines()[line - 1]
                eq = next((why for (f, needle), why in EQUIVALENT.items() if f == fname and needle in src_line), None)
                results.append({"file": fname, "line": line, "operator": desc, "killed": killed,
                                **({"equivalent": eq} if eq and not killed else {})})
            with open(os.path.join(pkg, fname), "w", encoding="utf-8") as fh:
                fh.write(original)
    n_killed = sum(r["killed"] for r in results)
    equivalent = [r for r in results if r.get("equivalent")]
    score = round(100 * n_killed / max(len(results) - len(equivalent), 1), 1)
    doc = {"schema": "PK_MUTATION/1", "tool": "tools/mutation.py", "suite": SUITE, "mutants": len(results),
           "killed": n_killed, "score_pct": score, "threshold_pct": a.threshold, "pass": score >= a.threshold,
           "equivalent": equivalent,
           "survivors": [r for r in results if not r["killed"] and not r.get("equivalent")], "seconds": round(time.time() - t0, 1),
           "sampled": bool(a.max)}
    write_json(EVIDENCE / "MUTATION.json", doc)
    for s in doc["survivors"]:
        print("SURVIVOR", f"{s['file']}:{s['line']}", s["operator"])
    print("MUTATION", "PASS" if doc["pass"] else "FAIL",
          f"{n_killed}/{len(results) - len(equivalent)} killed = {score}% ({len(equivalent)} equivalent)")
    return 0 if doc["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
