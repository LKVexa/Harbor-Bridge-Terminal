"""Errors, canonical encoding, negotiation, matrix contract, WIT inventory/diff (MC-06, 11, 12, 16, 25, 31, 34)."""
import copy
import importlib
import json
import random
import unittest

from _support import PKG, PKG_DIR

canonical = importlib.import_module(f"{PKG}.canonical")
errors = importlib.import_module(f"{PKG}.errors")
matrix = importlib.import_module(f"{PKG}.matrix")
wit = importlib.import_module(f"{PKG}.wit")
reference = importlib.import_module(f"{PKG}.reference")
E = errors.Inv22Error

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None


def ref_doc():
    return json.loads((PKG_DIR / "data/matrix.json").read_text())


class ErrorModel(unittest.TestCase):
    def test_registry_is_well_formed_and_additive(self):
        codes = set(errors.REGISTRY)
        self.assertIn("INV22.CLASSIFY.UNCLASSIFIED", codes)
        exits = {s.exit_code for s in errors.REGISTRY.values()}
        self.assertNotIn(0, exits)
        for c, s in errors.REGISTRY.items():
            self.assertTrue(c.startswith("INV22."))
            self.assertIn(s.disclosure, ("public", "operator"))

    def test_unknown_code_collapses_to_internal(self):
        self.assertEqual(E("NOPE", "x").code, "INV22.INTERNAL")

    def test_redaction_and_bounds(self):
        d = E("INV22.VALIDATION.INVALID_INPUT", "m", {"api_key": "hunter2", "note": "x" * 1000}).to_dict()
        self.assertEqual(d["details"]["api_key"], "[REDACTED]")
        self.assertLess(len(d["details"]["note"]), 300)
        op = E("INV22.INTERNAL", "stack trace /secret/path").to_dict()
        self.assertNotIn("/secret/path", op["message"])

    def test_wrap_never_serialises_exception_text(self):
        w = errors.wrap(RuntimeError("password=abc"))
        self.assertEqual(w.code, "INV22.INTERNAL")
        self.assertNotIn("abc", json.dumps(w.to_dict()))

    def test_error_documents_match_schema(self):
        if jsonschema is None:
            self.skipTest("jsonschema not installed")
        schema = json.loads((PKG_DIR / "schemas/pk_branch_error.v1.schema.json").read_text())
        for code in errors.REGISTRY:
            jsonschema.validate(E(code, "m", {"k": 1}).to_dict(), schema)


class Canonical(unittest.TestCase):
    def test_stable_bytes_and_digest(self):
        a = {"b": [1, 2, {"z": "é", "a": None}], "a": True}
        b = json.loads(json.dumps(a))
        self.assertEqual(canonical.dumps(a), canonical.dumps(b))
        self.assertEqual(canonical.loads(canonical.dumps(a)), a)
        self.assertEqual(canonical.digest(a), canonical.digest(b))

    def test_rejections(self):
        for bad in (b'{"a":1,"a":2}', b'{"a":1.5}', b'{"a":NaN}', b"\xff", b"[", b'{"a":Infinity}'):
            with self.assertRaises(E, msg=bad):
                canonical.loads(bad)
        lim = canonical.Limits(max_bytes=100, max_depth=3, max_items=5, max_string=4)
        for bad in ([[[[1]]]], [1, 2, 3, 4, 5, 6], "abcdef", "x" * 200):
            with self.assertRaises(E):
                canonical.dumps(bad, lim)

    def test_negotiation(self):
        self.assertEqual(canonical.negotiate("PK_BRANCH_MATRIX", [1, 2]), "PK_BRANCH_MATRIX/1")
        with self.assertRaises(E) as c:
            canonical.negotiate("PK_BRANCH_MATRIX", [2, 3])
        self.assertEqual(c.exception.code, "INV22.VERSION.UNSUPPORTED")
        for bad in ("PK_BRANCH_MATRIX/2", "PK_BRANCH_MATRIX/01", "PK_BRANCH_MATRIX", "PK_BRANCH_SHIM/1"):
            with self.assertRaises(E):
                canonical.require_supported(bad, "PK_BRANCH_MATRIX")

    def test_fuzz_loads_never_crashes(self):
        rng = random.Random(22)
        base = canonical.dumps(ref_doc())
        for _ in range(1500):
            b = bytearray(base)
            for _ in range(rng.randint(1, 6)):
                b[rng.randrange(len(b))] = rng.randrange(256)
            try:
                matrix.parse(bytes(b))
            except E:
                pass


