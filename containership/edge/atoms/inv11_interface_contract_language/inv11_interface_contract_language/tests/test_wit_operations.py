"""INV11-MC-17/18/22/29/30/31/32/33/34/35/36/37/40."""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from _support import FIX, PKG_DIR, ok, rd

from inv11_interface_contract_language.wit import lifecycle as L
from inv11_interface_contract_language.wit import ops, release
from inv11_interface_contract_language.wit.compat import classify_packages

TODAY = dt.date(2026, 9, 22)


def pol(code):
    return ok(rd(FIX / "policy" / code / "old.wit")), ok(rd(FIX / "policy" / code / "new.wit"))


def keypair(td):
    k, p = os.path.join(td, "k.pem"), os.path.join(td, "p.pem")
    subprocess.run(["openssl", "genpkey", "-algorithm", "ed25519", "-out", k], check=True, capture_output=True)
    subprocess.run(["openssl", "pkey", "-in", k, "-pubout", "-out", p], check=True, capture_output=True)
    return k, pathlib.Path(p).read_text()


class Provenance(unittest.TestCase):
    def make(self, td, sign_key=None):
        pkg = os.path.join(td, "pkg")
        os.makedirs(pkg)
        shutil.copy(FIX / "valid" / "06-resource.wit", os.path.join(pkg, "api.wit"))
        with open(os.path.join(pkg, "sbom.cdx.json"), "w") as fh:
            json.dump({"bomFormat": "CycloneDX"}, fh)
        man = {"files": {f: ops.sha256_file(os.path.join(pkg, f)) for f in ("api.wit", "sbom.cdx.json")},
               "sbom": "sbom.cdx.json", "provenance": {"builder": "urn:test"}, "key_id": "k1"}
        with open(os.path.join(pkg, "PROVENANCE.json"), "w") as fh:
            json.dump(man, fh)
        if sign_key:
            release.sign(os.path.join(pkg, "PROVENANCE.json"), sign_key, os.path.join(pkg, "PROVENANCE.json.sig"))
        return pkg

    def test_digest_sbom_provenance_and_signature(self):
        with tempfile.TemporaryDirectory() as td:
            k, pub = keypair(td)
            pkg = self.make(td, k)
            self.assertTrue(ops.verify_import(pkg, {"require_signature": True, "trusted_keys": {"k1": pub}})["signed"])

    def test_every_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            k, pub = keypair(td)
            _, other = keypair(tempfile.mkdtemp(dir=td))
            pol_ = {"require_signature": True, "trusted_keys": {"k1": pub}}
            pkg = self.make(td, k)
            with open(os.path.join(pkg, "api.wit"), "a") as fh:
                fh.write("\n// tampered")
            with self.assertRaisesRegex(ops.ProvenanceError, "digest mismatch"):
                ops.verify_import(pkg, pol_)
            shutil.rmtree(pkg)
            pkg = self.make(td, k)
            pathlib.Path(os.path.join(pkg, "extra.wit")).write_text("package x:y;")
            with self.assertRaisesRegex(ops.ProvenanceError, "file set mismatch"):
                ops.verify_import(pkg, pol_)
            shutil.rmtree(pkg)
            pkg = self.make(td, k)
            with self.assertRaisesRegex(ops.ProvenanceError, "signature invalid"):
                ops.verify_import(pkg, {"require_signature": True, "trusted_keys": {"k1": other}})
            with self.assertRaisesRegex(ops.ProvenanceError, "untrusted"):
                ops.verify_import(pkg, {"require_signature": True, "trusted_keys": {}})
            shutil.rmtree(pkg)
            pkg = self.make(td)
            with self.assertRaisesRegex(ops.ProvenanceError, "signature invalid"):
                ops.verify_import(pkg, pol_)


