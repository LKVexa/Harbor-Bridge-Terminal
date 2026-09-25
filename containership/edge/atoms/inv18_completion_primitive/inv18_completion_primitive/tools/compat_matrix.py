"""Run the full test suite under every supported Python found on this host (C084, C093).

Writes conformance/COMPAT_RESULTS.json. Platforms that cannot run here are listed as
not executed; the gate reports them as a condition (PLATFORMS_NOT_RUN).
"""
import json, pathlib, platform, shutil, sys
pkg = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pkg.parent))
certify = __import__(pkg.name + ".certify", fromlist=["run_suite"])
matrix = json.loads((pkg / "conformance/COMPAT_MATRIX.json").read_text())
# part of the certification pipeline: outputs of a previous certification are stale now
tv = __import__(pkg.name + ".tools_verify", fromlist=["GENERATED"])
for rel in tv.GENERATED - {"SHA256SUMS", "conformance/COMPAT_RESULTS.json"}:
    (pkg / rel).unlink(missing_ok=True)
plat = f"{platform.system().lower()}-{platform.machine().lower().replace('amd64', 'x86_64')}"
runs = []
for v in matrix["python"]["supported"]:
    exe = shutil.which(f"python{v}")
    if not exe:
        runs.append({"python": v, "platform": plat, "executed": False, "passed": False, "reason": "interpreter not installed"})
        continue
    res = certify.run_suite(exe, env={"INV18_CONTEXT": "compat"})
    c = res.get("counts", {})
    ok = bool(res["tests"]) and not c.get("fail") and not c.get("error")
    runs.append({"python": v, "platform": plat, "executed": True, "passed": ok, "counts": c,
                 "python_full": res.get("environment", {}).get("python"),
                 "failing": [{"id": t["id"], "detail": (t["detail"] or "")[-600:]} for t in res["tests"] if t["status"] in ("fail", "error")]})
    print(v, c)
out = {"schema": "INV18_COMPAT_RESULTS/1", "host_platform": plat,
       "runs": [dict(r, platform=r["platform"]) for r in runs],
       "note": "passed=true means no failures/errors; mandatory skips (pk_core, real tier) are gated separately"}
# the gate keys platform evidence by platform name; one passing interpreter is enough per platform
(pkg / "conformance/COMPAT_RESULTS.json").write_text(json.dumps(out, indent=1))
