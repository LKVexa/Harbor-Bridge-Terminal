"""INV11-MC-01/02/05/15: lexer, parser, AST, diagnostics, limits."""
from __future__ import annotations

import os
import subprocess
import sys
import unittest

from _support import EXPECTED, FIX, files, name, ok, parse_text, rd, resolve_text  # noqa: F401

from inv11_interface_contract_language.wit.diagnostics import CODES, DiagnosticBag
from inv11_interface_contract_language.wit.lexer import tokenize
from inv11_interface_contract_language.wit.limits import Limits
from inv11_interface_contract_language.wit.parser import ParseConfig, parse_sources
from inv11_interface_contract_language.wit.source import from_memory, load_path


class GoldenValid(unittest.TestCase):
    def test_every_valid_fixture_parses_and_resolves(self):
        fs = files("valid")
        self.assertGreaterEqual(len(fs), 25)
        for p in fs:
            with self.subTest(fixture=name(p)):
                r, res = resolve_text(rd(p), os.path.basename(p))
                self.assertEqual(r.status(), "OK", [d.render() for d in r.diagnostics.sorted()])
                self.assertTrue(res.ok, [d.render() for d in res.diagnostics.sorted()])

    def test_every_type_form_reaches_the_ast(self):
        r = parse_text(rd(FIX / "valid" / "04-containers.wit"))
        f = r.documents[0].interfaces[0].funcs[0]
        kinds = {type(p.type).__name__ for p in f.params} | {type(f.result).__name__}
        self.assertEqual(kinds, {"ListT", "OptionT", "TupleT", "ResultT"})
        results = [fn.result for fn in r.documents[0].interfaces[0].funcs[1:4]]
        self.assertEqual([(x.ok is None, x.err is None) for x in results], [(True, True), (False, True), (True, False)])

    def test_resource_members(self):
        r = parse_text(rd(FIX / "valid" / "06-resource.wit"))
        res = r.documents[0].interfaces[0].types[0]
        self.assertEqual(res.kind, "resource")
        self.assertEqual([(f.name, f.kind) for f in res.funcs],
                         [("constructor", "constructor"), ("get", "method"), ("set", "method"), ("open", "static")])

    def test_escaped_identifiers_and_uppercase_words(self):
        res = ok(rd(FIX / "valid" / "14-escaped-idents.wit"))
        self.assertIn("p:esc/interface@1.0.0", res.interfaces)
        self.assertIn("type", res.interfaces["p:esc/interface@1.0.0"]["functions"])
        ok(rd(FIX / "valid" / "18-uppercase-words.wit"))

    def test_gates_are_recorded(self):
        res = ok(rd(FIX / "valid" / "12-gates.wit"))
        self.assertEqual(res.gates["p:g/g@1.1.0.old"], [{"kind": "since", "value": "1.0.0"}, {"kind": "deprecated", "value": "1.1.0"}])
        self.assertNotIn("h", res.interfaces["p:g/g@1.1.0"]["functions"])
        res2 = ok(rd(FIX / "valid" / "12-gates.wit"), features=frozenset({"fancy"}))
        self.assertIn("h", res2.interfaces["p:g/g@1.1.0"]["functions"])


class Trivia(unittest.TestCase):
    def test_comments_are_trivia_and_docs_attach(self):
        src = from_memory("d", rd(FIX / "valid" / "13-comments-docs.wit"), DiagnosticBag())
        lex = tokenize(src, DiagnosticBag())
        self.assertEqual(len(lex.comments), 5)
        r = parse_text(rd(FIX / "valid" / "13-comments-docs.wit"))
        self.assertIn("ünïcödé", r.documents[0].interfaces[0].doc)
        self.assertEqual(r.documents[0].interfaces[0].funcs[0].doc, "block doc")

    def test_trivia_never_changes_semantics(self):
        from inv11_interface_contract_language.wit.normalize import package_fingerprint
        a = ok("package a:b;\ninterface i { f: func(x: u32); }\n")
        b = ok("// hello\npackage a:b; /* x */\n\n/// doc\ninterface i {\n  f: func( x : u32 ) ; // t\n}\n")
        self.assertEqual(package_fingerprint(a), package_fingerprint(b))

    def test_crlf_and_bom_normalized(self):
        crlf = ok(rd(FIX / "valid" / "15-crlf.wit"))
        lf = ok(b"\xef\xbb\xbf" + rd(FIX / "valid" / "15-crlf.wit").replace(b"\r\n", b"\n"))
        from inv11_interface_contract_language.wit.normalize import package_fingerprint
        self.assertEqual(package_fingerprint(crlf), package_fingerprint(lf))


