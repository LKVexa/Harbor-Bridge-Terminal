"""Crash/restart/replay (MC-047), backup/restore/reconstruction (MC-084) and
at-rest protection (MC-037)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from support import TENANT, client, make_service, seeded

from inv62_edge_topology.production import errors
from inv62_edge_topology.production.persistence import StateStore


class RecoveryTest(unittest.TestCase):
    def test_restart_replays_wal_to_identical_state(self):
        with tempfile.TemporaryDirectory() as d:
            svc, feed = seeded(state_dir=d)
            feed.apply([{"kind": "set_link_state", "a": "r1", "b": "s1-gw", "up": False}])
            op = svc.authn.issue("op", "operator", [TENANT])
            svc.admin(op, "quarantine", tenant=TENANT, node="s1-d2")
            before = svc.export_state()
            svc2 = make_service(state_dir=d, clock=svc.clock)
            self.assertEqual(svc2.export_state()["tenants"], before["tenants"])

    def test_checkpoint_then_more_wal(self):
        with tempfile.TemporaryDirectory() as d:
            svc, feed = seeded(state_dir=d)
            svc.checkpoint()
            self.assertEqual((Path(d) / "state" / "wal.jsonl").read_text(), "")
            feed.apply([{"kind": "remove_node", "node": "s1-d2"}])
            svc2 = make_service(state_dir=d, clock=svc.clock)
            self.assertNotIn("s1-d2", svc2.tenants[TENANT].topo.nodes)
            self.assertEqual(svc2.tenants[TENANT].topo.revision, svc.tenants[TENANT].topo.revision)

    def test_torn_final_append_is_truncated(self):
        with tempfile.TemporaryDirectory() as d:
            svc, feed = seeded(state_dir=d)
            wal = Path(d) / "state" / "wal.jsonl"
            with open(wal, "a") as fh:
                fh.write('{"seq": 99, "partial')
            svc2 = make_service(state_dir=d, clock=svc.clock)
            self.assertEqual(len(svc2.tenants[TENANT].topo.nodes), 6)
            self.assertTrue(wal.read_text().endswith("\n"))
            client(svc2, "topology-feed").apply([{"kind": "remove_node", "node": "s1-d2"}])
            make_service(state_dir=d, clock=svc.clock)  # chain still valid after truncation

    def test_tampered_or_reordered_wal_refuses_start(self):
        with tempfile.TemporaryDirectory() as d:
            svc, feed = seeded(state_dir=d)
            feed.apply([{"kind": "remove_node", "node": "s1-d2"}])
            wal = Path(d) / "state" / "wal.jsonl"
            lines = wal.read_text().splitlines()
            i = next(n for n, line in enumerate(lines) if '"apply"' in line)
            edited = lines[:i] + [lines[i].replace("s1-gw", "s1-gX")] + lines[i + 1:]
            self.assertNotEqual(edited, lines)
            for bad in (lines[::-1], edited, lines[1:]):
                wal.write_text("\n".join(bad) + "\n")
                with self.assertRaises(errors.TopoError):
                    make_service(state_dir=d, clock=svc.clock)

    def test_tampered_snapshot_refuses_start(self):
        with tempfile.TemporaryDirectory() as d:
            svc, feed = seeded(state_dir=d)
            svc.checkpoint()
            snap = Path(d) / "state" / "snapshot.json"
            body = json.loads(snap.read_text())
            body["state"]["frozen"] = True
            snap.write_text(json.dumps(body))
            with self.assertRaises(errors.TopoError):
                make_service(state_dir=d, clock=svc.clock)

    def test_encrypted_at_rest(self):
        with tempfile.TemporaryDirectory() as d:
            svc, feed = seeded(state_dir=d, security={"encrypt_at_rest": True, "audit_fsync": False})
            svc.checkpoint()
            feed.apply([{"kind": "remove_node", "node": "s1-d2"}])
            raw = (Path(d) / "state" / "snapshot.json").read_text() + (Path(d) / "state" / "wal.jsonl").read_text()
            self.assertNotIn("s1-gw", raw)
            svc2 = make_service(state_dir=d, clock=svc.clock, security={"encrypt_at_rest": True, "audit_fsync": False})
            self.assertEqual(len(svc2.tenants[TENANT].topo.nodes), 5)
            with self.assertRaises(errors.TopoError):  # plaintext reader cannot silently accept ciphertext
                make_service(state_dir=d, clock=svc.clock)


class BackupRestoreTest(unittest.TestCase):
    def test_export_import_reconstructs_on_empty_host(self):
        svc, feed = seeded()
        client(svc, "node-agent", node="s1-gw").acquire("s1", "s1-gw")
        backup = json.loads(json.dumps(svc.export_state()))
        fresh = make_service(clock=svc.clock)
        fresh.import_state(backup)
        self.assertEqual(fresh.export_state()["tenants"], svc.export_state()["tenants"])
        self.assertEqual(fresh.leases.term(f"{TENANT}/s1"), 1)
        self.assertEqual(client(fresh, "scheduler").resolve("s1-d1", "gpu")["result"]["node"], "s1-d2")

    def test_import_validates(self):
        fresh = make_service()
        with self.assertRaises(errors.TopoError):
            fresh.import_state({"format": "other"})
        bad = {"format": "inv62-state/1", "tenants": {"t": {"graph": {"nodes": {"d": {"tier": "device", "site": "s"}}, "links": []},
                                                            "revision": 1}}}
        with self.assertRaises(Exception):
            fresh.import_state(bad)
        self.assertEqual(fresh.tenants, {})

    def test_store_direct_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            s = StateStore(d, b"k" * 32, fsync=False)
            s.append("x", "t", {"a": 1})
            s.append("x", "t", {"a": 2})
            s2 = StateStore(d, b"k" * 32, fsync=False)
            snap, recs = s2.load()
            self.assertIsNone(snap)
            self.assertEqual([r["payload"]["a"] for r in recs], [1, 2])
            with self.assertRaises(errors.TopoError):
                StateStore(d, b"j" * 32, fsync=False).load()


if __name__ == "__main__":
    unittest.main()
