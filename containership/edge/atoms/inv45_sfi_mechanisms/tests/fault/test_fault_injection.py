"""Deterministic fault-injection suite (C060, C055-C058, C089, C048, C095).

Each test names the failure mode from docs/operations/FAILURE_MODEL.md (FM-xx) it injects,
then asserts detection, containment and recovery objectives.
"""
from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

from inv45_sfi_mechanisms.tests.support import Harness
from inv45_sfi_mechanisms.production import audit, config
from inv45_sfi_mechanisms.production.errors import SfiError


class Crash(Exception):
    pass


class FM01_ConfigCrashDuringActivation(unittest.TestCase):
    def test_crash_after_generation_write_leaves_old_active(self):
        with tempfile.TemporaryDirectory() as td:
            def fault(stage):
                if stage == "after-generation-write":
                    raise Crash()
            s = config.GenerationStore(Path(td), fault=fault)
            with self.assertRaises(Crash):
                s.activate(dict(config.DEFAULTS), author="a", source="t", approval=None, expected_current=0)
            s2 = config.GenerationStore(Path(td))  # restart
            self.assertEqual(s2.current_number(), 0)
            self.assertFalse((Path(td) / ".activate.lock").exists())  # lock released on crash path
            s2.activate(dict(config.DEFAULTS), author="a", source="t", approval=None, expected_current=0)

    def test_crash_after_pointer_swap_is_complete(self):
        with tempfile.TemporaryDirectory() as td:
            def fault(stage):
                if stage == "after-pointer-swap":
                    raise Crash()
            s = config.GenerationStore(Path(td), fault=fault)
            with self.assertRaises(Crash):
                s.activate(dict(config.DEFAULTS), author="a", source="t", approval=None, expected_current=0)
            s2 = config.GenerationStore(Path(td))
            self.assertEqual(s2.current_number(), 1)
            self.assertEqual(s2.recover(), (1, "active-ok"))


class FM02_CorruptedActiveGeneration(unittest.TestCase):
    def test_auto_rollback_to_last_valid(self):
        with tempfile.TemporaryDirectory() as td:
            s = config.GenerationStore(Path(td))
            s.activate(dict(config.DEFAULTS), author="a", source="t", approval=None, expected_current=0)
            c2 = copy.deepcopy(config.DEFAULTS)
            c2["telemetry"]["retention_days"] = 7
            s.activate(c2, author="a", source="t", approval=None, expected_current=1)
            g2 = Path(td) / "generations" / "gen-000002.json"
            rec = json.loads(g2.read_text())
            rec["config"]["telemetry"]["retention_days"] = 8  # bit-rot / tamper: digest no longer matches
            g2.write_text(json.dumps(rec))
            self.assertEqual(config.GenerationStore(Path(td)).recover(), (1, "auto-rollback"))


class FM03_AuditSinkOutage(unittest.TestCase):
    def test_spool_then_recover_then_fail_closed_when_full(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a.jsonl"
            down = {"on": True}

            def writer(path, line):
                if down["on"]:
                    raise OSError("sink down")
                with path.open("a") as fh:
                    fh.write(line)
            log = audit.AuditLog(p, writer=writer, spool_limit=3)
            for i in range(3):
                log.emit({"event": "e", "target": str(i)})
            self.assertEqual(len(log.spool), 3)
            with self.assertRaises(SfiError) as cm:
                log.emit({"event": "overflow"})
            self.assertEqual(cm.exception.code, "SFI_DEPENDENCY_UNAVAILABLE")
            down["on"] = False
            self.assertEqual(log.flush(), 0)
            self.assertEqual(audit.verify_chain(p)["events"], 4)


class FM04_KeyServiceUnavailable(unittest.TestCase):
    def test_no_trust_granted_and_recovery(self):
        h = Harness()
        try:
            env = os.environ.pop(h.seal_env)
            with self.assertRaises(SfiError) as cm:
                h.submit()
            self.assertEqual(cm.exception.code, "SFI_DEPENDENCY_UNAVAILABLE")
            self.assertTrue(cm.exception.retryable)
            os.environ[h.seal_env] = env
            h.submit()  # recovers without restart
        finally:
            h.close()


class FM05_ControllerCrashAndRestart(unittest.TestCase):
    def test_state_survives_restart_no_duplicate_owner(self):
        with tempfile.TemporaryDirectory() as td:
            h = Harness(root=Path(td))
            r = h.submit(version=4)
            h.svc.load(h.tenant_token("t1"), r["artifact"], r["descriptor"])
            h.svc.quarantine(h.token("op"), "tenant", "t9", "disable", "incident")
            seq = h.svc.audit.checkpoint()
            # restart the controller on the same durable root (same owner id)
            h2 = Harness(root=Path(td))
            self.assertEqual(h2.svc.state.read()["floors"]["wl"], 4)
            self.assertIn("tenant:t9", h2.svc.state.read()["quarantine"])
            self.assertEqual(h2.svc.instances, {})  # ephemeral instances are not resurrected
            self.assertEqual(audit.verify_chain(Path(td) / "audit" / "audit.jsonl", seq)["result"], "INTACT")
            h.close()
            h2.close()


class FM06_PartitionFromControlPlane(unittest.TestCase):
    def test_offline_operation_until_freshness_expires(self):
        h = Harness()
        try:
            r = h.submit()
            # control plane unreachable: no refresh; within freshness window loads continue
            h.svc.load(h.tenant_token("t1"), r["artifact"], r["descriptor"])
            h.keyring.loaded_at -= 7200  # freshness window elapsed while partitioned
            r2 = None
            with self.assertRaises(SfiError) as cm:
                r2 = h.submit(version=2)
            self.assertEqual(cm.exception.code, "SFI_TRUST_STALE")
            self.assertIsNone(r2)
            h.keyring.refresh()  # reconnect
            h.submit(version=2)
            self.assertEqual(h.svc.health()["status"], "ready")
        finally:
            h.close()


if __name__ == "__main__":
    unittest.main()