class MatrixContract(unittest.TestCase):
    def test_reference_matrix_valid_and_in_sync(self):
        m = matrix.parse(ref_doc())
        self.assertEqual(len(m.entries), 5)
        self.assertEqual(reference.main(["--check"]), 0)
        self.assertEqual(m.classification("wasi:sockets"), "divergent")
        with self.assertRaises(E) as c:
            m.classification("wasi:http")
        self.assertEqual(c.exception.code, "INV22.CLASSIFY.UNCLASSIFIED")

    def test_roundtrip_digest_stable(self):
        a = matrix.parse(ref_doc())
        b = matrix.parse(canonical.dumps(ref_doc()))
        self.assertEqual(a.digest, b.digest)

    def _mut(self, fn):
        d = ref_doc()
        fn(d)
        return d

    def test_negative_fixtures(self):
        def dup(d):
            d["entries"].append(copy.deepcopy(d["entries"][0]))
            d["integrity"]["entries_digest"] = matrix.entries_digest(d["entries"])

        def relabel(d):
            d["entries"][0]["classification"] = "maybe"

        def tamper(d):
            d["entries"][0]["rationale"] = "changed"

        cases = {
            "forward_version": (lambda d: d.update(contract="PK_BRANCH_MATRIX/2"), "INV22.VERSION.UNSUPPORTED"),
            "unknown_field": (lambda d: d.update(extra=1), "INV22.VALIDATION.SCHEMA"),
            "duplicate": (dup, "INV22.VALIDATION.SCHEMA"),
            "bad_enum": (relabel, "INV22.CLASSIFY.INVALID"),
            "tampered": (tamper, "INV22.INTEGRITY.CORRUPT"),
            "missing_baseline": (lambda d: d.pop("source_baseline"), "INV22.VALIDATION.SCHEMA"),
            "empty": (lambda d: d.update(entries=[]), "INV22.VALIDATION.SCHEMA"),
        }
        for name, (fn, code) in cases.items():
            with self.subTest(name):
                with self.assertRaises(E) as c:
                    matrix.parse(self._mut(fn))
                self.assertEqual(c.exception.code, code)

    def test_shimmable_requires_proof(self):
        d = ref_doc()
        for e in d["entries"]:
            if e["classification"] == "shimmable":
                e.pop("proof_ref")
        d["integrity"]["entries_digest"] = matrix.entries_digest(d["entries"])
        with self.assertRaises(E):
            matrix.parse(d)

    def test_deprecation_end_of_support_enforced(self):
        from datetime import date
        d = ref_doc()
        d["entries"][0]["deprecation"] = {"end_of_support": "2027-01-01"}
        d["integrity"]["entries_digest"] = matrix.entries_digest(d["entries"])
        matrix.parse(d, today=date(2026, 12, 31))
        with self.assertRaises(E) as c:
            matrix.parse(d, today=date(2027, 1, 2))
        self.assertEqual(c.exception.code, "INV22.VERSION.UNSUPPORTED")

    def test_json_schema_cross_validation(self):
        if jsonschema is None:
            self.skipTest("jsonschema not installed")
        schema = json.loads((PKG_DIR / "schemas/pk_branch_matrix.v1.schema.json").read_text())
        jsonschema.validate(ref_doc(), schema)
        bad = ref_doc()
        bad["entries"][0]["classification"] = "maybe"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)

    def test_committed_fixture_corpus(self):
        """Every fixture under fixtures/matrix declares its expected verdict (MC-31)."""
        files = sorted((PKG_DIR / "fixtures/matrix").glob("*.json"))
        self.assertGreaterEqual(len(files), 6)
        for f in files:
            fx = json.loads(f.read_text())
            with self.subTest(f.name):
                if fx["expect"] == "ok":
                    matrix.parse(fx["document"])
                else:
                    with self.assertRaises(E) as c:
                        matrix.parse(fx["document"])
                    self.assertEqual(c.exception.code, fx["expect"])

    def test_completeness_gate(self):
        m = matrix.parse(ref_doc())
        ok = matrix.completeness(m, ["wasi:clocks", "wasi:sockets"])
        self.assertTrue(ok["ok"])
        bad = matrix.completeness(m, ["wasi:clocks", "wasi:http"])
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["unclassified_ids"], ["wasi:http"])
        ex = matrix.completeness(m, ["wasi:http"], {"wasi:http": "unsupported on every site"})
        self.assertTrue(ex["ok"])
        with self.assertRaises(E):
            matrix.completeness(m, [], {"wasi:http": " "})

    def test_baselines_not_pinned_is_reported(self):
        rep = matrix.check_baselines(json.loads((PKG_DIR / "baselines/manifest.json").read_text()))
        self.assertFalse(rep["pinned"])
        good = {"schema": "PK_BRANCH_BASELINES/1",
                "standards": {"commit": "a" * 40, "digest": "sha256:" + "a" * 64, "feature_profile": ["filesystem"]},
                "fork": {"commit": "b" * 40, "digest": "sha256:" + "b" * 64, "feature_profile": ["filesystem", "processes"]}}
        self.assertTrue(matrix.check_baselines(good)["pinned"])


