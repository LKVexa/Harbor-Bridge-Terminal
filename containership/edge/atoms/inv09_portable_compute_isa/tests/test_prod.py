"""Production validation boundary tests (M01-M13, M17/M18, M22, M27, M33-M37,
M42-M44, M51).  stdlib unittest; the differential test needs Node.js and is
skipped (not passed) without it.

    python -m unittest discover -s inv09_portable_compute_isa/tests -p "test_prod.py" -v
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys
import tempfile
import threading
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import wasmgen as W  # noqa: E402
from wasmgen import F32, F64, FUNCREF, I32, I64, module, name, u  # noqa: E402

from inv09_portable_compute_isa import validator as kernel  # noqa: E402
from inv09_portable_compute_isa.prod import (admission, attest, bench, cache, config_store,  # noqa: E402
                                             decoder, differential, digest, errors, fuzz,
                                             hostimports, limits, registry, telemetry, typecheck,
                                             waivers)
from inv09_portable_compute_isa.prod.errors import Code, InvalidModule  # noqa: E402

V = typecheck.validate_module


def code_of(data: bytes, lim=limits.DEFAULT_LIMITS) -> str:
    try:
        V(data, lim)
        return "OK"
    except InvalidModule as e:
        return e.code.value


def fn(code: bytes, params=(), results=(), locals_=(), **kw) -> bytes:
    return module(types=[(params, results)], funcs=[0], codes=[(code, locals_)], **kw)


# ======================================================================= M01
class DecoderTest(unittest.TestCase):
    def test_seed_corpus_valid(self):
        for k, m in W.seeds().items():
            with self.subTest(k):
                self.assertEqual(code_of(m), "OK")

    def test_header(self):
        self.assertEqual(code_of(b""), "TRUNCATED")
        self.assertEqual(code_of(b"\x00as"), "TRUNCATED")
        self.assertEqual(code_of(b"\x00asn\x01\x00\x00\x00"), "BAD_MAGIC")
        self.assertEqual(code_of(b"\x00asm\x02\x00\x00\x00"), "BAD_VERSION")
        self.assertEqual(code_of(b"\x00asm\x01\x00\x00\x00\x01"), "TRUNCATED")

    def test_section_rules(self):
        t = W.section(1, W.vec([W.functype((), ())]))
        self.assertEqual(code_of(W.HEADER + t + t), "DUPLICATE_SECTION")
        f = W.section(3, W.vec([u(0)]))
        self.assertEqual(code_of(W.HEADER + f + t), "INVALID_INDEX")  # function before type: index checked
        self.assertEqual(code_of(W.HEADER + t + W.section(7, W.vec([])) + W.section(6, W.vec([]))), "SECTION_ORDER")
        self.assertEqual(code_of(W.HEADER + W.section(13, b"")), "UNKNOWN_SECTION")
        self.assertEqual(code_of(W.HEADER + b"\x01\x05\x00"), "TRUNCATED")
        # payload longer than its content -> unconsumed bytes
        self.assertEqual(code_of(W.HEADER + b"\x01\x02\x00\x00"), "SECTION_SIZE_MISMATCH")
        # datacount must precede code
        m = W.HEADER + t + f + W.section(10, W.vec([W.body(b"\x0b")])) + W.section(12, u(0))
        self.assertEqual(code_of(m), "SECTION_ORDER")

    def test_leb128(self):
        # 6-byte u32, and 5-byte u32 with high bits set
        self.assertEqual(code_of(W.HEADER + b"\x01\x80\x80\x80\x80\x80\x00"), "BAD_LEB128")
        self.assertEqual(code_of(W.HEADER + b"\x01\xff\xff\xff\xff\x7f"), "BAD_LEB128")
        # non-minimal but in-width encodings are legal per spec
        self.assertEqual(code_of(W.HEADER + b"\x01\x81\x80\x80\x80\x00\x00"), "OK")
        # s32 overflow in i32.const
        self.assertEqual(code_of(fn(b"\x41\xff\xff\xff\xff\x7f\x0b", results=(I32,))), "OK")
        self.assertEqual(code_of(fn(b"\x41\xff\xff\xff\xff\x4f\x0b", results=(I32,))), "BAD_LEB128")
        self.assertEqual(code_of(fn(b"\x41\x80\x80\x80\x80\x70\x0b", results=(I32,))), "BAD_LEB128")

    def test_vector_bombs_and_limits(self):
        self.assertEqual(code_of(W.HEADER + W.section(1, u(9_000))), "TRUNCATED")
        self.assertEqual(code_of(W.HEADER + W.section(1, u(200_000))), "LIMIT_EXCEEDED")
        small = limits.Limits(max_module_bytes=16)
        self.assertEqual(code_of(W.add_module(), small), "LIMIT_EXCEEDED")
        self.assertEqual(code_of(W.add_module(), limits.Limits(max_sections=2)), "LIMIT_EXCEEDED")
        self.assertEqual(code_of(W.add_module(), limits.Limits(max_steps=3)), "LIMIT_EXCEEDED")

    def test_utf8_and_exports(self):
        bad = W.HEADER + W.section(0, u(2) + b"\xc3\x28")
        self.assertEqual(code_of(bad), "BAD_UTF8")
        dup = module(types=[((), ())], funcs=[0], exports=[("a", 0, 0), ("a", 0, 0)], codes=[b"\x0b"])
        self.assertEqual(code_of(dup), "DUPLICATE_EXPORT")
        oob = module(types=[((), ())], funcs=[0], exports=[("a", 0, 1)], codes=[b"\x0b"])
        self.assertEqual(code_of(oob), "INVALID_INDEX")

    def test_counts_and_limits_types(self):
        self.assertEqual(code_of(module(types=[((), ())], funcs=[0])), "COUNT_MISMATCH")
        self.assertEqual(code_of(module(mems=[b"\x01\x02\x01"])), "INVALID_LIMITS")
        self.assertEqual(code_of(module(mems=[b"\x00" + u(65537)])), "INVALID_LIMITS")
        self.assertEqual(code_of(module(mems=[b"\x00\x01", b"\x00\x01"])), "LIMIT_EXCEEDED")
        self.assertEqual(code_of(module(mems=[b"\x04\x01"])), "UNSUPPORTED_PROPOSAL")

    def test_immutable_parse_and_offsets(self):
        m = decoder.decode(W.add_module())
        with self.assertRaises(Exception):
            m.types = ()  # type: ignore[misc]
        try:
            V(fn(b"\x6a\x0b", results=(I32,)))
        except InvalidModule as e:
            self.assertEqual(e.section, "code")
            self.assertIsInstance(e.offset, int)
            self.assertEqual(e.to_dict()["schema"], "PK_VALIDATION_FAILURE/1")


# ======================================================================= M02
class TypeCheckTest(unittest.TestCase):
    def test_negative_typing(self):
        cases = {
            "underflow": (fn(b"\x6a\x0b", results=(I32,)), "STACK_UNDERFLOW"),
            "mismatch": (fn(b"\x42\x00\x0b", results=(I32,)), "TYPE_MISMATCH"),
            "extra": (fn(b"\x41\x00\x41\x00\x0b", results=(I32,)), "TYPE_MISMATCH"),
            "bad_branch": (fn(b"\x0c\x01\x0b"), "INVALID_BRANCH"),
            "if_no_else_result": (fn(b"\x41\x01\x04\x7f\x41\x01\x0b\x0b", results=(I32,)), "TYPE_MISMATCH"),
            "else_without_if": (fn(b"\x02\x40\x05\x0b\x0b"), "MALFORMED"),
            "bad_local": (fn(b"\x20\x00\x1a\x0b"), "INVALID_INDEX"),
            "alignment": (fn(b"\x41\x00\x28\x03\x00\x1a\x0b", mems=[b"\x00\x01"]), "INVALID_ALIGNMENT"),
            "no_memory": (fn(b"\x41\x00\x28\x02\x00\x1a\x0b"), "INVALID_INDEX"),
            "immutable_global": (fn(b"\x41\x00\x24\x00\x0b", globals_=[bytes([I32, 0]) + b"\x41\x00\x0b"]),
                                 "IMMUTABLE_GLOBAL"),
            "select_ref": (fn(b"\xd0\x70\xd0\x70\x41\x00\x1b\x1a\x0b"), "TYPE_MISMATCH"),
            "undeclared_ref": (fn(b"\xd2\x00\x1a\x0b"), "UNDECLARED_FUNC_REF"),
            "br_table_arity": (fn(b"\x02\x7f\x02\x40\x41\x00\x0e\x01\x00\x01\x0b\x41\x00\x0b\x1a\x0b"),
                               "TYPE_MISMATCH"),
            "unknown_op": (fn(b"\x27\x0b"), "UNKNOWN_OPCODE"),
            "simd": (fn(b"\xfd\x0c" + b"\x00" * 16 + b"\x1a\x0b"), "UNSUPPORTED_PROPOSAL"),
            "atomics": (fn(b"\xfe\x03\x00\x0b"), "UNSUPPORTED_PROPOSAL"),
            "tail_call": (fn(b"\x12\x00\x0b"), "UNSUPPORTED_PROPOSAL"),
            "trailing": (module(types=[((), ())], funcs=[0], codes=[b"\x0b\x0b"]), "MALFORMED"),
            "unterminated": (module(types=[((), ())], funcs=[0], codes=[b"\x02\x40\x0b"]), "TRUNCATED"),
            "memory_init_no_datacount": (fn(b"\x41\x00\x41\x00\x41\x00\xfc\x08\x00\x00\x0b",
                                            mems=[b"\x00\x01"], datas=[b"\x01" + u(0)]), "MALFORMED"),
            "const_expr_nonconst": (module(globals_=[bytes([I32, 0]) + b"\x41\x00\x41\x00\x6a\x0b"]),
                                    "INVALID_CONST_EXPR"),
            "const_expr_type": (module(globals_=[bytes([I64, 0]) + b"\x41\x00\x0b"]), "TYPE_MISMATCH"),
            "start_sig": (module(types=[((I32,), ())], funcs=[0], start=0, codes=[b"\x0b"]), "TYPE_MISMATCH"),
        }
        for k, (m, want) in cases.items():
            with self.subTest(k):
                self.assertEqual(code_of(m), want)

    def test_unreachable_polymorphism(self):
        self.assertEqual(code_of(fn(b"\x00\x1b\x0b", results=(I32,))), "OK")       # select on unknowns
        self.assertEqual(code_of(fn(b"\x0f\x0b", results=(I32,))), "STACK_UNDERFLOW")
        self.assertEqual(code_of(fn(b"\x41\x00\x0f\x42\x00\x0b", results=(I32,))), "TYPE_MISMATCH")
        self.assertEqual(code_of(fn(b"\x02\x40\x0c\x00\x6a\x1a\x0b\x0b")), "OK")

    def test_deep_nesting_is_iterative_and_bounded(self):
        depth = 5000
        code = b"\x02\x40" * depth + b"\x0b" * depth + b"\x0b"
        self.assertEqual(code_of(fn(code)), "LIMIT_EXCEEDED")
        ok = b"\x02\x40" * 1000 + b"\x0b" * 1000 + b"\x0b"
        self.assertEqual(code_of(fn(ok)), "OK")


# ======================================================================= M03
class FeatureTest(unittest.TestCase):
    def feats(self, m):
        return V(m)[1].features

    def test_byte_derived_features(self):
        s = W.seeds()
        self.assertEqual(self.feats(s["add"]), {"core"})
        self.assertIn("multi-value", self.feats(s["multi_value"]))
        self.assertIn("sign-ext", self.feats(s["sign_ext"]))
        self.assertIn("sat-float-to-int", self.feats(s["sat"]))
        self.assertIn("bulk-memory", self.feats(s["bulk"]))
        self.assertIn("reference-types", self.feats(s["reftypes"]))
        self.assertTrue(V(s["float"])[1].uses_float)
        self.assertFalse(V(s["add"])[1].uses_float)
        shared = module(mems=[b"\x03\x01\x02"])
        self.assertIn("threads", self.feats(shared))

    def test_evidence_offsets(self):
        _, f = V(W.seeds()["sign_ext"])
        ev = {n: off for n, off, _ in f.evidence}
        self.assertGreater(ev["sign-ext"], 8)


# ======================================================================= M05/M06/M22
class RegistryTest(unittest.TestCase):
    def test_default_bundle_and_kernel_consistent(self):
        b = registry.default_bundle()
        for pid in ("deterministic", "extended", "permissive"):
            self.assertEqual(b.profiles[pid].features, kernel.PROFILES[pid], pid)
        self.assertTrue(b.revision.startswith("bundle:sha256:"))

    def test_strict_schema(self):
        doc = json.loads(registry.canonical_json(registry.DEFAULT_BUNDLE_DOC))
        doc["surprise"] = 1
        with self.assertRaises(InvalidModule):
            registry.load_bundle(json.dumps(doc).encode())
        doc = json.loads(registry.canonical_json(registry.DEFAULT_BUNDLE_DOC))
        doc["profiles"]["deterministic"]["features"].append("threads")
        with self.assertRaises(InvalidModule) as cm:
            registry.load_bundle(json.dumps(doc).encode())
        self.assertIn("non-deterministic", cm.exception.detail)
        with self.assertRaises(InvalidModule):
            registry.load_bundle(b'{"schema": NaN}')


# ======================================================================= M07
class DigestTest(unittest.TestCase):
    def test_digest(self):
        d = digest.module_digest(W.add_module())
        self.assertRegex(d, r"^sha256:[0-9a-f]{64}$")
        self.assertNotEqual(d, digest.module_digest(W.add_module() + b"\x00\x02\x01x"))
        with self.assertRaises(InvalidModule):
            digest.parse_digest("sha256:ABC")


# ======================================================================= gate
def make_gate(**kw):
    signer = attest.Signer("k1")
    verifier = attest.Verifier({"k1": signer.public_raw()})
    return admission.Gate(signer=signer, verifier=verifier, **kw), signer, verifier


class AdmissionTest(unittest.TestCase):
    def setUp(self):
        self.gate, self.signer, self.verifier = make_gate()

    def test_accept_attest_admit_execute(self):
        m = W.add_module()
        v = self.gate.validate(m, profile="deterministic", engine="reference-engine")
        self.assertEqual(v["outcome"], "accept", v)
        t = self.gate.admit(m, v["attestation"], profile="deterministic", engine="reference-engine")
        self.assertEqual(self.gate.execute(t, lambda b: len(b)), len(m))

    def test_profile_refusals(self):
        clock = W.seeds()["clock_import"]
        v = self.gate.validate(clock, profile="deterministic", engine="reference-engine")
        self.assertEqual(v["outcome"], "refuse")
        v = self.gate.validate(clock, profile="permissive", engine="reference-engine")
        self.assertEqual(v["outcome"], "accept")
        self.assertFalse(v["deterministic"])
        unknown_import = module(types=[((), ())], imports=[name("env") + name("evil") + b"\x00\x00"])
        v = self.gate.validate(unknown_import, profile="permissive", engine="reference-engine")
        self.assertEqual(v["failure"]["code"], "HOST_IMPORT_REFUSED")
        v = self.gate.validate(W.add_module(), profile="nope", engine="reference-engine")
        self.assertEqual(v["outcome"], "refuse")
        v = self.gate.validate(W.add_module(), profile="deterministic", engine="nope")
        self.assertEqual(v["failure"]["code"], "ENGINE_UNSUPPORTED")

    def test_binding_manifest(self):
        m = W.seeds()["sign_ext"]
        d = digest.module_digest(m)
        good = admission.CapabilityManifest(d, frozenset({"core", "sign-ext"}))
        self.assertEqual(self.gate.validate(m, profile="deterministic", engine="reference-engine",
                                            manifest=good)["outcome"], "accept")
        hiding = admission.CapabilityManifest(d, frozenset({"core"}))
        v = self.gate.validate(m, profile="deterministic", engine="reference-engine", manifest=hiding)
        self.assertEqual(v["failure"]["code"], "BINDING_MISMATCH")
        other = admission.CapabilityManifest(digest.module_digest(b"x"), frozenset({"core", "sign-ext"}))
        v = self.gate.validate(m, profile="deterministic", engine="reference-engine", manifest=other)
        self.assertEqual(v["failure"]["code"], "BINDING_MISMATCH")
        over = admission.CapabilityManifest(d, frozenset({"core", "sign-ext", "threads"}))
        v = self.gate.validate(m, profile="deterministic", engine="reference-engine", manifest=over)
        self.assertEqual(v["failure"]["code"], "FEATURE_REFUSED")

    def test_attestation_cannot_be_moved(self):
        a, b = W.add_module(), W.seeds()["sign_ext"]
        v = self.gate.validate(a, profile="deterministic", engine="reference-engine")
        with self.assertRaises(InvalidModule) as cm:
            self.gate.admit(b, v["attestation"], profile="deterministic", engine="reference-engine")
        self.assertEqual(cm.exception.code, Code.ATTESTATION_INVALID)
        with self.assertRaises(InvalidModule):
            self.gate.admit(a, v["attestation"], profile="permissive", engine="reference-engine")
        env = json.loads(v["attestation"])
        env["payload"] = env["payload"].replace('"deterministic":true', '"deterministic":false')
        with self.assertRaises(InvalidModule):
            self.gate.admit(a, json.dumps(env), profile="deterministic", engine="reference-engine")
        with self.assertRaises(InvalidModule):
            self.gate.admit(a, "{not json", profile="deterministic", engine="reference-engine")

    def test_foreign_key_and_revocation_and_expiry(self):
        rogue = attest.Signer("k1")  # same key id, different key
        other_gate = admission.Gate(signer=rogue, verifier=attest.Verifier({"k1": rogue.public_raw()}))
        v = other_gate.validate(W.add_module(), profile="deterministic", engine="reference-engine")
        with self.assertRaises(InvalidModule):
            self.gate.admit(W.add_module(), v["attestation"], profile="deterministic", engine="reference-engine")
        v = self.gate.validate(W.add_module(), profile="deterministic", engine="reference-engine")
        self.verifier.revoke("k1")
        with self.assertRaises(InvalidModule):
            self.gate.admit(W.add_module(), v["attestation"], profile="deterministic", engine="reference-engine")
        g2, s2, ver2 = make_gate(attestation_ttl=10)
        v = g2.validate(W.add_module(), profile="deterministic", engine="reference-engine")
        ver2.clock = lambda: 10**12
        with self.assertRaises(InvalidModule):
            g2.admit(W.add_module(), v["attestation"], profile="deterministic", engine="reference-engine")

    def test_toctou(self):
        buf = bytearray(W.add_module())
        v = self.gate.validate(buf, profile="deterministic", engine="reference-engine")
        t = self.gate.admit(buf, v["attestation"], profile="deterministic", engine="reference-engine")
        buf[-2] = 0x6B  # caller mutates its buffer after admission
        self.assertEqual(self.gate.execute(t, lambda b: b), bytes(W.add_module()))
        forged = admission.AdmissionTicket(t.module_digest, t.profile, t.engine, t.epoch, t.attestation,
                                           bytes(buf))
        with self.assertRaises(InvalidModule) as cm:
            self.gate.execute(forged, lambda b: b)
        self.assertEqual(cm.exception.code, Code.DIGEST_MISMATCH)
        with self.assertRaises(InvalidModule):
            self.gate.execute(object(), lambda b: b)  # type: ignore[arg-type]

    def test_stale_config_blocks_execution_and_rollback(self):
        m = W.add_module()
        v = self.gate.validate(m, profile="deterministic", engine="reference-engine")
        t = self.gate.admit(m, v["attestation"], profile="deterministic", engine="reference-engine")
        doc = json.loads(registry.canonical_json(registry.DEFAULT_BUNDLE_DOC))
        doc["epoch"] = 2
        self.gate.activate(registry.load_bundle(json.dumps(doc).encode()))
        with self.assertRaises(InvalidModule) as cm:
            self.gate.execute(t, lambda b: b)
        self.assertEqual(cm.exception.code, Code.STALE_CONFIGURATION)
        with self.assertRaises(InvalidModule):
            self.gate.admit(m, v["attestation"], profile="deterministic", engine="reference-engine")
        with self.assertRaises(InvalidModule):  # rollback to epoch 1 refused
            self.gate.activate(registry.default_bundle())

    def test_nan_canonicalisation_required(self):
        doc = json.loads(registry.canonical_json(registry.DEFAULT_BUNDLE_DOC))
        doc["engines"]["reference-engine"]["nan_canonicalization"] = False
        g, _, _ = make_gate(bundle=registry.load_bundle(json.dumps(doc).encode()))
        v = g.validate(W.seeds()["float"], profile="deterministic", engine="reference-engine")
        self.assertEqual(v["failure"]["code"], "ENGINE_UNSUPPORTED")
        self.assertEqual(g.validate(W.add_module(), profile="deterministic",
                                    engine="reference-engine")["outcome"], "accept")

    def test_health_and_audit_chain(self):
        self.assertEqual(self.gate.health()["status"], "ready")
        self.gate.validate(W.add_module(), profile="deterministic", engine="reference-engine")
        self.gate.validate(b"junk", profile="deterministic", engine="reference-engine")
        ev = self.gate.audit.events
        self.assertTrue(telemetry.verify_chain(ev))
        ev[1]["profile"] = "tampered"
        self.assertFalse(telemetry.verify_chain(ev))

    def test_audit_memory_window_bounded(self):
        a = telemetry.AuditStream(max_memory_events=5)
        for i in range(23):
            a.emit("x", i=i)
        self.assertEqual(len(a.events), 5)
        self.assertEqual(a.total, 23)
        self.assertTrue(telemetry.verify_chain(a.events, a.window_prev))
        self.assertFalse(telemetry.verify_chain(a.events))

    def test_internal_error_is_refusal(self):
        v = self.gate.validate(b"\x00asm\x01\x00\x00\x00\x01\x80\x80\x80\x80\x80\x00",
                               profile="deterministic", engine="reference-engine")
        self.assertEqual(v["outcome"], "reject")
        orig = typecheck._module_level
        try:
            typecheck._module_level = lambda ctx: 1 / 0
            v = admission.validate_module  # noqa: F841
            gate, _, _ = make_gate()
            res = gate.validate(W.add_module(), profile="deterministic", engine="reference-engine")
            self.assertEqual(res["failure"]["code"], "INTERNAL_ERROR")
            self.assertEqual(res["outcome"], "error")
        finally:
            typecheck._module_level = orig


# ======================================================================= M09
class CacheTest(unittest.TestCase):
    def test_cache_semantics(self):
        gate, _, _ = make_gate(cache=cache.ValidationCache(capacity=2))
        m = W.add_module()
        a = gate.validate(m, profile="deterministic", engine="reference-engine")
        b = gate.validate(m, profile="deterministic", engine="reference-engine")
        self.assertEqual(gate.cache.hits, 1)
        self.assertNotEqual(json.loads(a["attestation"])["payload"], json.loads(b["attestation"])["payload"])
        gate.validate(m, profile="permissive", engine="reference-engine")  # different key
        self.assertEqual(gate.cache.hits, 1)
        gate.validate(W.seeds()["float"], profile="deterministic", engine="reference-engine")
        self.assertEqual(len(gate.cache), 2)
        self.assertEqual(gate.cache.evictions, 1)
        gate.cache.bump_epoch()
        self.assertEqual(len(gate.cache), 0)

    def test_nondeterministic_failures_not_cached(self):
        c = cache.ValidationCache()
        gate, _, _ = make_gate(cache=c, limits=limits.Limits(deadline_seconds=-1))
        gate.validate(W.seeds()["control"], profile="deterministic", engine="reference-engine")
        self.assertEqual(len(c), 0)

    def test_thread_safety(self):
        c = cache.ValidationCache(capacity=50)
        errs = []

        def work(i):
            try:
                for j in range(500):
                    k = c.key(a=i, b=j % 70)
                    c.put(k, j)
                    c.get(k)
                    if j % 97 == 0:
                        c.bump_epoch()
            except Exception as e:  # noqa: BLE001
                errs.append(e)
        ts = [threading.Thread(target=work, args=(i,)) for i in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(errs, [])
        self.assertLessEqual(len(c), 50)


# ======================================================================= M12/M35/M37
class TelemetryTest(unittest.TestCase):
    def test_sanitize_and_bounds(self):
        s = errors.sanitize("a\nb\x1b[31m" + "x" * 1000)
        self.assertNotIn("\n", s)
        self.assertNotIn("\x1b", s)
        self.assertLessEqual(len(s), errors.MAX_DETAIL_CHARS + 10)

    def test_metrics_cardinality(self):
        mt = telemetry.Metrics(["deterministic"])
        for i in range(100):
            mt.inc("validations_total", outcome="accept", profile=f"attacker-{i}", code="OK")
        self.assertEqual(len(mt.counters), 1)
        self.assertIn('profile="other"', mt.exposition())

    def test_traceparent(self):
        tid, parent = telemetry.parse_traceparent("00-" + "a" * 32 + "-" + "b" * 16 + "-01")
        self.assertEqual((tid, parent), ("a" * 32, "b" * 16))
        tid, parent = telemetry.parse_traceparent("garbage\n")
        self.assertEqual(len(tid), 32)
        self.assertEqual(parent, "")

    def test_explain_and_no_raw_bytes(self):
        gate, _, _ = make_gate()
        m = W.seeds()["clock_import"]
        v = gate.validate(m, profile="deterministic", engine="reference-engine")
        text = telemetry.explain(v)
        self.assertIn("FEATURE_REFUSED", text)
        self.assertIn("wall-clock", text)
        self.assertIn("remedy", text)
        blob = json.dumps(gate.audit.events)
        self.assertNotIn(m.hex(), blob)


# ======================================================================= M17/M18
class HostImportTest(unittest.TestCase):
    def test_contract(self):
        b = registry.default_bundle()
        c = hostimports.default_contract(b.known_features)
        classes, feats = c.classify([("wasi_snapshot_preview1", "clock_time_get", 0)])
        self.assertEqual((classes, feats), ({"nondeterministic"}, {"wall-clock"}))
        with self.assertRaises(InvalidModule):
            c.classify([("wasi_snapshot_preview1", "clock_time_get", 3)])  # wrong kind
        with self.assertRaises(InvalidModule):
            c.classify([("wasi_snapshot_preview1", "path_open", 0)])     # deny by default
        with self.assertRaises(InvalidModule):
            hostimports.load_contract(b'{"schema":"PK_HOST_IMPORT_CONTRACT/1","imports":{"a.b":'
                                      b'{"class":"pure","implies_feature":"bogus","kinds":["func"]}}}',
                                      b.known_features)


# ======================================================================= M22/M42/M43/M44
class ConfigTest(unittest.TestCase):
    def test_signed_bundle_store_and_reconstruct(self):
        gate, _, _ = make_gate()
        cfg_signer = attest.Signer("cfg1")
        ver = attest.Verifier({"cfg1": cfg_signer.public_raw()})
        doc = json.loads(registry.canonical_json(registry.DEFAULT_BUNDLE_DOC))
        doc["epoch"] = 5
        env = attest.sign_bundle(cfg_signer, registry.canonical_json(doc))
        with tempfile.TemporaryDirectory() as d:
            store = config_store.ConfigStore(os.path.join(d, "cfg.jsonl"))
            b = store.activate(gate, env, ver, actor="ops@example", reason="test")
            self.assertEqual(gate.bundle.revision, b.revision)
            self.assertEqual(store.reconstruct(5, ver).revision, b.revision)
            tampered = json.loads(env)
            tampered["bundle"] = tampered["bundle"][:-4] + "AAAA"
            with self.assertRaises(InvalidModule):
                store.activate(gate, json.dumps(tampered), ver, actor="x", reason="y")
            self.assertEqual(gate.bundle.epoch, 5)  # failed activation left config unchanged
            self.assertTrue(store.verify())


# ======================================================================= M51
class WaiverTest(unittest.TestCase):
    def _w(self, **over):
        w = {"id": "W1", "items": ["M29-043"], "scope": "4.3.0", "owner": "a", "approver": "b",
             "compensating_control": "cache", "expires": "2027-01-01", "reason": "r"}
        w.update(over)
        return w

    def test_rules(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "w.json")
            for w, ok in [(self._w(), True), (self._w(approver="a"), False),
                          (self._w(items=["M01-051"]), False), (self._w(owner=""), False)]:
                with open(p, "w") as fh:
                    json.dump({"schema": "PK_WAIVER_REGISTER/1", "waivers": [w]}, fh)
                if ok:
                    self.assertTrue(waivers.load(p)[0].valid_on(dt.date(2026, 12, 31)))
                else:
                    with self.assertRaises(ValueError):
                        waivers.load(p)


# ======================================================================= M14/M15
class FuzzSmokeTest(unittest.TestCase):
    def test_fuzz_oracle(self):
        rep = fuzz.run(1234, list(W.seeds().values()), 3000)
        self.assertEqual(rep["crashes"], [])
        self.assertEqual(rep["nondeterministic"], [])

    def test_generator_emits_valid_modules(self):
        import random
        rng = random.Random(7)
        for _ in range(300):
            self.assertEqual(code_of(fuzz.gen_module(rng)), "OK")


@unittest.skipUnless(differential.node_available(), "node not available - differential NOT evaluated")
class DifferentialTest(unittest.TestCase):
    def test_no_false_accepts(self):
        corpus = list(W.seeds().items()) + list(fuzz.inputs(99, list(W.seeds().values()), 3000))
        rep = differential.run(corpus)
        self.assertEqual(rep["critical"], 0, rep)
        self.assertEqual(rep["disagreements"].get("FALSE_REJECT", 0), 0, rep)


class BenchSmokeTest(unittest.TestCase):
    def test_bench_small(self):
        r = bench.run(sizes=(1024,), reps=3)
        self.assertEqual(r["rows"][0]["reps"], 3)
        self.assertIn(bench.gate(r)["verdict"], ("PASS", "FAIL"))


if __name__ == "__main__":
    unittest.main()


class OracleCorpusTest(unittest.TestCase):
    """Hand-written instruction families; codes pinned, verdicts judged by V8."""

    def test_codes(self):
        from oracle_corpus import CASES
        for k, (m, want) in CASES.items():
            with self.subTest(k):
                self.assertEqual(code_of(m), want)

    @unittest.skipUnless(differential.node_available(), "node not available - differential NOT evaluated")
    def test_against_reference(self):
        from oracle_corpus import CASES, KNOWN_DIVERGENCE
        items = [(k, m) for k, (m, want) in CASES.items()
                 if want not in ("UNSUPPORTED_PROPOSAL", "LIMIT_EXCEEDED") and k not in KNOWN_DIVERGENCE]
        rep = differential.run(items)
        self.assertEqual(rep["agree"], rep["total"], rep)


try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None


@unittest.skipIf(jsonschema is None, "jsonschema not installed - schema conformance NOT evaluated")
class SchemaConformanceTest(unittest.TestCase):
    """A-004: every externally consumed document validates against schemas/."""

    def schema(self, name):
        p = HERE.parent / "schemas" / name
        s = json.loads(p.read_text())
        reg = {}
        for f in (HERE.parent / "schemas").glob("*.json"):
            reg[f.name] = json.loads(f.read_text())
        from referencing import Registry, Resource
        registry_ = Registry().with_resources((k, Resource.from_contents(v)) for k, v in reg.items())
        return jsonschema.Draft202012Validator(s, registry=registry_)

    def test_documents(self):
        gate, _, _ = make_gate()
        ok = gate.validate(W.add_module(), profile="deterministic", engine="reference-engine")
        bad = gate.validate(b"junk", profile="deterministic", engine="reference-engine")
        v = self.schema("PK_MODULE_VALIDATION-2.json")
        v.validate(ok)
        v.validate(bad)
        self.schema("PK_VALIDATION_FAILURE-1.json").validate(bad["failure"])
        self.schema("PK_VALIDATION_ATTESTATION-1.json").validate(
            json.loads(json.loads(ok["attestation"])["payload"]))
        self.schema("PK_ISA_POLICY_BUNDLE-1.json").validate(registry.DEFAULT_BUNDLE_DOC)
        self.schema("PK_HOST_IMPORT_CONTRACT-1.json").validate(hostimports.DEFAULT_CONTRACT_DOC)
        self.schema("PK_HEALTH-1.json").validate(gate.health())
        for ev in gate.audit.events:
            self.schema("PK_AUDIT_EVENT-1.json").validate(ev)
        with self.assertRaises(jsonschema.ValidationError):
            self.schema("PK_VALIDATION_FAILURE-1.json").validate(dict(bad["failure"], extra=1))
