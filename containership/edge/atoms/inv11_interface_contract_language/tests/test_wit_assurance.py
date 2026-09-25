"""INV11-MC-11/12/13/14/19/20: differential testing against the pinned
reference toolchain, fixture corpus, property/mutation tests, fuzzing,
component round-trip conformance and adjacent-layer contract tests.

Tests needing wasm-tools FAIL (never skip) when it is absent: set
INV11_WASM_TOOLS or put the pinned wasm-tools on PATH.
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import tempfile
import time
import unittest

from _support import EXPECTED, FIX, files, name, ok, pconfig, rd, resolve_text, wasm_tools

from inv11_interface_contract_language.wit import differential as D
from inv11_interface_contract_language.wit.compat import BREAKING, classify_packages
from inv11_interface_contract_language.wit.limits import Limits
from inv11_interface_contract_language.wit.normalize import package_fingerprint
from inv11_interface_contract_language.wit.parser import ParseConfig, parse_text
from inv11_interface_contract_language.wit.resolve import load_package
from inv11_interface_contract_language.wit.schema import PK_INTERFACE_DIFF_SCHEMA, export_interface, validate

DIVERGENCES = json.loads((FIX.parents[1] / "conformance" / "DIVERGENCES.json").read_text())


def tool():
    exe = wasm_tools()
    if exe is None:
        raise AssertionError("BLOCKED: pinned wasm-tools not found (set INV11_WASM_TOOLS); required test cannot pass")
    return exe


class Differential(unittest.TestCase):
    def test_reference_tool_is_the_pinned_version(self):
        self.assertTrue(D.pinned_ok(tool()), D.tool_version(tool()))

    def test_valid_corpus_agrees(self):
        exe = tool()
        for p in files("valid") + [str(FIX / "multi" / "app")]:
            with self.subTest(fixture=os.path.basename(p)):
                _, res = load_package(p)
                row = D.differential(p, res.ok, res, exe)
                self.assertEqual(row["verdict"], "AGREE", row)

    def test_invalid_corpus_agrees_or_is_a_registered_divergence(self):
        exe = tool()
        for p in files("invalid"):
            with self.subTest(fixture=name(p)):
                _, res = resolve_text(rd(p))
                row = D.differential(p, res.ok, res, exe)
                if row["verdict"] == "DIVERGENT":
                    reg = DIVERGENCES["entries"].get(name(p))
                    self.assertIsNotNone(reg, f"unregistered divergence: {row}")
                    self.assertEqual(reg["direction"], "ours-stricter")
                else:
                    self.assertEqual(row["verdict"], "AGREE_REJECT", row)

    def test_policy_corpus_agrees(self):
        exe = tool()
        for d in sorted(os.listdir(FIX / "policy")):
            for side in ("old", "new"):
                p = str(FIX / "policy" / d / f"{side}.wit")
                _, res = resolve_text(rd(p))
                row = D.differential(p, res.ok, res, exe)
                gated = bool(EXPECTED["policy"].get(d, {}).get("config"))
                # gated fixtures exceed the pinned level: default config must reject like the reference
                want = "AGREE_REJECT" if gated and side == "new" else "AGREE"
                self.assertEqual(row["verdict"], want, (d, side, row))


class ComponentRoundTrip(unittest.TestCase):
    """Cross-toolchain conformance: a real component binary built by the
    reference toolchain from our fixture carries an interface that our model
    interprets identically."""

    WORLDS = {"09-world-basic": "app", "10-world-inline": "app", "11-world-include": "full",
              "16-http-like": "proxy", "17-clocks": "imports", "21-world-types": "w"}

    def test_encode_decode_equivalence(self):
        exe = tool()
        for fx, world in sorted(self.WORLDS.items()):
            with self.subTest(fixture=fx), tempfile.TemporaryDirectory() as td:
                src = str(FIX / "valid" / f"{fx}.wit")
                core, comp = os.path.join(td, "core.wasm"), os.path.join(td, "c.wasm")
                subprocess.run([exe, "component", "embed", "--dummy", src, "-w", world, "-o", core], check=True, capture_output=True)
                subprocess.run([exe, "component", "new", core, "-o", comp], check=True, capture_output=True)
                subprocess.run([exe, "validate", "--features", "component-model", comp], check=True, capture_output=True)
                okk, doc, err = D.run_tool(exe, comp)
                self.assertTrue(okk, err)
                theirs = D.theirs_view(doc)
                _, res = resolve_text(rd(src))
                ours = D.ours_view(res)
                for iface, view in theirs["interfaces"].items():
                    if iface in ours["interfaces"]:
                        self.assertEqual(D.compare_views(ours["interfaces"][iface], view), [], iface)
                w = next(v for k, v in theirs["worlds"].items() if k.endswith("/root"))
                mine = ours["worlds"][next(k for k in ours["worlds"] if k.endswith("/" + world))]
                self.assertEqual(sorted(w["imports"]), sorted(k for k in mine["imports"]))
                self.assertEqual(sorted(w["exports"]), sorted(k for k in mine["exports"]))


# --------------------------------------------------------------------------
PRIMS = ["u8", "u16", "u32", "u64", "s32", "string", "bool", "f64", "char"]


def gen_type(rnd, depth, named):
    r = rnd.random()
    if depth > 3 or r < 0.4:
        return rnd.choice(PRIMS + named) if named else rnd.choice(PRIMS)
    k = rnd.choice(["list", "option", "result", "tuple"])
    if k == "list":
        return f"list<{gen_type(rnd, depth + 1, named)}>"
    if k == "option":
        return f"option<{gen_type(rnd, depth + 1, named)}>"
    if k == "result":
        return f"result<{gen_type(rnd, depth + 1, named)}, {gen_type(rnd, depth + 1, named)}>"
    return "tuple<" + ", ".join(gen_type(rnd, depth + 1, named) for _ in range(rnd.randrange(1, 4))) + ">"


def gen_package(rnd, version="1.0.0"):
    named, decls = [], []
    for t in range(rnd.randrange(0, 4)):
        kind = rnd.choice(["record", "enum", "flags", "variant"])
        nm = f"t{t}"
        if kind == "record":
            decls.append(f"record {nm} {{ " + ", ".join(f"m{i}: {gen_type(rnd, 1, named)}" for i in range(rnd.randrange(1, 4))) + " }")
        elif kind == "variant":
            decls.append(f"variant {nm} {{ " + ", ".join(f"c{i}" + (f"({gen_type(rnd, 1, named)})" if rnd.random() < 0.5 else "") for i in range(rnd.randrange(1, 4))) + " }")
        else:
            decls.append(f"{kind} {nm} {{ " + ", ".join(f"c{i}" for i in range(rnd.randrange(1, 4))) + " }")
        named.append(nm)
    for f in range(rnd.randrange(1, 6)):
        ps = ", ".join(f"p{i}: {gen_type(rnd, 0, named)}" for i in range(rnd.randrange(0, 4)))
        decls.append(f"op{f}: func({ps})" + (f" -> {gen_type(rnd, 0, named)}" if rnd.random() < 0.7 else "") + ";")
    return f"package gen:p@{version};\ninterface i {{\n  " + "\n  ".join(decls) + "\n}\n"


# single-edit mutations with the class the policy must assign
def mutate(rnd, text):
    lines = text.split("\n")
    funcs = [i for i, l in enumerate(lines) if ": func(" in l]
    choice = rnd.choice(["add-func", "remove-func", "rename-param", "retype-result", "add-field"])
    if choice == "add-func":
        lines.insert(len(lines) - 2, "  zz-added: func();")
        return "\n".join(lines), "additive"
    if choice == "remove-func" and len(funcs) > 1:
        del lines[funcs[-1]]
        return "\n".join(lines), BREAKING
    if choice == "rename-param" and any("(p0:" in lines[i] for i in funcs):
        i = next(i for i in funcs if "(p0:" in lines[i])
        lines[i] = lines[i].replace("(p0:", "(q0:", 1)
        return "\n".join(lines), BREAKING
    if choice == "retype-result":
        i = funcs[0]
        base = lines[i].split(") -> ")[0].rstrip(";") if ") -> " in lines[i] else lines[i].rstrip(";")
        lines[i] = base.rstrip(")") + ")" + " -> option<zz-marker>;"
        lines.insert(len(lines) - 2, "  record zz-marker { v: u8 }")
        return "\n".join(lines), BREAKING
    recs = [i for i, l in enumerate(lines) if l.strip().startswith("record ")]
    if choice == "add-field" and recs:
        i = recs[0]
        lines[i] = lines[i].replace(" }", ", zz-new: u8 }")
        return "\n".join(lines), BREAKING
    lines.insert(len(lines) - 2, "  zz-added: func();")
    return "\n".join(lines), "additive"


class Properties(unittest.TestCase):
    N = int(os.environ.get("INV11_PROPERTY_CASES", "300"))

    def test_invariants_over_generated_packages(self):
        rnd = random.Random(20260922)
        for case in range(self.N):
            txt = gen_package(rnd)
            a = ok(txt)
            b = ok(txt.replace("@1.0.0", "@7.0.0"))
            self.assertEqual(classify_packages(a, a)["class"], "compatible")  # reflexive
            self.assertEqual(classify_packages(a, b)["class"], "compatible")  # version-blind
            self.assertEqual(package_fingerprint(a, True), package_fingerprint(b, True))
            self.assertEqual(validate(classify_packages(a, b), PK_INTERFACE_DIFF_SCHEMA), [])
            # round trip through the PK_INTERFACE/1 export is lossless and stable
            self.assertEqual(export_interface(a), export_interface(ok(txt)))

    def test_mutations_are_classified_as_the_policy_requires(self):
        rnd = random.Random(99)
        tally = {}
        for case in range(self.N):
            txt = gen_package(rnd)
            new, want = mutate(rnd, txt)
            a, b = ok(txt), ok(new.replace("@1.0.0", "@1.0.1"))
            got = classify_packages(a, b)
            self.assertEqual(got["class"], want, (txt, new, got["reasons"]))
            back = classify_packages(b, a)["class"]
            if want == "additive":  # an addition reversed is a removal
                self.assertEqual(back, BREAKING)
            tally[want] = tally.get(want, 0) + 1
        self.assertGreater(tally.get(BREAKING, 0), 0)
        self.assertGreater(tally.get("additive", 0), 0)


class Fuzz(unittest.TestCase):
    """Hostile input must yield a structured result within bounded time: no
    uncaught exception, no hang, no limit bypass."""
    N = int(os.environ.get("INV11_FUZZ_CASES", "1500"))
    LIMITS = Limits(max_source_bytes=64 * 1024, max_tokens=20_000, max_nesting=48, max_identifier=128,
                    max_declarations=2000, max_diagnostics=50)

    def run_one(self, data):
        t = time.perf_counter()
        r = parse_text(data, config=ParseConfig(limits=self.LIMITS))
        if not r.fatal and r.documents:
            from inv11_interface_contract_language.wit.resolve import resolve_documents
            resolve_documents(r.documents, diags=r.diagnostics, limits=self.LIMITS)
        self.assertLessEqual(len(r.diagnostics.sorted()), self.LIMITS.max_diagnostics + 1)
        return time.perf_counter() - t

    def test_random_bytes_and_mutated_corpus(self):
        rnd = random.Random(1)
        seeds = [rd(p) for p in files("valid") + files("invalid")]
        worst = 0.0
        for i in range(self.N):
            s = bytearray(rnd.choice(seeds))
            op = i % 6
            if op == 0:
                data = bytes(rnd.randrange(256) for _ in range(rnd.randrange(1, 400)))
            elif op == 1 and s:
                for _ in range(rnd.randrange(1, 8)):
                    s[rnd.randrange(len(s))] = rnd.randrange(256)
                data = bytes(s)
            elif op == 2 and s:
                cut = rnd.randrange(len(s))
                data = bytes(s[:cut])
            elif op == 3:
                a, b = rnd.choice(seeds), rnd.choice(seeds)
                data = a[: rnd.randrange(len(a) + 1)] + b[rnd.randrange(len(b) + 1):]
            elif op == 4 and s:
                pos = rnd.randrange(len(s))
                data = bytes(s[:pos] + bytes(rnd.choice(b"{}<>();:,.@%-/*")) * rnd.randrange(1, 50) + s[pos:])
            else:
                data = bytes(s) * rnd.randrange(1, 4)
            worst = max(worst, self.run_one(data))
        self.assertLess(worst, 2.0, "a single input took too long")

    def test_pathological_shapes(self):
        cases = [
            "package a:b; interface i { f: func() -> " + "list<" * 5000 + "u8" + ">" * 5000 + "; }",
            "package a:b; interface i { " + "record r { " * 3000 + "}",
            "package a:b; interface " + "a" * 100_000 + " {}",
            "package a:b; interface i { " + "f: func(); " * 5000 + "}",
            "package a:b; interface i { enum e { " + ", ".join(f"c{i}" for i in range(9000)) + " } }",
            "/*" * 20000,
            "package a:b; " + "interface i {} " * 3000,
            "package a:b; interface x { use y.{t}; } interface y { use z.{t}; } interface z { use x.{t}; }",
        ]
        for c in cases:
            with self.subTest(prefix=c[:40]):
                self.assertLess(self.run_one(c.encode()), 2.0)

    def test_schema_fuzz(self):
        from inv11_interface_contract_language.wit.schema import load_document
        rnd = random.Random(3)
        good = json.dumps(classify_packages(ok("package a:b; interface i { f: func(); }"),
                                            ok("package a:b; interface i { f: func(); g: func(); }")))
        for _ in range(500):
            s = bytearray(good.encode())
            for _ in range(rnd.randrange(1, 5)):
                s[rnd.randrange(len(s))] = rnd.randrange(32, 127)
            try:
                doc = load_document(bytes(s), "PK_INTERFACE_DIFF/1")
            except (ValueError, UnicodeDecodeError, RecursionError):
                continue
            self.assertEqual(validate(doc, PK_INTERFACE_DIFF_SCHEMA), [])  # anything accepted is valid


class AdjacentContracts(unittest.TestCase):
    """INV11-MC-19: the documents INV-11 hands to adjacent layers are pinned by
    schema.  The adjacent components themselves are not in this archive; the
    evidence ledger records their live integration as BLOCKED."""

    def test_inv10_composition_consumes_linkable_flag(self):
        for code, want in EXPECTED["policy"].items():
            c = pconfig(code)
            d = classify_packages(ok(rd(FIX / "policy" / code / "old.wit"), config=c), ok(rd(FIX / "policy" / code / "new.wit"), config=c))
            self.assertIs(d["linkable"], want["class"] != BREAKING)

    def test_inv12_consumes_pk_interface_export(self):
        _, res = load_package(str(FIX / "multi" / "app"))
        doc = export_interface(res)
        self.assertEqual(doc["schema"], "PK_INTERFACE/1")
        self.assertIn("demo:app/runner@1.0.0", doc["worlds"])


if __name__ == "__main__":
    unittest.main()
