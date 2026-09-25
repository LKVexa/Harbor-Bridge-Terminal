"""Stdlib-only line coverage for prod/ (M01-036 diagnostic; not an acceptance criterion).

    python inv09_portable_compute_isa/tools/linecov.py  -> evidence/coverage.json
"""
import ast, json, pathlib, sys, threading, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROD = ROOT / "prod"
hits: dict[str, set[int]] = {}


def tracer(frame, event, arg):
    fn = frame.f_code.co_filename
    if fn.startswith(str(PROD)):
        if event == "line":
            hits.setdefault(fn, set()).add(frame.f_lineno)
        return tracer
    return None


def executable_lines(path: pathlib.Path) -> set[int]:
    tree = ast.parse(path.read_text())
    lines = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt) and not isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Import,
                                                                  ast.ImportFrom)):
            if isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant):
                continue  # docstrings
            lines.add(node.lineno)
    return lines


def main() -> int:
    sys.path.insert(0, str(ROOT.parent))
    sys.settrace(tracer)
    threading.settrace(tracer)
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    res = unittest.TextTestRunner(verbosity=0).run(suite)
    sys.settrace(None)
    report = {}
    tot_e = tot_h = 0
    for f in sorted(PROD.glob("*.py")):
        ex = executable_lines(f)
        h = hits.get(str(f), set()) & ex
        tot_e += len(ex)
        tot_h += len(h)
        report[f.name] = {"executable": len(ex), "hit": len(h), "pct": round(100 * len(h) / max(1, len(ex)), 1),
                          "missed": sorted(ex - h)}
    sys.path.insert(0, str(ROOT / "tools"))
    from evidence import release_digest
    out = {"release_digest": release_digest(), "schema": "PK_LINE_COVERAGE/1", "tests_ok": res.wasSuccessful(), "total_pct": round(100 * tot_h / tot_e, 1),
           "files": report}
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence" / "coverage.json").write_text(json.dumps(out, indent=1))
    for k, v in report.items():
        print(f"{k:18} {v['pct']:5}%  ({v['hit']}/{v['executable']})")
    print("TOTAL", out["total_pct"])
    return 0 if res.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
