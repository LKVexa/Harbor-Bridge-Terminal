"""Dependency-free security and lifecycle tests for the INV-39 sandbox policy model."""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("inv39_sandbox", PKG_DIR / "sandbox.py")
sandbox = importlib.util.module_from_spec(SPEC)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load sandbox.py test target")
sys.modules[SPEC.name] = sandbox
SPEC.loader.exec_module(sandbox)


class SandboxPolicyTest(unittest.TestCase):
    def profile(self):
        return sandbox.SandboxProfile("svc", frozenset({"read", "write", "exit_group"}))

    def test_profile_is_canonicalised(self):
        p = sandbox.SandboxProfile(
            " svc ", {" READ ", "write"}, {"cap_chown"}, {"PID", "mount", "net", "ipc", "uts", "user"}
        )
        self.assertEqual(p.name, "svc")
        self.assertEqual(p.syscalls, frozenset({"read", "write"}))
        self.assertEqual(p.capabilities, frozenset({"CAP_CHOWN"}))
        self.assertIn("pid", p.namespaces)

    def test_forbidden_capability_case_bypass_is_closed(self):
        p = sandbox.SandboxProfile("svc", {"read"}, {"cap_sys_admin"})
        self.assertTrue(p.validate())
        with self.assertRaises(sandbox.ProfileInvalid):
            sandbox.Sandbox("p", p).start(readback=sandbox.Sandbox("r", p).requested_state())

    def test_missing_namespace_is_rejected(self):
        p = sandbox.SandboxProfile("svc", {"read"}, namespaces={"pid", "mount"})
        with self.assertRaises(sandbox.ProfileInvalid):
            sandbox.Sandbox("p", p).start(readback=sandbox.Sandbox("r", p).requested_state())

    def test_no_readback_fails_closed(self):
        with self.assertRaises(sandbox.ProfileNotApplied):
            sandbox.Sandbox("p", self.profile()).start()

    def test_missing_readback_field_fails_closed(self):
        p = self.profile()
        with self.assertRaises(sandbox.ProfileNotApplied):
            sandbox.Sandbox("p", p).start(readback={"syscalls": p.syscalls})

    def test_mismatched_readback_fails_closed(self):
        p = self.profile()
        state = sandbox.Sandbox("r", p).requested_state()
        state["syscalls"] = {"read", "write", "exit_group", "ptrace"}
        box = sandbox.Sandbox("p", p)
        with self.assertRaises(sandbox.ProfileNotApplied):
            box.start(readback=state)
        self.assertFalse(box._started)
        self.assertEqual(box.applied_syscalls, frozenset())

    def test_call_before_verified_start_is_rejected(self):
        with self.assertRaises(sandbox.SandboxStateError):
            sandbox.Sandbox("p", self.profile()).call("read")

    def test_start_is_single_transition(self):
        p = self.profile()
        box = sandbox.Sandbox("p", p)
        box.start(readback=box.requested_state())
        with self.assertRaises(sandbox.SandboxStateError):
            box.start(readback=box.requested_state())

    def test_default_deny_and_bounded_denial_log(self):
        p = self.profile()
        box = sandbox.Sandbox("p", p)
        result = box.start(readback=box.requested_state())
        self.assertTrue(result["verified"])
        self.assertTrue(result["default_deny"])
        self.assertTrue(box.call("read"))
        for i in range(sandbox.MAX_DENIAL_LOG + 5):
            self.assertFalse(box.call(f"deny_{i}"))
        self.assertEqual(len(box.denials), sandbox.MAX_DENIAL_LOG)
        self.assertEqual(box.denials_dropped, 5)

    def test_profile_digest_is_stable(self):
        a = sandbox.SandboxProfile("svc", {"write", "read"})
        b = sandbox.SandboxProfile("svc", {"read", "write"})
        self.assertEqual(a.digest, b.digest)
        self.assertTrue(a.digest.startswith("sha256:"))

    def test_bad_iterable_shape_is_rejected(self):
        with self.assertRaises(sandbox.ProfileInvalid):
            sandbox.SandboxProfile("svc", "read")
        with self.assertRaises(sandbox.ProfileInvalid):
            sandbox.SandboxProfile("svc", {"read", "bad syscall"})


if __name__ == "__main__":
    unittest.main()
