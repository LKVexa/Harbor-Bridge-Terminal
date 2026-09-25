"""Real vsock paths, pk_core adapter/gate, fuzz properties, supply chain and governance consistency."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

import _util  # noqa: F401

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCMSIV
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from inv36_control_transport import gate, pkcore_adapter, schema_check, vsock
from inv36_control_transport.stream import StreamError, StreamUnavailable
from inv36_control_transport.tools import docs_check, fuzz, mc_status, release, secret_scan, traceability
from inv36_control_transport.transport import Session

PKG = pathlib.Path(__file__).resolve().parents[1]


@unittest.skipUnless(vsock.available(), "AF_VSOCK not available on this platform")
class RealVsockKernelTest(unittest.TestCase):
    """REQ: INV36-REQ-001 | KIND: integration"""

    def test_platform_probe(self):
        info = vsock.platform_support()
        self.assertIn(info["tier"], ("device-present-uncertified", "no-device"))

    @unittest.skipUnless(os.path.exists("/dev/vsock"), "no /dev/vsock device")
    def test_listen_collision_timeout_and_typed_connect_failure(self):
        lst = vsock.VsockListener(port=25036).open()
        try:
            with self.assertRaises(StreamUnavailable):
                vsock.VsockListener(port=25036).open()
            self.assertIsNone(lst.accept(timeout=0.05))
        finally:
            lst.close()
        with self.assertRaises(StreamError):
            vsock.vsock_connect(vsock.VMADDR_CID_HOST, 1, timeout=0.5)
        with self.assertRaises(ValueError):
            vsock.VsockListener(port=80).open()

    def test_churn_limiter(self):
        t = [0.0]
        cl = vsock.ChurnLimiter(rate_per_s=1, burst=3, clock=lambda: t[0])
        self.assertEqual([cl.allow(5) for _ in range(5)], [True, True, True, False, False])
        t[0] += 2
        self.assertTrue(cl.allow(5))


class PkCoreAdapterTest(unittest.TestCase):
    """REQ: INV36-REQ-043 | KIND: unit"""

    def fake(self, body: str, rc: int = 0, sleep: float = 0.0):
        code = f"import sys,time; time.sleep({sleep}); print({body!r}); sys.exit({rc})"
        return [sys.executable, "-c", code]

    def doc(self, status="PASS", n=100, schema="pk_core.findings/1"):
        return json.dumps({"schema": schema, "findings": [{"check_id": f"C{i:03d}", "status": status}
                                                           for i in range(n)]})

    def test_pass_fail_malformed_schema_timeout_crash(self):
        ok = pkcore_adapter.run_gate(runner=self.fake(self.doc()))
        self.assertTrue(ok["normalized"]["all_pass"])
        self.assertFalse(pkcore_adapter.run_gate(runner=self.fake(self.doc("FAIL")))["normalized"]["all_pass"])
        self.assertFalse(pkcore_adapter.run_gate(runner=self.fake(self.doc("SKIP")))["normalized"]["all_pass"])
        cases = {"malformed": self.fake("not json"), "short": self.fake(self.doc(n=99)),
                 "schema": self.fake(self.doc(schema="pk_core.findings/9")), "crash": self.fake("", rc=3)}
        for name, runner in cases.items():
            with self.subTest(name), self.assertRaises(pkcore_adapter.GateUnavailable):
                pkcore_adapter.run_gate(runner=runner)
        with self.assertRaises(pkcore_adapter.GateUnavailable) as cm:
            pkcore_adapter.run_gate(timeout_s=0.3, runner=self.fake(self.doc(), sleep=5))
        self.assertEqual(cm.exception.code.name, "GATE_TIMEOUT")

    def test_absent_pk_core_is_typed_and_never_pass(self):
        info = pkcore_adapter.probe()
        if info["status"] == "available":
            self.skipTest("pk_core installed")
        with self.assertRaises(pkcore_adapter.GateUnavailable):
            pkcore_adapter.require("contract", "Contract")
        with self.assertRaises(pkcore_adapter.GateUnavailable):
            pkcore_adapter.run_gate()

    def test_single_import_boundary(self):
        offenders = []
        for p in PKG.rglob("*.py"):
            if p.name == "pkcore_adapter.py" or "tests" in p.parts:
                continue
            if "import pk_core" in p.read_text() or "from pk_core" in p.read_text():
                offenders.append(p.name)
        self.assertEqual(offenders, [])


class GateTest(unittest.TestCase):
    """REQ: INV36-REQ-043, INV36-REQ-048 | KIND: integration"""

    def test_certify_mode_blocks_on_missing_pk_core_and_evidence_is_schema_valid(self):
        with tempfile.TemporaryDirectory() as d:
            code, doc = gate.run("certify", pathlib.Path(d), only=["G13-pk_core-estate-gate", "G01-wire-codegen"])
            if pkcore_adapter.probe()["status"] != "available":
                self.assertEqual(code, gate.EXIT_INFRA)
                self.assertEqual(doc["results"][-1]["status"], "ERROR")
            schema_check.validate(doc, schema_check.load("gate-evidence.schema.json"))
            self.assertFalse(doc["summary"]["certifiable"])
            ev = pathlib.Path(d) / "gate-evidence.json"
            digest = (pathlib.Path(d) / "gate-evidence.json.sha256").read_text().split()[0]
            self.assertEqual(hashlib.sha256(ev.read_bytes()).hexdigest(), digest)
            self.assertFalse(os.access(ev, os.W_OK) and os.geteuid() != 0)

    def test_local_mode_skip_is_not_pass_and_deterministic_digest(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            c1, a = gate.run("local", pathlib.Path(d1), only=["G13-pk_core-estate-gate", "G01-wire-codegen"])
            c2, b = gate.run("local", pathlib.Path(d2), only=["G13-pk_core-estate-gate", "G01-wire-codegen"])
            self.assertEqual(a["deterministic_digest"], b["deterministic_digest"])
            self.assertEqual(a["source_digest"], b["source_digest"])
            if pkcore_adapter.probe()["status"] != "available":
                self.assertEqual(a["summary"]["SKIP"], 1)
                self.assertFalse(a["summary"]["certifiable"])

    def test_bad_mode_is_config_error(self):
        self.assertEqual(gate.run("yolo")[0], gate.EXIT_CONFIG)

    def test_golden_evidence_fixture_validates(self):
        doc = json.loads((PKG / "fixtures" / "golden_gate_evidence.json").read_text())
        schema_check.validate(doc, schema_check.load("gate-evidence.schema.json"))
        bad = dict(doc, results=[dict(doc["results"][0], status="MAYBE")])
        with self.assertRaises(schema_check.SchemaViolation):
            schema_check.validate(bad, schema_check.load("gate-evidence.schema.json"))
        self.assertEqual(gate._deterministic(doc), doc["deterministic_digest"])


class FuzzPropertyTest(unittest.TestCase):
    """REQ: INV36-REQ-044, INV36-REQ-007, INV36-REQ-009 | KIND: fuzz"""

    def test_bounded_campaign_all_targets(self):
        res = fuzz.run(iterations=int(os.environ.get("INV36_FUZZ_ITERS", "150")),
                       seed=int(os.environ.get("INV36_FUZZ_SEED", "1")))
        self.assertTrue(res["ok"], res["failures"][:1])
        self.assertEqual(set(res["targets"]), set(fuzz.TARGETS))

    def test_persisted_regressions_replay_clean(self):
        self.assertEqual(fuzz.replay_regressions(), [])

    def test_near_2_64_sequence_values(self):
        a = Session("x-a", "x-b", b"k" * 32, session_id=b"s" * 16)
        b = Session("x-b", "x-a", b"k" * 32, session_id=b"s" * 16)
        a.send_seq = (1 << 64) - 2
        b.recv_seq = (1 << 64) - 2
        self.assertEqual(b.open(a.seal(b"last")), b"last")
        with self.assertRaises(Exception):
            a.seal(b"wrap")

    def test_differential_golden_frames_independent_derivation(self):
        """Re-derive keys with an independent HKDF/AES-GCM-SIV code path and reproduce golden wire bytes."""
        fx = json.loads((PKG / "fixtures" / "golden_frames_v2.json").read_text())
        shared, sid = bytes.fromhex(fx["shared"]), bytes.fromhex(fx["session_id"])

        def ident(s):
            e = s.encode()
            return len(e).to_bytes(2, "big") + e

        ctx = b"PK_CTRL_DIRECTION/2\x00" + len(sid).to_bytes(2, "big") + sid + ident(fx["sender"]) + ident(fx["receiver"])
        mat = HKDF(hashes.SHA256(), 36, hashlib.sha256(b"PK_CTRL_SESSION/2\x00" + sid).digest(), ctx).derive(shared)
        aead = AESGCMSIV(mat[:32])
        for seq, f in enumerate(fx["frames"][:3], 1):
            header = b"PKCT" + bytes([2, 1]) + seq.to_bytes(8, "big")
            ct = aead.encrypt(mat[32:] + seq.to_bytes(8, "big"), bytes.fromhex(f["plaintext"]),
                              b"PK_CTRL_FRAME/2\x00" + ctx + header)
            self.assertEqual((header + ct).hex(), f["wire"])
        rx = Session(fx["receiver"], fx["sender"], shared, session_id=sid)
        for f in fx["frames"][:3]:
            self.assertEqual(rx.open(bytes.fromhex(f["wire"])).hex(), f["plaintext"])


class GovernanceConsistencyTest(unittest.TestCase):
    """REQ: INV36-REQ-048, INV36-REQ-040, INV36-REQ-015 | KIND: unit"""

    def test_docs_consistent_and_master_md_not_claimed(self):
        self.assertEqual(docs_check.check(), [])

    def test_docs_check_detects_false_master_claim(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "x.md"
            p.write_text("The MASTER.md corpus ships with this repository and is authoritative.")
            orig = docs_check.DOCS
            try:
                docs_check.DOCS = [p]
                old_pkg = docs_check.PKG
                docs_check.PKG = pathlib.Path(d)
                shutil.copy(PKG / "CHECKLIST.json", d)
                for f in ("VERSION", "pyproject.toml", "__init__.py", "CHANGELOG.md"):
                    shutil.copy(PKG / f, d)
                self.assertTrue(any("MASTER.md" in x for x in docs_check.check()))
            finally:
                docs_check.DOCS = orig
                docs_check.PKG = old_pkg

    def test_traceability_complete(self):
        tr = traceability.build()
        self.assertEqual(tr["problems"], [])
        self.assertEqual(tr["orphan_tests"], [])

    def test_mc_ledger_valid_and_honest(self):
        res = mc_status.check()
        self.assertEqual(res["problems"], [])
        self.assertEqual(res["items"], 752)
        # Items that require humans/external systems must not be marked DONE
        ledger = json.loads((PKG / "MC_CHECKLIST_STATUS.json").read_text())["items"]
        for iid in ("MC-22.001", "MC-22.017", "MC-21.001", "MC-02.001", "MC-03.035", "MC-01.021", "MC-17.014"):
            self.assertNotEqual(ledger[iid]["status"], "DONE", iid)

    def test_secret_scan_clean(self):
        self.assertEqual(secret_scan.scan(), [])

    def test_license_findings_flag_nothing_copyleft(self):
        self.assertEqual(release.license_findings(), [])


@unittest.skipUnless(shutil.which("git") and (PKG / ".git").exists(), "needs a git checkout")
class ReleaseSupplyChainTest(unittest.TestCase):
    """REQ: INV36-REQ-042 | KIND: security"""

    def test_build_sbom_provenance_sign_verify_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            out = pathlib.Path(d) / "dist"
            proc = subprocess.run([sys.executable, "-m", "inv36_control_transport.tools.release", "all-local",
                                   "--out", str(out)], capture_output=True, text=True, cwd=PKG.parent,
                                  env={**os.environ, "PYTHONPATH": str(PKG.parent)}, timeout=300)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            pub = json.loads(proc.stdout.strip().splitlines()[-1])["pub"]
            sbom = json.loads((out / "sbom.cdx.json").read_text())
            self.assertEqual(sbom["bomFormat"], "CycloneDX")
            self.assertTrue(any(c["name"] == "cryptography" for c in sbom["components"]))
            wheel = next(out.glob("*.whl"))
            with open(wheel, "ab") as fh:
                fh.write(b"tamper")
            self.assertIn("artifact digests differ from SHA256SUMS", release.verify(out, pub, "ephemeral-test"))
            self.assertIn("signature key id not trusted", release.verify(out, pub, "other"))


if __name__ == "__main__":
    unittest.main()
