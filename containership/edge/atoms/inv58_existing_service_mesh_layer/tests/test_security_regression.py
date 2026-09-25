"""MC-016 / MC-030: threat-model-derived security regression suite.

Every threat in governance/threat_model.json must name >=1 test that exists;
every defect remediated in 4.2.0 and 4.3.0 has a regression case here.
"""
from __future__ import annotations

import ast
import json
import unittest

from _support import CTRL_A, NODE, PKG_DIR, Clock, errors, make_service, mesh, token

TM = json.loads((PKG_DIR / "governance" / "threat_model.json").read_text())


def _all_tests():
    names = set()
    for p in (PKG_DIR / "tests").glob("test_*.py"):
        tree = ast.parse(p.read_text())
        for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            for fn in cls.body:
                if isinstance(fn, ast.FunctionDef) and fn.name.startswith("test"):
                    names.add(f"{p.stem}.{cls.name}.{fn.name}")
    return names


class ThreatTraceTest(unittest.TestCase):
    def test_every_threat_maps_to_existing_tests(self):
        tests = _all_tests()
        self.assertGreaterEqual(len(TM["threats"]), 15)
        for t in TM["threats"]:
            self.assertTrue(t["tests"], t["id"])
            for ref in t["tests"]:
                self.assertIn(ref, tests, f"{t['id']} references missing test {ref}")
            self.assertTrue(t["mitigations"] and t["residual"], t["id"])

    def test_threat_ids_unique_and_stable(self):
        ids = [t["id"] for t in TM["threats"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(i.startswith("T-") for i in ids))


class RegressionTest(unittest.TestCase):
    """R01-R03: 4.3.0 fuzz findings.  R04-R06: 4.3.0 test findings.  R10+: 4.2.0 defects."""

    def test_R01_uppercase_scheme(self):
        with self.assertRaises(mesh.Unmappable):
            mesh.map_identity("SPIFFE://estate.local/ns/a/sa/b", "estate.local")

    def test_R02_empty_query_fragment(self):
        for s in ("spiffe://estate.local/ns/a/sa/b?", "spiffe://estate.local/ns/a/sa/b#"):
            with self.assertRaises(mesh.Unmappable):
                mesh.map_identity(s, "estate.local")

    def test_R03_non_spiffe_segment_chars(self):
        for s in ("spiffe://estate.local/ns/a,b", "spiffe://estate.local/ns/a;b", "spiffe://estate.local/ns/é"):
            with self.assertRaises(mesh.Unmappable):
                mesh.map_identity(s, "estate.local")

    def test_R04_admission_survives_config_swap(self):
        svc, clock, _ = make_service()
        self.assertTrue(svc._admission.try_acquire("alpha"))
        from _support import base_config, publisher
        svc.activate_config(publisher(clock), base_config(version="2"))
        svc._admission.release("alpha")  # previously raised: controller had been replaced
        self.assertEqual(svc._admission._inflight, 0)

    def test_R05_frozen_reports_E_FROZEN(self):
        svc, clock, _ = make_service()
        from _support import operator
        svc.freeze(operator(clock), True, reason="t")
        with self.assertRaises(errors.MeshError) as cm:
            svc.migrate_route(CTRL_A, "alpha", "a", 2, 1, fence=1, idempotency_key="r05-00001")
        self.assertEqual(cm.exception.code, "E_FROZEN")

    def test_R06_redaction_keeps_structure(self):
        from _support import secret_refs
        self.assertEqual(secret_refs.redact({"key": {"available": True}}), {"key": {"available": True}})
        self.assertEqual(secret_refs.redact({"api_key": "abc"})["api_key"], secret_refs.REDACTED)

    def test_R10_single_retry_owner_even_when_product_fits(self):
        r = mesh.reconcile("a->b", 2, 2, budget=4)
        self.assertEqual((r["app"], r["mesh"]), (2, 1))

    def test_R11_mesh_only_keeps_mesh_owner(self):
        self.assertEqual(mesh.reconcile("a->b", 1, 9, budget=3)["owner"], "mesh")

    def test_R12_prefix_match_identity(self):
        with self.assertRaises(mesh.Unmappable):
            mesh.map_identity("spiffe://estate.local.evil.com/ns/a", "estate.local")

    def test_R13_bypass_mtls_must_be_bool(self):
        d = mesh.BypassDetector({"p"})
        with self.assertRaises(ValueError):
            d.observe("a", "p", "false")

    def test_R14_injection_strings_are_inert(self):
        svc, clock, _ = make_service()
        payloads = ["'; DROP TABLE routes;--", "{{7*7}}", "${jndi:ldap://x}", "‮evil", "../../etc/passwd"]
        for p in payloads:
            try:
                svc.reconcile(CTRL_A, "alpha", p, 2, 1)
            except errors.MeshError:
                pass
            with self.assertRaises(errors.MeshError):
                svc.map_identity(NODE, "alpha", "spiffe://estate.local/ns/alpha/" + p)
        self.assertTrue(svc.audit.verify()[0])

    def test_R15_escape_via_token_claims(self):
        svc, clock, _ = make_service()
        for cred, want in (
            (token(clock, roles=("mesh-operator", "root")), "E_PERMISSION_DENIED"),        # unknown role poisons the grant
            (token(clock, roles=("mesh-operator",), key=b"Z" * 32), "E_UNAUTHENTICATED"),  # self-signed escalation
            (token(clock, typ="node", roles=("mesh-node",)), "E_UNAUTHENTICATED"),         # token cannot impersonate mesh actor
        ):
            with self.assertRaises(errors.MeshError) as cm:
                svc.freeze(cred, True, reason="escape attempt")
            self.assertEqual(cm.exception.code, want)
        self.assertFalse(svc.controls.frozen)


if __name__ == "__main__":
    unittest.main()
