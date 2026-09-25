"""Run the full stdlib unittest suite and write a machine-readable result (PK_INV32_TEST_RESULTS/1)."""
import json, platform, sys, time, unittest, io
from pathlib import Path
tests = Path(__file__).resolve().parents[1] / "inv32_elastic_virtualization" / "tests"
sys.path.insert(0, str(tests))
suite = unittest.defaultTestLoader.discover(str(tests), top_level_dir=str(tests))
buf = io.StringIO()
t0 = time.time()
res = unittest.TextTestRunner(stream=buf, verbosity=2).run(suite)
out = {"schema": "PK_INV32_TEST_RESULTS/1", "python": platform.python_version(), "platform": platform.platform(),
       "started": t0, "duration_s": round(time.time() - t0, 3), "tests_run": res.testsRun,
       "failures": len(res.failures), "errors": len(res.errors), "skipped": len(res.skipped),
       "skipped_detail": [f"{t.id()}: {r}" for t, r in res.skipped],
       "failed_detail": [t.id() for t, _ in res.failures + res.errors]}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1))
(Path(sys.argv[1]).with_suffix(".log")).write_text(buf.getvalue())
print(json.dumps({k: out[k] for k in ("tests_run", "failures", "errors", "skipped", "duration_s")}))
sys.exit(0 if res.wasSuccessful() else 1)
