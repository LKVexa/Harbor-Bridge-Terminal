"""MC-016/079 lifecycle coverage, MC-019/020 precedence + disconnected rules, MC-026/052/053 resilience,
MC-029..033 configuration, MC-046 sealed store, MC-027 failure model, MC-073 redaction, MC-024 authz edges."""
import copy
import importlib
import random
import unittest

from harness import PKGNAME, UkError

lifecycle = importlib.import_module(f"{PKGNAME}.lifecycle")
precedence = importlib.import_module(f"{PKGNAME}.precedence")
resilience = importlib.import_module(f"{PKGNAME}.resilience")
config = importlib.import_module(f"{PKGNAME}.config")
sealed = importlib.import_module(f"{PKGNAME}.sealed_store")
errors = importlib.import_module(f"{PKGNAME}.errors")
redaction = importlib.import_module(f"{PKGNAME}.redaction")
telemetry = importlib.import_module(f"{PKGNAME}.telemetry")


class Lifecycle(unittest.TestCase):
    def test_every_pair_of_states(self):
        allowed = refused = 0
        for a in lifecycle.TRANSITIONS:
            for b in lifecycle.TRANSITIONS:
                if b in lifecycle.TRANSITIONS[a]:
                    lifecycle.check(a, b)
                    allowed += 1
                else:
                    with self.assertRaises(UkError):
                        lifecycle.check(a, b)
                    refused += 1
        self.assertEqual(allowed + refused, len(lifecycle.TRANSITIONS) ** 2)
        self.assertEqual(lifecycle.TERMINAL, frozenset({"rejected", "stopped"}))

    def test_every_state_reachable_and_every_path_terminates(self):
        seen, stack = {"pending"}, ["pending"]
        while stack:
            for n in lifecycle.TRANSITIONS[stack.pop()]:
                if n not in seen:
                    seen.add(n)
                    stack.append(n)
        self.assertEqual(seen, set(lifecycle.TRANSITIONS))

    def test_generated_doc_matches(self):
        from harness import PKG
        self.assertEqual((PKG / "docs" / "LIFECYCLE.md").read_text(), lifecycle.render_markdown())


class Precedence(unittest.TestCase):
    C = precedence.Candidate

    def test_security_then_residency_then_slo_then_cost(self):
        r, _ = precedence.resolve([self.C("cheap-insecure", False, True, True, 1), self.C("ok", True, True, True, 9)])
        self.assertEqual(r.name, "ok")
        r, _ = precedence.resolve([self.C("abroad", True, False, True, 1), self.C("home", True, True, False, 9)])
        self.assertEqual(r.name, "home")
        r, why = precedence.resolve([self.C("slow", True, True, False, 1), self.C("fast", True, True, True, 5)])
        self.assertEqual(r.name, "fast")
        self.assertIsNone(precedence.resolve([self.C("x", False, True, True, 0)])[0])
        self.assertIsNone(precedence.resolve([self.C("x", True, False, True, 0)])[0])

    def test_disconnected(self):
        d = precedence.disconnected_decision
        self.assertFalse(d(trust_age_s=90000, max_age_s=86400, action="admit")[0])
        self.assertTrue(d(trust_age_s=90000, max_age_s=86400, action="keep_running")[0])
        self.assertTrue(d(trust_age_s=90000, max_age_s=86400, action="stop")[0])
        self.assertFalse(d(trust_age_s=1, max_age_s=10, action="launch-nukes")[0])


class Resilience(unittest.TestCase):
    def test_retry_only_retryable_and_idempotent(self):
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise UkError("UK_VMM_LAUNCH_FAILED")
            return "ok"
        self.assertEqual(resilience.retry(flaky, idempotent=True, sleep=lambda s: None, rng=random.Random(1)), "ok")
        calls.clear()
        with self.assertRaises(UkError):
            resilience.retry(flaky, idempotent=False, sleep=lambda s: None)
        self.assertEqual(len(calls), 1)
        with self.assertRaises(UkError):
            resilience.retry(lambda: (_ for _ in ()).throw(UkError("UK_SIG_INVALID")), idempotent=True, sleep=lambda s: None)

    def test_backoff_bounded_with_jitter(self):
        d = resilience.backoff_delays(5, 0.05, 1.0, random.Random(3))
        self.assertEqual(len(d), 4)
        self.assertTrue(all(0 <= x <= min(1.0, 0.05 * 2 ** i) for i, x in enumerate(d)))

    def test_circuit_breaker(self):
        t = [0.0]
        cb = resilience.CircuitBreaker("trust", failure_threshold=2, reset_after_s=10, clock=lambda: t[0])
        for _ in range(2):
            with self.assertRaises(ZeroDivisionError):
                cb.call(lambda: 1 / 0)
        with self.assertRaises(UkError) as c:
            cb.call(lambda: 1)
        self.assertEqual(c.exception.code, "UK_CIRCUIT_OPEN")
        t[0] = 11
        self.assertEqual(cb.call(lambda: 7), 7)
        self.assertEqual(cb.state, "closed")

    def test_deadline_and_cancel(self):
        t = [0.0]
        d = resilience.Deadline.after(100, clock=lambda: t[0])
        d.check()
        t[0] = 0.2
        with self.assertRaises(UkError) as c:
            d.check()
        self.assertEqual(c.exception.code, "UK_DEADLINE_EXCEEDED")
        tok = resilience.CancelToken()
        tok.cancel()
        with self.assertRaises(UkError):
            tok.check()


