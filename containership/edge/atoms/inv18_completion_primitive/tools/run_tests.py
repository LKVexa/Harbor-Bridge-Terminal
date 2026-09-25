"""Run the suite and write machine-readable results: python tools/run_tests.py [OUT.json]"""
import json, pathlib, sys
pkg = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pkg.parent))
tr = __import__(pkg.name + ".testrunner", fromlist=["run"])
res = tr.run()
out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pkg / "evidence" / "test_results.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(res, indent=1))
print(res["counts"], "->", out)
sys.exit(1 if res["counts"].get("fail") or res["counts"].get("error") else 0)
