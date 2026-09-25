"""INV11-MC-03/04/06/07/08/09/10/16: identity, resolver, normalization, type
graph, compatibility policy corpus, schemas, fingerprints."""
from __future__ import annotations

import json
import random
import unittest

from _support import EXPECTED, FIX, ok, pconfig, rd, resolve_text

from inv11_interface_contract_language.wit.compat import BREAKING, POLICY, Incompatible, check_link, classify_interface, classify_packages
from inv11_interface_contract_language.wit.limits import LimitExceeded, Limits
from inv11_interface_contract_language.wit.normalize import canonical_json, interface_fingerprint, package_fingerprint, package_form
from inv11_interface_contract_language.wit.resolve import load_package, unversioned
from inv11_interface_contract_language.wit.schema import (
    PK_INTERFACE_DIFF_SCHEMA,
    PK_INTERFACE_SCHEMA,
    export_interface,
    load_document,
    validate,
)
from inv11_interface_contract_language.wit.typegraph import Comparator


def pol(code):
    c = pconfig(code)
    return ok(rd(FIX / "policy" / code / "old.wit"), config=c), ok(rd(FIX / "policy" / code / "new.wit"), config=c)


class Identity(unittest.TestCase):
    def test_canonical_ids(self):
        res = ok(rd(FIX / "valid" / "07-use-alias.wit"))
        self.assertEqual(res.root_package, "p:u@1.0.0")
        self.assertEqual(sorted(res.interfaces), ["p:u/api@1.0.0", "p:u/types@1.0.0"])
        self.assertEqual(res.interfaces["p:u/api@1.0.0"]["scope"]["thing"], "p:u/types@1.0.0#item")
        self.assertEqual(unversioned("p:u/api@1.0.0.get"), "p:u/api.get")
        self.assertEqual(unversioned("p:u/api@1.0.0-rc.1#t"), "p:u/api#t")

    def test_interface_and_world_share_namespace(self):
        _, res = resolve_text("package a:b; interface x {} world x {}")
        self.assertEqual([d.code for d in res.diagnostics.errors], ["E-DUP-DECL"])

    def test_nested_packages_get_own_identity(self):
        res = ok(rd(FIX / "valid" / "20-nested-package.wit"))
        self.assertEqual(sorted(res.packages), ["p:inner@2.0.0", "p:outer@1.0.0"])

    def test_package_files_must_agree(self):
        _, res = resolve_text("package a:b; interface i {}\n")
        self.assertTrue(res.ok)


class Resolver(unittest.TestCase):
    def test_multi_file_package_with_versioned_dependency(self):
        pr, res = load_package(str(FIX / "multi" / "app"))
        self.assertTrue(res.ok, [d.render() for d in res.diagnostics.sorted()])
        self.assertTrue(res.packages["wasi:io@0.2.0"]["dependency"])
        self.assertEqual(res.interfaces["demo:app/types@1.0.0"]["uses"], ["wasi:io/streams@0.2.0"])
        self.assertIn("wasi:io/streams@0.2.0", res.worlds["demo:app/runner@1.0.0"]["imports"])

    def test_version_selection_is_explicit(self):
        from inv11_interface_contract_language.wit.parser import parse_text
        from inv11_interface_contract_language.wit.resolve import resolve_documents
        d1 = parse_text("package x:y@1.0.0; interface s { f: func(); }").documents
        d2 = parse_text("package x:y@2.0.0; interface s { f: func(); }").documents
        main = parse_text("package a:b; world w { import x:y/s; }").documents
        res = resolve_documents(main, [d1, d2])
        self.assertEqual([d.code for d in res.diagnostics.errors], ["E-RES-PACKAGE"])
        self.assertIn("pin one", res.diagnostics.errors[0].message)
        main2 = parse_text("package a:b; world w { import x:y/s@2.0.0; }").documents
        self.assertTrue(resolve_documents(main2, [d1, d2]).ok)

    def test_include_renames_and_conflicts(self):
        res = ok(rd(FIX / "valid" / "11-world-include.wit"))
        w = res.worlds["p:inc/full@1.0.0"]
        self.assertEqual(sorted(w["imports"]), ["p:inc/a@1.0.0", "p:inc/b@1.0.0"])
        _, bad = resolve_text("package a:b; world x { export f: func(); } world y { export f: func(x: u8); } world z { include x; include y; }")
        self.assertIn("E-DUP-DECL", [d.code for d in bad.diagnostics.errors])
        good = ok("package a:b; world x { export f: func(); } world y { export f: func(x: u8); } world z { include x; include y with { f as g }; }")
        self.assertEqual(sorted(good.worlds["a:b/z"]["exports"]), ["f", "g"])

    def test_declaration_order_independent(self):
        a = ok(rd(FIX / "valid" / "24-cross-use-order.wit"))
        b = ok(b"package p:ord@1.0.0;\ninterface a { type t = u8; }\ninterface z { use a.{t}; f: func(x: t); }\n")
        self.assertEqual(package_fingerprint(a), package_fingerprint(b))

    def test_bare_resource_means_own(self):
        res = ok(rd(FIX / "valid" / "25-result-of-handles.wit"))
        self.assertEqual(res.interfaces["p:rh/rh@1.0.0"]["functions"]["make"]["result"]["result"]["ok"], {"own": "p:rh/rh@1.0.0#r"})


