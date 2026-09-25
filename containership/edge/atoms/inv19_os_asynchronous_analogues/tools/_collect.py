"""Run the unittest suite and emit per-test outcomes as JSON (used by run_gate)."""
import json
import pathlib
import sys
import unittest

TESTS = pathlib.Path(__file__).resolve().parents[1] / "tests"
sys.path.insert(0, str(TESTS))


class R(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.rows = []

    def addSuccess(self, t):
        super().addSuccess(t); self.rows.append((t.id(), "pass", ""))

    def addFailure(self, t, e):
        super().addFailure(t, e); self.rows.append((t.id(), "fail", self._exc_info_to_string(e, t)[-600:]))

    def addError(self, t, e):
        super().addError(t, e); self.rows.append((t.id(), "error", self._exc_info_to_string(e, t)[-600:]))

    def addSkip(self, t, reason):
        super().addSkip(t, reason); self.rows.append((t.id(), "skip", reason))


def _apply_mutant(name: str) -> None:
    """Known-bad implementations the gate must reject (global rule: an
    acceptance gate is only credible if it fails on a known-bad build)."""
    sys.path.insert(0, str(TESTS.parents[1]))
    from inv19_os_asynchronous_analogues.hostio import readiness, driver
    import inv19_os_asynchronous_analogues.backend as be
    if name == "fabricate_completion":
        orig = readiness.ReadinessIO.read
        def fake(self, fd, n=65536):
            k, v = orig(self, fd, n)
            return ("value", b"") if k != "value" else (k, v)   # readiness pretends completion
        readiness.ReadinessIO.read = fake
        readiness.ReadinessIO.write = lambda self, fd, data: ("value", len(data))
    elif name == "drop_completion_error":
        orig_reap = be.AsyncBackend.reap
        def reap(self, fd):
            ev = orig_reap(self, fd)
            return ("value", None) if ev and ev[0] == "error" else ev
        be.AsyncBackend.reap = reap
        orig_fin = driver.AsyncHost._finish
        def fin(self, op_id, value, err, state, cause=None):
            from inv19_os_asynchronous_analogues.hostio.ops import OpState
            if err is not None and state is OpState.FAILED:
                return orig_fin(self, op_id, 0, None, OpState.COMPLETED, cause)
            return orig_fin(self, op_id, value, err, state, cause)
        driver.AsyncHost._finish = fin


if __name__ == "__main__":
    import os
    if os.environ.get("INV19_MUTANT"):
        _apply_mutant(os.environ["INV19_MUTANT"])
    suite = unittest.defaultTestLoader.discover(str(TESTS), pattern="test_*.py", top_level_dir=str(TESTS))
    runner = unittest.TextTestRunner(resultclass=R, verbosity=0, stream=open("/dev/null", "w"))
    res = runner.run(suite)
    json.dump({"optimized": sys.flags.optimize, "rows": res.rows, "ran": res.testsRun}, sys.stdout)
