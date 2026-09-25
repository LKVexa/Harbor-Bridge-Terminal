"""Interface/schema contract suite (Sections 5, 18).  Test names are traceability IDs."""
from __future__ import annotations

import copy
import json
import pickle
import subprocess
import sys
import unittest

from _common import PKG_DIR, ROOT, check_schema

from inv41_capability_security import errors
from inv41_capability_security.capabilities import (
    MAX_IDENTIFIER_LENGTH, MAX_MEMBRANE_DEPTH, MAX_OPERATIONS, Authority, CapabilityError, CrossAuthority, Forged,
    Holder, LimitExceeded, Membrane, Reference, Revoked, Widening,
)

VECTORS = json.loads((PKG_DIR / "tests" / "vectors" / "golden_vectors.json").read_text())


class Evil:
    """Pathological hash/eq object that must never enter an operation set."""
    calls = 0

    def __hash__(self):
        Evil.calls += 1
        return hash("read")

    def __eq__(self, other):
        return True


class ApiContractTest(unittest.TestCase):
    def setUp(self):
        self.a = Authority({"store": {"read", "write"}}, authority_id="ct")
        self.ref = self.a.grant("store")
        self.h = self.a.bind_holder("h", {"s": self.ref})

    def test_CT001_identifier_constraints(self):
        for bad in ("", "  ", "a\x00b", "a\nb", "x" * (MAX_IDENTIFIER_LENGTH + 1)):
            with self.assertRaises(ValueError, msg=repr(bad)):
                Authority({bad: {"read"}})
        self.assertEqual(Authority({"x" * MAX_IDENTIFIER_LENGTH: {"read"}}).policy.__len__(), 1)
        Authority({"résumé-Ω": {"lire"}})  # Unicode letters are allowed

    def test_CT002_operation_set_limits_and_types(self):
        with self.assertRaises(LimitExceeded):
            self.a.grant("store", {f"op{i}" for i in range(MAX_OPERATIONS + 1)})
        with self.assertRaises(ValueError):
            self.a.grant("store", {1})
        with self.assertRaises(TypeError):
            self.a.grant("store", "read")
        Evil.calls = 0
        with self.assertRaises(ValueError):
            self.a.grant("store", [Evil()])
        self.assertEqual(Evil.calls, 0, "hostile __hash__ was invoked")

    def test_CT003_duplicates_collapse(self):
        self.assertEqual(self.a.grant("store", ["read", "read"]).operations, frozenset({"read"}))

    def test_CT004_membrane_depth_limit(self):
        ref = self.ref
        for i in range(MAX_MEMBRANE_DEPTH):
            ref = Membrane(f"m{i}").wrap(ref)
        with self.assertRaises(LimitExceeded):
            Membrane("one-too-many").wrap(ref)

    def test_CT005_immutability(self):
        for obj, attr in ((self.a, "_policy"), (self.h, "_held"), (self.ref, "_operations")):
            with self.assertRaises(AttributeError):
                setattr(obj, attr, None)

    def test_CT006_foreign_authority_rejected_everywhere(self):
        other = Authority({"store": {"read", "write"}}, authority_id="ct")
        foreign = other.grant("store")
        with self.assertRaises(CrossAuthority):
            self.a.bind_holder("x", {"s": foreign})
        from inv41_capability_security.audit import AuditChain
        from inv41_capability_security.broker import Broker
        b = Broker(self.a, audit=AuditChain(b"k" * 32))
        b.selfcheck_passed = True
        with self.assertRaises(CrossAuthority):
            b.attenuate(foreign, {"read"})
        with self.assertRaises(CrossAuthority):
            b.wrap(Membrane("m"), foreign)
        foreign_holder = other.bind_holder("fh", {"s": foreign})
        with self.assertRaises(CrossAuthority):
            b.use(foreign_holder, "s", "read")

    def test_CT007_revoked_everywhere(self):
        m = Membrane("m")
        r = m.wrap(self.ref)
        m.revoke()
        for fn in (lambda: r.invoke("read"), lambda: r.attenuate({"read"}), lambda: Membrane("n").wrap(r),
                   lambda: self.a.bind_holder("x", {"s": r}), lambda: m.wrap(self.ref)):
            with self.assertRaises(Revoked):
                fn()

    def test_CT008_error_code_mapping_is_total_and_stable(self):
        classes = [CapabilityError, Forged, Widening, Revoked, CrossAuthority, LimitExceeded,
                   errors.Overloaded, errors.Unavailable, errors.Degraded, errors.StaleState,
                   errors.ConfigRejected, errors.AuthenticationFailed, errors.IncompatibleVersion]
        codes = [c.code for c in classes]
        self.assertEqual(len(codes), len(set(codes)))
        for c in classes:
            d = errors.describe(c("secret-seal-value-should-not-appear"))
            self.assertIn(d["code"], errors.ERROR_CODES)
            self.assertIn(d["outcome"], errors.OUTCOMES)
            self.assertNotIn("secret-seal", json.dumps(d))
        self.assertEqual(errors.describe(KeyError("x"))["code"], "INV41-E099")
        self.assertEqual(errors.describe(KeyError("x"))["outcome"], "internal-fault")
        for op, outs in errors.OPERATION_OUTCOMES.items():
            self.assertTrue(outs <= set(errors.OUTCOMES), op)

    def test_CT009_nonserializable_all_capability_objects(self):
        m = Membrane("m")
        for obj in (self.a, self.h, self.ref, m):
            for fn in (pickle.dumps, copy.copy, copy.deepcopy, lambda o: json.dumps(o)):
                with self.assertRaises(TypeError, msg=f"{type(obj).__name__} {fn}"):
                    fn(obj)

    def test_CT010_repr_redacts_all_secret_material(self):
        for obj in (self.a, self.h, self.ref):
            text = repr(obj)
            self.assertNotIn(self.ref.token, text)
            self.assertNotIn(self.a._authority_seal.hex(), text)
            self.assertNotIn(repr(self.a._authority_seal), text)

    def test_CT011_direct_construction_refused(self):
        with self.assertRaises(Forged):
            Holder("h", "ct", b"s", {})
        with self.assertRaises(Forged):
            Reference("ct", b"s", "store", frozenset({"read"}), "t", "sig")

    def test_CT012_golden_vectors_invocation_schema(self):
        schema = json.loads((PKG_DIR / "schemas" / "PK_REFERENCE.schema.json").read_text())
        self.assertEqual(check_schema(self.ref.invoke("read"), schema), [])
        for v in VECTORS["PK_REFERENCE/1"]:
            self.assertEqual(not check_schema(v["instance"], schema), v["valid"], v["name"])

    def test_CT013_golden_vectors_membrane_schema(self):
        schema = json.loads((PKG_DIR / "schemas" / "PK_MEMBRANE.schema.json").read_text())
        self.assertEqual(check_schema(Membrane("g").revoke(), schema), [])
        for v in VECTORS["PK_MEMBRANE/1"]:
            self.assertEqual(not check_schema(v["instance"], schema), v["valid"], v["name"])

    def test_CT014_golden_vectors_config(self):
        from inv41_capability_security import config
        for v in VECTORS["INV41_CONFIG/1"]:
            try:
                config.validate(v["instance"])
                ok = True
            except errors.ConfigRejected:
                ok = False
            self.assertEqual(ok, v["valid"], v["name"])

    def test_CT015_contract_suite_under_optimized_mode(self):
        code = ("import sys; sys.path.insert(0, %r); sys.path.insert(0, %r); import unittest, test_contracts as t; "
                "s=unittest.defaultTestLoader.loadTestsFromName('test_contracts.ApiContractTest');"
                "s=unittest.TestSuite([x for x in s if 'CT015' not in x.id()]);"
                "r=unittest.TextTestRunner(verbosity=0).run(s); sys.exit(0 if r.wasSuccessful() else 1)") % (
            str(ROOT), str(PKG_DIR / "tests"))
        out = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])

    def test_CT016_interface_catalog_covers_public_api(self):
        import inv41_capability_security as pkg
        catalog = json.loads((PKG_DIR / "contracts" / "INTERFACES.json").read_text())
        names = {b["name"] for b in catalog["boundaries"]}
        for sym in ("Authority.grant", "Authority.bind_holder", "Reference.attenuate", "Reference.invoke",
                    "Holder.use", "Holder.delegate", "Membrane.wrap", "Membrane.revoke", "selfcheck.run"):
            self.assertIn(sym, names)
        for b in catalog["boundaries"]:
            for k in ("classification", "producer", "consumer", "trust", "authn", "authz", "version", "limits", "errors"):
                self.assertIn(k, b, b["name"])
        for sym in pkg.__all__:
            if sym in ("COMPONENT", "CapabilitySecurityComponent", "build_contract"):
                continue
            self.assertTrue(any(n.split(".")[0] == sym or n == sym for n in names) or sym in catalog["exported_symbols"], sym)


if __name__ == "__main__":
    unittest.main()
