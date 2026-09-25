"""Configuration: schema, secure defaults, fail-closed validation, layering, provenance,
atomic activation, rollback, secrets (C032-C039)."""
import json
import pathlib
import random
import threading
import unittest

from _util import m, PKG_DIR

config = m("config")
errors = m("errors")


class ValidationTest(unittest.TestCase):
    def test_defaults_are_valid_and_secure(self):
        """REQ: C033 C039 C043"""
        self.assertEqual(config.validate(config.DEFAULTS), [])
        d = config.DEFAULTS
        self.assertEqual(d["network_exposure"], "none")
        self.assertFalse(d["log_payloads"])
        self.assertFalse(d["diagnostics_privileged"])
        self.assertTrue(d["auth_required"])
        self.assertIsNone(d["signing_key_ref"])
        self.assertLess(d["max_outstanding"], 10_000_000)
        for k in d:
            self.assertIn(k, config.SCHEMA)

    def test_every_shipped_config_layer_valid(self):
        """REQ: C033 C035"""
        files = sorted((PKG_DIR / "config").glob("*.json"))
        self.assertGreaterEqual(len(files), 5)
        for p in files:
            with self.subTest(p=p.name):
                self.assertEqual(config.validate(config.layer(config.DEFAULTS, config.load_file(p))), [])

    def test_matrix_of_invalid_documents(self):
        """REQ: C034 INV18-OPS-002"""
        base = dict(config.DEFAULTS)
        cases = {
            "unknown": {**base, "surprise": 1},
            "missing": {k: v for k, v in base.items() if k != "max_outstanding"},
            "type": {**base, "max_outstanding": "100"},
            "bool_as_int": {**base, "max_outstanding": True},
            "range_low": {**base, "max_outstanding": 0},
            "range_high": {**base, "trace_sampling": 1.5},
            "enum": {**base, "environment": "moon"},
            "nan": {**base, "stall_threshold_s": float("nan")},
            "schema_version": {**base, "schema_version": 2},
            "soft_gt_hard": {**base, "soft_outstanding": 200_000},
            "tenant_gt_process": {**base, "max_per_tenant": 200_000},
            "not_object": [],
        }
        for name, doc in cases.items():
            with self.subTest(case=name):
                errs = config.validate(doc)
                self.assertTrue(errs, name)
                self.assertTrue(all(e.code == "INVALID_CONFIG" for e in errs))

    def test_security_combinations_rejected(self):
        """REQ: C034 C033 C039 C047"""
        base = dict(config.DEFAULTS)
        for doc in ({**base, "network_exposure": "mtls", "auth_required": False},
                    {**base, "network_exposure": "mtls", "signing_key_ref": None},
                    {**base, "log_payloads": True},
                    {**base, "environment": "prod", "log_payloads": True, "diagnostics_privileged": True},
                    {**base, "signing_key_ref": "plain-secret-value"}):
            self.assertTrue(config.validate(doc))

    def test_fuzz_malformed_configs_never_crash_or_activate(self):
        """REQ: C034 C085"""
        rng = random.Random(1834)
        junk = [None, -1, 0, 1e308, "", "x" * 300, [], {}, True, float("inf"), "secret://ok"]
        store = config.ConfigStore({"environment": "test"})
        before = store.active().revision_id
        for _ in range(500):
            doc = dict(config.DEFAULTS)
            for _ in range(rng.randint(1, 4)):
                doc[rng.choice(list(config.SCHEMA) + ["zz"])] = rng.choice(junk)
            errs = config.validate(doc)
            if errs:
                with self.assertRaises(errors.Rejected):
                    store.activate(doc, author="fuzz")
        self.assertTrue(store.active().revision_id)
        self.assertEqual(config.validate(dict(store.values())), [])

    def test_fail_closed_no_partial_activation(self):
        """REQ: C034 C037"""
        store = config.ConfigStore({"environment": "test"})
        rev = store.active()
        with self.assertRaises(errors.Rejected):
            store.activate({**dict(store.values()), "max_outstanding": 5, "environment": "moon"}, author="x")
        self.assertIs(store.active(), rev)
        self.assertEqual(store.values()["max_outstanding"], config.DEFAULTS["max_outstanding"])


