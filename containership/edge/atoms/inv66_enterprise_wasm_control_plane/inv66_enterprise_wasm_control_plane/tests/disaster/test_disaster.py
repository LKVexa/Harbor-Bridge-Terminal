"""Disaster, partition and reconnect certification suite (MC-059, MC-063; C089, C095).

Scenarios are local simulations: "site loss" = a replica's process state discarded and
its lease left to expire; "partition" = the deployment manager unreachable; "restore" =
CLI backup/restore into a fresh root.  Multi-region storage loss is OPEN_EXTERNAL.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support import EcpError, Estate, FakeClock, PKG_DIR
from inv66_enterprise_wasm_control_plane.production.adapters import InMemoryDeploymentManager
from inv66_enterprise_wasm_control_plane.production.journal import Journal
from inv66_enterprise_wasm_control_plane.production.keys import Signer
from inv66_enterprise_wasm_control_plane.production.replication import FencedJournal, LeaseManager
from inv66_enterprise_wasm_control_plane.production.resilience import RetryPolicy

CLI = [sys.executable, "-m", "inv66_enterprise_wasm_control_plane.production.cli"]


def cli(*args, env=None):
    return subprocess.run([*CLI, *args], capture_output=True, text=True, cwd=str(PKG_DIR.parent), env=env, timeout=60)


class DisasterTest(unittest.TestCase):
    def state(self, svc):
        return {"gen": svc.config.active.generation, "inv": sorted(svc.inventory),
                "life": dict(svc.lifecycle.state), "frozen": svc.quarantine.snapshot(),
                "overlay": [b.to_doc() for b in svc.overlay], "head": svc.journal.head}

    def populate(self, e):
        for n in ("api", "web", "db"):
            e.service.admit(e.request(n), e.token("ops"))
        e.service.freeze("acme/analytics", e.principal("sec1"), "drill")
        e.service.rbac({"protocol": "PK_ECP_RBAC/1", "op": "bind", "request_id": "b",
                        "binding": {"subject": "n", "role": "viewer", "scope": "acme/payments", "effect": "allow"}},
                       e.principal("tadmin"))

    def test_backup_restore_reconstructs_identical_state(self):
        e = Estate()
        self.populate(e)
        before = self.state(e.service)
        bk = Path(tempfile.mkdtemp(prefix="inv66-bk-")) / "b"
        r = cli("backup", str(e.root), str(bk))
        self.assertEqual(r.returncode, 0, r.stderr)
        fresh = Path(tempfile.mkdtemp(prefix="inv66-restore-"))
        r = cli("restore", str(bk), str(fresh))
        self.assertEqual(r.returncode, 0, r.stderr)
        e2 = Estate.__new__(Estate)
        e2.__dict__.update(e.__dict__)
        e2.root = fresh
        restored = e2.open()
        self.assertEqual(self.state(restored), before)
        r = cli("restore", str(bk), str(fresh))  # never restores over live data
        self.assertNotEqual(r.returncode, 0)

    def test_restore_detects_tampered_backup(self):
        e = Estate()
        self.populate(e)
        bk = Path(tempfile.mkdtemp(prefix="inv66-bk-")) / "b"
        cli("backup", str(e.root), str(bk))
        meta = json.loads((bk / "BACKUP.json").read_text())
        meta["head_seq"] += 1
        (bk / "BACKUP.json").write_text(json.dumps(meta))
        r = cli("restore", str(bk), tempfile.mkdtemp())
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ECP_STORE_CORRUPT", r.stderr)

    def test_site_loss_failover_with_fencing(self):
        clk = FakeClock()
        shared = Path(tempfile.mkdtemp(prefix="inv66-ha-"))
        e = Estate(root=shared, clock=clk)
        a_lease = LeaseManager(shared, "site-a", ttl_s=10, clock=clk)
        b_lease = LeaseManager(shared, "site-b", ttl_s=10, clock=clk)
        self.assertTrue(a_lease.acquire())
        a = e.open(journal=FencedJournal(Journal(shared / "journal", clock=clk), a_lease), lease=a_lease)
        b = e.open(journal=FencedJournal(Journal(shared / "journal", clock=clk), b_lease), lease=b_lease)
        self.assertTrue(a.admit(e.request("api"), e.token("ops"))["admitted"])
        self.assertEqual((a.health()["role"], b.health()["role"]), ("leader", "follower"))
        self.assertFalse(b.health()["ready"])
        with self.assertRaises(EcpError) as cm:  # follower cannot write
            b.admit(e.request("web"), e.token("ops"))
        self.assertEqual(cm.exception.code, "ECP_NOT_LEADER")
        clk.advance(11)                             # site A lost: lease expires
        self.assertTrue(b_lease.acquire())
        b.refresh()
        self.assertEqual(len(b.inventory), 1)       # follower caught up from the shared journal
        self.assertTrue(b.admit(e.request("web"), e.token("ops"))["admitted"])
        with self.assertRaises(EcpError):           # site A comes back with a stale view: fenced
            a.admit(e.request("db"), e.token("ops"))
        self.assertEqual(Journal(shared / "journal").verify()["result"], "INTACT")

    def test_partition_from_deployment_manager_then_reconnect(self):
        dm = InMemoryDeploymentManager()
        e = Estate(deployer=dm, retry=RetryPolicy(max_attempts=2, sleep=lambda s: None))
        dm.fail_next = 1000
        ds = [e.service.admit(e.request(n), e.token("ops")) for n in ("a1", "a2", "a3")]
        self.assertEqual({d["state"] for d in ds}, {"delivery_pending"})
        self.assertEqual(e.service.health()["status"], "ok")  # deployment is not a required dependency
        dm.fail_next = 0
        e.service.delivery_breaker.state = "closed"
        s2 = e.open(deployer=dm)                              # also survive a restart during the partition
        self.assertEqual(set(s2.redeliver_pending().values()), {"delivered"})
        self.assertEqual(len(dm.received), 3)
        self.assertEqual(s2.redeliver_pending(), {})

    def test_retention_compaction_then_restart_preserves_state(self):
        clk = FakeClock()
        e = Estate(clock=clk, segment_records=10)
        self.populate(e)
        for i in range(25):
            e.service.admit(e.request(f"old{i}"), e.token("ops"))
        clk.advance(401 * 86400)                              # beyond retention_days=400
        e.service.admit(e.request("fresh"), e.token("ops"))
        before = self.state(e.service)
        res = e.service.enforce_retention()
        self.assertGreater(res["dropped_segments"], 0)
        after = e.open()
        st = self.state(after)
        self.assertEqual({k: st[k] for k in ("gen", "inv", "frozen", "overlay")},
                         {k: before[k] for k in ("gen", "inv", "frozen", "overlay")})
        self.assertEqual(after.journal.verify()["compacted_segments"], res["dropped_segments"])
        with self.assertRaises(EcpError):
            after.admit(e.request("x", tenant="analytics"), e.token("ops"))  # freeze survived compaction

    def test_anchor_cli_and_verification(self):
        e = Estate()
        self.populate(e)
        seed = os.urandom(32).hex()
        env = dict(os.environ, INV66_ANCHOR_KEY=seed, PYTHONPATH=str(PKG_DIR.parent))
        r = cli("anchor", str(e.root), "--key-ref", "env:INV66_ANCHOR_KEY", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        a = json.loads(r.stdout)
        keys = Path(tempfile.mkdtemp()) / "keys.json"
        keys.write_text(json.dumps({a["key_id"]: a["public_key"]}))
        r = cli("verify-journal", str(e.root), "--trusted-keys", str(keys))
        self.assertEqual(json.loads(r.stdout)["anchors_verified"], 1)


if __name__ == "__main__":
    unittest.main()