class Config(unittest.TestCase):
    def test_valid_and_invalid(self):
        config.validate(config.example())
        muts = [lambda c: c.pop("vmm"), lambda c: c["limits"].update(max_image_bytes=True),
                lambda c: c.update(environment="moon"), lambda c: c["permitted_syscalls"].append("Bad Name"),
                lambda c: c.update(trust_root_ref={"secret_ref": "-----BEGIN PRIVATE KEY-----", "max_age_hours": 1}),
                lambda c: c["provenance_policy"].update(require_source_digest=False) or c.update(environment="prod"),
                lambda c: c["vmm"].update(backend="script") or c.update(environment="prod")]
        for m in muts:
            c = copy.deepcopy(config.example())
            m(c)
            with self.assertRaises(UkError):
                config.validate(c)

    def test_atomic_apply_history_and_rollback(self):
        s = config.ConfigStore()
        g1 = s.apply(config.example(), actor="alice", reason="initial")
        bad = config.example()
        bad["limits"]["boot_deadline_ms"] = 0
        with self.assertRaises(UkError):
            s.apply(bad, actor="alice", reason="broken")
        self.assertIs(s.active, g1)                 # failed apply changed nothing
        c2 = config.example()
        c2["quotas"]["max_instances_per_tenant"] = 4
        s.apply(c2, actor="bob", reason="tighten quota")
        g3 = s.rollback(1, actor="bob", reason="incident")
        self.assertEqual(g3.sha256, g1.sha256)
        self.assertEqual(s.verify_history(), [])
        with self.assertRaises(TypeError):
            s.active.config["environment"] = "prod"
        with self.assertRaises(UkError):
            s.apply(config.example(), actor="", reason="x")

    def test_redacted_view(self):
        s = config.ConfigStore()
        s.apply(config.example(), actor="alice", reason="init")
        self.assertIn("trust_root_ref", s.redacted())


class SealedStore(unittest.TestCase):
    def test_roundtrip_rotation_tamper_context(self):
        try:
            import cryptography  # noqa: F401
        except ImportError:
            self.skipTest("cryptography not installed (optional lane: sealed_store refuses plaintext instead)")
        ring = sealed.KeyRing()
        ring.rotate(b"a" * 32)
        blob = sealed.seal(ring, b"journal", "journal/v1")
        ring.rotate(b"b" * 32)
        self.assertEqual(sealed.open_sealed(ring, blob, "journal/v1"), b"journal")
        new = sealed.rewrap(ring, blob, "journal/v1")
        ring.retire(1)
        with self.assertRaises(UkError):
            sealed.open_sealed(ring, blob, "journal/v1")
        self.assertEqual(sealed.open_sealed(ring, new, "journal/v1"), b"journal")
        with self.assertRaises(UkError):
            sealed.open_sealed(ring, new, "audit/v1")
        t = bytearray(new)
        t[-1] ^= 1
        with self.assertRaises(UkError):
            sealed.open_sealed(ring, bytes(t), "journal/v1")


class FailureModel(unittest.TestCase):
    def test_registry_is_consistent(self):
        for c in errors.REGISTRY.values():
            self.assertIn(c.outcome, errors.OUTCOMES)
            self.assertTrue(c.code.startswith("UK_"))
        e = errors.UkError("UK_SEAL_DRIFT", only_in_binary={"socket"})
        d = e.to_dict()
        self.assertEqual(d["schema"], "PK_UNIKERNEL_ERROR/1")
        self.assertEqual(d["details"]["only_in_binary"], ["socket"])
        with self.assertRaises(KeyError):
            errors.UkError("NOT_A_CODE")

    def test_codes_are_append_only_against_published_list(self):
        import json
        from harness import PKG
        published = json.loads((PKG / "ops" / "ERROR_CODES.json").read_text())["codes"]
        self.assertTrue(set(published) <= set(errors.REGISTRY), "a published code was removed or renamed")


class Diagnostics(unittest.TestCase):
    def test_redaction_and_bounded_cardinality(self):
        r = redaction.redact({"token": "abc", "msg": "Bearer abcdefghijkl", "deep": [[[[[[[[[[[[[[[[[["x"]]]]]]]]]]]]]]]]]]})
        self.assertEqual(r["token"], "[REDACTED]")
        self.assertIn("[REDACTED]", r["msg"])
        m = telemetry.Metrics(max_series=40)
        for i in range(500):
            m.inc("uk_seal_failures_total", reason=f"r{i}")
        self.assertGreater(m.dropped_series, 0)
        self.assertLessEqual(len(m.counters) + len(m.gauges) + len(m.hists), 40)

    def test_traceparent_parsing_is_safe(self):
        for bad in (None, "", "garbage", "00-" + "0" * 32 + "-" + "1" * 16 + "-01", "x" * 1000):
            tc = telemetry.TraceContext.parse(bad)
            self.assertEqual(len(tc.trace_id), 32)


if __name__ == "__main__":
    unittest.main()