class ApplicabilityTest(unittest.TestCase):
    def test_every_supported_context_runs(self):
        """REQ: C012 C005 — contexts from docs/ARCHITECTURE.md §1 emulated by config layers"""
        enum = config.SCHEMA["context"][3]
        self.assertEqual(set(enum), {"cloud", "datacenter", "near-edge", "far-edge", "local"})
        doc = (PKG_DIR / "docs/ARCHITECTURE.md").read_text()
        for ctx in ("cloud", "datacenter", "near-edge", "far-edge"):
            self.assertIn(ctx, doc)
            store = config.ConfigStore(config.layer(config.load_file(PKG_DIR / "config/site-far-edge.json"),
                                                    {"context": ctx}))
            rt = m("runtime").Runtime(store)
            w, r = rt.create(int); rt.resolve(w, 1); self.assertEqual(rt.take(r), ("ok", 1))
        far = config.load_file(PKG_DIR / "config/site-far-edge.json")
        self.assertLessEqual(far["max_outstanding"], 10000)
        env = m("testrunner").environment()
        self.assertIn("context", env)


class LayeringTest(unittest.TestCase):
    def test_deterministic_layering(self):
        """REQ: C035"""
        env = config.load_file(PKG_DIR / "config/prod.json")
        site = config.load_file(PKG_DIR / "config/site-far-edge.json")
        a = config.layer(config.DEFAULTS, env, site, {"trace_sampling": 0.01})
        b = config.layer(config.DEFAULTS, env, site, {"trace_sampling": 0.01})
        self.assertEqual(a, b)
        self.assertEqual(a["max_outstanding"], 10000)       # site overrides env
        self.assertEqual(a["trace_sampling"], 0.01)         # instance overrides site
        self.assertEqual(a["environment"], "prod")

    def test_env_injection_allowlisted(self):
        """REQ: C035 C039"""
        got = config.from_env({"INV18_CFG_MAX_OUTSTANDING": "500", "INV18_CFG_LOG_PAYLOADS": "false", "PATH": "/bin",
                               "INV18_RELEASE_KEY": "x", "INV18_CONTEXT": "compat"})   # operational vars ignored
        self.assertEqual(got, {"max_outstanding": 500, "log_payloads": False})
        for bad in ({"INV18_CFG_WHATEVER": "1"}, {"INV18_CFG_MAX_OUTSTANDING": "lots"}, {"INV18_CFG_AUTH_REQUIRED": "yes"}):
            with self.assertRaises(errors.Rejected):
                config.from_env(bad)

    def test_same_artifact_many_environments(self):
        """REQ: C035 C032"""
        tv = m("tools_verify")
        before = (PKG_DIR / "SHA256SUMS").read_text() if (PKG_DIR / "SHA256SUMS").exists() else None
        revs = set()
        for name in ("dev", "test", "staging", "prod", "site-far-edge"):
            store = config.ConfigStore(config.load_file(PKG_DIR / f"config/{name}.json"))
            revs.add(store.active().revision_id)
            rt = m("runtime").Runtime(store)
            w, r = rt.create(int); rt.resolve(w, 1); self.assertEqual(rt.take(r), ("ok", 1))
        self.assertEqual(len(revs), 5)
        after = (PKG_DIR / "SHA256SUMS").read_text() if (PKG_DIR / "SHA256SUMS").exists() else None
        self.assertEqual(before, after)


class ProvenanceTest(unittest.TestCase):
    def test_revision_records(self):
        """REQ: C036"""
        t = iter(range(100, 200))
        store = config.ConfigStore({"environment": "test"}, author="alice", approver="bob", clock=lambda: next(t))
        r1 = store.active()
        r2 = store.activate({**dict(store.values()), "trace_sampling": 0.3}, author="carol", approver="dan")
        self.assertEqual(r2.supersedes, r1.revision_id)
        self.assertEqual((r2.author, r2.approver, r2.environment), ("carol", "dan", "test"))
        self.assertEqual(r2.digest, config.digest(dict(r2.values)))
        self.assertTrue(r2.activated_at > r1.activated_at)
        self.assertEqual(len(store.history), 2)
        with self.assertRaises(TypeError):
            r2.values["max_outstanding"] = 1          # immutable
        rt = m("runtime").Runtime(store)
        st = m("status").status(rt)
        self.assertEqual(st["config_revision"], r2.revision_id)


