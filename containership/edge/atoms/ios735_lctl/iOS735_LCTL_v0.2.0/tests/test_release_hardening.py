"""Negative/positive tests for M01/M02.7/M04/M07/M08/M09 closure machinery.

Pure-Python tests always run. Tests that need a JDK (javac/jar) or OpenSSL build throwaway
simulated toolchains / keys in temp dirs and are skipped when those tools are missing. Nothing
produced here is release evidence.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import toolchain_trust as tt  # noqa: E402
from schema_check import validate, validate_file  # noqa: E402

PY = [sys.executable, "-B"]
HAVE_JDK = bool(shutil.which("javac") and shutil.which("jar") and shutil.which("java"))
HAVE_OPENSSL = bool(shutil.which("openssl"))
POSIX = os.name == "posix"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def make_roots(base: Path, content161=b"jar-161", content160=b"jar-160"):
    r161 = base / "LCTL_1.6.1_RC1_TEST root"
    r160 = base / "LCTL_1.6.0_RC1_TEST root"
    for r, rel, c in ((r161, "runtime/bin/lctl-hyperfederated.jar", content161), (r160, "runtime/bin/lctl-runtime.jar", content160)):
        (r / rel).parent.mkdir(parents=True, exist_ok=True)
        (r / rel).write_bytes(c)
    return r161, r160


def approved_lock(base: Path, h161: str, h160: str, name="lock.json") -> Path:
    lock = json.loads((ROOT / "toolchains/LOCK.json").read_text("utf-8"))
    for tc, h in zip(lock["toolchains"], (h161, h160)):
        tc.update(sha256=h, status="APPROVED", approval={"approved_by": "TEST", "approved_on": "2026-09-23"})
    p = base / name
    p.write_text(json.dumps(lock, indent=1), encoding="utf-8")
    return p


def fake_java(base: Path, version_line: str) -> str:
    p = base / "fakejava"
    p.write_text(f"#!/bin/sh\necho '{version_line}' 1>&2\n", encoding="utf-8")
    p.chmod(0o755)
    return str(p)


def copy_repo(dst: Path) -> Path:
    target = dst / "repo"
    shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns("__pycache__", ".git", "*.pyc"))
    return target


# ------------------------------------------------------------------ M04 lock validation
class LockTests(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.base = json.loads((ROOT / "toolchains/LOCK.json").read_text("utf-8"))

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def write(self, obj_or_text) -> Path:
        p = self.td / "l.json"
        p.write_text(obj_or_text if isinstance(obj_or_text, str) else json.dumps(obj_or_text), encoding="utf-8")
        return p

    def assertKind(self, path, kind):
        with self.assertRaises(tt.TrustError) as cm:
            tt.load_lock(path)
        self.assertEqual(cm.exception.kind, kind, str(cm.exception))

    def test_repository_lock_is_well_formed_but_pending(self):
        lock = tt.load_lock(ROOT / "toolchains/LOCK.json")
        self.assertTrue(all(tc["status"] in {"APPROVED", "PENDING_OWNER_APPROVAL"} for tc in lock["toolchains"]))

    def test_missing_lock(self):
        self.assertKind(self.td / "nope.json", "lock")

    def test_malformed_json(self):
        self.assertKind(self.write("{not json"), "lock")

    def test_duplicate_key(self):
        self.assertKind(self.write('{"schema":"a","schema":"b"}'), "lock")

    def test_unsupported_schema(self):
        b = copy.deepcopy(self.base); b["schema"] = "IOS735_LCTL/TOOLCHAIN_LOCK/9"
        self.assertKind(self.write(b), "schema")

    def test_duplicate_role(self):
        b = copy.deepcopy(self.base); b["toolchains"][1] = copy.deepcopy(b["toolchains"][0])
        self.assertKind(self.write(b), "lock")

    def test_unknown_role(self):
        b = copy.deepcopy(self.base); b["toolchains"][0]["role"] = "lctl999"
        self.assertKind(self.write(b), "lock")

    def test_malformed_hash(self):
        b = copy.deepcopy(self.base); b["toolchains"][0]["sha256"] = "ABC"
        self.assertKind(self.write(b), "lock")

    def test_approved_without_hash_or_approval(self):
        b = copy.deepcopy(self.base); b["toolchains"][0]["status"] = "APPROVED"
        self.assertKind(self.write(b), "lock")

    def test_traversal_jar_path(self):
        b = copy.deepcopy(self.base); b["toolchains"][0]["jar_path"] = "../../evil.jar"
        self.assertKind(self.write(b), "lock")

    def test_floating_version(self):
        b = copy.deepcopy(self.base); b["toolchains"][0]["version"] = "latest"
        self.assertKind(self.write(b), "lock")

    def test_java_policy_below_21(self):
        b = copy.deepcopy(self.base); b["java_policy"]["min_major"] = 17
        self.assertKind(self.write(b), "lock")

    def test_credentials_rejected(self):
        b = copy.deepcopy(self.base); b["toolchains"][0]["distribution"] = "https://x/?token=abc"
        self.assertKind(self.write(b), "lock")


# ------------------------------------------------------------------ M01 / M04 authentication
class TrustTests(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix="trust tests "))
        self.r161, self.r160 = make_roots(self.td)
        self.j161 = self.r161 / "runtime/bin/lctl-hyperfederated.jar"
        self.j160 = self.r160 / "runtime/bin/lctl-runtime.jar"
        self.lock = approved_lock(self.td, sha(self.j161), sha(self.j160))
        self.java = shutil.which("java")

    def tearDown(self):
        for p in self.td.rglob("*"):
            try:
                p.chmod(0o755 if p.is_dir() else 0o644)
            except OSError:
                pass
        shutil.rmtree(self.td, ignore_errors=True)

    def auth(self, **kw):
        return tt.authenticate(kw.get("r161", self.r161), kw.get("r160", self.r160), kw.get("lock", self.lock), kw.get("java"))

    def assertKind(self, kind, **kw):
        with self.assertRaises(tt.TrustError) as cm:
            self.auth(**kw)
        self.assertEqual(cm.exception.kind, kind, str(cm.exception))
        return cm.exception

    @unittest.skipUnless(shutil.which("java"), "java required")
    def test_correct_hashes_pass_with_spaces_in_paths(self):
        t = self.auth()
        self.assertEqual(t.hashes["lctl161"], sha(self.j161))
        self.assertGreaterEqual(t.java["major"], 21)
        self.assertEqual(t.evidence()["lock_sha256"], sha(self.lock))

    def test_pending_lock_refuses(self):
        self.assertKind("untrusted", lock=ROOT / "toolchains/LOCK.json")

    def test_missing_roots(self):
        self.assertKind("missing", r161=self.td / "absent")
        self.assertKind("missing", r160=self.td / "absent")

    def test_missing_jars(self):
        self.j161.unlink()
        self.assertKind("missing")
        make_roots(self.td)
        self.j160.unlink()
        self.assertKind("missing")

    def test_one_byte_modification(self):
        for jar in (self.j161, self.j160):
            orig = jar.read_bytes()
            jar.write_bytes(orig[:-1] + bytes([orig[-1] ^ 1]))
            self.assertKind("untrusted")
            jar.write_bytes(orig)

    def test_wrong_but_valid_jar_at_correct_path(self):
        self.j161.write_bytes(self.j160.read_bytes())
        self.assertKind("untrusted")

    def test_one_nibble_pin_change(self):
        h = sha(self.j161)
        lock = approved_lock(self.td, h[:-1] + ("0" if h[-1] != "0" else "1"), sha(self.j160), "l2.json")
        self.assertKind("untrusted", lock=lock)

    def test_wrong_version_with_same_naming_rejected(self):
        lock = json.loads(self.lock.read_text("utf-8"))
        lock["toolchains"][0]["version_marker"] = {"file": "VERSION.txt", "contains": "1.6.1-RC1"}
        p = self.td / "marker.json"
        p.write_text(json.dumps(lock), encoding="utf-8")
        (self.r161 / "VERSION.txt").write_text("LCTL 1.6.2-RC1\n")
        self.assertKind("untrusted", lock=p)

    def test_symlinked_jar_rejected(self):
        if not POSIX:
            self.skipTest("posix symlinks")
        real = self.td / "real.jar"
        real.write_bytes(self.j161.read_bytes())
        self.j161.unlink()
        self.j161.symlink_to(real)
        self.assertKind("missing")

    @unittest.skipUnless(POSIX, "shell-script fake java")
    def test_java_20_rejected(self):
        self.assertKind("java", java=fake_java(self.td, 'openjdk version "20.0.2" 2023-07-18'))

    @unittest.skipUnless(POSIX, "shell-script fake java")
    def test_java_1_8_rejected(self):
        self.assertKind("java", java=fake_java(self.td, 'java version "1.8.0_402"'))

    @unittest.skipUnless(POSIX, "shell-script fake java")
    def test_unparseable_java_rejected(self):
        self.assertKind("java", java=fake_java(self.td, "garbage output"))

    @unittest.skipUnless(POSIX and shutil.which("java"), "posix permissions + java")
    def test_read_only_toolchain_is_not_modified(self):
        before = {p: (p.stat().st_mtime_ns, sha(p)) for p in self.td.rglob("*.jar")}
        for p in [*self.r161.rglob("*"), *self.r160.rglob("*"), self.r161, self.r160]:
            p.chmod(0o555 if p.is_dir() else 0o444)
        self.auth()
        self.assertEqual(before, {p: (p.stat().st_mtime_ns, sha(p)) for p in self.td.rglob("*.jar")})

    def test_verifier_fails_closed_before_execution(self):
        # A pending lock must stop tools/verify.py with the stable 'untrusted' code and write nothing.
        repo = copy_repo(self.td)
        before = sha(repo / "evidence/VERIFY.json")
        cp = subprocess.run([*PY, str(repo / "tools/verify.py"), "--lctl161", str(self.r161), "--lctl160", str(self.r160)],
                            capture_output=True, text=True, timeout=120)
        self.assertEqual(cp.returncode, tt.EXIT["untrusted"], cp.stderr)
        self.assertEqual(before, sha(repo / "evidence/VERIFY.json"))

    def test_redaction(self):
        s = tt.redact("GET https://h/x?X-Amz-Signature=abc&token=zzz Authorization: Bearer eyJhbGciOi")
        for secret in ("abc", "zzz", "eyJhbGciOi"):
            self.assertNotIn(secret, s)


# ------------------------------------------------------------------ M01.6 archive provisioning
class ExtractTests(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def zip_with(self, name, members):
        p = self.td / name
        with zipfile.ZipFile(p, "w") as zf:
            for n, data, mode in members:
                zi = zipfile.ZipInfo(n)
                zi.external_attr = mode << 16
                zf.writestr(zi, data)
        return p

    def test_valid_archive_extracts_atomically(self):
        z = self.zip_with("ok.zip", [("runtime/bin/lctl-runtime.jar", b"x", stat.S_IFREG | 0o644)])
        dest = tt.safe_extract(z, self.td / "cache" / "root", sha(z))
        self.assertTrue((dest / "runtime/bin/lctl-runtime.jar").is_file())
        self.assertEqual([p.name for p in (self.td / "cache").iterdir()], ["root"])

    def test_traversal_rejected(self):
        for bad in ("../evil", "/abs/evil", "a/../../evil", "C:/evil"):
            z = self.zip_with("bad.zip", [(bad, b"x", stat.S_IFREG | 0o644)])
            with self.assertRaises(tt.TrustError) as cm:
                tt.safe_extract(z, self.td / "cache" / "root")
            self.assertEqual(cm.exception.kind, "extract")
            self.assertFalse((self.td / "evil").exists())
        self.assertFalse((self.td / "cache" / "root").exists())

    def test_symlink_member_rejected(self):
        z = self.zip_with("ln.zip", [("link", b"/etc/passwd", stat.S_IFLNK | 0o777)])
        with self.assertRaises(tt.TrustError):
            tt.safe_extract(z, self.td / "cache" / "root")

    def test_archive_digest_mismatch(self):
        z = self.zip_with("ok.zip", [("a", b"x", stat.S_IFREG | 0o644)])
        with self.assertRaises(tt.TrustError) as cm:
            tt.safe_extract(z, self.td / "cache" / "root", "0" * 64)
        self.assertEqual(cm.exception.kind, "untrusted")

    def test_truncated_archive_leaves_no_partial_root(self):
        z = self.zip_with("ok.zip", [("a" * 10, b"x" * 50000, stat.S_IFREG | 0o644)])
        z.write_bytes(z.read_bytes()[:-200])
        with self.assertRaises(tt.TrustError):
            tt.safe_extract(z, self.td / "cache" / "root")
        self.assertEqual(list((self.td / "cache").iterdir()), [])

    def test_concurrent_extraction_is_safe(self):
        z = self.zip_with("ok.zip", [(f"f{i}", os.urandom(2000), stat.S_IFREG | 0o644) for i in range(50)])
        errs = []

        def go():
            try:
                tt.safe_extract(z, self.td / "cache" / "root")
            except Exception as exc:  # pragma: no cover - failure path
                errs.append(exc)
        ts = [threading.Thread(target=go) for _ in range(6)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(errs, [])
        self.assertEqual(len(list((self.td / "cache/root").iterdir())), 50)
        self.assertEqual([p.name for p in (self.td / "cache").iterdir()], ["root"])


# ------------------------------------------------------------------ M09 schemas
class SchemaTests(unittest.TestCase):
    def test_current_artifacts_validate(self):
        cp = subprocess.run([*PY, str(ROOT / "tools/schema_check.py")], capture_output=True, text=True, timeout=120)
        self.assertEqual(cp.returncode, 0, cp.stdout)

    def test_negative_verify_fixtures(self):
        schema = json.loads((ROOT / "schemas/verify-v2.schema.json").read_text("utf-8"))
        good = json.loads((ROOT / "schemas/fixtures/verify-v2.valid.json").read_text("utf-8"))
        self.assertEqual(validate(good, schema), [])
        mutations = {
            "wrong schema id": lambda d: d.update(schema="IOS735_LCTL/VERIFY/1"),
            "missing field": lambda d: d.pop("gates"),
            "malformed hash": lambda d: d["toolchain_identity"].update(lctl161_jar_sha256="XYZ"),
            "wrong type": lambda d: d.update(units="44"),
            "unknown field": lambda d: d.update(extra=1),
            "invalid gate value": lambda d: d["units_detail"][0].update(lctl160_provenance="RAN"),
            "bad verdict": lambda d: d.update(verdict="MAYBE"),
            "negative count": lambda d: d["gates"].update(lctl161_column_stats=-1),
        }
        for name, mut in mutations.items():
            d = copy.deepcopy(good)
            mut(d)
            self.assertNotEqual(validate(d, schema), [], name)

    def test_negative_map_fixtures(self):
        schema = json.loads((ROOT / "schemas/translation-map-v1.schema.json").read_text("utf-8"))
        good = json.loads((ROOT / "map/TRANSLATION_MAP.json").read_text("utf-8"))
        mutations = {
            "schema id": lambda d: d.update(schema="IOS735_LCTL/MAP/2"),
            "phase sha": lambda d: d["phases"][0].update(sha="0" * 63),
            "component type": lambda d: d["components"][0].update(component="1"),
            "control status": lambda d: d["components"][0]["controls"][0].update(status="DONE"),
            "control complete": lambda d: d["components"][0]["controls"][0].update(complete="no"),
            "missing family_op": lambda d: d.pop("family_op"),
            "duplicate lifecycle": lambda d: d["lifecycle"].append(d["lifecycle"][0]),
        }
        for name, mut in mutations.items():
            d = copy.deepcopy(good)
            mut(d)
            self.assertNotEqual(validate(d, schema, limit=1), [], name)

    def test_historical_verify1_is_not_verify2(self):
        errs = validate_file(ROOT / "schemas/verify-v2.schema.json", ROOT / "evidence/VERIFY.json") \
            if json.loads((ROOT / "evidence/VERIFY.json").read_text("utf-8"))["schema"].endswith("/1") else ["n/a"]
        self.assertNotEqual(errs, [])


# ------------------------------------------------------------------ M07 SBOM
class SbomTests(unittest.TestCase):
    def test_committed_sbom_valid_and_consistent(self):
        cp = subprocess.run([*PY, str(ROOT / "tools/sbom.py"), "--check"], capture_output=True, text=True, timeout=60)
        self.assertEqual(cp.returncode, 0, cp.stdout)

    def test_release_sbom_refuses_unpinned_toolchains(self):
        lock = json.loads((ROOT / "toolchains/LOCK.json").read_text("utf-8"))
        if all(tc["status"] == "APPROVED" for tc in lock["toolchains"]):
            self.skipTest("lock already approved")
        with tempfile.TemporaryDirectory() as td:
            repo = copy_repo(Path(td))
            cp = subprocess.run([*PY, str(repo / "tools/sbom.py")], capture_output=True, text=True, timeout=60)
            self.assertNotEqual(cp.returncode, 0)


# ------------------------------------------------------------------ M02.7 transactional behaviour (simulated)
@unittest.skipUnless(HAVE_JDK, "JDK (javac/jar) required to build the test-only simulator")
class SimulatedVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = Path(tempfile.mkdtemp(prefix="sim verify "))
        cls.repo = copy_repo(cls.td)
        cls.cls_dir = cls.td / "cls"
        subprocess.run(["javac", "-d", str(cls.cls_dir), str(ROOT / "tests/fixtures/simtoolchain/Sim.java")], check=True, capture_output=True)
        (cls.td / "m.txt").write_text("Main-Class: Sim\n")
        cls.r161, cls.r160 = make_roots(cls.td)
        for jar in (cls.r161 / "runtime/bin/lctl-hyperfederated.jar", cls.r160 / "runtime/bin/lctl-runtime.jar"):
            jar.unlink()
            subprocess.run(["jar", "cfm", str(jar), str(cls.td / "m.txt"), "-C", str(cls.cls_dir), "."], check=True, capture_output=True)
        cls.lock = approved_lock(cls.td, sha(cls.r161 / "runtime/bin/lctl-hyperfederated.jar"), sha(cls.r160 / "runtime/bin/lctl-runtime.jar"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.td, ignore_errors=True)

    def run_verify(self, fail=""):
        env = {**os.environ, "SIM_CANON": str(ROOT / "canonical"), "SIM_FAIL": fail}
        return subprocess.run([*PY, str(self.repo / "tools/verify.py"), "--lctl161", str(self.r161), "--lctl160", str(self.r160),
                               "--lock", str(self.lock), "--jobs", "4"], capture_output=True, text=True, env=env, timeout=900)

    def snapshot(self):
        return {p.relative_to(self.repo).as_posix(): sha(p) for d in ("canonical", "evidence/lctl160")
                for p in (self.repo / d).rglob("*") if p.is_file()}

    def test_failed_gate_is_transactional(self):
        before = self.snapshot()
        for failing in ("provenance", "column-compile", "column-stats"):
            cp = self.run_verify(failing)
            self.assertEqual(cp.returncode, 1, cp.stdout + cp.stderr)
            ev = json.loads((self.repo / "evidence/VERIFY.json").read_text("utf-8"))
            self.assertEqual(ev["verdict"], "FAIL")
            self.assertFalse(ev["generated_outputs_committed"])
            self.assertEqual(before, self.snapshot(), failing)

    def test_simulated_pass_commits_and_is_accepted_under_its_lock(self):
        cp = self.run_verify()
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        ev = self.repo / "evidence/VERIFY.json"
        self.assertEqual(validate_file(ROOT / "schemas/verify-v2.schema.json", ev), [])
        chk = subprocess.run([*PY, str(self.repo / "tools/evidence_check.py"), "--lock", str(self.lock)], capture_output=True, text=True)
        self.assertEqual(chk.returncode, 0, chk.stdout)
        # ...but it is never accepted against the repository lock.
        chk = subprocess.run([*PY, str(self.repo / "tools/evidence_check.py")], capture_output=True, text=True)
        self.assertNotEqual(chk.returncode, 0)
        # canonical bytes are unchanged (no drift) because the simulator replays the committed corpus
        for p in (ROOT / "canonical").glob("*.lctl"):
            self.assertEqual(sha(p), sha(self.repo / "canonical" / p.name))


# ------------------------------------------------------------------ M08 release gate / signing (simulated identity)
@unittest.skipUnless(HAVE_JDK and HAVE_OPENSSL, "JDK and OpenSSL required")
class ReleaseSigningTests(unittest.TestCase):
    def test_repository_is_not_release_grade_until_owner_items_close(self):
        cp = subprocess.run([*PY, str(ROOT / "tools/release.py"), "preflight"], capture_output=True, text=True, timeout=600)
        if "RELEASE-GRADE: YES" in cp.stdout:
            self.skipTest("repository is release-grade")
        self.assertEqual(cp.returncode, 1)
        with tempfile.TemporaryDirectory() as td:
            cp = subprocess.run([*PY, str(ROOT / "tools/release.py"), "package", "--out", td], capture_output=True, text=True, timeout=600)
            self.assertNotEqual(cp.returncode, 0)
            self.assertEqual(list(Path(td).glob("*.zip")), [])

    def test_end_to_end_sign_and_verify_with_throwaway_identity(self):
        td = Path(tempfile.mkdtemp(prefix="sign test "))
        try:
            sim = SimulatedVerifierTests
            sim.setUpClass()
            repo = sim.repo
            env = {**os.environ, "SIM_CANON": str(ROOT / "canonical"), "SIM_FAIL": ""}
            subprocess.run([*PY, str(repo / "tools/verify.py"), "--lctl161", str(sim.r161), "--lctl160", str(sim.r160),
                            "--lock", str(sim.lock), "--jobs", "4"], env=env, check=True, capture_output=True, timeout=900)
            shutil.copy(sim.lock, repo / "toolchains/LOCK.json")
            # the verifier ran under the copied lock bytes, so evidence correlates
            (repo / "LICENSE").write_text("SPDX-License-Identifier: LicenseRef-Test-Only\nTest licence for signing test.\n")
            (repo / "SECURITY.md").write_text("# Security\nReport privately via the test channel.\n")
            key = td / "priv.pem"
            (repo / "provenance").mkdir(exist_ok=True)
            pub = repo / "provenance/release-signing-public.pem"
            subprocess.run(["openssl", "genpkey", "-algorithm", "ed25519", "-out", str(key)], check=True, capture_output=True)
            subprocess.run(["openssl", "pkey", "-in", str(key), "-pubout", "-out", str(pub)], check=True, capture_output=True)
            subprocess.run([*PY, str(repo / "tools/sbom.py")], check=True, capture_output=True)
            subprocess.run([*PY, str(repo / "tools/manifest.py"), "--write"], check=True, capture_output=True)
            dist = td / "dist"
            cp = subprocess.run([*PY, str(repo / "tools/release.py"), "package", "--out", str(dist)], capture_output=True, text=True, timeout=900)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            prov = next(dist.glob("*.provenance.json"))
            archive = next(dist.glob("*.zip"))
            first_digest = sha(archive)
            cp = subprocess.run([*PY, str(repo / "tools/release.py"), "sign", "--provenance", str(prov), "--key", str(key)],
                                capture_output=True, text=True, timeout=900)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            sig = prov.with_suffix(".sig")
            verify = lambda a=archive, p=prov, s=sig, k=pub: subprocess.run(  # noqa: E731
                [*PY, str(ROOT / "tools/release.py"), "verify", "--archive", str(a), "--provenance", str(p), "--sig", str(s), "--pubkey", str(k)],
                capture_output=True, text=True, timeout=600)
            self.assertEqual(verify().returncode, 0, verify().stdout)
            # deterministic packaging
            dist2 = td / "dist2"
            subprocess.run([*PY, str(repo / "tools/release.py"), "package", "--out", str(dist2)], check=True, capture_output=True, timeout=900)
            self.assertEqual(first_digest, sha(next(dist2.glob("*.zip"))))
            # one-byte archive modification
            bad = td / archive.name
            b = bytearray(archive.read_bytes()); b[len(b) // 2] ^= 1; bad.write_bytes(b)
            self.assertNotEqual(verify(a=bad).returncode, 0)
            # provenance modification
            badp = td / prov.name
            badp.write_text(prov.read_text().replace('"candidate": false', '"candidate": true'))
            self.assertNotEqual(verify(p=badp).returncode, 0)
            # wrong signer
            other = td / "other.pem"; otherpub = td / "other.pub.pem"
            subprocess.run(["openssl", "genpkey", "-algorithm", "ed25519", "-out", str(other)], check=True, capture_output=True)
            subprocess.run(["openssl", "pkey", "-in", str(other), "-pubout", "-out", str(otherpub)], check=True, capture_output=True)
            self.assertNotEqual(verify(k=otherpub).returncode, 0)
            # key inside repo refused; candidate never signable
            inside = repo / "k.pem"; shutil.copy(key, inside)
            cp = subprocess.run([*PY, str(repo / "tools/release.py"), "sign", "--provenance", str(prov), "--key", str(inside)], capture_output=True, text=True)
            self.assertNotEqual(cp.returncode, 0)
            inside.unlink()
            # failed verifier => signing refused
            env["SIM_FAIL"] = "provenance"
            subprocess.run([*PY, str(repo / "tools/verify.py"), "--lctl161", str(sim.r161), "--lctl160", str(sim.r160),
                            "--jobs", "4"], env=env, capture_output=True, timeout=900)
            cp = subprocess.run([*PY, str(repo / "tools/release.py"), "sign", "--provenance", str(prov), "--key", str(key)], capture_output=True, text=True, timeout=900)
            self.assertNotEqual(cp.returncode, 0)
        finally:
            SimulatedVerifierTests.tearDownClass()
            shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
