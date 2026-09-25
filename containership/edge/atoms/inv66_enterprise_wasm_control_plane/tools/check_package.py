"""Package lane (MC-028): build the wheel twice from the tree (SOURCE_DATE_EPOCH fixed), require identical
digests, install into a clean venv (system site-packages only for `cryptography`), and smoke-test the CLI
and import surface from outside the source tree."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
env = {**os.environ, "SETUPTOOLS_USE_DISTUTILS": "stdlib", "SOURCE_DATE_EPOCH": "1790035200", "PYTHONDONTWRITEBYTECODE": "1"}
digests = []
work = Path(tempfile.mkdtemp(prefix="inv66-pkg-"))
for i in range(2):
    out = work / f"w{i}"
    src = work / f"src{i}"
    shutil.copytree(ROOT, src, ignore=shutil.ignore_patterns("__pycache__", ".git", "build", "*.egg-info", "release"))
    r = subprocess.run([sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "--no-build-isolation", "-w", str(out), "-q"],
                       cwd=src, env=env, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:])
        sys.exit(1)
    whl = next(out.glob("*.whl"))
    digests.append(hashlib.sha256(whl.read_bytes()).hexdigest())
print("wheel sha256:", digests)
if digests[0] != digests[1]:
    print("NOT REPRODUCIBLE")
    sys.exit(1)
venv = work / "venv"
subprocess.run([sys.executable, "-m", "venv", "--system-site-packages", str(venv)], check=True)
pip = venv / "bin" / "pip"
subprocess.run([str(pip), "install", "-q", "--no-deps", str(whl)], check=True, env=env)
py = venv / "bin" / "python"
smoke = subprocess.run([str(py), "-c", "import inv66_enterprise_wasm_control_plane as m, json;"
                        "from inv66_enterprise_wasm_control_plane.production import schema, service;"
                        "print(json.dumps({'version': m.__version__, 'schemas': len(list(schema.SCHEMA_DIR.glob('*.schema.json'))), 'svc': service.VERSION}))"],
                       cwd=work, capture_output=True, text=True, env=env)
print(smoke.stdout.strip(), smoke.stderr[-500:])
demo = subprocess.run([str(venv / "bin" / "inv66"), "demo", "--seconds", "0.2"], cwd=work, capture_output=True, text=True, env=env)
ok = smoke.returncode == 0 and json.loads(smoke.stdout)["schemas"] >= 10 and demo.returncode == 0 and '"url"' in demo.stdout
(ROOT / "release").mkdir(exist_ok=True)
(ROOT / "release" / "package.json").write_text(json.dumps({"schema": "PK_ECP_PACKAGE/1", "wheel": whl.name, "sha256": digests[0],
                                                          "reproducible": True, "source_date_epoch": env["SOURCE_DATE_EPOCH"],
                                                          "python": sys.version.split()[0], "smoke": ok}, indent=1) + "\n")
dist = ROOT / "dist"
dist.mkdir(exist_ok=True)
shutil.copy2(whl, dist / whl.name)
print("package smoke:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