STD_WIT = """
package wasi:filesystem@0.2.0;
// comment
interface types {
  enum error-code { access, busy }
  flags open-flags { create, directory, exclusive, truncate }
  record stat { size: u64, mtime: u64 }
  open-at: func(path: string, flags: open-flags) -> result<u32, error-code>;
  close: func(fd: u32);
}
interface preopens { get: func() -> list<tuple<u32, string>>; }
world app { import wasi:filesystem/types; import wasi:clocks/wall-clock; }
"""


class Wit(unittest.TestCase):
    def fork(self, body):
        return wit.parse("package wasi:filesystem@0.2.0-wasix;\n" + body)

    def test_parse_and_inventory(self):
        p = wit.parse(STD_WIT)
        inv = wit.inventory(p)
        self.assertEqual([i["interface"] for i in inv], ["wasi:filesystem/preopens", "wasi:filesystem/types"])
        self.assertEqual(wit.workload_imports(p), ["wasi:clocks/wall-clock", "wasi:filesystem/types"])

    def test_every_change_category(self):
        s = wit.parse(STD_WIT)
        body = STD_WIT.split("\n", 2)[2]
        cases = {
            "identical": (body, None),
            "signature_changed": (body.replace("mtime: u64", "mtime: u32"), "signature_changed"),
            "item_removed": (body.replace("close: func(fd: u32);", ""), "item_removed"),
            "item_added": (body.replace("close: func(fd: u32);", "close: func(fd: u32); dup: func(fd: u32) -> u32;"), "item_added"),
            "error_set": (body.replace("access, busy", "access, busy, again"), "signature_changed"),
            "removed_iface": (body.replace("interface preopens { get: func() -> list<tuple<u32, string>>; }", ""), "removed_in_fork"),
            "added_iface": (body + "interface proc { fork: func() -> u32; }", "added_in_fork"),
        }
        for name, (fb, kind) in cases.items():
            with self.subTest(name):
                d = {x["interface"]: x for x in wit.diff(s, self.fork(fb))}
                if kind is None:
                    self.assertTrue(all(x["status"] == "identical" for x in d.values()))
                else:
                    kinds = {c["kind"] for x in d.values() for c in x["changes"]}
                    self.assertIn(kind, kinds)

    def test_rename_via_reviewed_alias(self):
        s = wit.parse(STD_WIT)
        f = self.fork(STD_WIT.split("\n", 2)[2].replace("interface preopens", "interface pre-opens"))
        d = {x["interface"]: x for x in wit.diff(s, f, aliases={"pre-opens": "preopens"})}
        self.assertEqual(d["wasi:filesystem/preopens"]["changes"], [{"kind": "renamed", "fork_name": "pre-opens"}])

    def test_candidate_matrix_blocks_unreviewed(self):
        s = wit.parse(STD_WIT)
        f = self.fork(STD_WIT.split("\n", 2)[2].replace("mtime: u64", "mtime: u32"))
        diffs = wit.diff(s, f)
        entries, blocking = wit.candidate_matrix(diffs)
        self.assertEqual(blocking, ["wasi:filesystem/types"])
        entries, blocking = wit.candidate_matrix(diffs, {"wasi:filesystem/types": {
            "classification": "divergent", "rationale": "mtime width", "reviewer": "r", "approved": "2026-09-23"}})
        self.assertEqual(blocking, [])
        with self.assertRaises(E):
            wit.candidate_matrix(diffs, {"wasi:filesystem/types": {"classification": "divergent"}})

    def test_deterministic(self):
        s, f = wit.parse(STD_WIT), self.fork(STD_WIT.split("\n", 2)[2].replace("u64", "u32"))
        self.assertEqual(canonical.dumps(wit.diff(s, f)), canonical.dumps(wit.diff(s, f)))

    def test_rejects_unsupported_syntax(self):
        for bad in ("interface x {}", "package a:b; interface x { ??? }", "package a:b; interface x { f: func(;",
                    "package a:b; banana", "package a:b; interface x {} interface x {}"):
            with self.assertRaises(E, msg=bad):
                wit.parse(bad)

    def test_fuzz_parser(self):
        rng = random.Random(7)
        for _ in range(1500):
            s = list(STD_WIT)
            for _ in range(rng.randint(1, 5)):
                s[rng.randrange(len(s))] = rng.choice("{}();:<>,-az \n")
            try:
                wit.parse("".join(s))
            except E:
                pass


if __name__ == "__main__":
    unittest.main()
