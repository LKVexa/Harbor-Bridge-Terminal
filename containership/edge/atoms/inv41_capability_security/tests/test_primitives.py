"""Standalone security tests for INV-41; requires only the Python standard library."""
from __future__ import annotations

import pathlib
import pickle
import subprocess
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv41_capability_security.capabilities import (  # noqa: E402
    Authority, CrossAuthority, Forged, Membrane, Reference, Revoked, Widening,
)


class CapabilityPrimitiveTest(unittest.TestCase):
    def test_package_version_without_pk_core(self):
        import inv41_capability_security as package
        self.assertEqual(package.__version__, "4.3.0")

    def setUp(self):
        self.authority = Authority({"store": {"read", "write"}, "queue": {"send"}}, authority_id="test-domain")
        self.store = self.authority.grant("store")
        self.holder = self.authority.bind_holder("api", {"store": self.store})

    def test_direct_reference_construction_is_refused(self):
        with self.assertRaises(Forged):
            Reference("x", b"seal", "store", frozenset({"read"}), "token", "signature")

    def test_unknown_resource_is_refused(self):
        with self.assertRaises(PermissionError):
            self.authority.grant("secrets", {"read"})

    def test_bootstrap_policy_cannot_be_widened(self):
        with self.assertRaises(Widening):
            self.authority.grant("queue", {"send", "receive"})

    def test_holder_is_immutable(self):
        with self.assertRaises(TypeError):
            self.holder.held["queue"] = self.authority.grant("queue")

    def test_authority_and_holder_identity_are_immutable(self):
        with self.assertRaises(AttributeError):
            self.authority._authority_id = "changed"
        with self.assertRaises(AttributeError):
            self.holder._held = {}

    def test_unheld_alias_is_refused(self):
        with self.assertRaises(Forged):
            self.holder.use("queue", "send")

    def test_unauthorized_operation_is_refused(self):
        with self.assertRaises(Forged):
            self.holder.use("store", "admin")

    def test_attenuation_is_narrow_and_gets_new_token(self):
        narrowed = self.holder.delegate("store", {"read"})
        self.assertEqual(narrowed.operations, frozenset({"read"}))
        self.assertNotEqual(narrowed.token, self.store.token)
        self.assertTrue(narrowed.invoke("read")["permitted"])
        with self.assertRaises(Forged):
            narrowed.invoke("write")

    def test_attenuation_cannot_widen(self):
        with self.assertRaises(Widening):
            self.holder.delegate("store", {"read", "write", "admin"})

    def test_cross_authority_injection_is_refused(self):
        other = Authority({"store": {"read"}}, authority_id="other-domain")
        foreign = other.grant("store")
        with self.assertRaises(CrossAuthority):
            self.authority.bind_holder("victim", {"store": foreign})

    def test_same_id_impostor_authority_is_refused(self):
        impostor = Authority({"store": {"read", "write", "admin"}}, authority_id="test-domain")
        forged = impostor.grant("store", {"admin"})
        with self.assertRaises(CrossAuthority):
            self.authority.bind_holder("victim", {"store": forged})

    def test_nested_membrane_revocation_cannot_be_escaped(self):
        inner = Membrane("inner")
        outer = Membrane("outer")
        first = inner.wrap(self.store)
        derived = first.attenuate({"read"})
        nested = outer.wrap(derived)
        self.assertTrue(nested.invoke("read")["permitted"])
        result = inner.revoke()
        self.assertEqual(result["references_killed"], 3)
        for reference in (first, derived, nested):
            with self.assertRaises(Revoked):
                reference.invoke("read")

    def test_outer_membrane_revocation_only_kills_its_descendants(self):
        inner = Membrane("inner")
        outer = Membrane("outer")
        inner_ref = inner.wrap(self.store)
        outer_ref = outer.wrap(inner_ref)
        outer.revoke()
        self.assertTrue(inner_ref.invoke("read")["permitted"])
        with self.assertRaises(Revoked):
            outer_ref.invoke("read")

    def test_revoked_reference_cannot_be_delegated(self):
        membrane = Membrane("session")
        reference = membrane.wrap(self.store)
        membrane.revoke()
        with self.assertRaises(Revoked):
            reference.attenuate({"read"})

    def test_rewrapping_same_membrane_does_not_duplicate_chain(self):
        membrane = Membrane("session")
        first = membrane.wrap(self.store)
        second = membrane.wrap(first)
        self.assertEqual(second.membranes, (membrane,))
        self.assertEqual(membrane.live_reference_count, 2)

    def test_concurrent_post_revoke_invocations_fail_closed(self):
        membrane = Membrane("race")
        reference = membrane.wrap(self.store)
        revoked = threading.Event()
        errors = []

        def worker():
            revoked.wait()
            try:
                reference.invoke("read")
            except Revoked:
                return
            except BaseException as exc:  # capture for the main test thread
                errors.append(exc)
            else:
                errors.append(AssertionError("post-revoke invocation succeeded"))

        threads = [threading.Thread(target=worker) for _ in range(16)]
        for thread in threads:
            thread.start()
        membrane.revoke()
        revoked.set()
        for thread in threads:
            thread.join(timeout=2)
        self.assertFalse(errors, errors)
        self.assertFalse([thread for thread in threads if thread.is_alive()])

    def test_reference_is_nonserializable_and_repr_redacts_token(self):
        with self.assertRaises(TypeError):
            pickle.dumps(self.store)
        self.assertNotIn(self.store.token, repr(self.store))
        self.assertIn("<redacted>", repr(self.store))

    def test_optimized_mode_runs_security_checks(self):
        code = (
            "from inv41_capability_security.capabilities import Authority, Widening; "
            "a=Authority({'r':{'read'}}, authority_id='opt'); r=a.grant('r'); "
            "\ntry: r.attenuate({'read','write'})\nexcept Widening: print('PASS')\nelse: raise SystemExit(7)"
        )
        result = subprocess.run(
            [sys.executable, "-O", "-c", code], cwd=str(ROOT), capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "PASS")


if __name__ == "__main__":
    unittest.main()
