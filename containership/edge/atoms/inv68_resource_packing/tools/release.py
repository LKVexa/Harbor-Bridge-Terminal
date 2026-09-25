"""Release build, SBOM, checksums, signed provenance and consumer verification.

INV-68 MC-09, MC-32, MC-42 (C031, C045, C090).  Shape adapted from the owner's
INV-64 4.3.0 ``tools/release.py``.

    python -m inv68_resource_packing.tools.release build  --out RELEASE_DIR [--evidence DIR]
    python -m inv68_resource_packing.tools.release verify --release RELEASE_DIR [--trusted-key HEX --trusted-kid ID]

``build``: wheel + sdist (setuptools, no network, no build isolation), then
``sbom.cdx.json`` (CycloneDX 1.5, license policy applied), ``SHA256SUMS`` over
artifacts + evidence + SBOM, ``provenance.intoto.json`` (in-toto Statement v1 /
SLSA provenance v1 predicate), and Ed25519 DSSE signatures over both.

Signing key: ``INV68_SIGNING_KEY_HEX`` (+ ``INV68_SIGNING_KID``) from a managed
signer, accepted only when ``evidence/EXIT_GATE.json`` says GO.  Otherwise an
**ephemeral** key is generated, its public half published, and ``verify``
reports signer identity as FAIL -- integrity without identity is not release
provenance.  Private keys never touch disk.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .common import PKG, PARENT, revision, write

from inv68_resource_packing import __version__  # noqa: E402
from inv68_resource_packing import provenance as P  # noqa: E402

ALLOWED = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC", "PSF-2.0", "Unlicense", "CC0-1.0",
           "LicenseRef-Proprietary-Pending"}


def build_dist(out: Path) -> list[Path]:
    """Wheel + sdist via setuptools.build_meta (PEP 517 hooks, no network) in a clean copy."""
    dist = out / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "inv68_resource_packing"
        shutil.copytree(PKG, src, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git", "evidence", "release",
                                                                  "build", "dist", "*.egg-info"))
        (src / "evidence").mkdir()
        # Isolated, offline build interpreter: a fresh venv seeded by ensurepip (bundled setuptools),
        # so distro-patched system setuptools cannot leak into the artifact.
        venv = Path(tmp) / "buildenv"
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, capture_output=True)
        bpy = str(venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
        env = dict(os.environ)
        for hook in ("build_wheel", "build_sdist"):
            code = ("import sys, os; os.chdir(sys.argv[1]); from setuptools import build_meta as b; "
                    f"print(b.{hook}(sys.argv[2]))")
            p = subprocess.run([bpy, "-c", code, str(src), str(dist)], capture_output=True, text=True, env=env)
            if p.returncode != 0:
                raise SystemExit(f"{hook} failed:\n" + p.stdout[-1500:] + p.stderr[-2500:])
            shutil.rmtree(src / "build", ignore_errors=True)
        ver = subprocess.run([bpy, "-c", "import setuptools; print(setuptools.__version__)"], capture_output=True,
                             text=True).stdout.strip()
        (out / "BUILD_TOOLCHAIN.json").write_text(json.dumps({"python": sys.version.split()[0], "setuptools": ver,
                                                              "isolation": "fresh venv (ensurepip), no network"}) + "\n")
    return sorted(q for q in dist.iterdir() if q.suffix in (".whl", ".gz"))


def sbom(artifacts: list[Path]) -> dict:
    tc = json.loads((artifacts[0].parent.parent / "BUILD_TOOLCHAIN.json").read_text())

    class setuptools:  # noqa: N801 - version of the build venv's setuptools, not the system one
        __version__ = tc["setuptools"]
    comps = [
        {"type": "library", "bom-ref": f"pkg:pypi/inv68-resource-packing@{__version__}", "name": "inv68-resource-packing",
         "version": __version__, "purl": f"pkg:pypi/inv68-resource-packing@{__version__}",
         "licenses": [{"license": {"id": "LicenseRef-Proprietary-Pending"}}],
         "hashes": [{"alg": "SHA-256", "content": P.sha256_file(a)} for a in artifacts]},
        {"type": "library", "bom-ref": f"pkg:pypi/setuptools@{setuptools.__version__}", "name": "setuptools",
         "version": setuptools.__version__, "scope": "excluded", "licenses": [{"license": {"id": "MIT"}}],
         "properties": [{"name": "role", "value": "build-backend"}]},
        {"type": "library", "bom-ref": "pkg:pypi/jsonschema@4.26.0", "name": "jsonschema", "version": "4.26.0",
         "scope": "excluded", "licenses": [{"license": {"id": "MIT"}}], "properties": [{"name": "role", "value": "evidence tooling"}]},
        {"type": "library", "bom-ref": "inv64-donor", "name": "inv64-application-model (adapted modules)", "version": "4.3.0",
         "licenses": [{"license": {"id": "LicenseRef-Proprietary-Pending"}}],
         "properties": [{"name": "role", "value": "vendored-adapted: redaction.py, audit.py, provenance.py, release_gate.py"}]},
    ]
    bad = [c["name"] for c in comps if c["licenses"][0]["license"]["id"] not in ALLOWED]
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"timestamp": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "component": {"type": "library", "name": "inv68-resource-packing", "version": __version__},
                         "tools": [{"name": "inv68 tools/release.py", "version": __version__}],
                         "properties": [{"name": "source_revision", "value": revision()},
                                        {"name": "runtime_dependencies", "value": "none (stdlib only)"},
                                        {"name": "license_policy_violations", "value": json.dumps(bad)},
                                        {"name": "pk_core", "value": "NOT BUNDLED; unknown version/license (MC-02)"}]},
            "components": comps, "dependencies": [{"ref": comps[0]["bom-ref"], "dependsOn": []}]}


def _key() -> tuple[bytes, bytes, str, str]:
    hexkey = os.environ.get("INV68_SIGNING_KEY_HEX")
    if hexkey:
        gate = PKG / "evidence" / "EXIT_GATE.json"
        verdict = json.loads(gate.read_text()).get("verdict") if gate.is_file() else None
        if verdict != "GO":
            raise SystemExit(f"refusing managed signing: EXIT_GATE verdict {verdict!r} is not GO")
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        k = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(hexkey))
        pub = k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        return bytes.fromhex(hexkey), pub, os.environ.get("INV68_SIGNING_KID", "inv68-release"), "managed"
    priv, pub = P.ed25519_keypair()
    return priv, pub, "ephemeral-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"), "ephemeral"


def build(out: Path, evidence: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    arts = build_dist(out)
    post_build = {"BUILD.json", "INSTALL.json", "RELEASE_VERIFY.json", "EXIT_GATE.json", "RUN.json"}
    ev = sorted(p for p in evidence.glob("*.json") if p.name not in post_build) if evidence.is_dir() else []
    bom = sbom(arts)
    (out / "sbom.cdx.json").write_text(json.dumps(bom, indent=2, sort_keys=True) + "\n")
    subjects = ([{"name": f"dist/{p.name}", "digest": {"sha256": P.sha256_file(p)}} for p in arts] +
                [{"name": f"evidence/{p.name}", "digest": {"sha256": P.sha256_file(p)}} for p in ev] +
                [{"name": "sbom.cdx.json", "digest": {"sha256": P.sha256_file(out / "sbom.cdx.json")}}])
    builder = os.environ.get("GITHUB_WORKFLOW_REF") or f"local:{platform.node() or 'unknown'}"
    stmt = P.statement(subjects, version=__version__, builder_id=builder,
                       invocation={"source": f"{os.environ.get('GITHUB_REPOSITORY', 'local-checkout')}@{revision()}",
                                   "workflow": os.environ.get("GITHUB_WORKFLOW", "tools/release.py build")},
                       dependencies=[{"uri": f"python:{sys.version.split()[0]}", "digest": {}}],
                       build_type="urn:pk:inv68:release:1")
    (out / "provenance.intoto.json").write_text(json.dumps(stmt, indent=2, sort_keys=True) + "\n")
    sums = "".join(f"{s['digest']['sha256']}  {s['name']}\n" for s in subjects)
    sums += f"{P.sha256_file(out / 'provenance.intoto.json')}  provenance.intoto.json\n"
    (out / "SHA256SUMS").write_text(sums)
    priv, pub, kid, mode = _key()
    (out / "provenance.dsse.json").write_text(json.dumps(P.sign(stmt, key=priv, key_id=kid, alg="ed25519"), indent=2) + "\n")
    sums_stmt = P.statement([{"name": "SHA256SUMS", "digest": {"sha256": hashlib.sha256(sums.encode()).hexdigest()}}],
                            version=__version__, builder_id=builder, invocation={}, dependencies=[],
                            build_type="urn:pk:inv68:release:1")
    (out / "SHA256SUMS.sig.json").write_text(json.dumps(P.sign(sums_stmt, key=priv, key_id=kid, alg="ed25519"), indent=2) + "\n")
    (out / "signing-key.pub.json").write_text(json.dumps({"kid": kid, "alg": "ed25519", "public_key_hex": pub.hex(),
                                                          "mode": mode}, indent=2) + "\n")
    return {"artifacts": [a.name for a in arts], "signing_mode": mode, "subjects": len(subjects)}


def verify(release: Path, trusted: dict | None) -> dict:
    import base64
    info = json.loads((release / "signing-key.pub.json").read_text())
    key = bytes.fromhex((trusted or info)["public_key_hex"])
    checks = []
    for name, target in (("SHA256SUMS.sig.json", "SHA256SUMS"), ("provenance.dsse.json", "provenance.intoto.json")):
        env = json.loads((release / name).read_text())
        payload = base64.b64decode(env["payload"])
        ok = P.check_signature("ed25519", key, P.pae(env["payloadType"], payload), base64.b64decode(env["signatures"][0]["sig"]))
        stmt = json.loads(payload)
        if target == "SHA256SUMS":
            ok = ok and stmt["subject"][0]["digest"]["sha256"] == hashlib.sha256((release / target).read_bytes()).hexdigest()
        else:
            ok = ok and stmt == json.loads((release / target).read_text())
        checks.append({"check": f"signature {name}", "result": "PASS" if ok else "FAIL"})
    for line in (release / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        cand = [release / name, PKG / name]
        p = next((c for c in cand if c.is_file()), None)
        checks.append({"check": f"digest {name}", "result": "FAIL" if p is None or P.sha256_file(p) != digest else "PASS"})
    bom = json.loads((release / "sbom.cdx.json").read_text())
    viol = json.loads(next(p["value"] for p in bom["metadata"]["properties"] if p["name"] == "license_policy_violations"))
    checks.append({"check": "license policy", "result": "PASS" if not viol else "FAIL"})
    lic_chosen = "UNDECIDED" not in (PKG / "LICENSING.md").read_text()
    checks.append({"check": "distribution license chosen", "result": "PASS" if lic_chosen else "FAIL",
                   "reason": None if lic_chosen else "owner has not chosen a license (MC-42)"})
    mode = "trusted-key" if trusted else info["mode"]
    checks.append({"check": "signer identity", "result": "FAIL" if mode == "ephemeral" else "PASS",
                   "reason": "ephemeral key proves integrity only; no managed signer configured" if mode == "ephemeral" else None})
    lock_hashes = any("--hash=" in ln for ln in (PKG / "requirements-dev.lock").read_text().splitlines()
                      if ln.strip() and not ln.lstrip().startswith("#"))
    checks.append({"check": "dependency lock hashes", "result": "PASS" if lock_hashes else "FAIL",
                   "reason": None if lock_hashes else "dev lock pins versions without hashes (index unavailable here)"})
    return {"schema": "PK_PACK_RELEASE_VERIFY/1", "signing_mode": mode, "checks": checks,
            "result": "FAIL" if any(c["result"] == "FAIL" for c in checks) else "PASS"}


def install_check(release: Path) -> dict:
    """Install the built wheel into a fresh venv (offline, no deps) and run smoke + preflight from it."""
    wheel = next((release / "dist").glob("*.whl"))
    with tempfile.TemporaryDirectory() as tmp:
        venv = Path(tmp) / "v"
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, capture_output=True)
        py = str(venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
        steps = []
        for name, args in (("install", ["-m", "pip", "install", "--no-index", "--no-deps", str(wheel)]),
                           ("import+smoke", ["-c", "import inv68_resource_packing as m; r=m.pack_detailed("
                                                   "[{'name':'a','cpu':1,'mem':1}],16,64); print(m.__version__, dict(r.assignments))"]),
                           ("service-import", ["-c", "import inv68_resource_packing.service, inv68_resource_packing.release_gate"]),
                           ("preflight", ["-m", "inv68_resource_packing.tools.preflight", "--out", str(Path(tmp) / "ev")]),
                           ("console-script", [str(venv / "bin" / "inv68-audit"), "--help"])):
            cmd = args if name == "console-script" else [py, *args]
            p = subprocess.run(cmd, capture_output=True, text=True, cwd=tmp)
            steps.append({"step": name, "exit": p.returncode, "stdout": p.stdout[-300:], "stderr": p.stderr[-300:]})
    ok = all(s["exit"] == 0 for s in steps)
    return {"schema": "PK_PACK_INSTALL/1", "wheel": wheel.name, "sha256": P.sha256_file(wheel), "steps": steps,
            "result": "PASS" if ok else "FAIL"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--out", required=True)
    b.add_argument("--evidence", default=str(PKG / "evidence"))
    v = sub.add_parser("verify")
    v.add_argument("--release", required=True)
    v.add_argument("--trusted-key")
    v.add_argument("--trusted-kid")
    v.add_argument("--evidence-out", default=str(PKG / "evidence"))
    ic = sub.add_parser("install-check")
    ic.add_argument("--release", required=True)
    ic.add_argument("--evidence-out", default=str(PKG / "evidence"))
    a = ap.parse_args(argv)
    if a.cmd == "install-check":
        res = install_check(Path(a.release))
        write(Path(a.evidence_out) / "INSTALL.json", res)
        print(json.dumps({"result": res["result"], "steps": [(s["step"], s["exit"]) for s in res["steps"]]}))
        return 0 if res["result"] == "PASS" else 1
    if a.cmd == "build":
        res = build(Path(a.out), Path(a.evidence))
        write(Path(a.evidence) / "BUILD.json", {"schema": "PK_PACK_BUILD/1", "result": "PASS", **res})
        print(json.dumps(res))
        return 0
    trusted = {"kid": a.trusted_kid, "public_key_hex": a.trusted_key} if a.trusted_key else None
    res = verify(Path(a.release), trusted)
    write(Path(a.evidence_out) / "RELEASE_VERIFY.json", res)
    print(json.dumps({"result": res["result"], "failed": [c["check"] for c in res["checks"] if c["result"] == "FAIL"]}))
    return 0 if res["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
