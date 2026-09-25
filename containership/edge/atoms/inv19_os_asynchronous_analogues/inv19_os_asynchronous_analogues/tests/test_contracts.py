"""MC-11 schemas, MC-12 errors, MC-13 policy, MC-14 config, MC-21 resources."""
import errno
import json
import pathlib
import threading
import unittest

from _helpers import ROOT  # noqa: F401

from inv19_os_asynchronous_analogues.hostio import config as cfgmod
from inv19_os_asynchronous_analogues.hostio import errors, policy, resources, schema

PKG = pathlib.Path(__file__).resolve().parents[1]


class SchemaTest(unittest.TestCase):
    def test_every_fixture_validates(self):
        for f in sorted((PKG / "schemas/fixtures").glob("*.json")):
            if f.name.startswith("errno_golden"):
                continue
            d = json.loads(f.read_text())
            self.assertEqual(schema.validate(d["doc"], schema.load(d["schema_file"])), [], f.name)

    def test_every_malformed_fixture_rejected(self):
        files = sorted((PKG / "schemas/fixtures/malformed").glob("*.json"))
        self.assertGreaterEqual(len(files), 4)
        for f in files:
            d = json.loads(f.read_text())
            self.assertNotEqual(schema.validate(d["doc"], schema.load(d["schema_file"])), [], f.name)

    def test_round_trip(self):
        d = json.loads((PKG / "schemas/fixtures/reap_error.json").read_text())["doc"]
        self.assertEqual(schema.from_wire(schema.to_wire(d), "PK_ASYNC_REAP_1"), d)

    def test_live_error_objects_conform(self):
        e = errors.translate("io_uring", -errno.ECONNRESET).to_dict()
        self.assertEqual(schema.validate(e, schema.load("PK_ASYNC_ERROR_1")), [])

    def test_no_breaking_change_against_frozen_v1(self):
        self.assertEqual(schema.check_all_compat(), {k: [] for k in schema.check_all_compat()})

    def test_breaking_change_is_detected(self):
        old = schema.load("PK_ASYNC_REAP_1", frozen=True)
        new = json.loads(json.dumps(old))
        new["properties"]["tag"]["enum"].remove("retry")
        new["required"].append("new_field")
        del new["properties"]["value"]
        br = schema.breaking_changes(old, new)
        self.assertTrue(any("enum members removed" in b for b in br))
        self.assertTrue(any("new required" in b for b in br))
        self.assertTrue(any("property removed" in b for b in br))

    def test_forward_compat_unknown_field_accepted_unknown_enum_rejected(self):
        d = {"schema": "PK_ASYNC_REAP/1", "kind": "completion", "op_id": 1, "tag": "value", "future": 1}
        self.assertEqual(schema.validate(d, schema.load("PK_ASYNC_REAP_1")), [])
        d["tag"] = "teleported"
        self.assertTrue(schema.validate(d, schema.load("PK_ASYNC_REAP_1")))

    def test_negotiation(self):
        self.assertEqual(schema.negotiate("PK_ASYNC_REAP", [(1, 3), (2, 0)]), (1, 0))
        self.assertIsNone(schema.negotiate("PK_ASYNC_REAP", [(2, 0)]))

    def test_oversized_payload_rejected(self):
        with self.assertRaises(ValueError):
            schema.from_wire(b"{" + b" " * (2 << 20) + b"}", "PK_ASYNC_REAP_1")


class ErrorTaxonomyTest(unittest.TestCase):
    def test_linux_golden_table(self):
        g = json.loads((PKG / "schemas/fixtures/errno_golden_linux.json").read_text())["table"]
        import platform
        if platform.system() != "Linux":
            self.skipTest("BLOCKED: Linux golden table")
        for k, v in g.items():
            self.assertEqual(errors.translate("epoll", int(k)).code, v)

    def test_iouring_negative_results(self):
        e = errors.translate("io_uring", -errno.ECANCELED)
        self.assertEqual((e.code, e.cancelled, e.native_code), ("CANCELLED", True, errno.ECANCELED))
        self.assertEqual(errors.translate("io_uring", -errno.EAGAIN).retryable, True)

    def test_windows_tables(self):
        self.assertEqual(errors.translate("iocp", 10054, "winsock").code, "CONNECTION_RESET")
        self.assertEqual(errors.translate("iocp", 995).code, "CANCELLED")
        self.assertEqual(errors.translate("iocp", 0xC0000120, "ntstatus").code, "CANCELLED")

    def test_same_condition_equivalence_across_platforms(self):
        linux = errors.translate("epoll", errno.ECONNRESET)
        win = errors.translate("iocp", 10054, "winsock")
        self.assertEqual((linux.code, linux.retryable, linux.transient), (win.code, win.retryable, win.transient))

    def test_unknown_is_visible_counted_and_not_success(self):
        before = errors.untranslatable_errors.value
        for bad in (999999, "EIO", None, 3.5, True, 2**70):
            e = errors.translate("epoll", bad)
            self.assertEqual(e.code, "UNKNOWN_HOST_ERROR")
            self.assertFalse(e.retryable)
        self.assertEqual(errors.untranslatable_errors.value, before + 6)

    def test_message_is_not_host_strerror(self):
        e = errors.translate("epoll", errno.ECONNRESET)
        import os
        self.assertNotEqual(e.message, os.strerror(errno.ECONNRESET))


