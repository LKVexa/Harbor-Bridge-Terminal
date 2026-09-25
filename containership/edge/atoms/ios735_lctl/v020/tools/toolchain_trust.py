#!/usr/bin/env python3
"""Authenticate the external LCTL toolchains against the owner-approved lock (M01/M04).

Nothing in this module ever executes a toolchain JAR. It resolves the toolchain roots,
validates the trust lock, hashes each JAR and compares it with the pinned digest, and checks
the Java runtime policy. Only after `authenticate()` returns may a caller run `java -jar`.

  python tools/toolchain_trust.py --lctl161 PATH --lctl160 PATH [--lock toolchains/LOCK.json] [--json OUT]

Stable exit codes (also used by tools/verify.py):
  0  trusted            10 lock missing/malformed     11 unsupported lock schema
  12 toolchain missing  13 untrusted (unpinned/mismatch/wrong version)
  14 unsupported Java   15 unsafe or failed extraction 16 access/authentication failure
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

PKG = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = PKG / "toolchains" / "LOCK.json"
LOCK_SCHEMA = "IOS735_LCTL/TOOLCHAIN_LOCK/1"
ROLES = {
    "lctl161": {"env": "LCTL161", "pattern": "LCTL_1.6.1_RC1_*", "jar": "runtime/bin/lctl-hyperfederated.jar"},
    "lctl160": {"env": "LCTL160", "pattern": "LCTL_1.6.0_RC1_*", "jar": "runtime/bin/lctl-runtime.jar"},
}
HEX64 = re.compile(r"[0-9a-f]{64}")
EXIT = {"ok": 0, "lock": 10, "schema": 11, "missing": 12, "untrusted": 13, "java": 14, "extract": 15, "access": 16}
SECRET_PAT = re.compile(r"(?i)(token|password|secret|signature|sig|x-amz-[a-z-]+|authorization)=([^&\s]+)|(bearer\s+)\S+")


class TrustError(Exception):
    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind
        self.code = EXIT[kind]


def redact(text: str) -> str:
    """Remove credentials/signed-URL parameters from anything headed for a log."""
    return SECRET_PAT.sub(lambda m: (m.group(3) + "***") if m.group(3) else f"{m.group(1)}=***", text)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_rel(p: str) -> bool:
    pp = PurePosixPath(p)
    return bool(p) and not pp.is_absolute() and "\\" not in p and ".." not in pp.parts and ":" not in p


# ---------------------------------------------------------------- lock handling
def load_lock(path: Path) -> dict:
    if not path.is_file():
        raise TrustError("lock", f"toolchain lock not found: {path}")
    try:
        raw = path.read_text(encoding="utf-8")
        lock = json.loads(raw, object_pairs_hook=_no_dupes)
    except (OSError, ValueError) as exc:
        raise TrustError("lock", f"toolchain lock is malformed: {exc}") from exc
    validate_lock(lock)
    lock["_digest"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return lock


def _no_dupes(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError(f"duplicate JSON key(s): {sorted(k for k in set(keys) if keys.count(k) > 1)}")
    return dict(pairs)


def validate_lock(lock) -> None:
    if not isinstance(lock, dict):
        raise TrustError("lock", "lock must be a JSON object")
    if lock.get("schema") != LOCK_SCHEMA:
        raise TrustError("schema", f"unsupported lock schema {lock.get('schema')!r}; expected {LOCK_SCHEMA}")
    for key in ("lock_version", "java_policy", "toolchains"):
        if key not in lock:
            raise TrustError("lock", f"lock missing required field {key!r}")
    jp = lock["java_policy"]
    if not isinstance(jp, dict) or not isinstance(jp.get("min_major"), int) or jp["min_major"] < 21:
        raise TrustError("lock", "java_policy.min_major must be an integer >= 21")
    tcs = lock["toolchains"]
    if not isinstance(tcs, list):
        raise TrustError("lock", "toolchains must be an array")
    seen = set()
    for tc in tcs:
        if not isinstance(tc, dict):
            raise TrustError("lock", "toolchain entry must be an object")
        role = tc.get("role")
        if role not in ROLES:
            raise TrustError("lock", f"unknown toolchain role {role!r}")
        if role in seen:
            raise TrustError("lock", f"duplicate toolchain entry for role {role!r}")
        seen.add(role)
        for key in ("name", "version", "publisher", "jar_path", "status"):
            if not isinstance(tc.get(key), str) or not tc[key]:
                raise TrustError("lock", f"{role}: field {key!r} must be a non-empty string")
        if tc["version"].lower() in {"latest", "*", "any"} or "*" in tc["version"]:
            raise TrustError("lock", f"{role}: floating version identifiers are not permitted")
        if not _safe_rel(tc["jar_path"]) or tc["jar_path"] != ROLES[role]["jar"]:
            raise TrustError("lock", f"{role}: jar_path must be exactly {ROLES[role]['jar']!r}")
        if tc["status"] not in {"APPROVED", "PENDING_OWNER_APPROVAL", "REVOKED"}:
            raise TrustError("lock", f"{role}: unknown status {tc['status']!r}")
        digest = tc.get("sha256")
        if tc["status"] == "APPROVED":
            if not isinstance(digest, str) or not HEX64.fullmatch(digest):
                raise TrustError("lock", f"{role}: APPROVED entry needs a full lowercase sha256")
            appr = tc.get("approval")
            if not isinstance(appr, dict) or not appr.get("approved_by") or not appr.get("approved_on"):
                raise TrustError("lock", f"{role}: APPROVED entry needs approval.approved_by/approved_on")
        elif digest is not None and not (isinstance(digest, str) and HEX64.fullmatch(digest)):
            raise TrustError("lock", f"{role}: malformed sha256")
        if "size" in tc and tc["size"] is not None and (not isinstance(tc["size"], int) or tc["size"] <= 0):
            raise TrustError("lock", f"{role}: size must be a positive integer")
        blob = json.dumps(tc).lower()
        if any(s in blob for s in ("password", "bearer ", "private key", "token=")):
            raise TrustError("lock", f"{role}: lock entries must not contain credentials")
    missing = set(ROLES) - seen
    if missing:
        raise TrustError("lock", f"lock missing toolchain role(s): {sorted(missing)}")


# ---------------------------------------------------------------- resolution
def find_root(explicit: Path | None, role: str) -> Path:
    spec = ROLES[role]
    if explicit is not None:
        root = Path(explicit).expanduser().resolve()
    elif os.environ.get(spec["env"]):
        root = Path(os.environ[spec["env"]]).expanduser().resolve()
    else:
        hits = sorted(glob.glob(str(PKG.parent / spec["pattern"])) + glob.glob(str(PKG.parent / "*" / spec["pattern"])))
        if not hits:
            raise TrustError("missing", f"cannot find {role} toolchain; pass --{role} or set {spec['env']}")
        root = Path(hits[0]).resolve()
    if not root.is_dir():
        raise TrustError("missing", f"{role} toolchain root is not a directory: {root}")
    return root


def java_identity(java_bin: str | None = None) -> dict:
    java_bin = java_bin or shutil.which("java")
    if not java_bin:
        raise TrustError("java", "Java is not available on PATH (Java 21+ required)")
    env = {**os.environ, "JAVA_TOOL_OPTIONS": "", "_JAVA_OPTIONS": ""}
    try:
        cp = subprocess.run([java_bin, "-XshowSettings:properties", "-version"], capture_output=True, text=True,
                            timeout=20, check=False, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TrustError("java", f"cannot query Java version: {exc}") from exc
    lines = [l for l in (cp.stdout + cp.stderr).splitlines() if not l.startswith("Picked up ")]
    first = next((l for l in lines if " version " in l and '"' in l), "")
    m = re.search(r'version\s+"([0-9]+)(?:\.([0-9]+))?', first)
    if not m:
        raise TrustError("java", f"cannot parse Java version from: {first!r}")
    major = int(m.group(1))
    if major == 1 and m.group(2):
        major = int(m.group(2))
    props = {}
    for l in lines:
        mm = re.match(r"\s+(java\.vendor|java\.runtime\.version|os\.name|os\.arch) = (.*)", l)
        if mm:
            props[mm.group(1)] = mm.group(2).strip()
    return {"major": major, "version_line": first.strip(), "path": str(Path(java_bin).resolve()), **props}


@dataclass
class Trusted:
    roots: dict
    jars: dict
    hashes: dict
    java: dict
    lock_version: str
    lock_digest: str
    notes: list = field(default_factory=list)

    def evidence(self) -> dict:
        return {
            "lock_schema": LOCK_SCHEMA,
            "lock_version": self.lock_version,
            "lock_sha256": self.lock_digest,
            "java_path": self.java.get("path", ""),
            "java_vendor": self.java.get("java.vendor", ""),
            "java_runtime_version": self.java.get("java.runtime.version", ""),
            "os": self.java.get("os.name", ""),
            "arch": self.java.get("os.arch", ""),
        }


def authenticate(lctl161: Path | None, lctl160: Path | None, lock_path: Path = DEFAULT_LOCK,
                 java_bin: str | None = None) -> Trusted:
    lock = load_lock(lock_path)
    entries = {tc["role"]: tc for tc in lock["toolchains"]}
    roots, jars, hashes = {}, {}, {}
    for role, explicit in (("lctl161", lctl161), ("lctl160", lctl160)):
        tc = entries[role]
        root = find_root(explicit, role)
        jar = root / tc["jar_path"]
        if jar.is_symlink() or not jar.is_file():
            raise TrustError("missing", f"{role}: required JAR missing or not a regular file: {jar}")
        if tc["status"] != "APPROVED":
            raise TrustError("untrusted", f"{role}: lock entry status is {tc['status']}; no owner-approved pin, refusing to execute")
        if tc.get("size") and jar.stat().st_size != tc["size"]:
            raise TrustError("untrusted", f"{role}: size {jar.stat().st_size} != pinned {tc['size']}")
        observed = sha256_file(jar)
        if observed != tc["sha256"]:
            raise TrustError("untrusted", f"{role}: JAR sha256 {observed} does not match pinned {tc['sha256']}")
        marker = tc.get("version_marker")
        if marker:
            mfile = root / marker["file"]
            if not _safe_rel(marker["file"]) or not mfile.is_file() or marker["contains"] not in mfile.read_text("utf-8", "replace"):
                raise TrustError("untrusted", f"{role}: version marker {marker['file']} does not declare {tc['version']}")
        roots[role], jars[role], hashes[role] = root, jar, observed
    jid = java_identity(java_bin)
    jp = lock["java_policy"]
    if jid["major"] < jp["min_major"]:
        raise TrustError("java", f"Java {jp['min_major']}+ required; found {jid['version_line']}")
    if jp.get("max_major") and jid["major"] > jp["max_major"]:
        raise TrustError("java", f"Java major {jid['major']} above approved max {jp['max_major']}")
    vendors = jp.get("allowed_vendors") or []
    if vendors and not any(v.lower() in jid.get("java.vendor", "").lower() for v in vendors):
        raise TrustError("java", f"Java vendor {jid.get('java.vendor')!r} not in approved list {vendors}")
    return Trusted(roots, jars, hashes, jid, str(lock["lock_version"]), lock["_digest"])


# ---------------------------------------------------------------- safe provisioning from an archive
def safe_extract(archive: Path, dest: Path, expected_sha256: str | None = None) -> Path:
    """Extract an owner-supplied toolchain archive atomically, rejecting traversal/links/devices.

    Extraction goes into a sibling temp dir and is renamed into place only when complete, so an
    interrupted run can never leave a partial root that looks valid. Concurrent callers race on
    the final rename; the loser discards its copy.
    """
    if expected_sha256 is not None and sha256_file(archive) != expected_sha256:
        raise TrustError("untrusted", f"archive digest mismatch: {archive.name}")
    dest = dest.resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=dest.name + ".partial.", dir=dest.parent))
    try:
        if zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive) as zf:
                for info in zf.infolist():
                    mode = (info.external_attr >> 16) & 0o170000
                    if not _safe_rel(info.filename.rstrip("/")) or mode in (stat.S_IFLNK, stat.S_IFCHR, stat.S_IFBLK, stat.S_IFIFO):
                        raise TrustError("extract", f"unsafe archive member: {info.filename!r}")
                zf.extractall(tmp)
        elif tarfile.is_tarfile(archive):
            with tarfile.open(archive) as tf:
                for m in tf.getmembers():
                    if not _safe_rel(m.name.rstrip("/")) or not (m.isfile() or m.isdir()):
                        raise TrustError("extract", f"unsafe archive member: {m.name!r}")
                tf.extractall(tmp, filter="data") if hasattr(tarfile, "data_filter") else tf.extractall(tmp)
        else:
            raise TrustError("extract", f"unsupported archive format: {archive.name}")
        for p in tmp.rglob("*"):
            if not p.resolve().is_relative_to(tmp.resolve()):
                raise TrustError("extract", f"archive member escapes root: {p}")
        try:
            os.rename(tmp, dest)
        except OSError:
            if not dest.is_dir():
                raise
        return dest
    except TrustError:
        raise
    except Exception as exc:
        raise TrustError("extract", f"extraction failed: {redact(str(exc))}") from exc
    finally:
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lctl161", type=Path)
    ap.add_argument("--lctl160", type=Path)
    ap.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    ap.add_argument("--json", type=Path, help="write a machine-readable provisioning result (no secrets)")
    ap.add_argument("--check-lock", action="store_true", help="validate the lock file only")
    a = ap.parse_args(argv)
    try:
        if a.check_lock:
            lock = load_lock(a.lock)
            states = {tc["role"]: tc["status"] for tc in lock["toolchains"]}
            print(f"PASS: lock {a.lock.name} v{lock['lock_version']} is well-formed; entries: {states}")
            return 0
        t = authenticate(a.lctl161, a.lctl160, a.lock)
    except TrustError as exc:
        print(f"FAIL[{exc.kind}]: {redact(str(exc))}", file=sys.stderr)
        if a.json:
            a.json.write_text(json.dumps({"result": "FAIL", "kind": exc.kind, "code": exc.code}, indent=1) + "\n")
        return exc.code
    result = {"result": "TRUSTED", "roots": {k: v.name for k, v in t.roots.items()},
              "jar_sha256": t.hashes, "java": t.java["version_line"], **t.evidence()}
    if a.json:
        a.json.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