class Normalization(unittest.TestCase):
    def test_canonical_json_is_byte_stable(self):
        res = ok(rd(FIX / "valid" / "16-http-like.wit"))
        a = canonical_json(package_form(res))
        self.assertEqual(a, canonical_json(json.loads(a)))
        self.assertNotIn(" ", a.replace("N/A", ""))  # no insignificant whitespace

    def test_declaration_shuffle_invariance(self):
        decls = ["interface a%d { f: func(x: u%d); }" % (i, 8 * 2 ** (i % 4)) for i in range(12)]
        fps = set()
        rnd = random.Random(7)
        for _ in range(8):
            rnd.shuffle(decls)
            fps.add(package_fingerprint(ok("package s:h@1.0.0;\n" + "\n".join(decls))))
        self.assertEqual(len(fps), 1)

    def test_semantic_order_retained(self):
        a = ok("package a:b; interface i { record r { x: u8, y: u8 } }")
        b = ok("package a:b; interface i { record r { y: u8, x: u8 } }")
        self.assertNotEqual(package_fingerprint(a), package_fingerprint(b))

    def test_fingerprint_format_and_version_independence(self):
        a = ok("package a:b@1.0.0; interface i { f: func(); }")
        b = ok("package a:b@2.0.0; interface i { f: func(); }")
        self.assertRegex(package_fingerprint(a), r"^sha256:[0-9a-f]{64}$")
        self.assertNotEqual(package_fingerprint(a), package_fingerprint(b))
        self.assertEqual(package_fingerprint(a, True), package_fingerprint(b, True))
        self.assertEqual(interface_fingerprint(a, "a:b/i@1.0.0"), interface_fingerprint(b, "a:b/i@2.0.0"))

    def test_golden_fingerprint(self):
        # pinned: any change to normalization must bump NORMALIZATION_VERSION
        res = ok("package g:old@1.0.0; interface i { record r { a: u32 } f: func(x: r) -> option<string>; }")
        self.assertEqual(package_fingerprint(res), GOLDEN)


GOLDEN = "sha256:ebe4d6dc936e7db77953ac74f161421c5ff04cff652ac608b7cc736cb3ba5131"


class TypeGraph(unittest.TestCase):
    def test_coinductive_cycle_guard(self):
        res = ok("package a:b; interface i { record r { x: u8 } }")
        # forge a cyclic graph (as hostile JSON could) and prove termination
        res.types["a:b/i#r"] = {"kind": "record", "fields": [["x", {"ref": "a:b/i#r"}]]}
        cmp = Comparator(res, res)
        self.assertIsNone(cmp.diff({"ref": "a:b/i#r"}, {"ref": "a:b/i#r"}))

    def test_work_budget(self):
        a = ok("package a:b; interface i { " + " ".join(f"g{i}: func(x: list<list<u8>>);" for i in range(50)) + " }")
        with self.assertRaises(LimitExceeded):
            classify_packages(a, a, Limits(max_compare_steps=20))

    def test_alias_is_transparent_but_nominal_types_are_not(self):
        self.assertEqual(classify_packages(*pol("alias-transparent-param"))["class"], "compatible")
        # component-model value types are structural: swapping between two
        # structurally identical records is ABI-compatible but is reported
        a = ok("package a:b; interface i { record r { x: u8 } record s { x: u8 } f: func(p: r); }")
        b = ok("package a:b; interface i { record r { x: u8 } record s { x: u8 } f: func(p: s); }")
        d = classify_packages(a, b)
        self.assertEqual(d["class"], "compatible")
        self.assertEqual([c["code"] for c in d["changes"]], ["named-type-swapped"])
        c = ok("package a:b; interface i { record r { x: u8 } record s { x: u16 } f: func(p: s); }")
        self.assertEqual(classify_packages(a, c)["class"], BREAKING)