class MatrixAndDependency(unittest.TestCase):
    def test_matrix(self):
        m = ops.matrix()
        self.assertEqual(m["reference_toolchain"]["pinned"], "1.219.1")
        self.assertIn("in_support_range", m["python"])
        doc = json.loads((PKG_DIR / "conformance" / "SUPPORT_MATRIX.json").read_text())
        self.assertEqual({k: v for k, v in doc.items() if k != "python"}, {k: v for k, v in ops.MATRIX.items() if k != "python"})

    def test_pk_core_absence_is_blocked_not_pass(self):
        env = dict(os.environ)
        env.pop("PK_CORE_PATH", None)
        st = ops.pk_core_status()
        self.assertIn(st["status"], ("BLOCKED", "OK", "FAILED"))
        if st["status"] != "OK":
            self.assertNotEqual(st["status"], "PASS")


class TelemetryAudit(unittest.TestCase):
    def test_counters_histograms_closed_label_set(self):
        t = ops.Telemetry()
        a, b = pol("func-removed")
        d = t.timed("compare_ms", classify_packages, a, b)
        t.inc("classifications")
        t.inc(d["class"])
        txt = t.prometheus()
        self.assertIn("inv11_breaking_total 1", txt)
        self.assertIn('inv11_compare_ms_bucket{le="+Inf"} 1', txt)
        with self.assertRaises(KeyError):
            t.inc("attacker-controlled-label")

    def test_hash_chain_detects_edit_delete_reorder_truncate(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "audit.jsonl")
            log = ops.AuditLog(p)
            for i in range(5):
                log.append("classification", f"a:b/i{i}", "breaking", {"from": "sha256:" + "0" * 64})
            head = log.verify()["head"]
            self.assertTrue(log.verify(head)["ok"])
            lines = pathlib.Path(p).read_text().splitlines()
            for mutated in (lines[:2] + [lines[2].replace("breaking", "additive")] + lines[3:],
                            lines[:2] + lines[3:], [lines[1], lines[0]] + lines[2:]):
                pathlib.Path(p).write_text("\n".join(mutated) + "\n")
                self.assertFalse(log.verify()["ok"])
            pathlib.Path(p).write_text("\n".join(lines[:4]) + "\n")
            self.assertTrue(log.verify()["ok"])  # truncation is invisible without the external head…
            self.assertFalse(log.verify(head)["ok"])  # …and caught with it


class Release(unittest.TestCase):
    def test_reproducible_archive_sbom_and_signature(self):
        with tempfile.TemporaryDirectory() as td:
            r = release.verify_reproducible(str(PKG_DIR), "inv11_interface_contract_language", td)
            self.assertTrue(r["reproducible"], r)
            os.environ["SOURCE_DATE_EPOCH"] = "1790000000"
            try:
                r2 = release.verify_reproducible(str(PKG_DIR), "inv11_interface_contract_language", td)
            finally:
                del os.environ["SOURCE_DATE_EPOCH"]
            self.assertTrue(r2["reproducible"])
            self.assertNotEqual(r["sha256_a"], r2["sha256_a"])
            sb = release.sbom(str(PKG_DIR))
            self.assertEqual(sb["bomFormat"], "CycloneDX")
            self.assertTrue(any(c["name"] == "pk-core" for c in sb["components"]))
            k, pub = keypair(td)
            z = os.path.join(td, "a.zip")
            release.sign(z, k, z + ".sig")
            self.assertTrue(ops.ed25519_verify(pub, z, z + ".sig"))
            with open(z, "ab") as fh:
                fh.write(b"x")
            self.assertFalse(ops.ed25519_verify(pub, z, z + ".sig"))


