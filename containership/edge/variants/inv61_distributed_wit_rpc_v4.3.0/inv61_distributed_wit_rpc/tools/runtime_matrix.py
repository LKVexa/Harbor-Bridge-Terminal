"""Run the full test suite on every locally available CPython (C084/M27) and
record results in evidence/runtime_matrix.json."""
from __future__ import annotations

import json
import pathlib
import platform
import re
import shutil
import subprocess
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
CANDIDATES = ["python3.10", "python3.11", "python3.12", "python3.13", "python3.14"]


def main() -> int:
    rows = []
    for exe in CANDIDATES:
        path = shutil.which(exe)
        if not path:
            rows.append({"runtime": exe, "status": "not-available"})
            continue
        for opt in ([], ["-O"]):
            p = subprocess.run([path, *opt, "-W", "ignore", "-m", "unittest", "discover", "-s", "tests", "-t", "tests"],
                               cwd=PKG, capture_output=True, text=True, timeout=900)
            tail = p.stderr.strip().splitlines()[-3:]
            m = re.search(r"Ran (\d+) tests", p.stderr)
            sk = re.search(r"skipped=(\d+)", p.stderr)
            rows.append({"runtime": exe, "version": subprocess.run([path, "-c", "import sys;print(sys.version.split()[0])"],
                                                                    capture_output=True, text=True).stdout.strip(),
                         "flags": " ".join(opt) or "-", "tests": int(m.group(1)) if m else 0,
                         "skipped": int(sk.group(1)) if sk else 0,
                         "status": "pass" if p.returncode == 0 else "fail", "tail": tail})
    doc = {"schema": "inv61-runtime-matrix/1", "machine": platform.machine(), "system": platform.system(),
           "platform": platform.platform(), "rows": rows,
           "not_covered": ["Windows", "macOS", "aarch64", "Wasm host runtimes (wasmtime/wasmer embedding)", "PyPy"]}
    (PKG / "evidence").mkdir(exist_ok=True)
    (PKG / "evidence" / "runtime_matrix.json").write_text(json.dumps(doc, indent=2) + "\n")
    for r in rows:
        print(r["runtime"], r.get("version", ""), r.get("flags", ""), r["status"], r.get("tests", ""), "skipped", r.get("skipped", ""))
    return 0 if all(r["status"] in ("pass", "not-available") for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
