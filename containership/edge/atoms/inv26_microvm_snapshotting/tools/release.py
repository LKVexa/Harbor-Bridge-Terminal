"""Build, sign and verify a release; install-check it read-only (X004, X005 partial, C031, C032, C045).

  build   -> dist/: wheel + sdist (setuptools build_meta, no isolation, SOURCE_DATE_EPOCH honoured),
             sbom.cdx.json (CycloneDX 1.5), SHA256SUMS, provenance.dsse.json (in-toto Statement v1 with a
             SLSA-provenance-shaped predicate, DSSE-signed with an EPHEMERAL Ed25519 key), signing-key.pub.json
  verify  -> recompute every digest, verify the DSSE signature against the published key, and refuse on any
             mismatch (tamper test included in the evidence run)
  install -> fresh venv (system site-packages for the pinned crypto lib only), install the wheel with
             --no-deps, make the installed package tree READ-ONLY, then run the smoke test and the unit suite
             from the installed copy: proves the runtime never writes into its install tree (C032)
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .. import provenance

PKG = Path(__file__).resolve().parents[1]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build(dist: Path) -> dict:
    dist.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="inv26-build-"))
    src = stage / "inv26_microvm_snapshotting"
    shutil.copytree(PKG, src, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "dist", "build", "*.egg-info",
                                                            ".git", "evidence"))
    env = dict(os.environ, SETUPTOOLS_USE_DISTUTILS="stdlib", SOURCE_DATE_EPOCH=os.environ.get("SOURCE_DATE_EPOCH", "1790121600"))
    code = ("import sys; from setuptools import build_meta as b; "
            f"print(b.build_wheel({str(dist)!r})); print(b.build_sdist({str(dist)!r}))")
    r = subprocess.run([sys.executable, "-c", code], cwd=src, env=env, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr[-3000:])
    names = [l.strip() for l in r.stdout.splitlines() if l.strip().endswith((".whl", ".tar.gz"))]
    import cffi
    import cryptography
    version = (PKG / "VERSION").read_text().strip()
    sbom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": "inv26-microvm-snapshotting", "version": version}},
            "components": [
                {"type": "library", "name": "cryptography", "version": cryptography.__version__, "purl":
                 f"pkg:pypi/cryptography@{cryptography.__version__}", "licenses": [{"license": {"id": "Apache-2.0"}}]},
                {"type": "library", "name": "cffi", "version": cffi.__version__, "purl": f"pkg:pypi/cffi@{cffi.__version__}",
                 "licenses": [{"license": {"id": "MIT"}}]},
                {"type": "library", "name": "pk_core", "version": "UNKNOWN", "description":
                 "optional conformance dependency; not present, not pinned (X013)"}],
            "properties": [{"name": "inv26:carried-code", "value": "redaction.py, audit.py, provenance.py, telemetry.py from owner's INV-68 v4.3.0"}]}
    (dist / "sbom.cdx.json").write_text(json.dumps(sbom, indent=1) + "\n")
    files = sorted([dist / n for n in names] + [dist / "sbom.cdx.json"])
    (dist / "SHA256SUMS").write_text("".join(f"{_sha(p)}  {p.name}\n" for p in files))
    priv, pub = provenance.ed25519_keypair()
    subjects = [{"name": p.name, "digest": {"sha256": _sha(p)}} for p in files]
    stmt = provenance.statement(subjects, version=version, builder_id="urn:inv26:cowork-cloud-builder:ephemeral",
                                invocation={"command": "tools/release.py build"},
                                dependencies=[{"uri": c["purl"], "digest": {}} for c in sbom["components"] if "purl" in c])
    dsse = provenance.sign(stmt, key=priv, key_id="inv26-ephemeral", alg="ed25519")
    (dist / "provenance.dsse.json").write_text(json.dumps(dsse, indent=1) + "\n")
    (dist / "signing-key.pub.json").write_text(json.dumps({"keyid": "inv26-ephemeral", "alg": "ed25519",
                                                          "public": base64.b64encode(pub).decode(),
                                                          "warning": "ephemeral key generated for this build; proves "
                                                                     "integrity, not publisher identity"}, indent=1) + "\n")
    del priv
    shutil.rmtree(stage, ignore_errors=True)
    return {"schema": "PK_SNAPSHOT_RELEASE/1", "version": version, "artifacts": {p.name: _sha(p) for p in files},
            "signer": "ephemeral ed25519", "source_date_epoch": env["SOURCE_DATE_EPOCH"]}


def verify(dist: Path) -> dict:
    problems = []
    for line in (dist / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        p = dist / name
        if not p.exists() or _sha(p) != digest:
            problems.append(f"digest mismatch: {name}")
    dsse = json.loads((dist / "provenance.dsse.json").read_text())
    key = json.loads((dist / "signing-key.pub.json").read_text())
    payload = base64.b64decode(dsse["payload"])
    msg = provenance.pae(dsse["payloadType"], payload)
    ok = provenance.check_signature("ed25519", base64.b64decode(key["public"]), msg,
                                    base64.b64decode(dsse["signatures"][0]["sig"]))
    if not ok:
        problems.append("DSSE signature invalid")
    stmt = json.loads(payload)
    for s in stmt["subject"]:
        p = dist / s["name"]
        if not p.exists() or _sha(p) != s["digest"]["sha256"]:
            problems.append(f"provenance subject mismatch: {s['name']}")
    return {"schema": "PK_SNAPSHOT_RELEASE_VERIFY/1", "problems": problems, "result": "PASS" if not problems else "FAIL",
            "identity": "UNVERIFIED (ephemeral signer)"}


def tamper_selftest(dist: Path) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="inv26-tamper-"))
    shutil.copytree(dist, tmp / "d")
    whl = next((tmp / "d").glob("*.whl"))
    b = bytearray(whl.read_bytes()); b[len(b) // 2] ^= 1; whl.write_bytes(bytes(b))
    res = verify(tmp / "d")
    return {"tampered_wheel_refused": res["result"] == "FAIL", "problems": res["problems"]}


def install_check(dist: Path) -> dict:
    venv = Path(tempfile.mkdtemp(prefix="inv26-venv-"))
    subprocess.run([sys.executable, "-m", "venv", "--system-site-packages", str(venv)], check=True)
    py = venv / "bin" / "python"
    whl = next(dist.glob("*.whl"))
    r = subprocess.run([str(py), "-m", "pip", "install", "--no-deps", "--no-index", "--no-compile", str(whl)], capture_output=True, text=True)
    if r.returncode:
        return {"result": "FAIL", "stage": "pip install", "stderr": r.stderr[-2000:]}
    loc = subprocess.run([str(py), "-c", "import inv26_microvm_snapshotting as m, os; print(os.path.dirname(m.__file__))"],
                         capture_output=True, text=True, cwd="/").stdout.strip()
    for root, dirs, files in os.walk(loc):
        for n in files + dirs:
            p = os.path.join(root, n)
            os.chmod(p, os.stat(p).st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    os.chmod(loc, os.stat(loc).st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    def tree():
        return {os.path.join(r, f): _sha(Path(r) / f) for r, _, fs in os.walk(loc) for f in fs}
    before = tree()
    envx = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    state = Path(tempfile.mkdtemp(prefix="inv26-state-"))
    smoke = subprocess.run([str(py), "-m", "inv26_microvm_snapshotting.tools.smoke", "--root", str(state)],
                           capture_output=True, text=True, cwd="/", env=envx)
    tests = subprocess.run([str(py), "-m", "unittest", "discover", "-s", os.path.join(loc, "tests"), "-t",
                            os.path.dirname(loc)], capture_output=True, text=True, cwd="/", env=envx)
    tail = tests.stderr.strip().splitlines()[-3:]
    after = tree()
    written = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    return {"schema": "PK_SNAPSHOT_INSTALL/1", "wheel": whl.name, "installed_at": loc, "package_tree_read_only": True, "running_as_root": os.geteuid() == 0,
            "method": "mode bits cleared AND full-tree SHA-256 compared before/after (root ignores mode bits)",
            "smoke_rc": smoke.returncode, "smoke": smoke.stdout.strip()[-600:], "tests_rc": tests.returncode,
            "tests_tail": tail, "files_written_into_package": written,
            "result": "PASS" if smoke.returncode == 0 and tests.returncode == 0 and not written else "FAIL"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "verify", "install", "all"])
    ap.add_argument("--dist", default=str(PKG.parent / "dist"))
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    dist = Path(a.dist)
    res = {}
    if a.cmd in ("build", "all"):
        res["build"] = build(dist)
    if a.cmd in ("verify", "all"):
        res["verify"] = verify(dist)
    if a.cmd == "all":
        res["tamper"] = tamper_selftest(dist)
    if a.cmd in ("install", "all"):
        res["install"] = install_check(dist)
    ok = all(v.get("result", "PASS") == "PASS" for v in res.values() if isinstance(v, dict)) and \
        res.get("tamper", {}).get("tampered_wheel_refused", True)
    res["result"] = "PASS" if ok else "FAIL"
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: (v.get("result") if isinstance(v, dict) else v) for k, v in res.items()}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
