"""Build the Go wasip1 guest and run the real-Wasm integration harness (MC-019/011/012)."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
out = pathlib.Path(tempfile.gettempdir()) / "inv12guest.wasm"
env = dict(os.environ, GOOS="wasip1", GOARCH="wasm")
subprocess.run(["go", "build", "-buildmode=c-shared", "-o", str(out), "."], cwd=ROOT / "fixtures/wasm-guest",
               env=env, check=True)
p = subprocess.run(["node", "--no-warnings", str(ROOT / "tools/wasm_host.mjs"), str(out)], capture_output=True, text=True)
rep = json.loads(p.stdout)
rep["guest_wasm_sha256"] = __import__("hashlib").sha256(out.read_bytes()).hexdigest()
(ROOT / "evidence").mkdir(exist_ok=True)
(ROOT / "evidence/wasm_guest.json").write_text(json.dumps(rep, indent=1) + "\n")
print(json.dumps({"verdict": rep["verdict"], "checks": [(c["name"], c["ok"]) for c in rep["checks"]]}))
sys.exit(0 if rep["verdict"] == "PASS" else 1)