class Spans(unittest.TestCase):
    def test_token_spans_carry_file_offsets_line_col(self):
        src = from_memory("s", "package a:b;\ninterface i {\n  f: func();\n}\n", DiagnosticBag())
        toks = tokenize(src, DiagnosticBag()).tokens
        f = next(t for t in toks if t.text == "f")
        self.assertEqual((f.start, f.end), (29, 30))
        self.assertEqual(src.position(f.start), (3, 3))

    def test_diagnostic_span_line_col(self):
        r = parse_text("package a:b;\ninterface i {\n  f: func(x: u32;\n}\n", "x.wit")
        d = r.diagnostics.errors[0]
        self.assertEqual((d.span.line, d.span.col, d.code), (3, 17, "E-PARSE-EXPECTED"))
        self.assertIn("<memory:x.wit>:3:17", d.render())
        self.assertTrue(d.hint)

    def test_related_location_on_duplicates(self):
        r = parse_text("package a:b;\ninterface i { record r { x: u8,\n x: u16 } }\n")
        d = r.diagnostics.errors[0]
        self.assertEqual(d.code, "E-DUP-MEMBER")
        self.assertEqual(d.related[0].line, 2)
        self.assertEqual(d.span.line, 3)

    def test_multi_file_independent_spans_and_order(self):
        diags = DiagnosticBag()
        srcs = load_path(str(FIX / "multi" / "app"), diags)
        self.assertEqual([s.name for s in srcs], ["a-types.wit", "b-world.wit"])
        r = parse_sources(srcs)
        self.assertEqual([d.file for d in r.documents], ["a-types.wit", "b-world.wit"])
        self.assertEqual(r.documents[1].worlds[0].span.line, 3)


class Negative(unittest.TestCase):
    def test_every_invalid_fixture_reports_its_stable_code(self):
        fs = files("invalid")
        self.assertGreaterEqual(len(fs), 25)
        for p in fs:
            with self.subTest(fixture=name(p)):
                r, res = resolve_text(rd(p), os.path.basename(p))
                codes = [d.code for d in res.diagnostics.errors]
                self.assertIn(EXPECTED["invalid"][name(p)], codes)
                self.assertFalse(res.ok)

    def test_codes_are_registered(self):
        for code in EXPECTED["invalid"].values():
            self.assertIn(code, CODES)

    def test_malformed_utf8_rejected_deterministically(self):
        for data in (b"package a:b;\ninterface \xff {}", b"\xc3\x28", b"package a:b; // \xed\xa0\x80"):
            r = parse_text(data)
            self.assertTrue(r.fatal)
            self.assertEqual(r.diagnostics.errors[0].code, "E-SRC-UTF8")

    def test_recovery_bounds_cascade(self):
        text = "package a:b;\ninterface i {\n  f: func(x: u32 ;\n  g: func();\n  h: func() -> ;\n  k: func();\n}\ninterface j { m: func(); }\n"
        r = parse_text(text)
        self.assertEqual(len(r.diagnostics.errors), 2)
        self.assertEqual(r.status(), "RECOVERED_WITH_ERRORS")
        ifs = r.documents[0].interfaces
        self.assertEqual([[f.name for f in i.funcs] for i in ifs], [["g", "k"], ["m"]])


class Limits_(unittest.TestCase):
    def cfg(self, **kw):
        return ParseConfig(limits=Limits(**kw))

    def test_each_limit_fails_closed(self):
        cases = {
            "source_bytes": ("package a:b;" + " " * 200, dict(max_source_bytes=100)),
            "tokens": ("package a:b; interface i { " + "f: func(); " * 50 + "}", dict(max_tokens=40)),
            "nesting": ("package a:b; interface i { f: func() -> " + "list<" * 40 + "u8" + ">" * 40 + "; }", dict(max_nesting=16)),
            "identifier": ("package a:b; interface " + "a" * 300 + " {}", dict(max_identifier=256)),
            "declarations": ("package a:b; interface i { " + "".join(f"g{i}: func(); " for i in range(30)) + "}", dict(max_declarations=10)),
        }
        for lim, (text, kw) in cases.items():
            with self.subTest(limit=lim):
                r = parse_text(text, config=self.cfg(**kw))
                self.assertTrue(r.fatal)
                self.assertEqual(r.diagnostics.errors[-1].code, "E-LIMIT")
                self.assertIn(lim, r.diagnostics.errors[-1].message)

    def test_diagnostic_cap(self):
        r = parse_text("package a:b; interface i {" + " $" * 100 + "}", config=self.cfg(max_diagnostics=5))
        out = r.diagnostics.sorted()
        self.assertEqual(len(out), 6)
        self.assertEqual(out[-1].code, "W-DIAG-TRUNCATED")


class Determinism(unittest.TestCase):
    def test_parse_is_stable_across_hash_seeds_and_O(self):
        code = ("import sys; sys.path.insert(0, %r); from inv11_interface_contract_language.wit.resolve import load_package;"
                "from inv11_interface_contract_language.wit.normalize import package_fingerprint;"
                "p, r = load_package(%r); print(package_fingerprint(r), len(r.diagnostics.items))") % (
            str(FIX.parents[2]), str(FIX / "valid" / "16-http-like.wit"))
        outs = set()
        for seed in ("0", "1", "12345"):
            for opt in ([], ["-O"]):
                env = dict(os.environ, PYTHONHASHSEED=seed)
                outs.add(subprocess.run([sys.executable, "-B", *opt, "-c", code], env=env, capture_output=True, text=True, check=True).stdout)
        self.assertEqual(len(outs), 1, outs)

    def test_config_is_explicit(self):
        text = "package a:b; interface i { f: func() -> future<u8>; }"
        self.assertFalse(parse_text(text).ok)  # async is beyond the pinned feature level
        self.assertTrue(parse_text(text, config=ParseConfig(allow_async=True)).ok)
        self.assertFalse(parse_text("package a:b; interface i { f: func(x: list<u8, 4>); }").ok)
        self.assertTrue(parse_text("package a:b; interface i { f: func(x: list<u8, 4>); }", config=ParseConfig(allow_fixed_lists=True)).ok)


if __name__ == "__main__":
    unittest.main()