class PolicyTest(unittest.TestCase):
    def test_deadlines(self):
        for bad in (0, -1, float("nan"), True, 10**9, "5"):
            with self.assertRaises(policy.InvalidDeadline):
                policy.deadline_after(bad)
        self.assertIsNone(policy.deadline_after(None))
        d = policy.deadline_after(5, clock=lambda: 100.0)
        self.assertEqual(d, 105.0)
        self.assertTrue(policy.expired(d, clock=lambda: 105.0))

    def test_retry_bounded_and_idempotency_required(self):
        calls = []
        rp = policy.RetryPolicy(max_attempts=3, budget_s=100, base_s=0.001, cap_s=0.01)
        def f():
            calls.append(1)
            raise policy.RetryableFailure(errors.translate("epoll", errno.EAGAIN))
        with self.assertRaises(policy.RetryableFailure):
            rp.run("nop", f, sleep=lambda s: None)
        self.assertEqual(len(calls), 4)
        with self.assertRaises(policy.NotIdempotent):
            rp.run("write", f, sleep=lambda s: None)
        calls.clear()
        def perm():
            calls.append(1)
            raise policy.RetryableFailure(errors.translate("epoll", errno.ECONNRESET))
        with self.assertRaises(policy.RetryableFailure):
            rp.run("nop", perm, sleep=lambda s: None)
        self.assertEqual(len(calls), 1)  # non-retryable never retried

    def test_backoff_capped_no_overflow_with_jitter(self):
        rp = policy.RetryPolicy(base_s=0.01, cap_s=0.5, jitter=0.5)
        vals = [rp.backoff(a) for a in (0, 1, 5, 1000, 10**9)]
        self.assertTrue(all(0 < v <= 0.5 for v in vals))

    def test_retry_budget(self):
        t = [0.0]
        rp = policy.RetryPolicy(max_attempts=32, budget_s=0.05, base_s=0.02, cap_s=0.02, jitter=0)
        n = []
        def f():
            n.append(1)
            raise policy.RetryableFailure(errors.translate("epoll", errno.EAGAIN))
        with self.assertRaises(policy.RetryableFailure):
            rp.run("nop", f, sleep=lambda s: t.__setitem__(0, t[0] + s), clock=lambda: t[0])
        self.assertLessEqual(len(n), 3)

    def test_admission_and_tenant_limit(self):
        a = policy.Admission(4, 4, 4, per_tenant_inflight=2)
        a.admit("t1"); a.admit("t1")
        with self.assertRaises(policy.Overloaded) as cm:
            a.admit("t1")
        self.assertEqual(cm.exception.reason, "OVERLOAD_TENANT")
        a.admit("t2"); a.admit("t2")
        with self.assertRaises(policy.Overloaded) as cm:
            a.admit("t3")
        self.assertEqual(cm.exception.reason, "OVERLOAD_INFLIGHT")
        a.done("t1")
        with self.assertRaises(RuntimeError):
            a.done("t9")

    def test_circuit_breaker_recovers_via_half_open(self):
        t = [0.0]
        cb = policy.CircuitBreaker(3, 1.0, clock=lambda: t[0])
        for _ in range(3):
            cb.failure()
        self.assertFalse(cb.allow())
        t[0] = 1.5
        self.assertTrue(cb.allow())
        self.assertEqual(cb.state.value, "half_open")
        cb.failure()
        self.assertEqual(cb.state.value, "open")
        t[0] = 3.0
        cb.allow(); cb.success()
        self.assertEqual(cb.state.value, "closed")
        self.assertGreaterEqual(len(cb.transitions), 4)


