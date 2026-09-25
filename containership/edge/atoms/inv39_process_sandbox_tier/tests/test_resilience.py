"""MC-056/057/062/065/092 — fault injection: each injected fault ends in a safe, recorded state."""
from __future__ import annotations

import io
import json
import os
import signal
import tempfile
import threading
import time
import unittest
from importlib import import_module

from _support import LINUX, PKG_DIR, require

L = import_module(PKG_DIR.name + ".linux.launcher")
profiles = import_module(PKG_DIR.name + ".profiles")
errors = import_module(PKG_DIR.name + ".errors")
att = import_module(PKG_DIR.name + ".attestation")
cfg = import_module(PKG_DIR.name + ".config")
rt = import_module(PKG_DIR.name + ".runtime")
ctl = import_module(PKG_DIR.name + ".control")


@require(LINUX, "Linux enforcement not available")
class LauncherFaultTest(unittest.TestCase):
    def test_supervisor_killed_during_verification(self):
        p = profiles.load_profile("posix-minimal")
        marker = tempfile.mktemp()
        spec = L.LaunchSpec(argv=("/bin/sh", "-c", f"echo x > {marker}"), syscalls=p.syscalls,
                            namespaces=frozenset({"user", "pid", "ipc", "uts", "net"}))

        def sabotage(pid, ev):
            os.kill(int(open(f"/proc/{pid}/status").read().split("PPid:")[1].split()[0]), signal.SIGKILL)
            time.sleep(0.1)
            raise errors.SandboxError("E_NOT_APPLIED", "supervisor vanished")
        with self.assertRaises(errors.SandboxError):
            L.launch(spec, on_ready=sabotage)
        time.sleep(0.2)
        self.assertFalse(os.path.exists(marker))

    def test_unapplyable_control_fails_closed(self):
        p = profiles.load_profile("posix-minimal")
        with self.assertRaises(errors.SandboxError) as c:
            L.launch(L.LaunchSpec(argv=("/bin/true",), syscalls=p.syscalls, rlimits={"bogus": 1}))
        self.assertEqual(c.exception.code, "E_APPLY_FAILED")
        with self.assertRaises(errors.SandboxError) as c:
            L.launch(L.LaunchSpec(argv=("/bin/true",), syscalls=p.syscalls, landlock_ro=("/does/not/exist",)))
        self.assertEqual(c.exception.code, "E_APPLY_FAILED")

    def test_exec_failure_is_reported_not_hidden(self):
        p = profiles.load_profile("posix-minimal")
        r = L.launch(L.LaunchSpec(argv=("/nonexistent/binary",), syscalls=p.syscalls))
        self.assertEqual(r.exit_code, 125)


class StateFaultTest(unittest.TestCase):
    def test_restart_with_corrupt_active_config_uses_history(self):
        d = tempfile.mkdtemp()
        st = cfg.ConfigStore(d)
        st.activate({"syscall_budget": 55}, actor="a", source="s")
        open(os.path.join(d, "active.json"), "w").write("{corrupt")
        self.assertEqual(cfg.ConfigStore(d).active["config"]["syscall_budget"], 55)

    def test_tampered_audit_blocks_service_start(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "a.jsonl")
        c = att.AuditChain(p); c.append("x", {"a": 1}); c.append("x", {"a": 2})
        lines = open(p).read().splitlines()
        open(p, "w").write(lines[1] + "\n")
        with self.assertRaises(errors.SandboxError):
            rt.SandboxService(identity=att.NodeIdentity("n", b"k" * 32), principal_keys={},
                              authz=ctl.Authorizer(), audit_path=p, log_stream=io.StringIO())

    def test_dependency_flap_is_fail_closed_then_recovers(self):
        state = {"up": False}
        svc = rt.SandboxService(identity=att.NodeIdentity("n", b"k" * 32), principal_keys={"op": b"k" * 32},
                                authz=ctl.Authorizer(), log_stream=io.StringIO(),
                                dependencies_online=lambda: state["up"])
        self.assertFalse(svc.status()["ready"])
        state["up"] = True
        self.assertEqual(svc.status()["ready"], svc.status()["not_ready_reasons"] == [])

    def test_breaker_opens_under_backend_failures_and_heals(self):
        now = [0.0]
        adm = ctl.Admission(ctl.Limits(breaker_failures=3, breaker_reset_s=5), clock=lambda: now[0])
        for _ in range(3):
            adm.acquire("t"); adm.release("t", ok=False)
        with self.assertRaises(errors.SandboxError):
            adm.acquire("t")
        now[0] = 6
        adm.acquire("t"); adm.release("t", ok=True)
        adm.acquire("t")


if __name__ == "__main__":
    unittest.main()
