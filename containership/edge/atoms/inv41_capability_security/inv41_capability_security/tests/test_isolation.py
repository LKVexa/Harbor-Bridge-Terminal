"""Isolation-profile escape/quota tests and capability bridge tests (Section 10)."""
from __future__ import annotations

import json
import os
import unittest

from _common import ROOT

from inv41_capability_security.capabilities import Authority, Membrane, Revoked
from inv41_capability_security.isolation import CapabilityBridge, profile_status, run_isolated

POSIX = os.name == "posix"


class IsolationTest(unittest.TestCase):
    def test_IS001_child_cannot_import_trusted_implementation(self):
        code = f"import sys; sys.path.insert(0, {str(ROOT)!r})\ntry:\n import inv41_capability_security\n print('IMPORTED')\nexcept Exception as e:\n print('BLOCKED')"
        out = run_isolated(code)
        # -I ignores PYTHONPATH/user site, but an explicit sys.path insert still works: that is exactly why
        # the bridge never hands the child a Reference.  Record the observed fact rather than assume.
        self.assertIn(out["stdout"].strip(), ("IMPORTED", "BLOCKED"))
        out2 = run_isolated("import inv41_capability_security")
        self.assertNotEqual(out2["returncode"], 0, "package importable from isolated child without path tampering")

    def test_IS002_child_gets_empty_environment(self):
        os.environ["INV41_SECRET_PROBE"] = "should-not-leak"
        try:
            out = run_isolated("import os, json; print(json.dumps(dict(os.environ)))")
            env = json.loads(out["stdout"])
            self.assertNotIn("INV41_SECRET_PROBE", env)
        finally:
            del os.environ["INV41_SECRET_PROBE"]

    @unittest.skipUnless(POSIX, "rlimits are POSIX-only")
    def test_IS003_cpu_quota_terminates_runaway(self):
        out = run_isolated("while True: pass", limits={"cpu_s": 1, "wall_s": 10})
        self.assertTrue(out["terminated"] or out["returncode"] != 0)

    @unittest.skipUnless(POSIX, "rlimits are POSIX-only")
    def test_IS004_memory_quota(self):
        out = run_isolated("x = bytearray(900 * 1024 * 1024); print('ALLOCATED')", limits={"address_space_mb": 256})
        self.assertNotIn("ALLOCATED", out["stdout"])

    def test_IS005_wall_clock_quota(self):
        out = run_isolated("import time; time.sleep(30)", limits={"wall_s": 0.5})
        self.assertTrue(out["terminated"])

    @unittest.skipUnless(POSIX, "rlimits are POSIX-only")
    def test_IS006_file_size_quota(self):
        out = run_isolated("open('big','wb').write(b'x'*(4*1024*1024)); print('WROTE')", limits={"file_size_mb": 1})
        self.assertNotIn("WROTE", out["stdout"])

    def test_IS007_profile_status_is_honest(self):
        st = profile_status()
        self.assertFalse(st["adversarial_production_ready"])
        self.assertFalse(st["network_namespace"])
        self.assertFalse(st["syscall_filter"])


class BridgeTest(unittest.TestCase):
    def setUp(self):
        self.a = Authority({"store": {"read"}}, authority_id="bridge")
        self.h = self.a.bind_holder("wl", {"store": self.a.grant("store")})
        self.br = CapabilityBridge()
        self.sid = self.br.open_session("svc-a", self.h)
        self.handle = next(iter(self.br.handles(self.sid)))

    def req(self, sid=None, principal="svc-a", **msg):
        return json.loads(self.br.request(sid or self.sid, principal, json.dumps(msg)))

    def test_BR001_handle_use_and_no_reference_crosses(self):
        r = self.req(handle=self.handle, op="read")
        self.assertTrue(r["ok"])
        raw = self.br.request(self.sid, "svc-a", json.dumps({"handle": self.handle, "op": "read"}))
        self.assertNotIn(self.h.held["store"].token, raw)

    def test_BR002_unknown_handle_wrong_principal_wrong_session(self):
        self.assertEqual(self.req(handle="forged", op="read")["error"]["code"], "INV41-E031")
        self.assertEqual(self.req(principal="svc-b", handle=self.handle, op="read")["error"]["code"], "INV41-E031")
        other = self.br.open_session("svc-b", self.h)
        self.assertFalse(self.req(sid=other, principal="svc-b", handle=self.handle, op="read")["ok"])

    def test_BR003_malformed_and_oversized(self):
        for msg in ("{", "[]", json.dumps({"handle": self.handle}), "x" * 5000,
                    json.dumps({"handle": self.handle, "op": "read", "extra": 1})):
            self.assertFalse(json.loads(self.br.request(self.sid, "svc-a", msg))["ok"])

    def test_BR004_close_revokes_across_boundary(self):
        ref_behind = self.br._sessions[self.sid]["handles"][self.handle][1]
        self.assertTrue(self.br.close_session(self.sid)["revoked"])
        with self.assertRaises(Revoked):
            ref_behind.invoke("read")
        self.assertFalse(self.req(handle=self.handle, op="read")["ok"])


if __name__ == "__main__":
    unittest.main()
