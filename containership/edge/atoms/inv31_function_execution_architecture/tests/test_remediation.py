"""Remediation tests for INV-31 4.3.0 (standard library only, no pk_core needed).

Each test class names the checklist items it provides evidence for.  Tests
that use the Reference* adapters are contract tests against test doubles and
are not interoperation evidence with the real adjacent layers.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import pathlib
import random
import subprocess
import sys
import tempfile
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG_DIR.parent))
PKG = PKG_DIR.name

import importlib  # noqa: E402

pkg = importlib.import_module(PKG)
boundary = importlib.import_module(f"{PKG}.boundary")
config = importlib.import_module(f"{PKG}.config")
errors = importlib.import_module(f"{PKG}.errors")
adapters = importlib.import_module(f"{PKG}.adapters")
runtime = importlib.import_module(f"{PKG}.runtime")
pkcompat = importlib.import_module(f"{PKG}.pkcompat")

KEY = b"k" * 32
OTHER_KEY = b"o" * 32
_nonce = iter(range(10**9))


def assertion(tenant="t1", caps=None, kind="service", now=0, life=100, key=KEY, key_id="k1",
              subject="caller"):
    caps = [f"invoke:{tenant}"] if caps is None else caps
    return boundary.HmacAuthenticator.sign(key, {
        "key_id": key_id, "subject": subject, "tenant": tenant, "capabilities": caps,
        "kind": kind, "issued_at": now, "expires_at": now + life, "nonce": f"n{next(_nonce)}"})


def req(tenant="t1", version="v1", **extra):
    return {"schema": boundary.REQUEST_SCHEMA, "tenant": tenant, "version": version, **extra}


def gateway(**kw):
    pool = kw.pop("pool", None) or runtime.FunctionPool(max_instances=8)
    return boundary.Gateway(pool=pool, authenticator=boundary.HmacAuthenticator({"k1": KEY}), **kw)


OPERATOR = dict(tenant="ops", caps=["pool:drain", "pool:observe", "config:apply"], kind="operator")


class AuthenticationTest(unittest.TestCase):  # C023 C044 C048 C050(replay/spoofing)
    def test_valid_assertion_invokes(self):
        r = gateway().invoke(assertion(), req(), now=1)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["result"]["schema"], "PK_INVOCATION/1")

    def test_empty_keystore_refuses_everyone(self):
        gw = boundary.Gateway(pool=runtime.FunctionPool(), authenticator=boundary.HmacAuthenticator())
        r = gw.invoke(assertion(), req(), now=1)
        self.assertEqual(r["error"]["code"], "INV31-E-AUTHN")
        self.assertFalse(gw.health(1)["ready"])

    def test_forged_signature_refused(self):
        r = gateway().invoke(assertion(key=OTHER_KEY), req(), now=1)
        self.assertEqual(r["error"]["code"], "INV31-E-AUTHN")

    def test_tampered_claims_refused(self):
        a = assertion()
        a["capabilities"] = ["invoke:t1", "pool:drain"]
        self.assertEqual(gateway().invoke(a, req(), now=1)["error"]["code"], "INV31-E-AUTHN")

    def test_replay_refused(self):
        gw, a = gateway(), assertion()
        self.assertTrue(gw.invoke(a, req(), now=1)["ok"])
        self.assertEqual(gw.invoke(a, req(), now=2)["error"]["code"], "INV31-E-REPLAY")

    def test_expired_future_and_overlong_refused(self):
        gw = gateway()
        self.assertEqual(gw.invoke(assertion(now=0, life=5), req(), now=5)["error"]["code"], "INV31-E-AUTHN")
        self.assertEqual(gw.invoke(assertion(now=50), req(), now=10)["error"]["code"], "INV31-E-AUTHN")
        self.assertEqual(gw.invoke(assertion(life=10_000), req(), now=1)["error"]["code"], "INV31-E-AUTHN")

    def test_revoked_key_refused(self):
        gw = gateway()
        gw.authenticator.revoke_key("k1")
        self.assertEqual(gw.invoke(assertion(), req(), now=1)["error"]["code"], "INV31-E-AUTHN")

    def test_short_keys_rejected(self):
        with self.assertRaises(ValueError):
            boundary.HmacAuthenticator({"k": b"short"})

    def test_security_rejections_are_audited(self):
        gw = gateway()
        gw.invoke(assertion(key=OTHER_KEY), req(), now=1)
        self.assertEqual(gw.audit.events[-1]["action"], "security.reject")
        self.assertTrue(gw.audit.verify())


class AuthorizationTest(unittest.TestCase):  # C024 C042 C050(escalation)
    def test_cross_tenant_invoke_denied(self):
        r = gateway().invoke(assertion(tenant="t1", caps=["invoke:t2"]), req(tenant="t2"), now=1)
        self.assertEqual(r["error"]["code"], "INV31-E-AUTHZ")

    def test_missing_capability_denied(self):
        r = gateway().invoke(assertion(caps=[]), req(), now=1)
        self.assertEqual(r["error"]["code"], "INV31-E-AUTHZ")

    def test_invoker_cannot_drain_or_explain(self):
        gw = gateway()
        self.assertEqual(gw.drain(assertion(), now=1)["error"]["code"], "INV31-E-AUTHZ")
        self.assertEqual(gw.explain(assertion(), tenant="t1", version="v1", now=1)["error"]["code"],
                         "INV31-E-AUTHZ")

    def test_service_cannot_emergency_disable(self):
        gw = gateway()
        r = gw.emergency_disable(assertion(tenant="ops", caps=["pool:drain"]), now=1, reason="x")
        self.assertEqual(r["error"]["code"], "INV31-E-AUTHZ")

    def test_no_ambient_authority_in_sources(self):  # C043: no fs/network/process imports
        banned = {"socket", "subprocess", "os", "shutil", "urllib", "http", "ctypes", "pickle"}
        for name in ("runtime", "boundary", "config", "errors", "adapters"):
            tree = ast.parse((PKG_DIR / f"{name}.py").read_text())
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    mods = [(node.module or "").split(".")[0]]
                self.assertFalse(banned & set(mods), f"{name}.py imports {banned & set(mods)}")


class ControlSemanticsTest(unittest.TestCase):  # C025 C053 C058
    def test_deadline_and_cancel_before_admission(self):
        gw = gateway()
        self.assertEqual(gw.invoke(assertion(), req(), now=5, deadline=5)["error"]["code"],
                         "INV31-E-DEADLINE")
        tok = boundary.CancelToken()
        tok.cancel()
        self.assertEqual(gw.invoke(assertion(), req(), now=5, cancel=tok)["error"]["code"],
                         "INV31-E-CANCELLED")
        self.assertEqual(gw.pool.invocations, 0)

    def test_idempotent_replay_does_not_execute_twice(self):  # duplicate execution guard
        gw = gateway()
        a = gw.invoke(assertion(), req(idempotency_key="k-1"), now=1)
        b = gw.invoke(assertion(), req(idempotency_key="k-1"), now=2)
        self.assertTrue(b["idempotent_replay"])
        self.assertEqual(a["result"], b["result"])
        self.assertEqual(gw.pool.invocations, 1)

    def test_idempotency_key_conflict(self):
        gw = gateway()
        gw.invoke(assertion(), req(idempotency_key="k-1"), now=1)
        r = gw.invoke(assertion(), req(version="v2", idempotency_key="k-1"), now=2)
        self.assertEqual(r["error"]["code"], "INV31-E-IDEMPOTENCY-CONFLICT")

    def test_idempotency_keys_are_tenant_scoped(self):
        gw = gateway()
        gw.invoke(assertion("t1"), req("t1", idempotency_key="same"), now=1)
        r = gw.invoke(assertion("t2"), req("t2", idempotency_key="same"), now=2)
        self.assertFalse(r["idempotent_replay"])
        self.assertEqual(r["result"]["tenant"], "t2")

    def test_bounded_retry_only_retries_retryable(self):
        calls = []
        outcomes = [{"ok": False, "error": {"retryable": True}}] * 2 + [{"ok": True}]
        r = boundary.bounded_retry(lambda: (calls.append(1), outcomes[len(calls) - 1])[1],
                                   attempts=5, sleep=lambda s: None)
        self.assertTrue(r["ok"])
        self.assertEqual(len(calls), 3)
        calls.clear()
        r = boundary.bounded_retry(lambda: (calls.append(1), {"ok": False,
                                   "error": {"retryable": False}})[1], sleep=lambda s: None)
        self.assertEqual(len(calls), 1)

    def test_retry_backoff_is_bounded_and_jittered(self):
        delays = []
        boundary.bounded_retry(lambda: {"ok": False, "error": {"retryable": True}}, attempts=6,
                               base_delay=0.05, max_delay=0.1, sleep=delays.append,
                               rng=random.Random(7))
        self.assertEqual(len(delays), 5)
        self.assertTrue(all(0 <= d <= 0.1 for d in delays))
        self.assertGreater(len(set(delays)), 1)


class ErrorsTest(unittest.TestCase):  # C026
    def test_runtime_exceptions_map_to_stable_codes(self):
        self.assertEqual(errors.to_error(runtime.PoolCapacityExceeded("x"))["code"],
                         "INV31-E-POOL-CAPACITY")
        self.assertTrue(errors.to_error(runtime.ConcurrencyExceeded("x"))["retryable"])
        self.assertEqual(errors.to_error(ValueError("x"))["code"], "INV31-E-INVALID-INPUT")

    def test_unexpected_errors_do_not_leak_text(self):
        e = errors.to_error(KeyError("secret-token-123"))
        self.assertEqual((e["code"], e["message"]), ("INV31-E-INTERNAL", "internal error"))

    def test_error_record_matches_schema_shape(self):
        schema = json.loads((PKG_DIR / "schemas/PK_INV31_ERROR_1.schema.json").read_text())
        e = errors.to_error(errors.QuotaExceeded("q", tenant="t", secret="nope"))
        self.assertEqual(set(e), set(schema["required"]))
        self.assertNotIn("secret", e["details"])
        self.assertIn(e["code"], schema["properties"]["code"]["enum"])
        self.assertEqual(sorted(schema["properties"]["code"]["enum"]), list(errors.CODES))


class VersioningTest(unittest.TestCase):  # C016 C027
    def test_unknown_schema_version_refused_with_supported_list(self):
        r = gateway().invoke(assertion(), {**req(), "schema": "PK_INVOKE_REQUEST/2"}, now=1)
        self.assertEqual(r["error"]["code"], "INV31-E-UNSUPPORTED-VERSION")
        self.assertEqual(r["error"]["details"]["supported"], ["PK_INVOKE_REQUEST/1"])

    def test_unknown_fields_refused_not_ignored(self):
        r = gateway().invoke(assertion(), req(priority="high"), now=1)
        self.assertEqual(r["error"]["code"], "INV31-E-UNSUPPORTED-VERSION")

    def test_request_schema_file_agrees(self):
        s = json.loads((PKG_DIR / "schemas/PK_INVOKE_REQUEST_1.schema.json").read_text())
        self.assertEqual(s["properties"]["schema"]["const"], boundary.REQUEST_SCHEMA)
        self.assertFalse(s["additionalProperties"])


class QuotaFairnessTest(unittest.TestCase):  # C017 C067
    def test_tenant_quota_limits_cold_growth_but_not_warm(self):
        gw = gateway(quotas={"t1": boundary.TenantQuota(1)})
        self.assertTrue(gw.invoke(assertion(), req(version="v1"), now=1)["ok"])
        self.assertTrue(gw.invoke(assertion(), req(version="v1"), now=2)["ok"])  # warm
        r = gw.invoke(assertion(), req(version="v2"), now=3)
        self.assertEqual(r["error"]["code"], "INV31-E-QUOTA")
        self.assertTrue(r["error"]["retryable"])

    def test_default_share_prevents_one_tenant_taking_the_pool(self):
        gw = gateway(max_tenant_share=0.5)
        oks = [gw.invoke(assertion(), req(version=f"v{i}"), now=1)["ok"] for i in range(8)]
        self.assertEqual(sum(oks), 4)
        self.assertTrue(gw.invoke(assertion("t2"), req("t2"), now=1)["ok"])


class DependencyTest(unittest.TestCase):  # C018 C048 C055 C056 C089 (local model)
    def test_critical_dependency_down_fails_closed(self):
        gw = gateway()
        gw.set_dependency("PLN-04 Execution plane", False)
        r = gw.invoke(assertion(), req(), now=1)
        self.assertEqual(r["error"]["code"], "INV31-E-DEPENDENCY-UNAVAILABLE")
        self.assertFalse(gw.health(1)["ready"])

    def test_noncritical_down_degrades_but_serves(self):
        gw = gateway()
        gw.set_dependency("GAP-09 Unified observability", False)
        r = gw.invoke(assertion(), req(), now=1)
        self.assertTrue(r["ok"])
        self.assertEqual(r["degraded"], ["GAP-09 Unified observability"])
        self.assertTrue(gw.health(1)["ready"])

    def test_telemetry_sink_partition_then_reconnect_loses_nothing(self):
        gw, sink = gateway(), adapters.ReferenceObservabilitySink(up=False)
        for t in range(5):
            gw.invoke(assertion(now=t), req(), now=t)
        self.assertEqual(adapters.flush_telemetry(gw, sink), 0)
        self.assertEqual(len(gw.telemetry.export_buffer), 5)
        sink.up = True
        self.assertEqual(adapters.flush_telemetry(gw, sink), 5)
        self.assertEqual(len(sink.received), 5)

    def test_telemetry_overflow_is_counted_not_silent(self):
        tel = boundary.Telemetry()
        for i in range(boundary.MAX_LOG_RECORDS + 3):
            tel.log("x", tenant=None, outcome="ok", trace_id="a", span_id="b")
        self.assertEqual(tel.counters["telemetry_dropped"], 3)


class AdjacentContractTest(unittest.TestCase):  # C030 C082 C083 - contract level with doubles
    def test_reference_doubles_satisfy_protocols(self):
        self.assertIsInstance(adapters.ReferenceExecutionPlane(), adapters.ExecutionPlane)
        self.assertIsInstance(adapters.ReferenceSnapshotService(), adapters.SnapshotService)
        self.assertIsInstance(adapters.ReferenceElasticityPlane(), adapters.ElasticityPlane)
        self.assertIsInstance(adapters.ReferenceObservabilitySink(), adapters.ObservabilitySink)

    def test_sync_and_saturation_publication(self):
        gw = gateway()
        exe = adapters.ReferenceExecutionPlane(up=False)
        adapters.sync_dependencies(gw, execution=exe, snapshots=adapters.ReferenceSnapshotService(),
                                   observability=adapters.ReferenceObservabilitySink())
        self.assertFalse(gw.health(0)["ready"])
        exe.up = True
        adapters.sync_dependencies(gw, execution=exe, snapshots=adapters.ReferenceSnapshotService(),
                                   observability=adapters.ReferenceObservabilitySink())
        gw.invoke(assertion(), req(), now=1)
        el = adapters.ReferenceElasticityPlane()
        adapters.publish_saturation(gw, el, now=1)
        self.assertEqual(el.observations[0]["instances"], 1)


class ConfigTest(unittest.TestCase):  # C033 C036 C037 C038 C040
    def doc(self, v=1, **pool):
        p = {"concurrency_limit": 2, "max_age": 50, "max_instances": 4, **pool}
        return {"schema": config.CONFIG_SCHEMA, "config_version": v, "author": "alice",
                "environment": "test", "pool": p, "tenant_quotas": {"t1": 2},
                "max_tenant_share": 0.5}

    def test_example_config_validates(self):
        for f in sorted((PKG_DIR / "config").glob("*.json")):
            config.load_file(str(f))

    def test_apply_records_provenance(self):
        gw = gateway()
        cm = config.ConfigManager(gw)
        r = cm.apply(assertion(**OPERATOR), self.doc(), now=3)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["provenance"]["author"], "alice")
        self.assertEqual(r["provenance"]["activated_at"], 3)
        self.assertEqual(r["provenance"]["digest"], config.digest(config.validate(self.doc())))
        self.assertEqual(gw.pool.max_instances, 4)
        self.assertEqual(gw.audit.events[-1]["action"], "config.activate")

    def test_invalid_config_changes_nothing(self):
        gw = gateway()
        before = gw.pool
        bad = self.doc(max_instances=0)
        r = config.ConfigManager(gw).apply(assertion(**OPERATOR), bad, now=1)
        self.assertEqual(r["error"]["code"], "INV31-E-CONFIG-REJECTED")
        self.assertIs(gw.pool, before)

    def test_unknown_fields_and_services_refused(self):
        gw = gateway()
        cm = config.ConfigManager(gw)
        self.assertFalse(cm.apply(assertion(**OPERATOR), {**self.doc(), "x": 1}, now=1)["ok"])
        svc = dict(OPERATOR, kind="service")
        self.assertEqual(cm.apply(assertion(**svc), self.doc(), now=1)["error"]["code"], "INV31-E-AUTHZ")

    def test_version_must_increase(self):
        cm = config.ConfigManager(gateway())
        cm.apply(assertion(**OPERATOR), self.doc(2), now=1)
        self.assertFalse(cm.apply(assertion(**OPERATOR), self.doc(2), now=2)["ok"])

    def test_automatic_rollback_on_failed_post_check(self):
        gw = gateway()
        before = gw.pool
        cm = config.ConfigManager(gw, post_apply_check=lambda g: False)
        r = cm.apply(assertion(**OPERATOR), self.doc(), now=1)
        self.assertFalse(r["ok"])
        self.assertIs(gw.pool, before)
        self.assertEqual(gw.audit.events[-1]["action"], "config.auto_rollback")

    def test_operator_rollback(self):
        gw = gateway()
        cm = config.ConfigManager(gw)
        cm.apply(assertion(**OPERATOR), self.doc(1, max_instances=4), now=1)
        cm.apply(assertion(**OPERATOR), self.doc(2, max_instances=6), now=2)
        self.assertEqual(gw.pool.max_instances, 6)
        self.assertTrue(cm.rollback(assertion(**OPERATOR), now=3)["ok"])
        self.assertEqual(gw.pool.max_instances, 4)

    def test_no_reuse_across_config_generations(self):
        gw = gateway()
        first = gw.invoke(assertion(), req(), now=1)["result"]["instance"]
        config.ConfigManager(gw).apply(assertion(**OPERATOR), self.doc(), now=2)
        r = gw.invoke(assertion(), req(), now=3)["result"]
        self.assertTrue(r["cold"])
        self.assertTrue(first)


class ObservabilityTest(unittest.TestCase):  # C071 C072 C073 C074 C075 C077 C049
    def test_health_is_tenant_free(self):
        gw = gateway()
        gw.invoke(assertion("secret-tenant"), req("secret-tenant"), now=1)
        self.assertNotIn("secret-tenant", json.dumps(gw.health(1)))
        self.assertEqual(gw.health(1)["version"], pkg.__version__)

    def test_logs_are_structured_and_pseudonymous(self):
        gw = gateway()
        gw.invoke(assertion("acme"), req("acme", workload="resize"), now=1)
        rec = gw.telemetry.logs[-1]
        for k in ("component", "node", "operation", "tenant", "trace_id", "span_id", "workload"):
            self.assertIn(k, rec)
        self.assertNotIn("acme", json.dumps(rec))
        self.assertEqual(rec["tenant"], boundary.redact_tenant("acme"))

    def test_trace_context_propagates(self):
        tp = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        r = gateway().invoke(assertion(), req(), now=1, traceparent=tp)
        self.assertEqual((r["trace_id"], r["parent_span"]), ("a" * 32, "b" * 16))
        r = gateway().invoke(assertion(), req(), now=1, traceparent="garbage")
        self.assertEqual(len(r["trace_id"]), 32)
        self.assertIsNone(r["parent_span"])

    def test_metrics_counters_and_latency(self):
        gw = gateway()
        for t in range(3):
            gw.invoke(assertion(now=t), req(), now=t)
        gw.invoke(assertion(caps=[]), req(), now=4)
        m = gw.metrics()
        self.assertEqual(m["counters"]["invocations.cold"], 1)
        self.assertEqual(m["counters"]["invocations.warm"], 2)
        self.assertEqual(m["counters"]["errors.INV31-E-AUTHZ"], 1)
        self.assertIsNotNone(m["latency_ns"]["p99"])

    def test_explain_view_is_tenant_scoped(self):
        gw = gateway()
        gw.invoke(assertion("t1"), req("t1"), now=1)
        gw.invoke(assertion("t2"), req("t2"), now=1)
        e = gw.explain(assertion(**OPERATOR), tenant="t1", version="v2", now=2)
        self.assertEqual(e["predicted"], "cold")
        self.assertEqual(len(e["candidates"]), 1)
        self.assertEqual(e["candidates"][0]["rejected_because"], ["version_mismatch"])

    def test_audit_chain_detects_tampering(self):
        gw = gateway()
        gw.drain(assertion(**OPERATOR), now=1)
        gw.emergency_disable(assertion(**OPERATOR), now=2, reason="incident-1")
        self.assertTrue(gw.audit.verify())
        gw.audit.events[0]["destroyed"] = 99
        self.assertFalse(gw.audit.verify())

    def test_emergency_disable_and_enable(self):  # C092
        gw = gateway()
        gw.emergency_disable(assertion(**OPERATOR), now=1, reason="incident-1")
        self.assertEqual(gw.invoke(assertion(), req(), now=2)["error"]["code"], "INV31-E-DRAINING")
        gw.enable(assertion(**OPERATOR), now=3)
        self.assertTrue(gw.invoke(assertion(), req(), now=4)["ok"])


class PkCoreCompatTest(unittest.TestCase):  # A01
    def run_probe(self, files: dict[str, str]) -> dict:
        with tempfile.TemporaryDirectory() as d:
            for rel, src in files.items():
                p = pathlib.Path(d, rel)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(src)
            code = (f"import json,sys; sys.path[:0]=[{d!r},{str(PKG_DIR.parent)!r}];"
                    f"import {PKG} as p; print(json.dumps([p.PK_CORE_STATUS, p.COMPONENT is None]))")
            out = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True,
                                 check=True)
            return json.loads(out.stdout)

    def test_absent_pk_core_is_a_documented_failure(self):
        self.assertIn(pkcompat.PK_CORE_STATUS["available"], (True, False))
        if not pkcompat.PK_CORE_STATUS["available"]:
            with self.assertRaises(errors.FrameworkUnavailable) as cm:
                pkg.build_contract()
            self.assertEqual(errors.to_error(cm.exception)["code"], "INV31-E-PKCORE-UNAVAILABLE")

    def test_incompatible_pk_core_rejected(self):
        status, component_none = self.run_probe({"pk_core/__init__.py": "__version__='0.0-bad'\n"})
        self.assertTrue(status["available"])
        self.assertFalse(status["compatible"])
        self.assertTrue(component_none)
        self.assertIn("pk_core.contract", status["missing"])

    def test_pin_is_declared_unset_not_guessed(self):
        self.assertIsNone(pkcompat.PINNED_VERSION)
        self.assertIsNone(pkcompat.PINNED_DIGEST)


class FuzzAndPropertyTest(unittest.TestCase):  # C085 C050 C087 A10
    def test_randomised_operation_sequences_preserve_invariants(self):
        rng = random.Random(0xC0FFEE)
        for trial in range(60):
            pool = runtime.FunctionPool(concurrency_limit=rng.randint(1, 3),
                                        max_age=rng.randint(1, 20), max_instances=rng.randint(1, 6))
            now = 0
            for _ in range(200):
                now = max(0, now + rng.randint(-3, 6))
                t, v = f"t{rng.randint(0, 3)}", f"v{rng.randint(0, 2)}"
                op = rng.random()
                try:
                    if op < 0.8:
                        r = pool.invoke(tenant=t, version=v, now=now)
                        inst = next(i for i in pool.instances if i.name == r["instance"])
                        self.assertEqual((inst.tenant, inst.version), (t, v))
                        self.assertTrue(r["scratch_cleared"])
                    elif op < 0.9:
                        pool.destroy_idle(tenant=t)
                    else:
                        pool.evict_aged(now)
                except runtime.PoolCapacityExceeded:
                    pass
                self.assertLessEqual(len(pool.instances), pool.max_instances)
                for i in pool.instances:
                    self.assertEqual(i.in_flight, 0)
                    self.assertEqual(i.scratch, {})
                    self.assertFalse(i.destroyed)

    def test_hostile_assertions_never_raise(self):
        rng = random.Random(1234)
        gw = gateway()
        junk = [None, 1, "x", [], {}, {"key_id": "k1"}, {"key_id": ["k1"]},
                {"key_id": "k1", "sig": "0" * 64}, {"key_id": "k1" * 500}]
        for _ in range(500):
            a = rng.choice(junk)
            if isinstance(a, dict) and rng.random() < 0.5:
                a = {**a, rng.choice(["subject", "tenant", "nonce"]): rng.choice(["\x00", "a" * 999, 3])}
            r = gw.invoke(a, req(), now=rng.randint(0, 10))
            self.assertFalse(r["ok"])
            self.assertIn(r["error"]["code"], errors.CODES)
        self.assertEqual(gw.pool.invocations, 0)

    def test_hostile_requests_never_raise(self):
        rng = random.Random(99)
        gw = gateway()
        values = [None, 0, True, "", " ", "\n", "a" * 300, "é", [], {}, "PK_INVOKE_REQUEST/1"]
        for _ in range(500):
            r = {k: rng.choice(values) for k in rng.sample(
                ["schema", "tenant", "version", "idempotency_key", "workload", "zz"], rng.randint(0, 6))}
            if rng.random() < 0.5:
                r["schema"] = boundary.REQUEST_SCHEMA
            out = gw.invoke(assertion(tenant="t1"), r, now=1)
            if not out["ok"]:
                self.assertIn(out["error"]["code"], errors.CODES)

    def test_config_fuzz_rejects_or_accepts_cleanly(self):
        rng = random.Random(5)
        vals = [None, -1, 0, 1, 2**40, 1.5, "1", True, [], {}]
        for _ in range(400):
            doc = {"schema": config.CONFIG_SCHEMA, "config_version": rng.choice(vals + [1]),
                   "author": rng.choice(["a", "", None]), "environment": rng.choice(["test", "x"]),
                   "pool": {k: rng.choice(vals + [3]) for k in
                            ("concurrency_limit", "max_age", "max_instances")}}
            try:
                config.validate(doc)
            except errors.ConfigurationRejected:
                pass


class ConcurrencyStressTest(unittest.TestCase):  # C058 C063 A10
    def test_threads_never_share_instances_across_tenants(self):
        gw = gateway(pool=runtime.FunctionPool(max_instances=64), max_tenant_share=1.0)
        seen: dict[str, set] = {}
        lock = threading.Lock()
        failures = []

        def worker(tenant):
            for t in range(200):
                r = gw.invoke(assertion(tenant, now=0, life=500), req(tenant, version=f"v{t % 3}"), now=t)
                if not r["ok"]:
                    failures.append(r["error"]["code"])
                    continue
                with lock:
                    seen.setdefault(r["result"]["instance"], set()).add(tenant)

        threads = [threading.Thread(target=worker, args=(f"t{i}",)) for i in range(8)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        self.assertEqual(failures, [])
        self.assertTrue(all(len(ts) == 1 for ts in seen.values()))
        self.assertEqual(gw.pool.invocations, 1600)


@unittest.skipUnless((PKG_DIR / "pyproject.toml").exists(), "source-tree checks; not in an installed wheel")
class RepositoryIntegrityTest(unittest.TestCase):  # A02 A04 A08 A09 C009 C010
    def test_master_md_absence_is_recorded_not_fabricated(self):
        prov = json.loads((PKG_DIR / "evidence/source_hashes.json").read_text())
        self.assertEqual(prov["MASTER.md"]["status"], "ABSENT")
        self.assertFalse((PKG_DIR / "MASTER.md").exists())

    def test_pyproject_declares_no_runtime_dependencies(self):
        text = (PKG_DIR / "pyproject.toml").read_text()
        self.assertIn('version = "4.3.0"', text)
        self.assertIn("dependencies = []", text)

    def test_owner_and_license_are_unassigned_not_invented(self):
        own = (PKG_DIR / "OWNERSHIP.md").read_text()
        self.assertIn("UNASSIGNED", own)
        self.assertFalse((PKG_DIR / "LICENSE").exists())
        adr = (PKG_DIR / "docs/ADR-001-function-execution.md").read_text()
        self.assertIn("Status: PROPOSED", adr)

    def test_contract_identity_matches_package(self):
        src = (PKG_DIR / "contract.py").read_text()
        self.assertIn(f'ELEMENT_ID = "{pkg.ELEMENT_ID}"', src)
        self.assertIn(f'ELEMENT_NAME = "{pkg.ELEMENT_NAME}"', src)

    def test_remediation_status_covers_all_85(self):
        s = json.loads((PKG_DIR / "REMEDIATION_STATUS.json").read_text())
        self.assertEqual(len(s["items"]), 85)
        self.assertEqual(s["production_gate"], "NO_GO")
        self.assertFalse(any(i["status"] == "DONE" for i in s["items"] if i["blockers"]))


class FixtureCorpusTest(unittest.TestCase):  # C029 C082
    fx = json.loads((PKG_DIR / "fixtures/conformance_fixtures.json").read_text())

    def test_valid_requests_accepted(self):
        for r in self.fx["request_valid"]:
            out = gateway().invoke(assertion(r["tenant"]), r, now=1)
            self.assertTrue(out["ok"], (r, out))

    def test_invalid_requests_refused_with_codes(self):
        for r in self.fx["request_invalid"]:
            out = gateway().invoke(assertion("t1"), r, now=1)
            self.assertFalse(out["ok"], r)
            self.assertIn(out["error"]["code"], errors.CODES)

    def test_invalid_configs_refused(self):
        for d in self.fx["config_invalid"]:
            with self.assertRaises(errors.ConfigurationRejected):
                config.validate(d)


if __name__ == "__main__":
    unittest.main()
