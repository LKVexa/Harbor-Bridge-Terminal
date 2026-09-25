"""Deterministic release builder (MC-09 / MC-11 / MC-30): wheel, sdist, SBOM, provenance,
SHA256SUMS and an HMAC signature, from the git-tracked files of one source revision.

    python tools/build_release.py --out DIR [--source-revision REV] [--version V] [--root TREE]

Deterministic: fixed timestamps (the commit time, or SOURCE_DATE_EPOCH), sorted entries,
fixed permissions; building twice yields identical digests (checked by tools/ci.py).
The signature key is generated per build (ephemeral) — it proves bundle integrity to the
holder of the build log only; a managed signing identity is a recorded release blocker."""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import gzip
import hashlib
import hmac
import io
import json
import os
import pathlib
import secrets
import subprocess
import sys
import tarfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = "pln05_elasticity_plane"
DIST = "pln05_elasticity_plane"
NAME = "pln05-elasticity-plane"
DATA_DIRS = ("schemas/", "config/", "security/")
RUNTIME_EXT = (".py",)


def git(root, *args) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout.strip()


def tracked(root) -> list[str]:
    return sorted(git(root, "ls-files").splitlines())


def wheel_members(files: list[str]) -> list[str]:
    keep = []
    for f in files:
        top = f.split("/")[0]
        if "/" not in f and (f.endswith(RUNTIME_EXT) or f in ("VERSION", "NOTICE", "LICENSE", "LICENSE-PENDING.md")):
            keep.append(f)
        elif f.startswith(DATA_DIRS) and f.endswith((".json", ".md")):
            keep.append(f)
    return keep


def _zinfo(name, ts):
    zi = zipfile.ZipInfo(name, date_time=ts)
    zi.external_attr = 0o644 << 16
    zi.compress_type = zipfile.ZIP_DEFLATED
    return zi


def build_wheel(root, files, version, out, ts_epoch, build_info) -> pathlib.Path:
    ts = dt.datetime.fromtimestamp(max(ts_epoch, 315532800), dt.timezone.utc).timetuple()[:6]
    whl = out / f"{DIST}-{version}-py3-none-any.whl"
    di = f"{DIST}-{version}.dist-info"
    record = []
    entries = []
    for f in wheel_members(files):
        entries.append((f"{PKG}/{f}", (root / f).read_bytes()))
    entries.append((f"{PKG}/build_info.json", json.dumps(build_info, sort_keys=True, indent=1).encode()))
    lic = "LicenseRef-PLN05-Owner-Pending"
    appr = root / "security" / "approved-versions.json"
    if appr.exists():
        lic = json.loads(appr.read_text())["license"]
    meta = (f"Metadata-Version: 2.1\nName: {NAME}\nVersion: {version}\nSummary: PLN-05 elasticity plane\n"
            f"License: {lic}\nRequires-Python: >=3.10,<3.14\nProvides-Extra: framework\n"
            f"Requires-Dist: pk_core<5.0,>=4.0; extra == \"framework\"\n")
    entries.append((f"{di}/METADATA", meta.encode()))
    entries.append((f"{di}/WHEEL", b"Wheel-Version: 1.0\nGenerator: pln05-build_release\nRoot-Is-Purelib: true\nTag: py3-none-any\n"))
    entries.append((f"{di}/entry_points.txt", b"[console_scripts]\npln05 = pln05_elasticity_plane.cli:main\n"))
    entries.sort()
    for name, data in entries:
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
        record.append(f"{name},sha256={digest},{len(data)}")
    record.append(f"{di}/RECORD,,")
    with zipfile.ZipFile(whl, "w") as z:
        for name, data in entries:
            z.writestr(_zinfo(name, ts), data)
        z.writestr(_zinfo(f"{di}/RECORD", ts), ("\n".join(record) + "\n").encode())
    return whl


def build_sdist(root, files, version, out, ts_epoch) -> pathlib.Path:
    base = f"{NAME}-{version}"
    path = out / f"{base}.tar.gz"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for f in files:
            data = (root / f).read_bytes()
            ti = tarfile.TarInfo(f"{base}/{PKG}/{f}")
            ti.size, ti.mtime, ti.mode, ti.uid, ti.gid, ti.uname, ti.gname = len(data), ts_epoch, 0o644, 0, 0, "", ""
            tar.addfile(ti, io.BytesIO(data))
    with open(path, "wb") as fh:
        with gzip.GzipFile(filename="", mode="wb", fileobj=fh, mtime=0) as gz:
            gz.write(buf.getvalue())
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--source-revision")
    ap.add_argument("--version")
    ap.add_argument("--no-sign", action="store_true")
    a = ap.parse_args(argv)
    root = pathlib.Path(a.root)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rev = a.source_revision or git(root, "rev-parse", "HEAD")
    version = a.version or (root / "VERSION").read_text().strip()
    ts_epoch = int(os.environ.get("SOURCE_DATE_EPOCH") or git(root, "log", "-1", "--format=%ct", rev))
    files = tracked(root)
    build_info = {"package": NAME, "version": version, "source_revision": rev,
                  "build_id": f"{version}+g{rev[:12]}", "source_date_epoch": ts_epoch}
    whl = build_wheel(root, files, version, out, ts_epoch, build_info)
    sd = build_sdist(root, files, version, out, ts_epoch)
    subjects = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (whl, sd)}
    when = dt.datetime.fromtimestamp(ts_epoch, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = {"wheel": whl.name, "sdist": sd.name, "subjects": subjects, "build_info": build_info}
    if (root / "supplychain.py").exists():
        sys.path.insert(0, str(root.parent))
        from pln05_elasticity_plane import supplychain
        (out / "sbom.cdx.json").write_text(json.dumps(supplychain.sbom(NAME, version, subjects, when), indent=1, sort_keys=True))
        (out / "provenance.intoto.json").write_text(json.dumps(supplychain.provenance(
            subjects, source_revision=rev, builder="pln05/tools/build_release.py (local, unmanaged)",
            build_time=when, params={"version": version, "files": len(files)}), indent=1, sort_keys=True))
    sums = "".join(f"{hashlib.sha256((out / n).read_bytes()).hexdigest()}  {n}\n"
                   for n in sorted(p.name for p in out.iterdir() if p.is_file() and p.name not in ("SHA256SUMS", "SHA256SUMS.sig.json")))
    (out / "SHA256SUMS").write_text(sums)
    if not a.no_sign:
        key = secrets.token_bytes(32)
        sig = hmac.new(key, sums.encode(), hashlib.sha256).hexdigest()
        (out / "SHA256SUMS.sig.json").write_text(json.dumps({
            "alg": "HMAC-SHA256", "kid": "ephemeral-" + hashlib.sha256(key).hexdigest()[:16], "signature": sig,
            "note": "ephemeral per-build key; not a managed signing identity (release blocker MC-11/MC-33)"}, indent=1))
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
