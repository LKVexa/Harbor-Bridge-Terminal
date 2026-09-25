"""C081-C087: line + branch-arc coverage for the runtime modules using only the stdlib
(sys.settrace; the ``coverage`` package is not required). Runs the whole unittest suite in
process, then reports per-module line coverage and arc coverage against executable lines
from ``ast``/``dis``. Fails below thresholds in ci/coverage-policy.json."""
import ast, json, os, sys, threading, types, unittest
from _tools_pkg import ROOT

RUNTIME = ["stream.py", "control.py", "security.py", "configuration.py", "observability.py", "adapters.py", "wire.py"]
FILES = {str(ROOT / m): m for m in RUNTIME}
hits: dict = {f: set() for f in FILES}
arcs: dict = {f: set() for f in FILES}
last: dict = {}


def tracer(frame, event, arg):
    f = frame.f_code.co_filename
    if f not in FILES:
        return None
    def local(fr, ev, a):
        if ev == "line":
            key = (threading.get_ident(), id(fr))
            prev = last.get(key)
            hits[f].add(fr.f_lineno)
            if prev is not None:
                arcs[f].add((prev, fr.f_lineno))
            last[key] = fr.f_lineno
        return local
    return local


def executable_lines(path):
    code = compile(open(path).read(), path, "exec")
    lines = set()
    def walk(c):
        for _, _, ln in c.co_lines():
            if ln:
                lines.add(ln)
        for k in c.co_consts:
            if isinstance(k, types.CodeType):
                walk(k)
    walk(code)
    tree = ast.parse(open(path).read())
    excluded = set()
    src = open(path).read().splitlines()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.lineno - 1 < len(src) and "pragma: no cover" in src[node.lineno - 1]:
            excluded.update(range(node.lineno, node.end_lineno + 1))
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            pass
    docstr = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and ast.get_docstring(node):
            d = node.body[0]; docstr.update(range(d.lineno, d.end_lineno + 1))
    return lines - excluded - docstr, excluded


def branch_points(path):
    """(line -> set of successor lines) for if/while/for/try decision points, from ast."""
    tree = ast.parse(open(path).read())
    points = {}
    for n in ast.walk(tree):
        if isinstance(n, (ast.If, ast.While, ast.For)):
            succ = {n.body[0].lineno}
            if n.orelse:
                succ.add(n.orelse[0].lineno)
            points[n.lineno] = succ
    return points


def main():
    sys.path.insert(0, str(ROOT / "tests"))
    os.environ.setdefault("INV17_SOAK_SECONDS", "0.5")
    os.environ.setdefault("INV17_FUZZ_CASES", "150")
    sys.settrace(tracer); threading.settrace(tracer)
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py", top_level_dir=str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, "w")).run(suite)
    sys.settrace(None); threading.settrace(None)
    policy = json.loads((ROOT / "ci" / "coverage-policy.json").read_text())
    report = {"tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "modules": {}}
    ok = result.wasSuccessful()
    tl = tc = tb = tbc = 0
    for f, name in FILES.items():
        exe, _ = executable_lines(f)
        covered = hits[f] & exe
        bp = branch_points(f)
        b_total = sum(len(v) for v in bp.values())
        b_cov = sum(1 for ln, succ in bp.items() for s in succ if (ln, s) in arcs[f])
        missing = sorted(exe - covered)
        report["modules"][name] = {"lines": len(exe), "covered": len(covered), "line_pct": round(100 * len(covered) / len(exe), 1),
                                   "branches": b_total, "branches_covered": b_cov,
                                   "branch_pct": round(100 * b_cov / b_total, 1) if b_total else 100.0, "missing_lines": missing}
        tl += len(exe); tc += len(covered); tb += b_total; tbc += b_cov
        crit = policy["critical_modules"].get(name)
        if crit and (report["modules"][name]["line_pct"] < crit["line"] or report["modules"][name]["branch_pct"] < crit["branch"]):
            ok = False; report["modules"][name]["below_threshold"] = True
    report["total"] = {"line_pct": round(100 * tc / tl, 1), "branch_pct": round(100 * tbc / tb, 1)}
    if report["total"]["line_pct"] < policy["total"]["line"] or report["total"]["branch_pct"] < policy["total"]["branch"]:
        ok = False
    report["verdict"] = "PASS" if ok else "FAIL"
    out = ROOT / "evidence" / "coverage.json"; out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"total": report["total"], "verdict": report["verdict"], "tests": result.testsRun,
                      "modules": {k: (v["line_pct"], v["branch_pct"]) for k, v in report["modules"].items()}}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
