"""M32 fault-injection + M39 canary tests: every injected fault must end in a
refusal/error outcome or an explicit exception - never an accept or admission."""
from __future__ import annotations

import json
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import wasmgen as W  # noqa: E402
from inv09_portable_compute_isa.prod import admission, attest, canary, fuzz, registry, typecheck  # noqa: E402
from inv09_portable_compute_isa.prod.errors import InvalidModule  # noqa: E402


def gate(**kw):
    s = attest.Signer("k")
    return admission.Gate(signer=s, verifier=attest.Verifier({"k": s.public_raw()}), **kw)


class FaultInjectionTest(unittest.TestCase):
    def test_signer_failure_is_not_accept(self):
        g = gate()
        g.signer.sign = lambda payload: (_ for _ in ()).throw(OSError("HSM unavailable"))
        with self.assertRaises(OSError):  # surfaced to caller; no verdict, no attestation
            g.validate(W.add_module(), profile="deterministic", engine="reference-engine")
        self.assertFalse(any(e["kind"] == "validation.accept" for e in g.audit.events))

    def test_cache_corruption_cannot_admit(self):
        g = gate()
        m = W.seeds()["clock_import"]
        v = g.validate(m, profile="deterministic", engine="reference-engine")
        self.assertEqual(v["outcome"], "refuse")
        for k in list(g.cache._d):  # attacker flips the cached verdict to accept
            value, mac = g.cache._d[k]
            g.cache._d[k] = (dict(value, outcome="accept", used=["core"], deterministic=True), mac)
        again = g.validate(m, profile="deterministic", engine="reference-engine")
        self.assertEqual(again["outcome"], "refuse")      # tampered entry discarded, re-validated
        self.assertEqual(g.cache.integrity_failures, 1)

    def test_audit_sink_failure_propagates(self):
        g = gate()
        g.audit.emit = lambda *a, **k: (_ for _ in ()).throw(OSError("disk full"))
        with self.assertRaises(OSError):
            g.validate(W.add_module(), profile="deterministic", engine="reference-engine")

    def test_deadline_mid_validation(self):
        from inv09_portable_compute_isa.prod import limits
        ticks = iter(range(10**9))
        g = limits.Governor(limits.Limits(deadline_seconds=5), clock=lambda: next(ticks) * 10)
        with self.assertRaises(InvalidModule) as cm:
            from inv09_portable_compute_isa.prod import decoder
            decoder.decode(W.add_module(), gov=g)
        self.assertEqual(cm.exception.code.value, "DEADLINE_EXCEEDED")

    def test_verifier_clock_skew(self):
        g = gate()
        v = g.validate(W.add_module(), profile="deterministic", engine="reference-engine")
        g.verifier.clock = lambda: 0  # clock far in the past -> not yet valid
        with self.assertRaises(InvalidModule):
            g.admit(W.add_module(), v["attestation"], profile="deterministic", engine="reference-engine")

    def test_recursion_and_memory_errors_mapped(self):
        orig = typecheck._module_level
        for exc in (RecursionError, MemoryError):
            typecheck._module_level = lambda ctx, e=exc: (_ for _ in ()).throw(e())
            try:
                with self.assertRaises(InvalidModule) as cm:
                    typecheck.validate_module(W.add_module())
                self.assertEqual(cm.exception.code.value, "LIMIT_EXCEEDED")
            finally:
                typecheck._module_level = orig


class CanaryTest(unittest.TestCase):
    def test_widening_blocks_promotion(self):
        inc = gate()
        doc = json.loads(registry.canonical_json(registry.DEFAULT_BUNDLE_DOC))
        doc["profiles"]["deterministic"]["allowed_import_classes"].append("io-deterministic")
        cand = gate(bundle=registry.load_bundle(json.dumps(doc).encode()))
        corpus = list(W.seeds().items())
        rep = canary.compare(inc, cand, corpus, profile="deterministic", engine="reference-engine")
        self.assertEqual(rep["decision"], "HOLD")
        self.assertIn("wasi_import", rep["widening"])
        same = canary.compare(inc, gate(), corpus + list(fuzz.inputs(3, [W.add_module()], 300)),
                              profile="deterministic", engine="reference-engine")
        self.assertEqual(same["decision"], "PROMOTE")


if __name__ == "__main__":
    unittest.main()