class ConfigTest(unittest.TestCase):
    def test_defaults_valid_and_digest_stable(self):
        s = cfgmod.ConfigStore()
        self.assertEqual(s.active.digest, cfgmod.digest(cfgmod.defaults()))
        self.assertEqual(s.active.version, 1)

    def test_precedence(self):
        s = cfgmod.ConfigStore()
        c = s.activate([("site", {"retry.max_attempts": 3}),
                        ("env", cfgmod.env_layer({"INV19_RETRY.MAX_ATTEMPTS": "4"})),
                        ("tenant", {"retry.max_attempts": 6}),
                        ("cli", {"retry.max_attempts": 7})], actor="t")
        self.assertEqual(c["retry.max_attempts"], 7)
        self.assertEqual(c.source, ("compiled-defaults", "site", "env", "tenant", "cli"))

    def test_invalid_cannot_partially_activate(self):
        s = cfgmod.ConfigStore()
        before = s.active
        for bad in ({"ring.sq_entries": 0}, {"nope": 1}, {"backends.disabled": ["portable"]},
                    {"security.key_ref": "AAAAsecretbytes"}, {"auth.password": "x"},
                    {"quota.per_workload_descriptors": 999999}, {"retry.max_attempts": "many"},
                    {"timeout.default_s": float("nan")}):
            with self.assertRaises(cfgmod.ConfigError):
                s.activate([("cli", bad)], actor="t")
            self.assertIs(s.active, before)

    def test_failed_activation_hook_rolls_back_and_operator_rollback(self):
        s = cfgmod.ConfigStore()
        v1 = s.active
        def boom(c):
            raise RuntimeError("apply failed")
        with self.assertRaises(cfgmod.ConfigError):
            s.activate([("cli", {"retry.max_attempts": 2})], actor="t", on_activate=boom)
        self.assertIs(s.active, v1)
        v2 = s.activate([("cli", {"retry.max_attempts": 2})], actor="ops")
        self.assertEqual(s.rollback("ops").digest, v1.digest)
        self.assertNotEqual(v1.digest, v2.digest)

    def test_restart_required_classification(self):
        s = cfgmod.ConfigStore()
        with self.assertRaises(cfgmod.ConfigError):
            s.activate([("cli", {"ring.sq_entries": 128, "ring.cq_entries": 256})], actor="t",
                       allow_restart_fields=False)
        s.activate([("cli", {"retry.max_attempts": 1})], actor="t", allow_restart_fields=False)

    def test_provenance_has_no_secrets(self):
        s = cfgmod.ConfigStore()
        p = json.dumps(s.active.provenance())
        self.assertIn("digest", p)
        self.assertNotIn("password", p)

    def test_concurrent_activation_is_atomic(self):
        s = cfgmod.ConfigStore()
        seen = set()
        def w(i):
            c = s.activate([("cli", {"retry.max_attempts": i % 30})], actor="t")
            seen.add(c.version)
        ts = [threading.Thread(target=w, args=(i,)) for i in range(20)]
        for t in ts: t.start()
        for t in ts: t.join()
        self.assertEqual(s.active.values["retry.max_attempts"] in range(30), True)


class ResourceTest(unittest.TestCase):
    def acct(self):
        return resources.Accountant({"inflight_ops": resources.Limits(10, 6, 3, per_backend=10, admin_reserve=2)})

    def test_scopes_and_reserve(self):
        a = self.acct()
        rs = [a.reserve("inflight_ops", 1, tenant="t", workload="w") for _ in range(3)]
        with self.assertRaises(resources.QuotaExceeded) as cm:
            a.reserve("inflight_ops", 1, tenant="t", workload="w")
        self.assertEqual(cm.exception.scope, "workload:w")
        rs += [a.reserve("inflight_ops", 1, tenant="t", workload="w2") for _ in range(3)]
        with self.assertRaises(resources.QuotaExceeded) as cm:
            a.reserve("inflight_ops", 1, tenant="t", workload="w3")
        self.assertEqual(cm.exception.scope, "tenant:t")
        rs += [a.reserve("inflight_ops", 1, tenant="u", workload="x") for _ in range(2)]
        with self.assertRaises(resources.QuotaExceeded):  # global minus admin reserve = 8
            a.reserve("inflight_ops", 1, tenant="v", workload="y")
        rs.append(a.reserve("inflight_ops", 1, tenant="v", workload="y", admin=True))
        for r in rs:
            a.release(r)
        self.assertTrue(a.at_baseline())

    def test_per_backend_scope(self):
        a = resources.Accountant({"inflight_ops": resources.Limits(10, 10, 10, per_backend=2)})
        a.reserve("inflight_ops", 2, tenant="t", workload="w", backend="epoll")
        with self.assertRaises(resources.QuotaExceeded) as cm:
            a.reserve("inflight_ops", 1, tenant="t", workload="w", backend="epoll")
        self.assertEqual(cm.exception.scope, "backend:epoll")
        a.reserve("inflight_ops", 1, tenant="t", workload="w", backend="io_uring")

    def test_double_release_and_rollback(self):
        a = self.acct()
        r = a.reserve("inflight_ops", 1, tenant="t", workload="w")
        a.release(r)
        with self.assertRaises(resources.AccountingError):
            a.release(r)
        with self.assertRaises(ZeroDivisionError):
            with a.reserved("inflight_ops", 1, tenant="t", workload="w"):
                1 / 0
        self.assertTrue(a.at_baseline())

    def test_invalid_amounts(self):
        a = self.acct()
        for bad in (0, -1, True, 2**63, 1.0):
            with self.assertRaises(resources.AccountingError):
                a.reserve("inflight_ops", bad, tenant="t", workload="w")
        with self.assertRaises(resources.AccountingError):
            a.reserve("unknown", 1, tenant="t", workload="w")

    def test_concurrent_accounting(self):
        a = resources.Accountant({"inflight_ops": resources.Limits(1000, 1000, 1000)})
        def w():
            for _ in range(200):
                a.release(a.reserve("inflight_ops", 1, tenant="t", workload="w"))
        ts = [threading.Thread(target=w) for _ in range(8)]
        for t in ts: t.start()
        for t in ts: t.join()
        self.assertTrue(a.at_baseline())
        self.assertEqual(a.leaked(), [])

    def test_all_resources_have_limits_by_default(self):
        self.assertEqual(set(resources.default_limits()), set(resources.RESOURCES))


if __name__ == "__main__":
    unittest.main()