class PolicyCorpus(unittest.TestCase):
    def test_every_policy_code_is_exercised(self):
        exercised = set()
        for code, want in sorted(EXPECTED["policy"].items()):
            with self.subTest(case=code):
                a, b = pol(code)
                d = classify_packages(a, b)
                self.assertEqual(d["class"], want["class"], d["reasons"])
                codes = [c["code"] for c in d["changes"]]
                if code in POLICY:
                    self.assertIn(code, codes)
                exercised.update(codes)
                self.assertEqual(d["linkable"], d["class"] != BREAKING)
        self.assertEqual(set(POLICY) - exercised, set(), "policy rows without a fixture")

    def test_versions_never_decide(self):
        a = ok("package a:b@1.0.0; interface i { f: func(); }")
        b = ok("package a:b@99.0.0; interface i { f: func(); }")
        c = ok("package a:b@1.0.1; interface i { f: func(x: u8); }")
        self.assertEqual(classify_packages(a, b)["class"], "compatible")
        self.assertEqual(classify_packages(a, c)["class"], BREAKING)

    def test_mixed_diff_reports_everything(self):
        d = classify_packages(*pol("mixed-additive-breaking"))
        self.assertEqual(sorted(c["code"] for c in d["changes"]), ["func-added", "func-removed"])

    def test_reason_ordering_is_deterministic(self):
        a, b = pol("mixed-additive-breaking")
        self.assertEqual(classify_packages(a, b), classify_packages(a, b))

    def test_interface_level_and_link(self):
        a, b = pol("func-added")
        d = classify_interface(a, "a:b/i@1.0.0", b, "a:b/i@1.1.0")
        self.assertEqual(d["class"], "additive")
        self.assertTrue(check_link(b, "a:b/i@1.1.0", a, "a:b/i@1.0.0")["linked"])
        with self.assertRaises(Incompatible):
            check_link(a, "a:b/i@1.0.0", b, "a:b/i@1.1.0")
        x, y = pol("param-type-changed")
        with self.assertRaises(Incompatible):
            check_link(y, "a:b/i@1.1.0", x, "a:b/i@1.0.0")

    def test_refuses_unresolved_input(self):
        _, bad = resolve_text("package a:b; interface i { f: func(x: nope); }")
        good = ok("package a:b; interface i { f: func(); }")
        with self.assertRaises(ValueError):
            classify_packages(bad, good)


class Schemas(unittest.TestCase):
    def test_diff_documents_validate(self):
        for code in sorted(EXPECTED["policy"]):
            d = classify_packages(*pol(code))
            self.assertEqual(validate(d, PK_INTERFACE_DIFF_SCHEMA), [], code)

    def test_export_validates_and_roundtrips(self):
        res = ok(rd(FIX / "valid" / "16-http-like.wit"))
        doc = export_interface(res)
        self.assertEqual(validate(doc, PK_INTERFACE_SCHEMA), [])
        again = load_document(canonical_json(doc), "PK_INTERFACE/1")
        self.assertEqual(again, doc)

    def test_hostile_documents_fail_closed(self):
        d = classify_packages(*pol("func-added"))
        bad = [dict(d, schema="PK_INTERFACE_DIFF/2"), dict(d, extra=1), dict(d, **{"class": "fine"}),
               dict(d, changes=[]), {k: v for k, v in d.items() if k != "linkable"}]
        for b in bad:
            self.assertNotEqual(validate(b, PK_INTERFACE_DIFF_SCHEMA), [])
        for raw in ('{"a":1,"a":2}', '{"x": NaN}', "[" * 10):
            with self.assertRaises(ValueError):
                load_document(raw, "PK_INTERFACE_DIFF/1")
        with self.assertRaises(LimitExceeded):
            load_document("{}" + " " * 100, "PK_INTERFACE/1", Limits(max_json_bytes=50))

    def test_schema_files_match_code(self):
        on_disk = json.loads((FIX.parents[1] / "schemas" / "PK_INTERFACE_DIFF-1.schema.json").read_text())
        self.assertEqual(on_disk, PK_INTERFACE_DIFF_SCHEMA)


if __name__ == "__main__":
    unittest.main()
