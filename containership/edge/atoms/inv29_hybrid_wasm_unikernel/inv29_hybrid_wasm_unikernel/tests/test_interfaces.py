"""Typed interface fixtures (MC002 fixture set, MC010) - local layer, no INV-11."""
import dataclasses
import unittest

import _fixtures as F
from inv29_hybrid_wasm_unikernel import admission as adm
from inv29_hybrid_wasm_unikernel import interfaces as I

NOW = I.Func("now", (("id", "string"),), ("u64",))
RES = I.Func("resolution", (), ("u64",))
HOST = I.Interface("wasi:clocks", "0.2.0", frozenset({NOW, RES}))


class InterfaceTest(unittest.TestCase):
    def test_identical_and_additive(self):
        self.assertEqual(I.classify(HOST, HOST)["class"], I.IDENTICAL)
        self.assertEqual(I.classify(HOST, I.Interface("wasi:clocks", "0.2.0", frozenset({NOW})))["class"], I.ADDITIVE)
        self.assertEqual(I.classify(HOST, I.Interface("wasi:clocks", "0.9.9", frozenset({NOW})))["class"], I.ADDITIVE)

    def test_breaking_cases(self):
        cases = {
            "param-change": I.Interface("wasi:clocks", "0.2.0", frozenset({I.Func("now", (("id", "u32"),), ("u64",))})),
            "result-change": I.Interface("wasi:clocks", "0.2.1", frozenset({I.Func("now", (("id", "string"),), ("u64", "error"))})),
            "removed-export": I.Interface("wasi:clocks", "0.2.0", frozenset({I.Func("monotonic", (), ("u64",))})),
            "renamed-interface": I.Interface("wasi:time", "0.2.0", frozenset({NOW})),
            "unknown-major": I.Interface("wasi:clocks", "1.0.0", frozenset({NOW})),
        }
        for name, guest in cases.items():
            with self.subTest(name):
                self.assertEqual(I.classify(HOST, guest)["class"], I.BREAKING)
                with self.assertRaises(I.InterfaceIncompatible):
                    I.check_link(HOST, guest)

    def test_guest_interface_not_exported(self):
        with self.assertRaises(I.InterfaceIncompatible):
            I.check_all([HOST], [I.Interface("wasi:sockets", "0.2.0", frozenset())])

    def test_record_roundtrip_and_strict_parse(self):
        self.assertEqual(I.from_record(I.to_record(HOST)), HOST)
        for bad in ({}, {"id": "x", "version": "1.0.0", "funcs": [], "extra": 1},
                    {"id": "x", "version": "v1", "funcs": []}):
            with self.subTest(bad=bad), self.assertRaises((ValueError, TypeError)):
                I.from_record(bad)

    def test_invalid_definitions(self):
        for args in (("BAD", (), ()), ("ok", (("x", "BAD TYPE!"),), ())):
            with self.subTest(args=args), self.assertRaises(ValueError):
                I.Func(*args)
        with self.assertRaises(ValueError):
            I.Interface("wasi:clocks", "0.2.0", frozenset({NOW, I.Func("now", (), ())}))

    def test_admission_enforces_typed_link_in_addition_to_names(self):
        kr = F.keyring()
        a = F.admitter(kr)
        drifted = I.Interface("wasi:clocks", "0.2.1", frozenset({I.Func("now", (("id", "string"),), ("u64", "error"))}))
        with self.assertRaises(adm.InterfaceRefused):
            a.admit(F.request(kr, host_interfaces=(HOST,), guest_interfaces=(drifted,)))
        rec = a.admit(F.request(kr, host_interfaces=(HOST,), guest_interfaces=(HOST,)))
        self.assertEqual(rec["admission"]["interfaces"][0]["class"], I.IDENTICAL)
        strict = F.admitter(kr, F.policy(require_typed_interfaces=True))
        with self.assertRaises(adm.InterfaceRefused):
            strict.admit(F.request(kr))


if __name__ == "__main__":
    unittest.main()
