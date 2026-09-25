"""govops group tests: components 01-12, 56-65 (stdlib unittest, deterministic).

Run:  cd /home/claude/w && python3 -B -m unittest \
        inv08_dynamic_infrastructure_model.production.tests.test_govops -v
"""
from __future__ import annotations

import copy
import datetime as dt
import importlib
import io
import json
import random
import sys
import tempfile
import threading
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from ...model import Pool, PoolInvariantError
from .. import (backup, concurrency, corpus, envmatrix, evidence, governance, incident,
                license_policy, ownership, pkcore_pin, provenance, pyproject_check, rollout, rtm,
                soak, topology, vuln_policy, waivers)
from ..audit import AuditLog, verify_file
from ..ci import release_check
from ..core import (Inv08Error, Outcome, TrustRoot, canonical, digest, parse_outcome,
                    wrap_provider_error)

PROD = Path(__file__).resolve().parents[1]
PKG = PROD.parent
KEY = b"k" * 32


def _opt(name):
    try:
        return importlib.import_module(f"inv08_dynamic_infrastructure_model.production.{name}")
    except ImportError:
        return None

# ============================================================== 01 pk_core pin


class PkCorePinTest(unittest.TestCase):
    def test_version_parse_positive_and_ordering(self):
        v = [pkcore_pin.parse_version(x) for x in ["1.0.dev1", "1.0a1", "1.0rc2", "1.0", "1.0.post1", "1.1"]]
        keys = [x.key() for x in v]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(pkcore_pin.parse_version("1.0").key(), pkcore_pin.parse_version("1.0.0").key())
        self.assertEqual(pkcore_pin.parse_version("4.2.0+overlay1.0.0").local, "overlay1.0.0")

    def test_version_parse_negative(self):
        for bad in ["", "v1.0", "1..0", "1.0-final", "latest", "1.0+", "x" * 200, None]:
            with self.subTest(bad=bad), self.assertRaises(Inv08Error) as cm:
                pkcore_pin.parse_version(bad)
            self.assertEqual(cm.exception.code, "INV08.PIN.INVALID")

    def test_requirement_specifiers(self):
        r = pkcore_pin.parse_requirement("pk_core>=1.2,<2.0,!=1.5.0")
        self.assertEqual(r.name, "pk-core")
        self.assertTrue(pkcore_pin.satisfies("1.2", r))
        self.assertTrue(pkcore_pin.satisfies("1.9.9", r))
        self.assertFalse(pkcore_pin.satisfies("1.5.0", r))
        self.assertFalse(pkcore_pin.satisfies("2.0", r))
        self.assertFalse(pkcore_pin.satisfies("2.0a1", pkcore_pin.parse_requirement("x<2.0")))
        self.assertFalse(pkcore_pin.satisfies("1.1", r))
        c = pkcore_pin.parse_requirement("pk_core~=1.4.2")
        self.assertTrue(pkcore_pin.satisfies("1.4.9", c))
        self.assertFalse(pkcore_pin.satisfies("1.5.0", c))
        w = pkcore_pin.parse_requirement("pk_core==1.4.*")
        self.assertTrue(pkcore_pin.satisfies("1.4.7", w))
        self.assertFalse(w.exact)
        self.assertTrue(pkcore_pin.parse_requirement("pk_core==1.4.2").exact)

    def test_requirement_negative(self):
        for bad in ["", "pk_core >> 1", "pk_core~=1", "pk_core; python_version>'3'",
                    "pk_core @ https://x/y.whl", "pk_core[extra]==1", "pk_core>=1.0+local"]:
            with self.subTest(bad=bad), self.assertRaises(Inv08Error):
                pkcore_pin.parse_requirement(bad)

    def test_shipped_lock_is_valid_and_unresolved(self):
        lock = pkcore_pin.load_lock()
        self.assertEqual(lock["state"], "UNRESOLVED")
        self.assertIsNone(lock["sha256"])
        self.assertTrue(lock["blocker"])

    def test_lock_validation_negative(self):
        base = pkcore_pin.load_lock()
        bad = dict(base, sha256="ab" * 32)
        self.assertIn("UNRESOLVED lock must not carry a digest", pkcore_pin.validate_lock(bad))
        res = dict(base, state="RESOLVED", requirement="pk_core>=1", version="1.0", wheel="pk_core-1.0-py3-none-any.whl",
                   sha256="zz")
        p = pkcore_pin.validate_lock(res)
        self.assertTrue(any("exact" in x for x in p) and any("sha256" in x for x in p))
        self.assertEqual(pkcore_pin.validate_lock([]), ["lock must be an object"])

    def _resolved(self, tmp, content=b"wheel-bytes"):
        whl = Path(tmp) / "pk_core-1.0-py3-none-any.whl"
        whl.write_bytes(content)
        import hashlib
        return {"schema": "PK_DYN_LOCK/1", "package": "pk_core", "state": "RESOLVED",
                "requirement": "pk_core==1.0", "version": "1.0", "wheel": whl.name,
                "sha256": hashlib.sha256(b"wheel-bytes").hexdigest(), "source": "file:test", "blocker": None}

    def test_wheelhouse_resolves_verified_wheel(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = self._resolved(tmp)
            self.assertEqual(pkcore_pin.resolve_wheelhouse(lock, tmp).name, lock["wheel"])

    def test_wheelhouse_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(Inv08Error) as cm:
                pkcore_pin.resolve_wheelhouse(pkcore_pin.load_lock(), tmp)
            self.assertEqual(cm.exception.code, "INV08.PIN.UNRESOLVED")
            self.assertEqual(cm.exception.outcome, Outcome.BLOCKED)
            lock = self._resolved(tmp, b"tampered")
            with self.assertRaises(Inv08Error) as cm:
                pkcore_pin.resolve_wheelhouse(lock, tmp)
            self.assertEqual(cm.exception.code, "INV08.PIN.HASH_MISMATCH")
            with self.assertRaises(Inv08Error) as cm:
                pkcore_pin.resolve_wheelhouse(lock, "https://mirror.invalid/simple")
            self.assertEqual(cm.exception.code, "INV08.PIN.REMOTE_FORBIDDEN")
            with self.assertRaises(Inv08Error) as cm:
                pkcore_pin.resolve_wheelhouse(lock, Path(tmp) / "nope")
            self.assertEqual(cm.exception.code, "INV08.PIN.NO_WHEEL")

    def test_api_surface_static(self):
        s = pkcore_pin.api_surface()
        for sym in ["pk_core.component.Component", "pk_core.contract.Contract", "pk_core.contract.Slo",
                    "pk_core.contract.Dependency", "pk_core.checklist.ChecklistItem", "pk_core.checklist.Finding",
                    "pk_core.component.Component.satisfied", "pk_core.component.Component._evidence",
                    "pk_core.component.Component.assess_resilience", "pk_core.component.Component.assess_all"]:
            self.assertIn(sym, s)
        self.assertEqual(s, sorted(set(s)))
        self.assertNotIn("pk_core", sys.modules)  # probe did not import pk_core

    def test_compat_blocked_without_pk_core(self):
        def imp(name):
            raise ImportError(name)
        r = pkcore_pin.check_compat(["pk_core.contract.Contract"], imp)
        self.assertEqual(r["state"], "BLOCKED")

    def test_compat_against_fake_pk_core_double(self):
        mods = {"pk_core": types.ModuleType("pk_core"), "pk_core.contract": types.ModuleType("pk_core.contract")}
        mods["pk_core.contract"].Contract = type("Contract", (), {})

        def imp(name):
            if name in mods:
                return mods[name]
            raise ImportError(name)
        ok = pkcore_pin.check_compat(["pk_core.contract.Contract"], imp)
        self.assertEqual(ok["state"], "COMPATIBLE")
        bad = pkcore_pin.check_compat(["pk_core.contract.Contract", "pk_core.contract.Slo",
                                       "pk_core.component.Component"], imp)
        self.assertEqual(bad["state"], "INCOMPATIBLE")
        self.assertEqual(bad["missing"], ["pk_core.contract.Slo", "pk_core.component.Component"])

    def test_cli_status_fails_closed(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = pkcore_pin.main(["status"])
        self.assertEqual(rc, 2)
        self.assertEqual(json.loads(buf.getvalue())["lock_state"], "UNRESOLVED")

# ============================================================== 02 pyproject


@unittest.skipIf(pyproject_check.tomllib is None, "tomllib requires Python >= 3.11")
class PyprojectTest(unittest.TestCase):
    def setUp(self):
        self.data = pyproject_check.load()

    def test_build_system_pep517(self):
        self.assertEqual(self.data["build-system"]["build-backend"], "setuptools.build_meta")
        self.assertTrue(pyproject_check.check(self.data)["ok"], pyproject_check.check(self.data)["errors"])

    def test_identity_version_license(self):
        p = self.data["project"]
        self.assertEqual(p["name"], "inv08-dynamic-infrastructure-model")
        self.assertEqual(p["version"], "4.3.0.dev1")
        v = pkcore_pin.parse_version(p["version"])
        self.assertGreater(v.key(), pkcore_pin.parse_version("4.2.0").key())
        self.assertLess(v.key(), pkcore_pin.parse_version("4.3.0").key())
        self.assertEqual(p["license"]["text"], "LicenseRef-UNASSIGNED")
        self.assertEqual(pyproject_check.check(self.data)["base_version"], "4.2.0")

    def test_dependencies_declared(self):
        p = self.data["project"]
        self.assertEqual(p["dependencies"], [])
        self.assertIn("pk-core", p["optional-dependencies"])
        w = pyproject_check.check(self.data)["warnings"]
        self.assertTrue(any("not pinned" in x for x in w))

    def test_requires_python_and_classifiers(self):
        self.assertEqual(self.data["project"]["requires-python"], ">=3.10")
        bad = copy.deepcopy(self.data)
        bad["project"]["requires-python"] = ">=3.8"
        self.assertFalse(pyproject_check.check(bad)["ok"])
        bad = copy.deepcopy(self.data)
        bad["project"]["classifiers"].append("Programming Language :: Python :: 3.9")
        self.assertFalse(pyproject_check.check(bad)["ok"])

    def test_package_layout_and_data(self):
        r = pyproject_check.check(self.data)
        self.assertIn("inv08_dynamic_infrastructure_model.production", r["packages"])
        self.assertFalse([w for w in r["warnings"] if "matches no file" in w], r["warnings"])

    def test_negative_metadata(self):
        for mut in [lambda d: d["build-system"].update({"build-backend": "flit"}),
                    lambda d: d["project"].update({"name": "Bad_Name"}),
                    lambda d: d["project"].update({"version": "4.2.0+overlay1"}),
                    lambda d: d["project"].update({"dependencies": ["requests"]}),
                    lambda d: d["project"].update({"readme": "nope.md"}),
                    lambda d: d["tool"]["setuptools"]["package-data"].update({"ghost.pkg": ["*.json"]})]:
            d = copy.deepcopy(self.data)
            mut(d)
            with self.subTest():
                self.assertFalse(pyproject_check.check(d)["ok"])

# ============================================================== 03 evidence


class EvidenceTest(unittest.TestCase):
    def _mk(self, tmp):
        (Path(tmp) / "r.json").write_text('{"ok": true}')
        (Path(tmp) / "log.txt").write_text("run")
        return evidence.build_bundle(
            [{"control": "INV-08-C082", "status": "PASS", "detail": "56"},
             {"control": "INV-08-C020", "status": "PASS"}],
            {"INV-08-C082": ["r.json", "log.txt"], "INV-08-C020": ["r.json"]}, tmp, build_id="b1")

    def test_gate_results_machine_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = self._mk(tmp)
            self.assertEqual(b["gate"]["overall"], "PASS")
            self.assertEqual(json.loads(canonical(b)), b)
        self.assertEqual(evidence.overall([{"status": "PASS"}, {"status": "NOT_RUN"}]), "BLOCKED")
        self.assertEqual(evidence.overall([{"status": "FAIL"}, {"status": "BLOCKED"}]), "FAIL")
        self.assertEqual(evidence.overall([]), "FAIL")

    def test_manifest_keyed_by_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = self._mk(tmp)
            self.assertEqual(sorted(b["manifest"]), ["INV-08-C020", "INV-08-C082"])
            with self.assertRaises(ValueError):
                evidence.build_bundle([], {"C-82": ["r.json"]}, tmp, build_id="x")
            with self.assertRaises(ValueError):
                evidence.build_bundle([], {"INV-08-C001": ["../escape"]}, tmp, build_id="x")

    def test_digests_detect_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = self._mk(tmp)
            self.assertEqual(evidence.verify_bundle(b, tmp), (True, []))
            (Path(tmp) / "log.txt").write_text("changed")
            ok, p = evidence.verify_bundle(b, tmp)
            self.assertFalse(ok)
            self.assertIn("INV-08-C082: digest mismatch log.txt", p)
            b2 = copy.deepcopy(b)
            b2["gate"]["results"][0]["status"] = "FAIL"
            self.assertIn("bundle_digest mismatch", evidence.verify_bundle(b2, tmp)[1])

    def test_approvers_unassigned_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = self._mk(tmp)
            self.assertTrue(all(a["identity"] == "UNASSIGNED" for a in b["approvals"]))
            ok, p = evidence.verify_bundle(b, tmp, require_approvals=True)
            self.assertFalse(ok)
            self.assertEqual(len([x for x in p if "UNASSIGNED" in x]), 3)
            t = TrustRoot()
            t.add("ev", KEY)
            s = evidence.sign_bundle(b, t, "ev")
            self.assertTrue(evidence.verify_bundle(s, tmp, trust=t)[0])
            self.assertFalse(evidence.verify_bundle(s, tmp, trust=t, require_production=True)[0])

    def test_verify_command_replays(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = self._mk(tmp)
            bp = Path(tmp) / "bundle.json"
            bp.write_text(json.dumps(b))
            outs = []
            for _ in range(2):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = evidence.main(["verify", str(bp), "--root", tmp])
                outs.append((rc, buf.getvalue()))
            self.assertEqual(outs[0], outs[1])
            self.assertEqual(outs[0][0], 0)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(evidence.main(["verify", str(bp), "--root", tmp, "--require-approvals"]), 1)

# ============================================================== 04 provenance


class ProvenanceTest(unittest.TestCase):
    def _tree(self, tmp):
        (Path(tmp) / "a.py").write_text("x=1\n")
        (Path(tmp) / "sub").mkdir()
        (Path(tmp) / "sub" / "b.json").write_text("{}")
        return Path(tmp)

    def test_sbom_cyclonedx(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(tmp)
            s1 = provenance.sbom(root)
            self.assertEqual(provenance.validate_sbom(s1), [])
            self.assertEqual([c["name"] for c in s1["components"]], ["a.py", "sub/b.json"])
            self.assertEqual(s1, provenance.sbom(root))  # deterministic
            (root / "a.py").write_text("x=2\n")
            self.assertNotEqual(s1["serialNumber"], provenance.sbom(root)["serialNumber"])
        real = provenance.sbom()
        self.assertEqual(provenance.validate_sbom(real), [])
        self.assertTrue(any(c["name"] == "model.py" for c in real["components"]))
        self.assertIn("SHA-256", provenance.validate_sbom({"bomFormat": "CycloneDX", "specVersion": "1.5",
                                                          "serialNumber": "urn:uuid:x",
                                                          "components": [{"name": "z", "hashes": []}]})[0])

    def _env(self, root, trust):
        dig = provenance.file_digests(root, provenance.package_files(root))
        st = provenance.statement(dig, sbom_doc=provenance.sbom(root), builder_id="local-test-builder",
                                  invocation_id="run-1")
        return dig, st, provenance.sign_envelope(st, trust, "rel")

    def test_in_toto_slsa_statement(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = TrustRoot()
            t.add("rel", KEY)
            dig, st, _ = self._env(self._tree(tmp), t)
            self.assertEqual(st["_type"], "https://in-toto.io/Statement/v1")
            self.assertEqual(st["predicateType"], "https://slsa.dev/provenance/v1")
            self.assertEqual({s["name"] for s in st["subject"]}, set(dig))

    def test_signature_nonproduction_and_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = TrustRoot()
            t.add("rel", KEY)
            dig, st, env = self._env(self._tree(tmp), t)
            self.assertFalse(env["signatures"][0]["production"])
            prod = provenance.VerificationPolicy(trusted_kids={"rel"})
            ok, why = prod.verify(env, t, dig)
            self.assertFalse(ok)
            self.assertIn("nonproduction signature rejected by production policy", why)
            dev = provenance.VerificationPolicy(trusted_kids={"rel"}, require_production=False,
                                                trusted_builders={"local-test-builder"})
            self.assertEqual(dev.verify(env, t, dig), (True, []))
            with self.assertRaises(PermissionError):
                t.add("prod", KEY, production=True)

    def test_policy_rejects_mismatch_unsigned_untrusted(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = TrustRoot()
            t.add("rel", KEY)
            t.add("other", b"o" * 32)
            dig, st, env = self._env(self._tree(tmp), t)
            dev = provenance.VerificationPolicy(trusted_kids={"rel"}, require_production=False,
                                                trusted_builders={"ci"})
            bad = dict(dig, **{"a.py": "0" * 64})
            _, why = dev.verify(env, t, bad)
            self.assertIn("artifact a.py digest mismatch", why)
            self.assertIn("untrusted builder 'local-test-builder'", why)
            _, why = dev.verify(dict(env, signatures=[]), t, dig)
            self.assertIn("unsigned", why)
            other = provenance.sign_envelope(st, t, "other")
            self.assertIn("no signature from a trusted key verifies",
                          provenance.VerificationPolicy(trusted_kids={"rel"}, require_production=False).verify(other, t)[1])
            self.assertFalse(dev.verify({"payload": {}}, t)[0])

    def test_ci_release_check(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as meta:
            root = self._tree(tmp)
            t = TrustRoot()
            t.add("rel", KEY)
            _, _, env = self._env(root, t)
            ep, kp = Path(meta) / "env.json", Path(meta) / "k.json"
            ep.write_text(json.dumps(env))
            kp.write_text(json.dumps({"kid": "rel", "key_hex": KEY.hex()}))
            args = ["--root", tmp, "--envelope", str(ep), "--key-file", str(kp)]
            with redirect_stdout(io.StringIO()):
                self.assertEqual(release_check.main(args + ["--allow-nonproduction"]), 0)
                self.assertEqual(release_check.main(args), 1)          # production required -> fail closed
                (root / "a.py").write_text("tampered")
                self.assertEqual(release_check.main(args + ["--allow-nonproduction"]), 1)
                (root / "extra.bin").write_bytes(b"x")
                self.assertEqual(release_check.main(args + ["--allow-nonproduction"]), 1)
                ep.write_text(json.dumps(dict(env, signatures=[])))
                self.assertEqual(release_check.main(args + ["--allow-nonproduction"]), 1)
                self.assertEqual(release_check.main(["--root", tmp, "--envelope", "/nonexistent",
                                                     "--key-file", str(kp)]), 2)

# ============================================================== 05 licence


class LicenseTest(unittest.TestCase):
    def test_project_license_blocked(self):
        self.assertEqual(license_policy.PROJECT_LICENSE, "LicenseRef-UNASSIGNED")
        self.assertFalse((PKG / "LICENSE").exists())
        self.assertEqual(license_policy.compatibility("LicenseRef-UNASSIGNED", [])["state"], "BLOCKED")

    def test_inventory_stdlib_only(self):
        inv = license_policy.inventory({"project": {"dependencies": [],
                                                    "optional-dependencies": {"pk-core": ["pk_core"]}}})
        self.assertEqual([i["name"] for i in inv if i["scope"] == "runtime"], ["python-stdlib"])
        self.assertEqual([i["class"] for i in inv if i["name"] == "pk_core"], ["UNKNOWN"])

    def test_notice_rules(self):
        inv = [{"name": "libA", "scope": "runtime", "license": "Apache-2.0", "bundled": True, "class": "ALLOW"},
               {"name": "libB", "scope": "runtime", "license": "Apache-2.0", "bundled": False, "class": "ALLOW"}]
        n = license_policy.notice(inv)
        self.assertIn("libA under Apache-2.0", n)
        self.assertNotIn("libB", n)
        self.assertEqual(license_policy.notice(license_policy.inventory()).count("includes"), 0)

    def test_classification_and_compatibility(self):
        c = license_policy.classify
        self.assertEqual([c("MIT"), c("GPL-3.0-only"), c("LicenseRef-X"), c(None), c("GPL-2.0-only OR MIT"),
                          c("MIT AND AGPL-3.0-only")], ["ALLOW", "DENY", "UNKNOWN", "UNKNOWN", "ALLOW", "DENY"])
        inv = [{"name": "g", "scope": "runtime", "license": "GPL-3.0-only", "bundled": True, "class": "DENY"}]
        self.assertEqual(license_policy.compatibility("Apache-2.0", inv), {"state": "CONFLICT", "conflicts": ["g"]})
        self.assertEqual(license_policy.compatibility("MIT", [])["state"], "OK")

    def test_ci_gate(self):
        inv = license_policy.inventory({"project": {"optional-dependencies": {"pk-core": ["pk_core"]}}})
        g = license_policy.ci_gate(inv)
        self.assertTrue(g["ok"])
        self.assertEqual(len(g["blockers"]), 1)
        inv.append({"name": "evil", "scope": "runtime", "license": "SSPL-1.0", "bundled": True, "class": "DENY"})
        inv.append({"name": "mystery", "scope": "runtime", "license": None, "bundled": True, "class": "UNKNOWN"})
        g = license_policy.ci_gate(inv)
        self.assertFalse(g["ok"])
        self.assertEqual(len(g["failures"]), 2)

# ============================================================== 06 corpus


class CorpusTest(unittest.TestCase):
    def test_master_scope_blocked(self):
        it = corpus.DEFAULT_MANIFEST["items"][0]
        self.assertEqual((it["path"], it["state"], it["owner"]), ("MASTER.md", "BLOCKED", "UNASSIGNED"))
        self.assertFalse((PKG / "MASTER.md").exists())

    def test_versioning(self):
        old = corpus.DEFAULT_MANIFEST
        new = copy.deepcopy(old)
        new["items"].append({"id": "CORPUS-002", "path": "README.md", "distribution": "bundled",
                             "controls": ["INV-08-C001"], "sha256": "x", "state": "BUNDLED"})
        self.assertEqual(corpus.version_check(old, new), ["corpus content changed without a version bump"])
        new["version"] = "0.2.0"
        self.assertEqual(corpus.version_check(old, new), [])
        self.assertEqual(corpus.version_check(old, copy.deepcopy(old)), [])

    def test_control_linkage(self):
        self.assertEqual(corpus.validate_manifest(corpus.DEFAULT_MANIFEST), [])
        bad = copy.deepcopy(corpus.DEFAULT_MANIFEST)
        bad["items"][0]["controls"] = ["INV-08-C999"]
        self.assertIn("CORPUS-001: unknown control INV-08-C999", corpus.validate_manifest(bad))
        bad["items"][0]["controls"] = []
        self.assertIn("CORPUS-001: no control linkage", corpus.validate_manifest(bad))

    def test_distribution_rules(self):
        from ..core import sha256_hex
        m = copy.deepcopy(corpus.DEFAULT_MANIFEST)
        readme = (PKG / "README.md").read_bytes()
        m["items"].append({"id": "CORPUS-002", "path": "README.md", "distribution": "bundled",
                           "controls": ["INV-08-C001"], "sha256": sha256_hex(readme), "state": "BUNDLED"})
        self.assertEqual(corpus.validate_manifest(m), [])
        m["items"][1]["sha256"] = "0" * 64
        m["items"][0]["sha256"] = "ab"
        p = corpus.validate_manifest(m)
        self.assertIn("CORPUS-002: digest mismatch", p)
        self.assertIn("CORPUS-001: external item must not claim a shipped digest", p)
        m["items"][1]["path"], m["items"][1]["sha256"] = "MASTER.md", None
        self.assertIn("CORPUS-002: bundled file MASTER.md missing", corpus.validate_manifest(m))

    def test_drift_detection(self):
        shipped = corpus.shipped_files()
        cur = corpus.detect_drift((PKG / "README.md").read_text(encoding="utf-8"), shipped)
        self.assertEqual([d for d in cur if d["kind"] == "DRIFT"], [])
        self.assertTrue(any(d["file"] == "MASTER.md" and d["kind"] == "NOTED_ABSENT" for d in cur))
        old = "The package carries `MASTER.md`, the master workflow, next to `CHECKLIST.json`."
        d = corpus.detect_drift(old, shipped)
        self.assertEqual([(x["file"], x["kind"]) for x in d], [("MASTER.md", "DRIFT")])
        self.assertEqual(corpus.detect_drift("", shipped), [])

# ============================================================== docs (07, 09, 10, 62, 63, runbook)


class DocsTest(unittest.TestCase):
    def _doc(self, name):
        return (PROD / "docs" / name).read_text(encoding="utf-8")

    def test_adr_template_and_id(self):
        d = self._doc("07_adr.md")
        self.assertIn("ADR-0001", d)
        self.assertIn("**Status:** PROPOSED", d)
        for h in ["## Template", "## Context", "## Decision", "## Alternatives", "## State representation",
                  "## Dependency inference and simulation assumptions", "## Consequences and review triggers"]:
            self.assertIn(h, d)

    def test_adr_tradeoffs_boundaries_assumptions_consequences(self):
        d = self._doc("07_adr.md")
        for kw in ["System Initiative", "digital twin", "Reversible", "Review when", "Simulation", "INV-06"]:
            self.assertIn(kw.lower(), d.lower())
        self.assertGreaterEqual(d.count("\n| "), 5)   # alternatives table rows

    def test_persistence_doc(self):
        d = self._doc("10_persistence.md")
        for kw in ["Lease data model", "Technology selection - BLOCKED", "Linearizable", "compare-and-swap",
                   "Compaction", "Retention", "PK_DYN_BACKUP/2"]:
            self.assertIn(kw, d)

    def test_incident_vuln_runbook_docs(self):
        self.assertIn("SEV1", self._doc("62_incident_response.md"))
        self.assertIn("critical (>= 9.0)", self._doc("63_vuln_policy.md"))
        rb = self._doc("RUNBOOK.md")
        for h in ["Deployment / activation", "Rollback", "Incident steps", "UNASSIGNED"]:
            self.assertIn(h, rb)

    def test_no_invented_people(self):
        for f in (PROD / "docs").glob("*.md"):
            if f.name[:2] in {"07", "08", "09", "10", "11", "62", "63"} or f.name == "RUNBOOK.md":
                self.assertNotRegex(f.read_text(encoding="utf-8"), r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}")

# ============================================================== 08 ownership


class OwnershipTest(unittest.TestCase):
    def test_raci_valid(self):
        doc = ownership.load()
        self.assertEqual(ownership.validate(doc), [])
        bad = copy.deepcopy(doc)
        bad["roles"][1]["raci"]["design"] = "A"
        self.assertTrue(any("design" in p for p in ownership.validate(bad)))
        bad["roles"][0]["raci"]["release"] = "X"
        self.assertTrue(any("bad RACI" in p for p in ownership.validate(bad)))

    def test_oncall_unassigned_blockers(self):
        b = ownership.blockers(ownership.load())
        self.assertIn("oncall_primary.primary UNASSIGNED", b)
        self.assertIn("oncall_secondary.rotation UNASSIGNED", b)

    def test_security_and_ic_roles(self):
        doc = ownership.load()
        self.assertEqual(doc["security_chain"][-1], "incident_commander")
        self.assertIn("incident_commander.primary UNASSIGNED", ownership.blockers(doc))
        bad = copy.deepcopy(doc)
        bad["security_chain"] = ["ghost"]
        self.assertIn("security_chain references undefined role ghost", ownership.validate(bad))

    def test_vendor_handoff(self):
        doc = ownership.load()
        self.assertTrue(doc["vendors"][0]["handoff"])
        self.assertTrue(any(x.startswith("vendor") for x in ownership.blockers(doc)))

    def test_queryable_metadata(self):
        doc = ownership.load()
        self.assertEqual(ownership.query(doc, "service_owner")["raci"]["design"], "A")
        with self.assertRaises(KeyError):
            ownership.query(doc, "nobody")
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = ownership.main([])
        self.assertEqual(rc, 3)
        self.assertFalse(json.loads(buf.getvalue())["ready"])
        filled = copy.deepcopy(doc)
        for r in filled["roles"]:
            for k in ("primary", "secondary", "contact", "rotation"):
                if k in r:
                    r[k] = "role-alias-placeholder"
        filled["vendors"] = []
        filled["repository"]["team"] = "team-placeholder"
        self.assertTrue(ownership.report(filled)["ready"])

# ============================================================== 09 topology


class TopologyTest(unittest.TestCase):
    def setUp(self):
        self.doc = topology.load()

    def test_shipped_topology_valid(self):
        self.assertEqual(topology.validate(self.doc), [])
        self.assertTrue((PROD / "docs" / "09_topology.md").is_file())

    def test_placement_rules(self):
        d = copy.deepcopy(self.doc)
        d["sites"][1]["instances"].append({"service": "lease_store", "tenant": "tenant-x", "failure_domain": "fd-e1"})
        self.assertTrue(any(p.startswith("T1 site-e") for p in topology.validate(d)))

    def test_failure_domains_and_singletons(self):
        d = copy.deepcopy(self.doc)
        d["sites"][0]["failure_domains"] = ["fd-a1", "fd-a2"]
        self.assertTrue(any(p.startswith("T2") for p in topology.validate(d)))
        d = copy.deepcopy(self.doc)
        d["sites"][0]["instances"].append({"service": "pool_controller", "tenant": "tenant-x", "failure_domain": "fd-a3"})
        self.assertTrue(any(p.startswith("T3") for p in topology.validate(d)))
        d["sites"][0]["instances"].append({"service": "audit_sink", "tenant": "t", "failure_domain": "fd-zz"})
        self.assertTrue(any("unknown failure domain" in p for p in topology.validate(d)))

    def test_tenant_isolation(self):
        d = copy.deepcopy(self.doc)
        d["sites"][0]["instances"].append({"service": "lease_store", "tenant": "tenant-x", "failure_domain": "fd-a3"})
        self.assertTrue(any(p.startswith("T5") for p in topology.validate(d)))
        d = copy.deepcopy(self.doc)
        d["sites"][1]["instances"].append({"service": "pool_controller", "tenant": "tenant-y", "failure_domain": "fd-e1"})
        self.assertIn("T4 site-e: tenant tenant-y has no upstream lease_store", topology.validate(d))
        d["shared_services"][0]["tenant_isolation"] = ""
        self.assertTrue(any(p.startswith("T6") for p in topology.validate(d)))

    def test_dependency_mapping(self):
        planes = {x["plane"] for x in self.doc["dependencies"]}
        self.assertEqual(planes, {"control", "data"})
        d = copy.deepcopy(self.doc)
        d["dependencies"][0]["plane"] = "management"
        self.assertTrue(any(p.startswith("T7") for p in topology.validate(d)))

# ============================================================== 11 requirements (behaviour)


class RequirementBehaviourTest(unittest.TestCase):
    def test_req001_constructor_bounds(self):
        for args in [(True, 2), (-1, 2), (3, 2), (0, 1.5)]:
            with self.assertRaises(ValueError):
                Pool(*args)
        self.assertEqual(Pool(0, 0).max_nodes, 0)

    def test_req002_upper_bound(self):
        p = Pool(min_nodes=0, max_nodes=7)
        for t, d in enumerate([10 ** 100, 0, 28, 29, 10 ** 6]):
            self.assertLessEqual(p.tick(t, d)["size"], 7)

    def test_req003_target_formula(self):
        p = Pool(min_nodes=2, max_nodes=10, per_node=4)
        for t, (d, want) in enumerate([(0, 2), (9, 3), (8, 2), (40, 10), (41, 10), (1, 2)]):
            r = p.tick(t, d)
            self.assertEqual((r["target"], r["size"]), (want, want))

    def test_req004_busy_never_reclaimed(self):
        p = Pool(min_nodes=0, max_nodes=5, lease_ttl=1)
        p.tick(0, 20)
        busy = sorted(p.nodes)[:3]
        for n in busy:
            p.set_busy(n)
        r = p.tick(100, 0)
        self.assertEqual(sorted(p.nodes), busy)
        self.assertFalse(set(r["reclaimed"]) & set(busy))

    def test_req005_busy_renewed(self):
        p = Pool(min_nodes=1, max_nodes=1, lease_ttl=5)
        p.tick(0, 1)
        n = next(iter(p.nodes))
        p.set_busy(n)
        r = p.tick(3, 1)
        self.assertEqual((r["renewed"], p.nodes[n]["expires"]), ([n], 8))

    def test_req006_idle_reclaim(self):
        p = Pool(min_nodes=0, max_nodes=3, lease_ttl=10)
        p.tick(0, 12)
        r = p.tick(1, 4)   # surplus
        self.assertEqual((r["size"], len(r["reclaimed"])), (1, 2))
        r = p.tick(11, 0)  # expired
        self.assertEqual(r["size"], 0)

    def test_req007_admission_lease(self):
        p = Pool(min_nodes=2, max_nodes=2, lease_ttl=4)
        p.tick(5, 0)
        self.assertEqual(list(p.nodes.values()), [{"expires": 9, "busy": False}] * 2)

    def test_req008_transactional(self):
        p = Pool(min_nodes=1, max_nodes=3)
        p.tick(5, 4)
        before = p.snapshot()
        for args in [(4, 1), (6, float("nan")), (6, -1), (6, 1, "x")]:
            with self.assertRaises((ValueError, TypeError)):
                if len(args) == 3:
                    p.tick(args[0], args[1], elapsed_hours=args[2])
                else:
                    p.tick(*args)
            self.assertEqual(p.snapshot(), before)

    def test_req009_input_rejection(self):
        p = Pool(min_nodes=0, max_nodes=2)
        for now, demand in [(float("inf"), 1), (True, 1), (0, True), (0, -0.1)]:
            with self.assertRaises(ValueError):
                p.tick(now, demand)
        with self.assertRaises(ValueError):
            p.tick(0, 1, elapsed_hours=-1)

    def test_req010_restored_state(self):
        p = Pool(min_nodes=0, max_nodes=1)
        p.nodes = {"a": {"expires": 1, "busy": False}, "b": {"expires": 1, "busy": False}}
        with self.assertRaises(PoolInvariantError):
            p.tick(0, 0)
        p.nodes = {"a": {"expires": 1}}
        with self.assertRaises(PoolInvariantError):
            p.tick(0, 0)

    def test_req011_accounting(self):
        p = Pool(min_nodes=3, max_nodes=3)
        p.tick(0, 0, elapsed_hours=2)       # pre-tick size 0
        p.tick(1, 0, elapsed_hours=0.5)     # pre-tick size 3
        self.assertEqual(p.node_hours, 1.5)

    def test_req012_unique_ids(self):
        p = Pool(min_nodes=0, max_nodes=5, nodes={"node-2": {"expires": 99, "busy": True},
                                                 "custom": {"expires": 99, "busy": True}})
        p.tick(0, 20)
        self.assertEqual(len(p.nodes), 5)
        self.assertEqual(len(set(p.nodes)), 5)
        self.assertIn("node-2", p.nodes)

    def test_req013_lifecycle(self):
        rng = random.Random(13)
        p = Pool(min_nodes=0, max_nodes=6, lease_ttl=2)
        for t in range(200):
            busy = {n for n, s in p.nodes.items() if s["busy"]}
            r = p.tick(t, rng.randint(0, 30))
            self.assertFalse(busy - set(p.nodes), "LEASED_BUSY -> ABSENT observed")
            for n in r["reclaimed"]:
                self.assertNotIn(n, busy)
            for n in list(p.nodes):
                if rng.random() < 0.3:
                    p.set_busy(n, not p.nodes[n]["busy"])
        with self.assertRaises(KeyError):
            p.set_busy("ghost")

    def test_req014_determinism(self):
        def run():
            rng = random.Random(7)
            p = Pool(min_nodes=1, max_nodes=8)
            out = []
            for t in range(50):
                out.append(p.tick(t, rng.randint(0, 40)))
                for n in sorted(p.nodes):
                    if rng.random() < 0.2:
                        p.set_busy(n)
            return canonical([out, p.snapshot()])
        self.assertEqual(run(), run())

    def test_req015_bounded_work(self):
        p = Pool(min_nodes=0, max_nodes=4, per_node=2)
        self.assertEqual(p.tick(0, 10 ** 1000)["size"], 4)
        self.assertEqual(p.tick(1, 8)["size"], 4)

    def test_req016_contexts(self):
        doc = topology.load()
        self.assertEqual(set(doc["tiers"]), {"cloud", "datacenter", "near_edge", "far_edge"})
        import inspect
        self.assertNotIn("tier", inspect.signature(Pool).parameters)

    def test_req017_outcomes(self):
        self.assertEqual({o.value for o in Outcome}, {"SUCCESS", "PARTIAL", "DEGRADED", "RETRYABLE_FAILURE",
                                                      "TERMINAL_FAILURE", "OPERATOR_REQUIRED", "BLOCKED"})
        self.assertEqual(parse_outcome("FUTURE_CODE"), Outcome.OPERATOR_REQUIRED)

    def test_req018_single_writer(self):
        self.assertFalse(hasattr(Pool(0, 1), "_lock"))
        self.assertTrue(hasattr(concurrency.LockedPool(Pool(0, 1)), "_lock"))


class RequirementsSpecTest(unittest.TestCase):
    def setUp(self):
        self.doc = rtm.load_json(PROD / "requirements.json")

    def test_shall_ids_and_versions(self):
        self.assertEqual(rtm.validate_requirements(self.doc), [])
        ids = [r["id"] for r in self.doc["requirements"]]
        self.assertEqual(ids, [f"REQ-INV08-{i:03d}" for i in range(1, len(ids) + 1)])
        bad = copy.deepcopy(self.doc)
        bad["requirements"][0]["text"] = "The pool should work."
        bad["requirements"][1]["id"] = "REQ-1"
        self.assertEqual(len(rtm.validate_requirements(bad)), 2)

    def test_inputs_pre_post(self):
        for r in self.doc["requirements"]:
            for k in ("inputs", "preconditions", "postconditions", "code", "controls"):
                self.assertTrue(r.get(k), f"{r['id']} lacks {k}")

    def test_invariants_and_c011_c015(self):
        ctl = {c for r in self.doc["requirements"] for c in r["controls"]}
        self.assertTrue({f"INV-08-C0{i}" for i in range(11, 16)} <= ctl)
        self.assertIn("## State invariants", (PROD / "docs" / "11_requirements.md").read_text(encoding="utf-8"))

    def test_nonfunctional_present(self):
        self.assertGreaterEqual(sum(r["kind"] == "nonfunctional" for r in self.doc["requirements"]), 3)

    def test_change_control(self):
        self.assertEqual(self.doc["baseline_digest"], digest(self.doc["requirements"]))
        self.assertEqual(rtm.check_change_control(self.doc, self.doc), [])
        new = copy.deepcopy(self.doc)
        new["requirements"][0]["text"] += " Additionally SHALL log."
        p = rtm.check_change_control(new, self.doc)
        self.assertIn("REQ-INV08-001 changed without per-requirement version bump", p)
        self.assertIn("requirement set changed without set version bump", p)
        new["requirements"][0]["version"] = 2
        new["version"] = "1.1.0"
        self.assertEqual(rtm.check_change_control(new, self.doc), [])
        gone = copy.deepcopy(self.doc)
        gone["requirements"].pop()
        gone["version"] = "1.2.0"
        self.assertTrue(any("removed without major" in x for x in rtm.check_change_control(gone, self.doc)))

# ============================================================== 12 RTM


class RtmTest(unittest.TestCase):
    def _fixture(self, tmp):
        cdir = Path(tmp) / "components"
        cdir.mkdir()
        good = "inv08_dynamic_infrastructure_model.production.tests.test_govops.RtmTest.test_stable_ids"
        (cdir / "90.json").write_text(json.dumps({"component": 90, "subparts": [
            {"name": "a", "state": "IMPLEMENTED", "spec": "x", "modules": ["m"], "tests": [good]},
            {"name": "b", "state": "IMPLEMENTED", "spec": "x", "modules": [], "tests": ["no.such.Test.t"]},
            {"name": "c", "state": "BLOCKED", "spec": "x", "modules": [], "tests": []}]}))
        (cdir / "91.json").write_text("{not json")
        (cdir / "92.json").write_text(json.dumps({"component": 92}))
        reqs = {"version": "1", "requirements": [
            {"id": "REQ-INV08-001", "text": "x SHALL y", "version": 1, "controls": ["INV-08-C011"],
             "design": ["d"], "code": ["model.py"], "tests": [good]},
            {"id": "REQ-INV08-002", "text": "x SHALL z", "version": 1, "controls": ["INV-08-C999"],
             "design": [], "code": [], "tests": []}]}
        checklist = {"items": [{"check_id": f"INV-08-C{i:03d}"} for i in range(1, 101)]}
        return rtm.build(reqs, cdir, checklist)

    def test_stable_ids(self):
        self.assertTrue(rtm.REQ_RE.match("REQ-INV08-001"))
        self.assertFalse(rtm.REQ_RE.match("REQ-INV08-1"))

    def test_design_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = self._fixture(tmp)
            self.assertEqual(m["rows"][0]["design"], ["d"])
            self.assertEqual(m["coverage"]["controls_total"], 100)

    def test_code_links_and_orphans(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = self._fixture(tmp)
            self.assertEqual(m["orphan_requirements"], ["REQ-INV08-002"])
            self.assertEqual(m["unknown_controls"], ["INV-08-C999"])

    def test_test_links_and_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = self._fixture(tmp)
            self.assertEqual(m["unverified_requirements"], ["REQ-INV08-002"])
            self.assertEqual(m["implemented_but_unverified"], ["90:b"])
            self.assertEqual(len(m["component_errors"]), 2)  # tolerant of malformed files
            self.assertEqual(len(m["uncovered_controls"]), 99)
        self.assertTrue(rtm.resolve_test("inv08_dynamic_infrastructure_model.production.tests.test_govops.RtmTest"))
        self.assertFalse(rtm.resolve_test("inv08_dynamic_infrastructure_model.production.tests.test_govops.RtmTest.nope"))

    def test_real_repository_report(self):
        m = rtm.build(rtm.load_json(PROD / "requirements.json"), PROD / "components",
                      rtm.load_json(PKG / "CHECKLIST.json"))
        self.assertEqual(m["orphan_requirements"], [])
        self.assertEqual(m["unverified_requirements"], [])
        self.assertEqual(m["coverage"]["controls_total"], 100)
        self.assertGreater(len(m["uncovered_controls"]), 0)   # honest: most C-controls lack requirements

# ============================================================== 56 contract tests


class ContractTest(unittest.TestCase):
    GOLDEN = json.loads((PROD / "fixtures" / "govops_golden.json").read_text(encoding="utf-8"))

    def test_serialization_contract_core(self):
        g = self.GOLDEN
        self.assertEqual(canonical({"b": [1, 2.5, None, True], "a": "é"}).decode(), g["canonical_sample"])
        self.assertEqual(digest({"x": 1}), g["digest_sample"])
        for bad in [{"x": float("nan")}, {1: 2}]:
            with self.assertRaises((ValueError, TypeError)):
                canonical(bad)

    def test_schema_contract_if_present(self):
        schemas = _opt("schemas")
        if schemas is None or not hasattr(schemas, "validate_message"):
            self.skipTest("schemas.py (parallel builder) not present")
        gpath = PROD / "fixtures" / "golden" / "pk_dyn_v1.json"
        if gpath.is_file():
            gold = json.loads(gpath.read_text(encoding="utf-8"))
            for name, v in gold.get("valid", {}).items():
                msg = v.get("message", v) if isinstance(v, dict) else v
                with self.subTest(valid=name):
                    self.assertEqual(schemas.decode(schemas.encode(msg)), msg)
            for name, v in gold.get("invalid", {}).items():
                with self.subTest(invalid=name):
                    try:
                        errs = schemas.validate_message(v["message"])
                    except Inv08Error:
                        errs = ["rejected"]
                    self.assertTrue(errs)
        with self.assertRaises(Inv08Error):
            schemas.decode(b"{not json")
        with self.assertRaises(Inv08Error):
            schemas.decode(b'{"schema": "PK_DYN_LEASE/1", "x": NaN}')
        self.assertEqual(schemas.validate_message([]) != [], True)

    def test_authz_contract_if_present(self):
        authz = _opt("authz")
        if authz is None or not hasattr(authz, "Authorizer"):
            self.skipTest("authz.py (parallel builder) not present")
        self.assertEqual(authz.validate_policy(), [])
        a = authz.Authorizer()
        nobody = authz.Principal(sub="anon", roles=(), authn_role="node")
        d = a.evaluate(nobody, "scale", {"type": "pool", "id": "p", "tenant": "t"})
        self.assertFalse(d.allow)   # deny by default
        with self.assertRaises(Inv08Error) as cm:
            a.require(nobody, "scale", {"type": "pool", "id": "p", "tenant": "t"})
        self.assertTrue(cm.exception.code.startswith("INV08.AUTHZ."))
        wild = copy.deepcopy(authz.POLICY)
        next(iter(wild["roles"].values()))["caps"].append("*:pool")
        self.assertTrue(authz.validate_policy(wild))
        authn = _opt("authn")
        if authn is not None:
            self.assertTrue(hasattr(authn, "Authority"))

    def test_error_contract(self):
        g = self.GOLDEN
        e = Inv08Error(code="INV08.GOLDEN.SAMPLE", message="token=abc failed", outcome=Outcome.RETRYABLE_FAILURE)
        self.assertEqual(e.to_dict(), g["error_sample"])
        self.assertEqual(wrap_provider_error("sim", TimeoutError("t"), retryable=True).to_dict(), g["provider_error"])
        with self.assertRaises(ValueError):
            Inv08Error(code="OTHER.X.Y", message="m")
        self.assertEqual([o.value for o in Outcome][:len(g["outcomes"])], g["outcomes"])

    def test_idempotency_retry_contract(self):
        p1, p2 = Pool(1, 3), Pool(1, 3)
        p1.tick(0, 5)
        p2.tick(0, 5)
        self.assertEqual(p1.tick(0, 5), p2.tick(0, 5))           # replay at same now is stable
        self.assertEqual(p1.snapshot(), p2.snapshot())
        t = TrustRoot()
        t.add("golden", b"g" * 32)
        self.assertEqual(t.sign("golden", {"a": 1}), self.GOLDEN["signature_sample"])
        idem = _opt("idempotency")
        if idem is None or not hasattr(idem, "IdempotencyStore"):
            return
        s = idem.IdempotencyStore(clock=lambda: 0.0)
        calls = []
        self.assertEqual(s.execute("p", "op1", {"a": 1}, lambda: calls.append(1) or "r"), "r")
        self.assertEqual(s.execute("p", "op1", {"a": 1}, lambda: calls.append(1) or "r2"), "r")
        self.assertEqual(len(calls), 1)
        with self.assertRaises(Inv08Error):
            s.execute("p", "op1", {"a": 2}, lambda: "x")

    def test_provider_adapter_contract_if_present(self):
        adapters = _opt("adapters")
        if adapters is None or not hasattr(adapters, "make_provider"):
            self.skipTest("adapters.py (parallel builder) not present")
        for kind in adapters.KINDS:
            with self.subTest(kind=kind):
                prov = adapters.make_provider(kind)
                for m in ("capabilities", "create", "drain", "delete", "list"):
                    self.assertTrue(callable(getattr(prov, m)))
                r1 = prov.create("n1", {}, idempotency_key="k1", fence=1)
                r2 = prov.create("n1", {}, idempotency_key="k1", fence=1)
                self.assertEqual(r1, r2)
                self.assertIn(r1["state"], adapters.NORMAL_STATES)
                self.assertIn("n1", prov.list())

    def test_golden_pool_fixture(self):
        g = self.GOLDEN
        p = Pool(min_nodes=1, max_nodes=5)
        seq = [p.tick(0, 1000)]
        p.set_busy("node-1")
        p.set_busy("node-2")
        seq += [p.tick(20, 0), p.tick(21, 9)]
        self.assertEqual(json.loads(json.dumps(seq)), g["pool_sequence"])
        self.assertEqual(json.loads(json.dumps(p.snapshot())), g["pool_snapshot"])
        self.assertEqual(set(g["pool_sequence"][0]), {"size", "target", "added", "reclaimed", "renewed",
                                                       "demand", "node_hours"})

# ============================================================== 57 env matrix


class EnvMatrixTest(unittest.TestCase):
    def test_cpu_arch_matrix(self):
        o = envmatrix.observe()
        self.assertTrue(o["arch"])
        fake_plat = types.SimpleNamespace(machine=lambda: "AMD64", python_implementation=lambda: "CPython",
                                          system=lambda: "Linux")
        self.assertEqual(envmatrix.observe(platform_mod=fake_plat)["arch"], "x86_64")
        r = envmatrix.qualify({**o, "arch": "riscv64"})
        self.assertIn("arch", r["unsupported_observed"])

    def test_python_matrix(self):
        r = envmatrix.qualify()
        py = [c for c in r["cells"] if c["dimension"] == "python"]
        cur = f"{sys.version_info[0]}.{sys.version_info[1]}"
        self.assertEqual({c["value"]: c["state"] for c in py}[cur], "PASS")
        self.assertTrue(all(c["state"] == "NOT_RUN" for c in py if c["value"] != cur))
        fake_sys = types.SimpleNamespace(version_info=(3, 9, 0))
        old = envmatrix.qualify(envmatrix.observe(sys_mod=fake_sys))
        self.assertIn("python<3.10", old["unsupported_observed"])

    def test_hypervisor_provider_matrix(self):
        r = envmatrix.qualify()
        hv = {c["value"]: c["state"] for c in r["cells"] if c["dimension"] == "hypervisor"}
        self.assertEqual(set(hv.values()), {"NOT_RUN"})
        self.assertEqual([c["state"] for c in r["cells"] if c["dimension"] == "provider"], ["PASS"])
        m = dict(envmatrix.DECLARED, provider=["none", "aws"])
        self.assertIn("BLOCKED", [c["state"] for c in envmatrix.qualify(declared=m)["cells"]])

    def test_protocol_matrix(self):
        r = envmatrix.qualify()
        proto = [c for c in r["cells"] if c["dimension"] == "protocol"]
        self.assertEqual(len(proto), 4)
        self.assertTrue(all(c["state"] == "PASS" for c in proto))

    def test_qualification_report(self):
        r1, r2 = envmatrix.qualify(), envmatrix.qualify()
        self.assertEqual(r1["digest"], r2["digest"])
        self.assertFalse(r1["certified"])
        self.assertTrue(all(s["ok"] for s in r1["smoke"]))

# ============================================================== 58 concurrency


class _HookPool(Pool):
    """Deterministically interleaves a foreign set_busy between tick's copy and commit."""
    hook = None

    def _next_node_id(self, nodes, counter):
        if self.hook:
            h, self.hook = self.hook, None
            h()
        return super()._next_node_id(nodes, counter)


class ConcurrencyTest(unittest.TestCase):
    def test_model_pool_not_thread_safe_lost_update(self):
        p = _HookPool(min_nodes=1, max_nodes=4)
        p.tick(0, 4)                                   # one node
        n = next(iter(p.nodes))
        p.hook = lambda: p.set_busy(n, True)          # lands mid-tick
        p.tick(1, 8)                                  # adds a node -> hook fires
        self.assertFalse(p.nodes[n]["busy"], "documented defect: concurrent set_busy lost")

    def test_locked_pool_serializes(self):
        base = _HookPool(min_nodes=1, max_nodes=4)
        lp = concurrency.LockedPool(base)
        lp.tick(0, 4)
        n = next(iter(base.nodes))
        started, release = threading.Event(), threading.Event()

        def hook():
            started.set()
            release.wait(5)
        base.hook = hook
        t1 = threading.Thread(target=lambda: lp.tick(1, 8))
        t1.start()
        started.wait(5)
        t2 = threading.Thread(target=lambda: lp.set_busy(n, True))
        t2.start()
        t2.join(0.05)
        self.assertTrue(t2.is_alive())               # blocked behind tick
        release.set()
        t1.join(5)
        t2.join(5)
        self.assertTrue(base.nodes[n]["busy"])       # no lost update

    def test_concurrent_lease_acquisition(self):
        lt = concurrency.LeaseTable("t1")
        ep = lt.elect("c1")
        wins, errs = [], []
        barrier = threading.Barrier(16)

        def worker(i):
            barrier.wait()
            try:
                wins.append(lt.acquire("node-1", f"h{i}", 0, 10, epoch=ep))
            except Inv08Error as e:
                errs.append(e.code)
        ts = [threading.Thread(target=worker, args=(i,)) for i in range(16)]
        [t.start() for t in ts]
        [t.join(5) for t in ts]
        self.assertEqual(len(wins), 1)
        self.assertEqual(set(errs), {"INV08.LEASE.HELD"})

    def test_cas_and_fencing_race(self):
        lt = concurrency.LeaseTable("t1")
        ep = lt.elect("c1")
        l1 = lt.acquire("n", "a", 0, 1, epoch=ep)
        ok = lt.cas("n", l1.revision, l1.fence, epoch=ep, busy=True)
        with self.assertRaises(Inv08Error) as cm:
            lt.cas("n", l1.revision, l1.fence, epoch=ep, busy=False)     # lost CAS
        self.assertEqual((cm.exception.code, cm.exception.retryable), ("INV08.LEASE.CAS_CONFLICT", True))
        lt.cas("n", ok.revision, ok.fence, epoch=ep, busy=False)
        lt.reclaim_expired(5, epoch=ep)
        l2 = lt.acquire("n", "b", 5, 10, epoch=ep)
        self.assertGreater(l2.fence, l1.fence)
        with self.assertRaises(Inv08Error) as cm:
            lt.cas("n", l2.revision, l1.fence, epoch=ep, busy=True)      # stale holder
        self.assertEqual(cm.exception.code, "INV08.LEASE.STALE_FENCE")
        with self.assertRaises(ValueError):
            lt.cas("n", l2.revision, l2.fence, epoch=ep, holder="x")

    def test_dual_leader_stale_writer(self):
        lt = concurrency.LeaseTable("t1")
        old = lt.elect("c1")
        new = lt.elect("c2")
        with self.assertRaises(Inv08Error) as cm:
            lt.acquire("n", "c1", 0, 5, epoch=old)
        self.assertEqual(cm.exception.code, "INV08.LEASE.STALE_EPOCH")
        self.assertFalse(cm.exception.retryable)
        lt.acquire("n", "c2", 0, 5, epoch=new)
        with self.assertRaises(Inv08Error):
            lt.reclaim_expired(100, epoch=old)
        self.assertIsNotNone(lt.get("n"))

    def test_reconcile_vs_expiry_race(self):
        lt = concurrency.LeaseTable("t1")
        ep = lt.elect("c")
        for i in range(50):
            lt.acquire(f"n{i}", "h", 0, 1, epoch=ep)
        barrier = threading.Barrier(2)
        marked = []

        def renewer():
            barrier.wait()
            for i in range(50):
                cur = lt.get(f"n{i}")
                if cur is None:
                    continue
                try:
                    lt.cas(f"n{i}", cur.revision, cur.fence, epoch=ep, busy=True, expires=100)
                    marked.append(f"n{i}")
                except Inv08Error:
                    pass

        def reaper():
            barrier.wait()
            for _ in range(20):
                lt.reclaim_expired(5, epoch=ep)
        ts = [threading.Thread(target=renewer), threading.Thread(target=reaper)]
        [t.start() for t in ts]
        [t.join(5) for t in ts]
        for n in marked:
            self.assertIsNotNone(lt.get(n), f"busy/renewed {n} reclaimed")
        self.assertTrue(all(l.busy for l in lt.all().values()))

    def test_deterministic_stress_invariants(self):
        for seed in range(3):
            rng = random.Random(seed)
            lp = concurrency.LockedPool(Pool(min_nodes=1, max_nodes=12, lease_ttl=2))
            clock = [0]
            clock_lock = threading.Lock()
            errors = []

            def worker(wseed):
                r = random.Random(wseed)
                for _ in range(150):
                    try:
                        if r.random() < 0.5:
                            with clock_lock:
                                clock[0] += 1
                                now = clock[0]
                                lp.tick(now, r.randint(0, 60))
                        else:
                            snap = lp.snapshot()
                            if snap["nodes"]:
                                try:
                                    lp.set_busy(r.choice(sorted(snap["nodes"])), r.random() < 0.5)
                                except KeyError:
                                    pass   # reclaimed between snapshot and set_busy: legal
                        if lp.check_invariants():
                            errors.append(lp.check_invariants())
                    except Exception as exc:  # noqa: BLE001
                        errors.append(repr(exc))
            ts = [threading.Thread(target=worker, args=(rng.random(),)) for _ in range(6)]
            [t.start() for t in ts]
            [t.join(10) for t in ts]
            self.assertEqual(errors, [])

# ============================================================== 59 soak


class SoakTest(unittest.TestCase):
    def test_soak_profiles_compressed(self):
        for prof in ("soak_72h", "soak_7d"):
            r = soak.run(prof, pools=5)
            self.assertEqual(r.violations, [])
            self.assertEqual(r.ticks, soak.PROFILES[prof]["hours"] * 2)
        r = soak.run("soak_72h", pools=2, tick_hours=0.5, epochs=1)
        self.assertEqual(r.ticks, 144)

    def test_burst_and_churn(self):
        for prof in ("burst", "churn"):
            r = soak.run(prof, pools=10, max_nodes=15)
            self.assertEqual(r.violations, [])
            self.assertEqual(r.max_size_seen, 15)
        with self.assertRaises(ValueError):
            soak.demand_at("nope", 0, random.Random(0), 1)

    def test_large_fleet_synthetic(self):
        r = soak.run("churn", pools=150, max_nodes=40, epochs=1)
        self.assertEqual((r.pools, r.violations), (150, []))

    def test_leak_detection(self):
        clean = soak.run("burst", pools=5)
        self.assertLess(clean.mem_growth_bytes, 64 * 1024)
        self.assertIn(clean.fd_growth, (0, None))
        sink = []

        class LeakyPool(Pool):
            def tick(self, *a, **kw):
                sink.append(bytearray(2048))
                return super().tick(*a, **kw)
        leaky = soak.run("burst", pools=5, pool_factory=LeakyPool)
        self.assertTrue(any("memory growth" in str(v) for v in leaky.violations))

    def test_saturation_recovery_convergence(self):
        r = soak.run("burst", pools=5, max_nodes=8, lease_ttl=4)
        self.assertTrue(r.converged)
        self.assertLessEqual(r.convergence_ticks, 5)
        self.assertEqual(r.max_size_seen, 8)            # saturated at bound, never above

# ============================================================== 60 rollout


def _fleet(n=40, sites=4, bad_version=None, bad_ids=None):
    def health(m, v):
        bad = v == bad_version and (bad_ids is None or m.id in bad_ids)
        return {"error_rate": 0.2 if bad else 0.0, "invariants_ok": not bad}
    ms = [rollout.Member(f"m{i:03d}", f"s{i % sites}", "1.0") for i in range(n)]
    f = rollout.SimFleet(ms, health)
    for m in ms:
        m.metrics = health(m, "1.0")
    return f


class RolloutTest(unittest.TestCase):
    def test_canary_selection(self):
        ms = _fleet(100).members.values()
        c = rollout.select_canary(list(ms), 0.05, salt="r1")
        self.assertEqual(len(c), 5)
        self.assertEqual(len({_fleet(100).members[i].site for i in c}), 4)   # site spread
        self.assertEqual(c, rollout.select_canary(list(ms), 0.05, salt="r1"))
        self.assertNotEqual(c, rollout.select_canary(list(ms), 0.05, salt="r2"))
        self.assertEqual(len(rollout.select_canary(list(ms)[:3], 0.01, salt="x")), 1)
        self.assertEqual(len(rollout.select_canary(list(ms), 1.0, salt="x")), 10)  # capped at max_fraction
        with self.assertRaises(ValueError):
            rollout.select_canary(list(ms), 0, salt="x")

    def test_progressive_stages(self):
        f = _fleet(200)
        plan = rollout.stage_plan(list(f.members.values()), salt="s")
        self.assertEqual([len(s) for s in plan], [2, 18, 80, 100])
        flat = [m for s in plan for m in s]
        self.assertEqual(sorted(flat), sorted(f.members))

    def test_health_gate(self):
        self.assertEqual(rollout.gate([{"error_rate": 0.0, "invariants_ok": True}]), (True, []))
        ok, why = rollout.gate([{"error_rate": 0.5, "invariants_ok": False}])
        self.assertFalse(ok)
        self.assertEqual(len(why), 2)
        self.assertFalse(rollout.gate([{}])[0])     # missing metrics fail closed

    def test_rollback_triggers(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit = AuditLog(Path(tmp) / "a.jsonl")
            f = _fleet(40, bad_version="2.0")
            r = rollout.rollout(f, "2.0", salt="s", audit=audit)
            self.assertEqual((r.status, r.stages_completed), ("ROLLED_BACK", 0))
            ok, _, entries = verify_file(Path(tmp) / "a.jsonl")
            self.assertTrue(ok)
            self.assertEqual([e["action"] for e in entries], ["stage", "rollback"])
        f = _fleet(40)
        r = rollout.rollout(f, "2.0", salt="s", abort=lambda i: i == 2)
        self.assertEqual((r.status, r.stages_completed, r.reasons), ("ROLLED_BACK", 2, ["manual abort"]))
        f = _fleet(40)
        self.assertEqual(rollout.rollout(f, "2.0", salt="s").status, "COMPLETED")
        self.assertTrue(all(m.version == "2.0" for m in f.members.values()))

    def test_rollback_execution_and_verify(self):
        f = _fleet(100, bad_version="2.0", bad_ids={"m050"})
        r = rollout.rollout(f, "2.0", salt="s")
        self.assertEqual(r.status, "ROLLED_BACK")
        self.assertTrue(r.verified)
        self.assertTrue(all(m.version == "1.0" for m in f.members.values()))
        self.assertFalse(rollout.verify_rollback(f, {"m000": "9.9"}))

# ============================================================== 61 backup


class BackupTest(unittest.TestCase):
    def _pool(self):
        p = Pool(min_nodes=1, max_nodes=6, lease_ttl=5)
        p.tick(0, 17)
        p.set_busy(sorted(p.nodes)[0])
        p.tick(1, 9)
        return p

    def setUp(self):
        self.t = TrustRoot()
        self.t.add("bk", KEY)

    def test_backup_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            man = backup.write_backup(self._pool(), Path(tmp) / "b1", self.t, "bk", created=10.0)
            self.assertEqual(man["schema"], "PK_DYN_BACKUP/2")
            st = json.loads((Path(tmp) / "b1" / "state.json").read_text())
            self.assertEqual(st["format"], 2)
            with self.assertRaises(FileExistsError):
                backup.write_backup(self._pool(), Path(tmp) / "b1", self.t, "bk", created=11.0)

    def test_integrity_hmac_and_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "b"
            backup.write_backup(self._pool(), d, self.t, "bk", created=1.0)
            self.assertEqual(backup.verify_backup(d, self.t), [])
            other = TrustRoot()
            other.add("bk", b"x" * 32)
            self.assertIn("manifest signature invalid", backup.verify_backup(d, other))
            (d / "state.json").write_bytes((d / "state.json").read_bytes().replace(b'"busy":true', b'"busy":false'))
            self.assertIn("digest mismatch state.json", backup.verify_backup(d, self.t))
            with self.assertRaises(Inv08Error):
                backup.restore(d, self.t, workdir=tmp)
            (d / "manifest.json").write_text("garbage")
            self.assertTrue(backup.verify_backup(d, self.t)[0].startswith("manifest unreadable"))

    def test_restore_isolated_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._pool()
            d = Path(tmp) / "b"
            backup.write_backup(p, d, self.t, "bk", created=1.0)
            q, iso = backup.restore(d, self.t, workdir=tmp)
            self.assertNotEqual(iso, d)
            self.assertEqual(q.snapshot(), p.snapshot())
            with self.assertRaises(ValueError):
                q.tick(0, 0)       # time watermark restored: regression rejected
            # a state that violates invariants but carries a valid signature
            bad = Path(tmp) / "bad"
            bad.mkdir()
            state = {"format": 2, "pool": dict(p.snapshot(), max_nodes=1), "meta": {}}
            from ..core import sha256_hex
            (bad / "state.json").write_bytes(canonical(state))
            body = {"schema": backup.SCHEMA, "files": {"state.json": sha256_hex(canonical(state))}, "created": 1.0}
            (bad / "manifest.json").write_bytes(canonical(dict(body, signature=self.t.sign("bk", body))))
            with self.assertRaises(Inv08Error) as cm:
                backup.restore(bad, self.t, workdir=tmp)
            self.assertEqual(cm.exception.code, "INV08.BACKUP.VALIDATION")

    def test_schema_migration(self):
        v1 = {"min": 1, "max": 4, "ttl": 3, "nodes": {"node-1": 5, "node-7": 6}, "node_hours": 2}
        v2 = backup.migrate(v1)
        self.assertEqual(v2["format"], 2)
        p = backup.pool_from_state(v1)
        self.assertEqual(sorted(p.nodes), ["node-1", "node-7"])
        self.assertEqual(p.tick(6, 16)["size"], 4)
        self.assertEqual(backup.migrate(v2), v2)
        with self.assertRaises(Inv08Error):
            backup.migrate({"format": 9})

    def test_reconstruction(self):
        leases = {"node-1": {"expires": 10, "busy": True}, "node-2": {"expires": 10}, "node-3": {"expires": 4}}
        r = backup.reconstruct(leases, ["node-1", "node-2", "rogue-9"], min_nodes=1, max_nodes=5)
        self.assertEqual((r["lost_leases"], r["leaked_nodes"], r["outcome"]),
                         (["node-3"], ["rogue-9"], "OPERATOR_REQUIRED"))
        self.assertTrue(r["pool"].nodes["node-1"]["busy"])
        ok = backup.reconstruct({"a": {"expires": 1}}, ["a"], min_nodes=0, max_nodes=1)
        self.assertEqual(ok["outcome"], "SUCCESS")
        over = backup.reconstruct({"a": {"expires": 1}, "b": {"expires": 1}}, ["a", "b"], min_nodes=0, max_nodes=1)
        self.assertNotIn("pool", over)

# ============================================================== 62 incident


class IncidentTest(unittest.TestCase):
    def test_severity_taxonomy(self):
        self.assertEqual([incident.classify(s) for s in [
            {"busy_reclaimed": 1}, {"size_over_max": 1}, {"audit_chain_broken": True}, {"failed_ticks": 2},
            {"lease_store_down": True}, {"leaked_nodes": 3}, {"slo_budget_used": 0.6}, {"failed_ticks": 1}, {}]],
            ["SEV1", "SEV1", "SEV1", "SEV2", "SEV2", "SEV3", "SEV3", "SEV4", "SEV4"])

    def test_paging_escalation(self):
        e0 = incident.escalation("SEV1", 0)
        self.assertEqual(e0["level"], 0)
        self.assertTrue(e0["blocked"])
        self.assertIn("incident_commander", e0["unassigned"])
        e = incident.escalation("SEV3", 125)
        self.assertEqual((e["level"], e["page"]), (2, ["oncall_primary", "oncall_secondary", "incident_commander"]))
        self.assertEqual(incident.escalation("SEV4", 10)["page"], [])

    def test_containment_safe_mode(self):
        p = Pool(min_nodes=0, max_nodes=5, lease_ttl=2)
        sm = incident.SafeModePool(p)
        sm.tick(0, 20)
        sm.frozen = True
        r = sm.tick(10, 0)
        self.assertEqual((r["size"], r["reclaimed"]), (5, []))
        self.assertEqual(len(sm.suppressed), 1)
        self.assertTrue(all(s["expires"] >= 12 for s in p.nodes.values()))
        with self.assertRaises(ValueError):
            sm.tick(5, 0)                    # time regression still enforced
        self.assertLessEqual(sm.tick(11, 10 ** 9)["size"], 5)
        sm.frozen = False
        self.assertEqual(sm.tick(20, 0)["size"], 0)

    def test_recovery_validation(self):
        p = Pool(min_nodes=1, max_nodes=3)
        p.tick(0, 12)
        busy = sorted(p.nodes)[:1]
        p.set_busy(busy[0])
        self.assertEqual(incident.recovery_validation(p, expected_busy=set(busy)), [])
        self.assertTrue(incident.recovery_validation(p, expected_busy={"ghost"}))
        p.nodes["x"] = {"expires": float("nan"), "busy": False}
        self.assertTrue(any("state invalid" in x for x in incident.recovery_validation(p, expected_busy=set())))

    def test_post_incident_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit = AuditLog(Path(tmp) / "a.jsonl")
            pi = incident.PostIncident("INC-1", "SEV2")
            pi.add_event(1, "oncall", "paged")
            pi.add_event(2, "oncall", "safe mode on")
            with self.assertRaises(ValueError):
                pi.add_event(1, "x", "late")
            pi.add_action("add fencing to adapter", 100)
            rec = pi.record(audit)
            self.assertTrue(rec["complete"])
            self.assertEqual(rec["blockers"], ["add fencing to adapter"])
            self.assertTrue(verify_file(Path(tmp) / "a.jsonl")[0])

# ============================================================== 63 vuln policy


class VulnPolicyTest(unittest.TestCase):
    P = vuln_policy.load()
    D = dt.date(2026, 9, 1)

    def test_sla_matrix(self):
        self.assertEqual([vuln_policy.severity(s, self.P) for s in (10, 9.0, 8.9, 4.0, 0.1, 0)],
                         ["critical", "critical", "high", "medium", "low", "none"])
        for bad in (-1, 11, True, "9"):
            with self.assertRaises(ValueError):
                vuln_policy.severity(bad, self.P)
        self.assertEqual(vuln_policy.due("critical", self.D, self.P)["fix_by"], dt.date(2026, 9, 8))
        self.assertIsNone(vuln_policy.due("none", self.D, self.P)["fix_by"])

    def test_support_eol_windows(self):
        p = copy.deepcopy(self.P)
        self.assertTrue(vuln_policy.supported("4.2.0", p, self.D)["supported"])
        p["releases"] = [{"version": "4.4.0", "superseded": None}, {"version": "4.3.0", "superseded": "2026-01-01"},
                         {"version": "4.2.0", "superseded": "2025-06-01"}]
        self.assertFalse(vuln_policy.supported("4.2.0", p, self.D)["supported"])
        self.assertEqual(vuln_policy.supported("4.3.1", p, dt.date(2026, 3, 1))["eol"], "2026-06-30")
        self.assertIn("EOL", vuln_policy.supported("4.3.1", p, self.D)["reason"])
        self.assertFalse(vuln_policy.supported("9.0", p, self.D)["supported"])

    def test_patch_intake(self):
        t = vuln_policy.intake({"id": "ADV-1", "cvss": 7.5, "disclosed": self.D}, self.P, dt.date(2026, 10, 5))
        self.assertEqual((t["severity"], t["overdue"], t["route"]), ("high", True, "scheduled-patch"))
        with self.assertRaises(ValueError):
            vuln_policy.intake({"id": "x"}, self.P, self.D)

    def test_emergency_release_routing(self):
        t = vuln_policy.intake({"id": "ADV-2", "cvss": 9.8, "disclosed": self.D}, self.P, self.D)
        self.assertTrue(t["emergency_release"])
        self.assertEqual(t["route"], "emergency-release")

    def test_upgrade_enforcement_and_notification(self):
        adv = [{"id": "ADV-3", "cvss": 9.1, "disclosed": self.D, "fixed_in": "4.2.1"}]
        r = vuln_policy.enforce_upgrade("4.2.0", adv, self.P, dt.date(2026, 9, 30))
        self.assertFalse(r["allowed"])
        self.assertTrue(r["notification_blocked"])
        self.assertTrue(vuln_policy.enforce_upgrade("4.2.0", adv, self.P, dt.date(2026, 9, 3))["allowed"])
        self.assertTrue(vuln_policy.enforce_upgrade("4.2.1", adv, self.P, dt.date(2026, 9, 30))["allowed"])

# ============================================================== 64 governance


class GovernanceTest(unittest.TestCase):
    D = governance.DAY

    def _rec(self, kind, ts, reviewer="reviewer-alias", subj="sha256:" + "a" * 64):
        return governance.ReviewRecord(kind, ts, reviewer, subj, [])

    def _st(self, recs, now, **kw):
        return {s["kind"]: s for s in governance.status(recs, now, **kw)}

    def test_access_review(self):
        s = self._st([self._rec("access", 0)], 89 * self.D)
        self.assertFalse(s["access"]["overdue"])
        s = self._st([self._rec("access", 0)], 95 * self.D)
        self.assertEqual((s["access"]["level"], s["access"]["escalate_to"]), (1, "service_owner"))

    def test_policy_config_review(self):
        s = self._st([self._rec("policy_config", 0)], (180 + 20) * self.D)
        self.assertEqual(s["policy_config"]["level"], 2)

    def test_dependency_sbom_review(self):
        sb = digest(provenance.sbom())
        s = self._st([self._rec("dependency_sbom", 0, subj=sb)], 10 * self.D,
                     current_subjects={"dependency_sbom": sb})
        self.assertFalse(s["dependency_sbom"]["overdue"])
        s = self._st([self._rec("dependency_sbom", 0, subj=sb)], 10 * self.D,
                     current_subjects={"dependency_sbom": "sha256:changed"})
        self.assertTrue(s["dependency_sbom"]["never_reviewed"])

    def test_architecture_review(self):
        s = self._st([], 0)
        self.assertTrue(all(v["never_reviewed"] and v["level"] == 3 for v in s.values()))
        s = self._st([self._rec("architecture_adr", 0)], 800 * self.D)
        self.assertEqual(s["architecture_adr"]["escalate_to"], "incident_commander")

    def test_evidence_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit = AuditLog(Path(tmp) / "g.jsonl")
            e = governance.record_review(self._rec("access", 5.0), audit)
            self.assertEqual(e["action"], "review.access")
            for bad in [self._rec("access", 6, reviewer="UNASSIGNED"), self._rec("nope", 6),
                        self._rec("access", 6, subj="md5:x")]:
                with self.assertRaises(ValueError):
                    governance.record_review(bad, audit)
            self.assertTrue(verify_file(Path(tmp) / "g.jsonl")[0])

# ============================================================== 65 waivers


class WaiverTest(unittest.TestCase):
    PRI = {1: "P0", 5: "P1"}
    D = waivers.DAY

    def _w(self, **kw):
        w = {"id": "WVR-0001", "component": 5, "check": 7, "kind": "waiver", "owner": "owner-alias",
             "approver": "approver-alias", "created": 0.0, "expires": 30 * self.D, "review_by": 20 * self.D,
             "compensating_controls": ["manual licence review"], "residual_risk": "medium", "rationale": "r"}
        w.update(kw)
        return w

    def test_schema(self):
        self.assertEqual(waivers.validate(self._w(), priorities=self.PRI), [])
        self.assertTrue(waivers.validate(self._w(id="W1", kind="x", check=40), priorities=self.PRI))
        self.assertEqual(waivers.load(), [])

    def test_owner_approver(self):
        for kw in [{"owner": "UNASSIGNED"}, {"approver": ""}, {"approver": "owner-alias"}]:
            with self.subTest(kw=kw):
                self.assertTrue(waivers.validate(self._w(**kw), priorities=self.PRI))

    def test_expiry(self):
        self.assertIn("expires must be after created", waivers.validate(self._w(expires=0.0), priorities=self.PRI))
        self.assertTrue(waivers.validate(self._w(expires=91 * self.D, review_by=1.0), priorities=self.PRI))
        self.assertTrue(waivers.validate(self._w(residual_risk="high", expires=31 * self.D, review_by=1.0),
                                         priorities=self.PRI))
        self.assertIn("review_by after expiry", waivers.validate(self._w(review_by=31 * self.D), priorities=self.PRI))

    def test_compensating_controls(self):
        self.assertIn("compensating controls required",
                      waivers.validate(self._w(compensating_controls=[]), priorities=self.PRI))
        self.assertTrue(waivers.validate(self._w(residual_risk="none"), priorities=self.PRI))

    def test_gate_enforcement(self):
        g = waivers.gate([(5, 7), (5, 20)], [self._w()], now=1.0, priorities=self.PRI)
        self.assertEqual((g["pass"], g["blocking"]), (False, [[5, 20]]))
        g = waivers.gate([(5, 7)], [self._w()], now=1.0, priorities=self.PRI)
        self.assertTrue(g["pass"])
        g = waivers.gate([(5, 7)], [self._w()], now=20 * self.D, priorities=self.PRI)
        self.assertEqual(g["alerts"], ["WVR-0001"])                       # expiry alert
        g = waivers.gate([(5, 7)], [self._w()], now=31 * self.D, priorities=self.PRI)
        self.assertFalse(g["pass"])                                       # expired -> blocking
        self.assertEqual(g["invalid"][0]["errors"], ["expired"])
        p0 = self._w(component=1, check=12)
        g = waivers.gate([(1, 12)], [p0], now=1.0, priorities=self.PRI)
        self.assertFalse(g["pass"])                                       # P0 implementation unwaivable
        self.assertIn("unwaivable", g["invalid"][0]["errors"][0])
        self.assertTrue(waivers.gate([(1, 1)], [self._w(component=1, check=1)], now=1.0, priorities=self.PRI)["pass"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
