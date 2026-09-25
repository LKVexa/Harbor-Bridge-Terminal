"""Focused security tests for the INV-55 executable reference model.

The repository depends on the external ``pk_core`` package.  This test installs
minimal import-only stubs when that package is unavailable so the reference
broker can still be security-tested in isolation; it does not emulate pk_core
assessment behavior.
"""
from __future__ import annotations

import importlib
import pathlib
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "inv55_secrets_integration"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_import_stubs() -> None:
    try:
        import pk_core  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    pkg = types.ModuleType("pk_core")
    pkg.__path__ = []
    sys.modules["pk_core"] = pkg

    checklist = types.ModuleType("pk_core.checklist")
    checklist.ChecklistItem = object
    checklist.Finding = object
    sys.modules["pk_core.checklist"] = checklist

    component = types.ModuleType("pk_core.component")
    component.Component = type("Component", (), {})
    sys.modules["pk_core.component"] = component

    contract = types.ModuleType("pk_core.contract")

    class _Data:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    contract.Contract = _Data
    contract.Dependency = _Data
    contract.Slo = _Data
    sys.modules["pk_core.contract"] = contract


_install_import_stubs()
m = importlib.import_module(f"{PKG_DIR.name}.component")


class SecretPrimitiveTests(unittest.TestCase):
    def test_secret_container_is_not_a_string_and_redacts(self):
        secret = m._SecretValue("TOPSECRET")
        self.assertNotIsInstance(secret, str)
        self.assertEqual(str(secret), "Secret(***)")
        self.assertEqual(repr(secret), "Secret(***)")
        self.assertEqual(f"{secret:>14}", "   Secret(***)")
        for method in ("encode", "lower", "upper", "replace", "split"):
            self.assertFalse(hasattr(secret, method), method)

    def test_secret_serialization_is_blocked(self):
        import pickle

        secret = m._SecretValue("TOPSECRET")
        with self.assertRaises(TypeError):
            pickle.dumps(secret)

    def test_resolution_scope_and_diagnostics_do_not_leak(self):
        t = [0.0]
        b = m.SecretBroker(lease_ttl=60, clock=lambda: t[0])
        b.put("db-password", "hunter2-prod", ["orders"])
        lease = b.resolve("orders", "db-password")
        with self.assertRaises(m.SecretDenied):
            b.resolve("marketing", "db-password")
        self.assertEqual(b.use(lease, "orders", "db-password"), "hunter2-prod")
        diagnostics = repr(lease) + repr(b) + " ".join(map(repr, b.audit))
        self.assertNotIn("hunter2", diagnostics)

    def test_lease_is_bound_to_broker_application_and_name(self):
        t = [0.0]
        a = m.SecretBroker(clock=lambda: t[0])
        b = m.SecretBroker(clock=lambda: t[0])
        a.put("token", "value", ["svc"])
        b.put("token", "other", ["svc"])
        lease = a.resolve("svc", "token")
        with self.assertRaises(m.LeaseContextMismatch):
            b.use(lease, "svc", "token")
        with self.assertRaises(m.LeaseContextMismatch):
            a.use(lease, "other", "token")
        with self.assertRaises(m.LeaseContextMismatch):
            a.use(lease, "svc", "other")


    def test_missing_and_unauthorized_are_indistinguishable_to_caller(self):
        b = m.SecretBroker(clock=lambda: 0.0)
        b.put("exists", "value", ["orders"])
        messages = []
        for name in ("exists", "missing"):
            with self.assertRaises(m.SecretDenied) as ctx:
                b.resolve("marketing", name)
            messages.append(str(ctx.exception))
        self.assertEqual(messages[0], messages[1])

    def test_audit_and_reference_resource_limits_are_bounded(self):
        b = m.SecretBroker(
            clock=lambda: 0.0,
            audit_limit=2,
            max_secret_chars=4,
            max_apps_per_secret=1,
            max_secrets=1,
            max_versions_per_secret=2,
        )
        with self.assertRaises(ValueError):
            b.put("token", "12345", ["svc"])
        with self.assertRaises(ValueError):
            b.put("token", "1234", ["svc", "other"])
        b.put("token", "v1", ["svc"])
        b.put("token", "v2", ["svc"])
        with self.assertRaises(OverflowError):
            b.put("token", "v3", ["svc"])
        with self.assertRaises(OverflowError):
            b.put("other", "v", ["svc"])
        lease = b.resolve("svc", "token")
        b.use(lease, "svc", "token")
        b.use(lease, "svc", "token")
        self.assertEqual(len(b.audit), 2)
        self.assertEqual(b.audit.maxlen, 2)

    def test_concurrent_rotation_is_serialized(self):
        from concurrent.futures import ThreadPoolExecutor

        b = m.SecretBroker(clock=lambda: 0.0, max_versions_per_secret=128)
        with ThreadPoolExecutor(max_workers=8) as pool:
            versions = list(pool.map(lambda i: b.put("token", f"v{i}", ["svc"]), range(64)))
        self.assertEqual(sorted(versions), list(range(1, 65)))
        self.assertEqual(len(b.versions["token"]), 64)

    def test_expiry_revocation_and_retirement(self):
        t = [0.0]
        b = m.SecretBroker(lease_ttl=10, clock=lambda: t[0])
        b.put("token", "v1", ["svc"])
        lease = b.resolve("svc", "token")
        b.revoke(lease)
        with self.assertRaises(m.LeaseRevoked):
            b.use(lease, "svc", "token")

        lease2 = b.resolve("svc", "token")
        b.retire("token", 1)
        with self.assertRaises(m.VersionRetired):
            b.use(lease2, "svc", "token")

        b.put("token", "v2", ["svc"])
        lease3 = b.resolve("svc", "token")
        t[0] = 11.0
        with self.assertRaises(m.LeaseExpired):
            b.use(lease3, "svc", "token")

    def test_clock_rollback_fails_closed(self):
        t = [5.0]
        b = m.SecretBroker(clock=lambda: t[0])
        b.put("token", "v", ["svc"])
        b.resolve("svc", "token")
        t[0] = 4.0
        with self.assertRaises(m.ClockRollbackError):
            b.resolve("svc", "token")

    def test_identifier_log_injection_is_rejected(self):
        b = m.SecretBroker(clock=lambda: 0.0)
        with self.assertRaises(m.InvalidSecretReference):
            b.put("bad\nname", "value", ["svc"])
        with self.assertRaises(m.InvalidSecretReference):
            b.put("ok", "value", ["svc\radmin"])

    def test_rotation_preserves_old_version_until_policy_invalidates_it(self):
        t = [0.0]
        b = m.SecretBroker(clock=lambda: t[0])
        b.put("api-key", "v1", ["svc"])
        old = b.resolve("svc", "api-key")
        t[0] = 1.0
        b.put("api-key", "v2", ["svc"])
        new = b.resolve("svc", "api-key")
        self.assertEqual(old.version, 1)
        self.assertEqual(new.version, 2)
        self.assertEqual(b.use(old, "svc", "api-key"), "v1")
        self.assertEqual(b.use(new, "svc", "api-key"), "v2")

    def test_invalid_ttl_rejected(self):
        for ttl in (0, -1, float("inf"), float("nan")):
            with self.subTest(ttl=ttl):
                with self.assertRaises((TypeError, ValueError)):
                    m.SecretBroker(lease_ttl=ttl)


if __name__ == "__main__":
    unittest.main()
