#!/usr/bin/env python3
"""Release gate, deterministic packaging, provenance, signing and verification (M08, section 11).

  python tools/release.py preflight                      # closure status of every release gate
  python tools/release.py package --out DIST [--candidate]
  python tools/release.py sign --provenance FILE --key PRIVATE.pem   # key must live outside the repo
  python tools/release.py verify --archive ZIP --provenance FILE --sig FILE --pubkey PUBLIC.pem

`package` without --candidate and `sign` refuse to run unless every preflight gate passes, so a
failed full-verifier build can never be signed. Signatures are Ed25519 over the provenance
statement (OpenSSL 3 CLI); the statement binds the archive digest to the manifest, SBOM,
VERIFY/2 evidence and toolchain-lock digests.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
PY = [sys.executable, "-B"]
PLACEHOLDER = re.compile(r"(?i)\b(TODO|TBD|PLACEHOLDER|CHANGEME|example\.(com|org)|<owner>|<email>)\b")
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def run(*args) -> tuple[bool, str]:
    cp = subprocess.run([*PY, *map(str, args)], cwd=PKG, capture_output=True, text=True, timeout=600)
    out = (cp.stdout + cp.stderr).strip().splitlines()
    return cp.returncode == 0, (out[-1] if out else "")


def _doc_gate(name: str) -> tuple[bool, str]:
    p = PKG / name
    if not p.is_file():
        return False, f"{name} absent (owner decision required)"
    if PLACEHOLDER.search(p.read_text("utf-8", "replace")):
        return False, f"{name} contains placeholder text"
    return True, f"{name} present"


def gates() -> list[tuple[str, str, bool, str]]:
    g = []
    ok, msg = run("tools/check_translation.py"); g.append(("11.1", "semantic round trip", ok, msg))
    cp = subprocess.run([*PY, "tools/check_translation.py", "--falsify"], cwd=PKG, capture_output=True, text=True, timeout=600)
    caught, missed = cp.stdout.count("falsifier CAUGHT:"), cp.stdout.count("falsifier MISSED:")
    g.append(("11.1", "falsifiers", cp.returncode == 0 and caught == 9 and not missed, f"{caught} caught, {missed} missed"))
    ok, msg = run("tools/manifest.py"); g.append(("11.1", "MANIFEST.sha256", ok, msg))
    ok, msg = run("tools/schema_check.py"); g.append(("M09", "JSON Schemas", ok, msg))
    ok, msg = run("tools/toolchain_trust.py", "--check-lock")
    lock = json.loads((PKG / "toolchains/LOCK.json").read_text("utf-8"))
    pinned = all(tc["status"] == "APPROVED" for tc in lock["toolchains"])
    g.append(("M04", "toolchain pins APPROVED", ok and pinned, msg))
    ok, msg = run("tools/evidence_check.py"); g.append(("M02", "genuine VERIFY/2 evidence", ok, msg))
    ok, msg = run("tools/sbom.py", "--check")
    g.append(("M07", "release SBOM", ok and "DRAFT" not in msg, msg))
    ok, msg = _doc_gate("LICENSE"); g.append(("M05", "owner-approved LICENSE", ok, msg))
    ok, msg = _doc_gate("SECURITY.md"); g.append(("M06", "SECURITY.md with private channel", ok, msg))
    pub = PKG / "provenance/release-signing-public.pem"
    g.append(("M08", "published signing public key", pub.is_file(), "present" if pub.is_file() else "no owner signing identity published"))
    return g


def preflight(quiet=False) -> bool:
    rows = gates()
    if not quiet:
        for ref, name, ok, msg in rows:
            print(f"{'PASS' if ok else 'OPEN'}  {ref:<5} {name:<34} {msg}")
    allok = all(r[2] for r in rows)
    if not quiet:
        print("RELEASE-GRADE: YES" if allok else f"RELEASE-GRADE: NO ({sum(not r[2] for r in rows)} open gate(s))")
    return allok


def release_files() -> list[Path]:
    sys.path.insert(0, str(PKG / "tools"))
    from manifest import release_files as rf  # same membership as the manifest, plus the manifest itself
    return sorted([*rf(), PKG / "MANIFEST.sha256"], key=lambda p: p.relative_to(PKG).as_posix())


def package(out: Path, candidate: bool) -> int:
    if not candidate and not preflight():
        print("FAIL: release-grade packaging refused; use --candidate for an explicitly unsigned candidate")
        return 1
    ok, msg = run("tools/manifest.py")
    if not ok:
        print("FAIL:", msg)
        return 1
    version = (PKG / "VERSION").read_text().strip()
    name = f"iOS735_LCTL_v{version}" + ("-candidate" if candidate else "")
    out.mkdir(parents=True, exist_ok=True)
    archive = out / f"{name}.zip"
    fd, tmp = tempfile.mkstemp(dir=out, suffix=".tmp")
    os.close(fd)
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in release_files():
            rel = f"iOS735_LCTL_v{version}/{p.relative_to(PKG).as_posix()}"
            zi = zipfile.ZipInfo(rel, FIXED_ZIP_TIME)
            zi.external_attr = ((0o755 if p.suffix == ".py" and p.parent.name == "tools" else 0o644) | stat.S_IFREG) << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.create_system = 3
            zf.writestr(zi, p.read_bytes())
    os.replace(tmp, archive)
    digest = sha256(archive)
    (out / f"{name}.zip.sha256").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    ev = PKG / "evidence/VERIFY.json"
    sb = PKG / "sbom" / f"iOS735_LCTL-{version}.spdx.json"
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PKG, capture_output=True, text=True)
    statement = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": archive.name, "digest": {"sha256": digest}}],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": "https://ios735-lctl.invalid/release/v1",
                "externalParameters": {"version": version, "candidate": candidate,
                                       "trigger": os.environ.get("GITHUB_EVENT_NAME", "manual")},
                "internalParameters": {"python": sys.version.split()[0],
                                       "source_identity": "git commit" if head.returncode == 0 else "MANIFEST.sha256 (no git checkout)"},
                "resolvedDependencies": [
                    *([{"name": "source", "digest": {"gitCommit": head.stdout.strip()}}] if head.returncode == 0 else []),
                    {"name": "MANIFEST.sha256", "digest": {"sha256": sha256(PKG / "MANIFEST.sha256")}},
                    {"name": "toolchains/LOCK.json", "digest": {"sha256": sha256(PKG / "toolchains/LOCK.json")}},
                    {"name": "evidence/VERIFY.json", "digest": {"sha256": sha256(ev)},
                     "annotations": {"schema": json.loads(ev.read_text("utf-8")).get("schema")}},
                    *([{"name": sb.relative_to(PKG).as_posix(), "digest": {"sha256": sha256(sb)}}] if sb.is_file() else []),
                    *[{"name": f"jar:{k}", "digest": {"sha256": v}} for k, v in _jar_hashes(ev).items()],
                ],
            },
            "runDetails": {"builder": {"id": os.environ.get("RELEASE_BUILDER_ID", "manual-operator")},
                           "metadata": {"invocationId": os.environ.get("GITHUB_RUN_ID", "local")}},
        },
    }
    prov = out / f"{name}.provenance.json"
    prov.write_text(json.dumps(statement, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {archive.name} sha256={digest}\nwrote {prov.name}" + ("  (CANDIDATE: not signable)" if candidate else ""))
    return 0


def _jar_hashes(ev: Path) -> dict:
    d = json.loads(ev.read_text("utf-8"))
    ti = d.get("toolchain_identity") or {}
    return {k: ti[f"{k}_jar_sha256"] for k in ("lctl161", "lctl160") if f"{k}_jar_sha256" in ti}


def sign(provenance: Path, key: Path) -> int:
    if key.resolve().is_relative_to(PKG.resolve()):
        print("FAIL: private signing key must not be inside the repository")
        return 1
    st = json.loads(provenance.read_text("utf-8"))
    if st["predicate"]["buildDefinition"]["externalParameters"].get("candidate"):
        print("FAIL: candidate provenance cannot be signed")
        return 1
    if not preflight():
        print("FAIL: signing refused; release gates are open")
        return 1
    archive = provenance.parent / st["subject"][0]["name"]
    if not archive.is_file() or sha256(archive) != st["subject"][0]["digest"]["sha256"]:
        print("FAIL: provenance subject does not match the archive on disk")
        return 1
    sig = provenance.with_suffix(".sig")
    cp = subprocess.run(["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(key), "-in", str(provenance), "-out", str(sig)],
                        capture_output=True, text=True)
    if cp.returncode:
        print("FAIL: openssl signing failed:", cp.stderr.strip()[:200])
        return 1
    print(f"wrote {sig.name}")
    return 0


def verify(archive: Path, provenance: Path, sig: Path, pubkey: Path, extract_check=True) -> int:
    cp = subprocess.run(["openssl", "pkeyutl", "-verify", "-rawin", "-pubin", "-inkey", str(pubkey),
                         "-in", str(provenance), "-sigfile", str(sig)], capture_output=True, text=True)
    if cp.returncode:
        print("FAIL: signature does not verify with the published public key — do not use this artifact")
        return 1
    st = json.loads(provenance.read_text("utf-8"))
    if st["subject"][0]["digest"]["sha256"] != sha256(archive) or st["subject"][0]["name"] != archive.name:
        print("FAIL: archive digest/name differs from the signed provenance subject — do not use this artifact")
        return 1
    if extract_check:
        with tempfile.TemporaryDirectory() as td:
            with zipfile.ZipFile(archive) as zf:
                for n in zf.namelist():
                    if n.startswith("/") or ".." in Path(n).parts:
                        print("FAIL: unsafe path in archive")
                        return 1
                zf.extractall(td)
            root = next(Path(td).iterdir())
            man = subprocess.run([*PY, str(root / "tools/manifest.py")], capture_output=True, text=True)
            if man.returncode:
                print("FAIL: extracted MANIFEST.sha256 does not verify")
                return 1
            want = [d["digest"]["sha256"] for d in st["predicate"]["buildDefinition"]["resolvedDependencies"] if d["name"] == "MANIFEST.sha256"]
            if want and sha256(root / "MANIFEST.sha256") != want[0]:
                print("FAIL: MANIFEST.sha256 differs from the signed provenance")
                return 1
    print("PASS: signature, provenance subject, and extracted manifest all verify")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("preflight")
    p = sub.add_parser("package"); p.add_argument("--out", type=Path, required=True); p.add_argument("--candidate", action="store_true")
    s = sub.add_parser("sign"); s.add_argument("--provenance", type=Path, required=True); s.add_argument("--key", type=Path, required=True)
    v = sub.add_parser("verify")
    for k in ("archive", "provenance", "sig", "pubkey"):
        v.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "preflight":
        return 0 if preflight() else 1
    if a.cmd == "package":
        return package(a.out, a.candidate)
    if a.cmd == "sign":
        return sign(a.provenance, a.key)
    return verify(a.archive, a.provenance, a.sig, a.pubkey)


if __name__ == "__main__":
    sys.exit(main())
