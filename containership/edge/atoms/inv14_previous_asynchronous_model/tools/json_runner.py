"""Run one unittest file and write per-test outcomes as JSON (xx.30).
usage: python [-O] -B tools/json_runner.py tests/<file>.py OUT.json"""
import json, pathlib, platform, sys, time, unittest
test_file = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(test_file.parent)); sys.path.insert(0, str(test_file.parents[1]))
sys.dont_write_bytecode = True


class R(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k); self.rows = []; self._t = {}
    def startTest(self, t):
        self._t[t.id()] = time.perf_counter(); super().startTest(t)
    def _row(self, t, outcome, detail=""):
        name = ".".join(t.id().split(".")[-2:])
        self.rows.append({"test": name, "outcome": outcome, "seconds": round(time.perf_counter() - self._t.get(t.id(), time.perf_counter()), 4), "detail": detail[-600:]})
    def addSuccess(self, t): super().addSuccess(t); self._row(t, "pass")
    def addFailure(self, t, e): super().addFailure(t, e); self._row(t, "fail", self._exc_info_to_string(e, t))
    def addError(self, t, e): super().addError(t, e); self._row(t, "error", self._exc_info_to_string(e, t))
    def addSkip(self, t, r): super().addSkip(t, r); self._row(t, "skip", r)


suite = unittest.defaultTestLoader.loadTestsFromName(test_file.stem) if False else unittest.defaultTestLoader.discover(str(test_file.parent), pattern=test_file.name, top_level_dir=str(test_file.parent))
runner = unittest.TextTestRunner(resultclass=R, verbosity=0, stream=open("/dev/null", "w") if sys.platform != "win32" else sys.stderr)
res = runner.run(suite)
json.dump({"file": test_file.name, "optimized": sys.flags.optimize > 0, "python": platform.python_version(),
           "tests": res.rows, "summary": {k: sum(r["outcome"] == k for r in res.rows) for k in ("pass", "fail", "error", "skip")}},
          open(sys.argv[2], "w"), indent=1)
sys.exit(0 if res.wasSuccessful() else 1)
