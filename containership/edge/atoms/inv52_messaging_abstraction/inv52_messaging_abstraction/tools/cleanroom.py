"""Reproducible clean-room certification (REPO-14).

Copies the tracked files (per CHECKSUMS.sha256) into a fresh temporary
directory, then runs integrity verification and the full test suite there with
``-I`` (isolated mode: no user site, no PYTHONPATH, no cwd injection) and
bytecode writing disabled.  Emits a JSON record; exit 0 only if both pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    manifest = (ROOT / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines()
    rels = [line.split("  ", 1)[1] for line in manifest if line.strip()]
    with tempfile.TemporaryDirectory(prefix="inv52-cleanroom-") as tmp:
        dst = pathlib.Path(tmp) / ROOT.name
        for rel in rels + ["CHECKSUMS.sha256"]:
            (dst / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dst / rel)
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0",
               "LC_ALL": "C.UTF-8"}
        runs = []
        for argv_ in ([sys.executable, "-I", "-B", str(dst / "verify_integrity.py")],
                      [sys.executable, "-I", "-B", "-m", "unittest", "discover", "-s", f"{ROOT.name}/tests",
                       "-p", "test_*.py"]):
            p = subprocess.run(argv_, cwd=tmp, capture_output=True, text=True, env=env, timeout=900)
            runs.append({"argv": [x.replace(tmp, "<cleanroom>") for x in argv_], "exit": p.returncode,
                         "tail": (p.stdout + p.stderr)[-1500:].replace(tmp, "<cleanroom>")})
        tree = hashlib.sha256("".join(sorted(manifest)).encode()).hexdigest()
    rec = {"schema": "INV52_CLEANROOM/1", "python": sys.version.split()[0], "platform": sys.platform,
           "tree_digest": tree, "files": len(rels), "runs": runs,
           "result": "PASS" if all(r["exit"] == 0 for r in runs) else "FAIL"}
    text = json.dumps(rec, indent=2)
    if a.out:
        pathlib.Path(a.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if rec["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
