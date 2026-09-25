"""MC-016, MC-021..MC-026: keys, identity, capabilities, audit chain, secrets, isolation, adversarial."""
import json
import os
import pathlib
import unittest

from inv24_microvm_runtime.tests.helpers import keyring, tmpdir

from inv24_microvm_runtime import MicroVM
from inv24_microvm_runtime.errors import Inv24Error
from inv24_microvm_runtime.security.audit import AuditLog
from inv24_microvm_runtime.security.identity import TokenAuthority
from inv24_microvm_runtime.security.isolation import JailPolicy, policy_for, verify_process_isolation
from inv24_microvm_runtime.security.keys import EnvKeyProvider, Keyring, StaticKeyProvider
from inv24_microvm_runtime.security.secrets import (REDACTED, SecretRef, forbid_inline_secrets, redact,
                                                    scan_for_secrets)


class Clock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


class KeyTest(unittest.TestCase):
    def test_missing_short_and_malformed_keys_fail_closed(self):
        with self.assertRaises(Inv24Error) as cm:
            Keyring(StaticKeyProvider({}), "k1")
        self.assertEqual(cm.exception.code, "KEY_UNAVAILABLE")
        with self.assertRaises(Inv24Error):
            Keyring(StaticKeyProvider({"k1": b"short"}), "k1")
        os.environ["INV24_KEY_BAD"] = "!!!notbase64"
        with self.assertRaises(Inv24Error):
            EnvKeyProvider().fetch("bad")

    def test_rotation_grace_then_retire(self):
        clk = Clock()
        kr = Keyring(StaticKeyProvider({"k1": b"a" * 32, "k2": b"b" * 32}), "k1", grace_s=60, clock=clk)
        kid, mac = kr.sign(b"x")
        kr.rotate("k2")
        self.assertEqual(kr.active_id, "k2")
        self.assertTrue(kr.verify(kid, b"x", mac))
        clk.t += 61
        self.assertFalse(kr.verify(kid, b"x", mac))
        self.assertNotIn("a" * 8, kr.fingerprint())


class IdentityTest(unittest.TestCase):
    def setUp(self):
        self.clk = Clock()
        self.auth = TokenAuthority(keyring(), clock=self.clk)

    def test_valid_token_and_capability_scope(self):
        tok = self.auth.issue("svc", "workload", {"microvm:create"}, tenant="t1")
        p = self.auth.verify(tok)
        p.require("microvm:create", tenant="t1")
        with self.assertRaises(Inv24Error) as cm:
            p.require("microvm:stop")
        self.assertEqual(cm.exception.code, "UNAUTHORIZED")
        with self.assertRaises(Inv24Error) as cm:
            p.require("microvm:create", tenant="t2")
        self.assertEqual(cm.exception.code, "TENANT_MISMATCH")

    def test_replay_expiry_tamper_spoof(self):
        tok = self.auth.issue("svc", "workload", {"microvm:create"}, tenant="t1")
        self.auth.verify(tok)
        with self.assertRaises(Inv24Error) as cm:
            self.auth.verify(tok)
        self.assertEqual(cm.exception.code, "REPLAY_DETECTED")
        body, kid, mac = self.auth.issue("svc", "workload", {"microvm:create"}, tenant="t1").split(".")
        import base64
        claims = json.loads(base64.urlsafe_b64decode(body + "=="))
        claims["cap"] = sorted(claims["cap"] + ["operator:freeze"])
        forged = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
        spoof = TokenAuthority(keyring("k1-other"), clock=self.clk).issue("svc", "operator", {"operator:freeze"})
        expired = self.auth.issue("svc", "workload", {"microvm:create"}, ttl_s=1)
        self.clk.t += 5
        for bad, code in [(f"{forged}.{kid}.{mac}", "UNAUTHENTICATED"), (spoof, "UNAUTHENTICATED"),
                          (expired, "UNAUTHENTICATED"), ("", "UNAUTHENTICATED"), (None, "UNAUTHENTICATED"),
                          ("a.b", "UNAUTHENTICATED"), ("x" * 5000, "UNAUTHENTICATED")]:
            with self.subTest(bad=str(bad)[:20]), self.assertRaises(Inv24Error) as cm:
                self.auth.verify(bad)
            self.assertEqual(cm.exception.code, code)

    def test_issue_rejects_unknown_caps_and_long_ttl(self):
        with self.assertRaises(Inv24Error):
            self.auth.issue("s", "workload", {"root:everything"})
        with self.assertRaises(Inv24Error):
            self.auth.issue("s", "workload", {"microvm:create"}, ttl_s=86400)


