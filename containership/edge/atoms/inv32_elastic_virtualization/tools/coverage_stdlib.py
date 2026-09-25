"""Line coverage with the stdlib only (no coverage.py available offline).  Writes PK_INV32_COVERAGE/1."""
import ast, json, sys, threading, unittest, io
from pathlib import Path
PKG = Path(__file__).resolve().parents[1] / "inv32_elastic_virtualization"
TESTS = PKG / "tests"
sys.path.insert(0, str(TESTS))
hits: dict[str, set] = {}
prefix = str(PKG)
def tracer(frame, event, arg):
    f = frame.f_code.co_filename
    if not f.startswith(prefix) or "/tests/" in f:
        return None
    s = hits.setdefault(f, set())
    def local(fr, ev, a):
        if ev == "line":
            s.add(fr.f_lineno)
        return local
    s.add(frame.f_lineno)
    return local
sys.settrace(tracer); threading.settrace(tracer)
suite = unittest.defaultTestLoader.discover(str(TESTS), top_level_dir=str(TESTS))
res = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
sys.settrace(None); threading.settrace(None)
def executable(path):
    tree = ast.parse(Path(path).read_text())
    lines = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt) and not isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            if isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant) and isinstance(node.value.value, str):
                continue  # docstrings
            lines.add(node.lineno)
    return lines
report, tot_e, tot_h = {}, 0, 0
for p in sorted(PKG.rglob("*.py")):
    if "/tests/" in str(p):
        continue
    ex = executable(p)
    h = hits.get(str(p), set()) & ex
    report[str(p.relative_to(PKG))] = round(100 * len(h) / max(1, len(ex)), 1)
    tot_e += len(ex); tot_h += len(h)
out = {"schema": "PK_INV32_COVERAGE/1", "tool": "stdlib sys.settrace (statement coverage)", "tests_ok": res.wasSuccessful(),
       "total_percent": round(100 * tot_h / tot_e, 1), "threshold": 85, "files": report}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1))
print(json.dumps({"total": out["total_percent"], **{k: v for k, v in report.items() if v < 85}}, indent=0))