class AtomicityTest(unittest.TestCase):
    def test_concurrent_readers_never_see_mixed_state(self):
        """REQ: C037"""
        store = config.ConfigStore({"environment": "test"})
        A = {**dict(store.values()), "max_outstanding": 1000, "soft_outstanding": 900, "max_per_tenant": 100}
        B = {**dict(store.values()), "max_outstanding": 2000, "soft_outstanding": 1900, "max_per_tenant": 200}
        stop = threading.Event()
        mixed = []
        def reader():
            while not stop.is_set():
                v = store.values()
                pair = (v["max_outstanding"], v["soft_outstanding"], v["max_per_tenant"])
                if pair not in ((1000, 900, 100), (2000, 1900, 200), (100000, 80000, 10000)):
                    mixed.append(pair)
        ts = [threading.Thread(target=reader) for _ in range(4)]
        [t.start() for t in ts]
        for i in range(300):
            store.activate(A if i % 2 else B, author="flip")
        stop.set(); [t.join() for t in ts]
        self.assertEqual(mixed, [])

    def test_crash_between_stage_and_commit(self):
        """REQ: C037 C060"""
        store = config.ConfigStore({"environment": "test"})
        rev = store.active()
        with self.assertRaises(errors.Rejected):
            store.activate({**dict(store.values()), "trace_sampling": 0.9}, author="x", _fail_after_stage=True)
        self.assertIs(store.active(), rev)
        self.assertEqual(len(store.history), 1)


class RollbackTest(unittest.TestCase):
    def test_operator_and_automatic_rollback(self):
        """REQ: C038 INV18-OPS-003"""
        audit = []
        store = config.ConfigStore({"environment": "test"}, audit=lambda a, d: audit.append((a, d)))
        good = store.active()
        store.activate({**dict(store.values()), "trace_sampling": 0.9}, author="upgrade")
        rb = store.rollback(author="operator", reason="drill")
        self.assertEqual(dict(rb.values), dict(good.values))
        self.assertIsNotNone(rb.rollback_of)
        auto = store.activate_or_rollback({**dict(store.values()), "trace_sampling": 0.7}, author="canary",
                                          health_check=lambda r: False)
        self.assertEqual(auto.values["trace_sampling"], good.values["trace_sampling"])
        self.assertIn("config.rollback", [a for a, _ in audit])
        with self.assertRaises(errors.Rejected):
            config.ConfigStore({"environment": "test"}).rollback(author="x", reason="none")

    def test_rollback_with_inflight_futures(self):
        """REQ: C038 C092"""
        rt = m("runtime").Runtime(config.ConfigStore({"environment": "test"}))
        caps = [rt.create(int) for _ in range(10)]
        rt.config.activate({**dict(rt.config.values()), "max_outstanding": 20, "soft_outstanding": 20,
                            "max_per_tenant": 20}, author="u")
        rt.config.rollback(author="op", reason="drill")
        for w, r in caps:
            rt.resolve(w, 1); self.assertEqual(rt.take(r), ("ok", 1))


class SecretsTest(unittest.TestCase):
    def test_no_plaintext_secrets_in_repository_configs(self):
        """REQ: C039"""
        import re
        pat = re.compile(r"(sk-[A-Za-z0-9]{8,}|BEGIN [A-Z ]*PRIVATE KEY|password\"\s*:\s*\"[^\"]+)", re.I)
        for p in list((PKG_DIR / "config").glob("*.json")) + list((PKG_DIR / "governance").glob("*.json")):
            self.assertIsNone(pat.search(p.read_text()), p.name)
            data = json.loads(p.read_text())
            if isinstance(data, dict) and data.get("signing_key_ref"):
                self.assertTrue(data["signing_key_ref"].startswith("secret://"))

    def test_sentinel_secret_not_leaked_by_config_errors(self):
        """REQ: C039 INV18-SEC-004"""
        errs = config.validate({**config.DEFAULTS, "signing_key_ref": "SENTINEL-SECRET-xyz789"})
        self.assertNotIn("SENTINEL-SECRET-xyz789", json.dumps([e.to_dict() for e in errs]))


if __name__ == "__main__":
    unittest.main()