class AuditTest(unittest.TestCase):
    def test_chain_detects_modification_deletion_reorder(self):
        d = tmpdir()
        path = os.path.join(d, "audit.jsonl")
        log = AuditLog(path, keyring())
        for i in range(5):
            log.append("admission", "svc", "accepted", n=i, capability_token="secret-value")
        self.assertEqual(log.verify()[1], 5)
        text = pathlib.Path(path).read_text()
        self.assertNotIn("secret-value", text)
        lines = text.splitlines()
        variants = {
            "modify": lines[:2] + [lines[2].replace('"accepted"', '"rejected"')] + lines[3:],
            "delete": lines[:2] + lines[3:],
            "reorder": [lines[1], lines[0]] + lines[2:],
        }
        for name, v in variants.items():
            with self.subTest(name=name):
                pathlib.Path(path).write_text("\n".join(v) + "\n")
                with self.assertRaises(Inv24Error) as cm:
                    AuditLog(path, keyring())
                self.assertEqual(cm.exception.code, "INTEGRITY_VIOLATION")

    def test_restart_continues_chain(self):
        path = os.path.join(tmpdir(), "a.jsonl")
        AuditLog(path, keyring()).append("e", "a", "ok")
        log2 = AuditLog(path, keyring())
        log2.append("e", "a", "ok")
        self.assertEqual(log2.verify()[1], 2)


class SecretsTest(unittest.TestCase):
    def test_redaction_of_keys_values_and_bounds(self):
        out = redact({"password": "hunter2", "note": "key AKIAABCDEFGHIJKLMNOP here",
                      "nested": {"api_key": "x", "ok": 1}, "blob": b"\0" * 10, "author": "dave"})
        self.assertEqual(out["password"], REDACTED)
        self.assertNotIn("AKIA", out["note"])
        self.assertEqual(out["nested"]["api_key"], REDACTED)
        self.assertEqual(out["author"], "dave")
        self.assertEqual(out["blob"], "[10 bytes]")
        self.assertLessEqual(len(redact("x" * 10000)), 1100)

    def test_config_must_use_secret_refs(self):
        forbid_inline_secrets({"kms_token": "secret://kms-main", "author": "dave"})
        for bad in [{"kms_token": "plaintext"}, {"x": "-----BEGIN RSA PRIVATE KEY-----"}]:
            with self.assertRaises(Inv24Error):
                forbid_inline_secrets(bad)
        self.assertEqual(SecretRef.parse("secret://a.b").name, "a.b")
        with self.assertRaises(Inv24Error):
            SecretRef.parse("vault:/x")
        self.assertTrue(scan_for_secrets("ghp_" + "a" * 40))


class IsolationTest(unittest.TestCase):
    def test_policy_is_least_privilege(self):
        vm = MicroVM("vm1", "t1", vcpus=2, memory_mib=256)
        p = policy_for(vm, allocated_uids=set())
        self.assertGreaterEqual(p.uid, 200_000)
        self.assertEqual(p.cgroup["memory.swap.max"], "0")
        self.assertEqual(p.cgroup["cpu.max"], "200000 100000")
        argv = p.jailer_argv("/opt/fc/jailer", "/opt/fc/firecracker")
        for flag in ("--new-pid-ns", "--netns", "--chroot-base-dir", "--uid"):
            self.assertIn(flag, argv)
        with self.assertRaises(Inv24Error):
            p.jailer_argv("jailer", "/opt/fc/firecracker")
        with self.assertRaises(Inv24Error):
            policy_for(vm, allocated_uids=set(), seccomp_level=0)

    def test_uids_never_shared(self):
        used = set()
        for i in range(500):
            used.add(policy_for(MicroVM(f"vm{i}", "t"), allocated_uids=used).uid)
        self.assertEqual(len(used), 500)

    def test_unisolated_process_is_detected(self):
        """This test process is NOT jailed, so verification must refuse it (negative evidence)."""
        p = JailPolicy("x", 200001, 200001, "/srv/jailer", "/var/run/netns/x", {})
        with self.assertRaises(Inv24Error) as cm:
            verify_process_isolation(os.getpid(), p)
        self.assertEqual(cm.exception.code, "INTEGRITY_VIOLATION")


class AdversarialTest(unittest.TestCase):
    """MC-026: hostile inputs at every boundary exercised in-process."""

    def test_hostile_identifiers(self):
        for name in ["a" * 129, "x\x00", "\x1b[31m", "", "   "]:
            with self.subTest(name=repr(name)), self.assertRaises((TypeError, ValueError)):
                MicroVM(name, "t")

    def test_resource_exhaustion_bounded(self):
        from inv24_microvm_runtime.schemas import validate
        with self.assertRaises(Inv24Error):
            validate({"schema": "PK_MICROVM/1", "instance": "i", "tenant": "t", "vcpus": 1, "memory_mib": 32,
                      "devices": ["serial"] * 10000, "state": "created"})

    def test_device_spoof_via_subclass_rejected(self):
        from inv24_microvm_runtime.devices import SerialSpec, order_and_check

        class Evil(SerialSpec):
            kind = "serial"
        with self.assertRaises(Inv24Error):
            order_and_check([Evil()], declared=frozenset({"serial"}))


if __name__ == "__main__":
    unittest.main()
