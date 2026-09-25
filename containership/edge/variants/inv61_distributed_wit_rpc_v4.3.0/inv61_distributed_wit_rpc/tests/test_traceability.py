"""M02/M21 traceability + master-source integrity, M04 golden fixtures,
M31 packaging, C077 explain view."""
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from _harness import PKG_DIR, Fixture, codec, key, security

TOOLS = PKG_DIR / "tools"


def run(*a):
    return subprocess.run([sys.executable, *map(str, a)], capture_output=True, text=True, cwd=PKG_DIR)


class MasterSourceTest(unittest.TestCase):
    def test_checklist_is_authoritative_100_unique_sequential(self):
        d = json.loads((PKG_DIR / "CHECKLIST.json").read_text())
        ids = [i["check_id"] for i in d["items"]]
        self.assertEqual(d["item_count"], 100)
        self.assertEqual(ids, [f"INV-61-C{n:03d}" for n in range(1, 101)])
        self.assertEqual([i["ordinal"] for i in d["items"]], list(range(1, 101)))

    def test_readme_does_not_claim_absent_files(self):
        readme = (PKG_DIR / "README.md").read_text()
        for name in set(__import__("re").findall(r"`([\w./-]+\.(?:md|json|py|toml|sh|wit))`", readme)):
            with self.subTest(name=name):
                self.assertTrue((PKG_DIR / name).exists() or name.startswith(("dist/", "evidence/")), name)


class TraceabilityTest(unittest.TestCase):
    def test_matrix_complete_bidirectional_and_fresh(self):
        r = run(TOOLS / "build_traceability.py", "--check")
        self.assertEqual(r.returncode, 0, r.stderr)
        t = json.loads((PKG_DIR / "TRACEABILITY.json").read_text())
        self.assertEqual(len(t["rows"]), 100)
        self.assertEqual(t["checklist_sha256"], hashlib.sha256((PKG_DIR / "CHECKLIST.json").read_bytes()).hexdigest())
        req = (PKG_DIR / "docs" / "REQUIREMENTS.md").read_text()
        used = {rq for row in t["rows"] for rq in row["requirements"]}
        declared = set(__import__("re").findall(r"\| (RQ-\d{3}) \|", req))
        self.assertEqual(declared - used, set(), "requirements with no control")


class GoldenFixtureTest(unittest.TestCase):
    def test_fixtures_have_not_drifted(self):
        r = run(TOOLS / "gen_fixtures.py", "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_golden_request_frame_is_accepted_by_verifier(self):
        g = json.loads((PKG_DIR / "tests" / "fixtures" / "golden.json").read_text())
        _, _, kind, body = codec.unpack_frame(bytes.fromhex(g["request_frame_hex"]))
        env = codec.decode(codec.REQUEST_ENVELOPE, body)
        ring = security.KeyRing()
        ring.add(security.Key("fixture-k1", "fixture-client", bytes.fromhex(g["test_key_hex"])))
        self.assertEqual(security.verify_mac(env, ring, 0).principal, "fixture-client")
        self.assertEqual(env["fp"], g["fingerprints"]["get"])


class PackagingTest(unittest.TestCase):
    def test_wheel_build_sbom_checksums_and_bootstrap(self):
        out = pathlib.Path(tempfile.mkdtemp()) / "dist"
        r = run(TOOLS / "make_release.py", "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        self.assertEqual(run(TOOLS / "verify_release.py", out).returncode, 0)
        wheel = next(out.glob("*.whl"))
        # reproducible: rebuilding yields the same digest
        out2 = out.parent / "dist2"
        run(TOOLS / "make_release.py", "--out", out2)
        self.assertEqual(hashlib.sha256(wheel.read_bytes()).hexdigest(),
                         hashlib.sha256(next(out2.glob("*.whl")).read_bytes()).hexdigest())
        # tamper detection
        (out / "sbom.cdx.json").write_text("{}")
        self.assertNotEqual(run(TOOLS / "verify_release.py", out2.parent / "dist").returncode, 0)
        # deterministic bootstrap from an empty prefix, then rollback refusal (no previous)
        prefix = pathlib.Path(tempfile.mkdtemp()) / "opt"
        cfg = pathlib.Path(tempfile.mkdtemp()) / "cfg.json"
        cfg.write_text(json.dumps({"require_tls": False}))
        b = subprocess.run(["bash", str(PKG_DIR / "bootstrap.sh"), "--wheel", str(next(out2.glob("*.whl"))),
                            "--prefix", str(prefix), "--python", sys.executable, "--config", str(cfg)],
                           capture_output=True, text=True)
        self.assertEqual(b.returncode, 0, b.stdout + b.stderr)
        self.assertIn('"status": "pass"', b.stdout)
        rb = subprocess.run(["bash", str(PKG_DIR / "bootstrap.sh"), "--rollback", "--prefix", str(prefix)],
                            capture_output=True, text=True)
        self.assertNotEqual(rb.returncode, 0)


class ExplainTest(unittest.TestCase):
    def test_explain_view_links_decision_to_inputs_and_refuses_tampered_log(self):
        fx = Fixture(grants=[])
        fx.call(fx.envelope("get", ["a"]))
        (fx.tmp / "k").write_bytes(fx.audit_key)
        r = run(TOOLS / "explain.py", fx.tmp / "audit.jsonl", "--key-file", fx.tmp / "k", "--event", "authz-deny")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("authz-deny", r.stdout)
        self.assertIn("who=client-a", r.stdout)
        self.assertIn("why=no-grant policy v1", r.stdout)
        p = fx.tmp / "audit.jsonl"
        p.write_text(p.read_text().replace("no-grant", "granted"))
        self.assertNotEqual(run(TOOLS / "explain.py", p, "--key-file", fx.tmp / "k").returncode, 0)


if __name__ == "__main__":
    unittest.main()