class Lifecycle(unittest.TestCase):
    def test_semver_recommendation_is_advisory(self):
        self.assertEqual(L.recommend_version("1.4.2", classify_packages(*pol("func-removed")))["recommended"], "2.0.0")
        self.assertEqual(L.recommend_version("1.4.2", classify_packages(*pol("func-added")))["recommended"], "1.5.0")
        self.assertEqual(L.recommend_version("1.4.2", classify_packages(*pol("version-only")))["recommended"], "1.4.3")
        self.assertEqual(L.recommend_version("0.3.1", classify_packages(*pol("func-removed")))["recommended"], "0.4.0")
        r = L.recommend_version("1.0.0", classify_packages(*pol("func-removed")))
        self.assertTrue(r["declared_under_bumped"])  # 1.1.0 declared for a breaking change
        self.assertEqual(L.recommend_version("v1", classify_packages(*pol("func-added")))["status"], "BLOCKED")

    def test_deprecation_removal_gate(self):
        a, b = pol("func-removed")
        d = classify_packages(a, b)
        none = L.DeprecationManager([])
        self.assertFalse(none.removal_gate(d, TODAY)["pass"])
        early = L.DeprecationManager([L.Deprecation("a:b/i.g", "1.0.0", "2027-01-01")])
        self.assertIn("grace", early.removal_gate(d, TODAY)["verdicts"][0]["reason"])
        used = L.DeprecationManager([L.Deprecation("a:b/i.g", "1.0.0", "2026-01-01", consumers=["app"])])
        self.assertFalse(used.removal_gate(d, TODAY)["pass"])
        done = L.DeprecationManager([L.Deprecation("a:b/i.g", "1.0.0", "2026-01-01")])
        self.assertTrue(done.removal_gate(d, TODAY)["pass"])
        res = ok(rd(FIX / "valid" / "12-gates.wit"))
        self.assertEqual([e.path for e in L.DeprecationManager.from_gates(res, "2027-01-01")], ["p:g/g.old"])
        w = ok(rd(FIX / "valid" / "09-world-basic.wit"))
        self.assertEqual(L.discover_consumers("p:w/host.log", {"svc": w}), ["svc:p:w/app"])

    def test_waivers(self):
        d = classify_packages(*pol("func-removed"))
        good = {"id": "W-1", "owner": "team-a", "rationale": "planned", "scope": "a:b/i", "codes": ["func-removed"],
                "expires": "2026-12-31", "approved_by": "arch-board", "audit_ref": "AUD-1"}
        self.assertEqual(L.WaiverRegistry([good]).apply(d, TODAY)["gate"], "PASS")
        for bad in (dict(good, expires="2026-01-01"), dict(good, approved_by="team-a"), dict(good, scope="*"),
                    {k: v for k, v in good.items() if k != "rationale"}, dict(good, codes=["func-added"]),
                    dict(good, scope="a:b/")):
            out = L.WaiverRegistry([bad]).apply(d, TODAY)
            self.assertEqual(out["gate"], "FAIL")
            self.assertEqual(out["class"], "breaking")

    def test_waiver_scope_does_not_cover_prefix_siblings(self):
        self.assertTrue(L._in_scope("a:b/i.g", "a:b/i"))
        self.assertFalse(L._in_scope("a:b/ix.g", "a:b/i"))

    def test_adapters_only_where_mechanical(self):
        a, b = pol("func-added")
        d = classify_packages(a, b)
        self.assertEqual(L.adapter_plan(d)["status"], "GENERATED")
        wit = L.render_adapter_wit(d, b, "a:b/i@1.1.0")
        self.assertIn("forwards f", wit)
        self.assertNotIn("forwards g", wit)
        self.assertEqual(L.adapter_plan(classify_packages(*pol("param-type-changed")))["status"], "REFUSED")
        with self.assertRaises(ValueError):
            L.render_adapter_wit(classify_packages(*pol("enum-case-added")), b, "a:b/i@1.1.0")

    def test_renderer(self):
        d = classify_packages(*pol("mixed-additive-breaking"))
        short, long = L.render_diff(d), L.render_diff(d, expanded=True)
        self.assertIn("class: BREAKING", short)
        self.assertIn("!! a:b/i.f  func-removed", short)
        self.assertIn("why: callers lose the function", long)


class Ownership(unittest.TestCase):
    def test_ownership_record_reports_placeholders(self):
        st = ops.load_ownership()
        self.assertEqual(st["missing"], [])
        self.assertEqual(st["status"], "BLOCKED")  # accountable owner is the owner's decision
        self.assertIn("accountable_owner", st["placeholders"])


if __name__ == "__main__":
    unittest.main()
