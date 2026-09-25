"""Supply-chain tooling: build, manifest check, SBOM, provenance, sign, verify (MC-17, MC-22.018).

    python -m inv36_control_transport.tools.release build   --out dist
    python -m inv36_control_transport.tools.release sbom    --out dist
    python -m inv36_control_transport.tools.release provenance --out dist --builder ID
    python -m inv36_control_transport.tools.release sign    --out dist --key-file PEM --key-id ID
    python -m inv36_control_transport.tools.release verify  --out dist --pub HEX --key-id ID

``build`` builds the wheel and sdist from a clean ``git archive`` of HEAD (never
from a dirty tree) and checks their contents against ``release/manifest.json``.
``verify`` fails closed when any digest, signature, provenance subject or SBOM
is missing or wrong.  Production signing uses the CI OIDC-bound signer; the
``--key-file`` path exists for offline/air-gapped releases and tests.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import fnmatch
import hashlib
import importlib.metadata as md
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

PKG = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = PKG / "release" / "manifest.json"
RUNTIME_DEPS = ("cryptography", "cffi", "pycparser")
COPYLEFT = ("GPL", "AGPL", "LGPL", "MPL", "SSPL", "EUPL")


def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def version() -> str:
    return (PKG / "VERSION").read_text().strip()


def source_commit() -> str:
    try:
        return subprocess.run(["git", "-C", str(PKG), "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _distutils_workaround() -> dict[str, str]:
    """Debian-patched setuptools < 70 on Python 3.11 breaks bdist_wheel (``install_layout``); use stdlib distutils."""
    try:
        import setuptools
        major = int(setuptools.__version__.split(".")[0])
    except (ImportError, ValueError):
        return {}
    return {"SETUPTOOLS_USE_DISTUTILS": "stdlib"} if major < 70 and sys.version_info < (3, 12) else {}


def build(out: pathlib.Path) -> list[pathlib.Path]:
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        src = pathlib.Path(td) / "inv36_control_transport"
        src.mkdir()
        arch = subprocess.run(["git", "-C", str(PKG), "archive", "--format=tar", "HEAD"], capture_output=True,
                              check=True).stdout
        tar_path = pathlib.Path(td) / "src.tar"
        tar_path.write_bytes(arch)
        with tarfile.open(tar_path) as tf:
            tf.extractall(src, filter="data")
        env = {**os.environ, "SOURCE_DATE_EPOCH": subprocess.run(
            ["git", "-C", str(PKG), "log", "-1", "--format=%ct"], capture_output=True, text=True).stdout.strip() or "0"}
        env.update(_distutils_workaround())
        for hook in ("build_wheel", "build_sdist"):
            proc = subprocess.run([sys.executable, "-c",
                                   f"import sys; from setuptools import build_meta as b; b.{hook}(sys.argv[1])",
                                   str(out.resolve())], cwd=src, env=env, capture_output=True, text=True)
            if proc.returncode != 0:
                raise SystemExit(f"{hook} failed: {proc.stderr[-2000:]}")
    arts = sorted(p for p in out.iterdir() if p.suffix in (".whl", ".gz"))
    check_manifest(arts)
    return arts


def _members(p: pathlib.Path) -> list[str]:
    if p.suffix == ".whl":
        with zipfile.ZipFile(p) as z:
            return z.namelist()
    with tarfile.open(p) as t:
        return [m.name.split("/", 1)[1] if "/" in m.name else m.name for m in t.getmembers() if m.isfile()]


def check_manifest(arts: list[pathlib.Path]) -> None:
    man = json.loads(MANIFEST.read_text())
    for a in arts:
        kind = "wheel" if a.suffix == ".whl" else "sdist"
        names = _members(a)
        req = man[kind]["required"]
        forbid = man["forbidden"]
        missing = [r for r in req if not any(fnmatch.fnmatch(n, r) for n in names)]
        bad = [n for n in names if any(fnmatch.fnmatch(n, f) for f in forbid)]
        if missing or bad:
            raise SystemExit(f"manifest check failed for {a.name}: missing={missing} forbidden={bad[:10]}")


def _license(dist: str) -> str:
    try:
        meta = md.metadata(dist)
    except md.PackageNotFoundError:
        return "UNKNOWN"
    lic = meta["License-Expression"] or meta["License"] or ""
    if not lic:
        lic = "; ".join(c.split("::")[-1].strip() for c in (meta.get_all("Classifier") or []) if "License" in c)
    return lic or "UNKNOWN"


def _serial(arts: list[pathlib.Path]) -> str:
    """Deterministic UUID derived from the artifact digests and version."""
    u = hashlib.sha256(("".join(sha256(a) for a in arts) + version()).encode()).hexdigest()[:32]
    return f"urn:uuid:{u[:8]}-{u[8:12]}-{u[12:16]}-{u[16:20]}-{u[20:32]}"


def sbom(out: pathlib.Path) -> pathlib.Path:
    arts = sorted(p for p in out.iterdir() if p.suffix in (".whl", ".gz"))
    comps: list[dict] = []
    for dep in RUNTIME_DEPS:
        try:
            v = md.version(dep)
        except md.PackageNotFoundError:
            v = "UNKNOWN"
        comps.append({"type": "library", "bom-ref": f"pkg:pypi/{dep}@{v}", "name": dep, "version": v,
                      "purl": f"pkg:pypi/{dep}@{v}", "licenses": [{"license": {"name": _license(dep)}}],
                      "scope": "required"})
    doc = {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "serialNumber": _serial(arts),
        "metadata": {"timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
                     "tools": [{"name": "inv36 tools/release.py", "version": version()}],
                     "component": {"type": "library", "name": "inv36-control-transport", "version": version(),
                                   "bom-ref": f"pkg:pypi/inv36-control-transport@{version()}",
                                   "licenses": [{"license": {"name": _own_license()}}],
                                   "hashes": [{"alg": "SHA-256", "content": sha256(a)} for a in arts],
                                   "properties": [{"name": "source_commit", "value": source_commit()},
                                                  {"name": "python", "value": platform.python_version()}]}},
        "components": comps,
        "dependencies": [{"ref": f"pkg:pypi/inv36-control-transport@{version()}",
                          "dependsOn": [c["bom-ref"] for c in comps if c["name"] == "cryptography"]},
                         {"ref": comps[0]["bom-ref"], "dependsOn": [comps[1]["bom-ref"]]},
                         {"ref": comps[1]["bom-ref"], "dependsOn": [comps[2]["bom-ref"]]}],
    }
    p = out / "sbom.cdx.json"
    p.write_text(json.dumps(doc, indent=1, sort_keys=True))
    return p


def _own_license() -> str:
    lic = PKG / "LICENSE"
    return "SEE LICENSE" if lic.exists() else "NOASSERTION (license decision pending - MC-22)"


def license_findings() -> list[str]:
    """Flag copyleft/unknown licenses among runtime deps (MC-22.014/.016)."""
    bad = []
    for dep in RUNTIME_DEPS:
        lic = _license(dep)
        if lic == "UNKNOWN" or any(c in lic.upper() for c in COPYLEFT):
            bad.append(f"{dep}: {lic}")
    return bad


def provenance(out: pathlib.Path, builder: str) -> pathlib.Path:
    arts = sorted(p for p in out.iterdir() if p.suffix in (".whl", ".gz"))
    stmt = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": a.name, "digest": {"sha256": sha256(a)}} for a in arts],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {"buildType": "https://inv36.invalid/build/pip-wheel-sdist/v1",
                                "externalParameters": {"source": "git archive HEAD", "version": version()},
                                "resolvedDependencies": [{"uri": "git+repository", "digest": {"gitCommit": source_commit()}}]},
            "runDetails": {"builder": {"id": builder},
                           "metadata": {"invocationId": os.environ.get("GITHUB_RUN_ID", "local"),
                                        "startedOn": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")}},
        },
    }
    p = out / "provenance.intoto.json"
    p.write_text(json.dumps(stmt, indent=1, sort_keys=True))
    return p


def _digest_list(out: pathlib.Path) -> bytes:
    files = sorted(p for p in out.iterdir() if p.suffix in (".whl", ".gz") or p.name in ("sbom.cdx.json",
                                                                                      "provenance.intoto.json"))
    return "".join(f"{sha256(p)}  {p.name}\n" for p in files).encode()


def sign(out: pathlib.Path, key_file: pathlib.Path, key_id: str) -> pathlib.Path:
    priv = serialization.load_pem_private_key(key_file.read_bytes(), password=None)
    if not isinstance(priv, Ed25519PrivateKey):
        raise SystemExit("release signing key must be Ed25519")
    sums = _digest_list(out)
    (out / "SHA256SUMS").write_bytes(sums)
    sig = {"key_id": key_id, "alg": "ed25519", "sig": priv.sign(b"INV36-RELEASE/1\x00" + sums).hex()}
    p = out / "SHA256SUMS.sig.json"
    p.write_text(json.dumps(sig, indent=1))
    return p


def verify(out: pathlib.Path, pub_hex: str, key_id: str) -> list[str]:
    errs = []
    for need in ("SHA256SUMS", "SHA256SUMS.sig.json", "sbom.cdx.json", "provenance.intoto.json"):
        if not (out / need).exists():
            errs.append(f"missing {need}")
    if errs:
        return errs
    sums = (out / "SHA256SUMS").read_bytes()
    if sums != _digest_list(out):
        errs.append("artifact digests differ from SHA256SUMS")
    sig = json.loads((out / "SHA256SUMS.sig.json").read_text())
    if sig.get("key_id") != key_id:
        errs.append("signature key id not trusted")
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex)).verify(bytes.fromhex(sig["sig"]),
                                                                            b"INV36-RELEASE/1\x00" + sums)
    except Exception:  # noqa: BLE001
        errs.append("signature invalid")
    prov = json.loads((out / "provenance.intoto.json").read_text())
    subj = {s["name"]: s["digest"]["sha256"] for s in prov["subject"]}
    for a in sorted(p for p in out.iterdir() if p.suffix in (".whl", ".gz")):
        if subj.get(a.name) != sha256(a):
            errs.append(f"provenance subject mismatch for {a.name}")
    return errs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "sbom", "provenance", "sign", "verify", "licenses", "all-local"])
    ap.add_argument("--out", default="dist")
    ap.add_argument("--builder", default="local://" + platform.node())
    ap.add_argument("--key-file")
    ap.add_argument("--key-id", default="release-local")
    ap.add_argument("--pub")
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out)
    if a.cmd == "build":
        if out.exists():
            shutil.rmtree(out)
        print(json.dumps({a.name: sha256(a) for a in build(out)}, indent=1))
    elif a.cmd == "sbom":
        print(sbom(out))
    elif a.cmd == "provenance":
        print(provenance(out, a.builder))
    elif a.cmd == "sign":
        print(sign(out, pathlib.Path(a.key_file), a.key_id))
    elif a.cmd == "verify":
        errs = verify(out, a.pub, a.key_id)
        print(json.dumps({"ok": not errs, "errors": errs}))
        return 1 if errs else 0
    elif a.cmd == "licenses":
        bad = license_findings()
        print(json.dumps({"ok": not bad, "flagged": bad}))
        return 1 if bad else 0
    elif a.cmd == "all-local":
        if out.exists():
            shutil.rmtree(out)
        build(out)
        sbom(out)
        provenance(out, a.builder)
        key = Ed25519PrivateKey.generate()
        kf = out / ".ephemeral-test-signing-key.pem"
        kf.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                         serialization.NoEncryption()))
        sign(out, kf, "ephemeral-test")
        kf.unlink()
        pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
        errs = verify(out, pub, "ephemeral-test")
        print(json.dumps({"ok": not errs, "errors": errs, "pub": pub}))
        return 1 if errs else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
