import json, os, tempfile, unittest
from inv65_capability_providers.tests.helpers import World
from inv65_capability_providers.errors.mapping import ProviderFault
from inv65_capability_providers.state.store import LinkStateStore
from inv65_capability_providers.tools.backup_state import backup, restore


def rd(p):
    with open(p, "rb") as f:
        return f.read()


class StateRecovery(unittest.TestCase):
    def test_process_restart_restores_non_revoked_and_not_revoked(self):
        w = World(); w.svc.start(); w.link("a"); w.link("b"); w.link("c"); w.unlink("b")
        w2 = World(state_dir=w.tmp, instance="inst-a")
        self.assertEqual(w2.svc.start(), 2)
        self.assertEqual(w2.call("a")["result"]["bucket"], "acme-a")
        with self.assertRaises(ProviderFault):
            w2.call("b")

    def test_torn_tail_discarded_mid_record_corruption_fails_closed(self):
        d = tempfile.mkdtemp(); s = LinkStateStore(d, compact_every=0)
        for i in range(3):
            s.put(["t", "e", "s", "w", "c", f"l{i}"], {"config_version": 1, "i": i})
        wal = os.path.join(d, "wal.jsonl")
        data = rd(wal)
        with open(wal, "wb") as f:
            f.write(data + b'{"op":"put","key":"x"')  # crash mid-append
        s2 = LinkStateStore(d, compact_every=0)
        self.assertTrue(s2.discarded_torn_tail); self.assertEqual(len(s2.links), 3)
        lines = rd(wal).split(b"\n"); lines[1] = lines[1].replace(b'"i":1', b'"i":9')
        with open(wal, "wb") as f:
            f.write(b"\n".join(lines))
        with self.assertRaises(ProviderFault) as c:
            LinkStateStore(d)
        self.assertEqual(c.exception.code, "PK_PROVIDER_STATE_CORRUPT")

    def test_snapshot_checksum_and_compaction(self):
        d = tempfile.mkdtemp(); s = LinkStateStore(d, compact_every=2)
        for i in range(5):
            s.put(["t", "e", "s", "w", "c", f"l{i}"], {"config_version": 1})
        s.revoke(["t", "e", "s", "w", "c", "l0"])
        self.assertEqual(LinkStateStore(d).links.keys(), s.links.keys())
        snap = json.loads(rd(os.path.join(d, "snapshot.json"))); snap["seq"] += 1
        with open(os.path.join(d, "snapshot.json"), "w") as f:
            json.dump(snap, f)
        with self.assertRaises(ProviderFault):
            LinkStateStore(d)

    def test_revocation_tombstone_blocks_stale_relink(self):
        d = tempfile.mkdtemp(); s = LinkStateStore(d); k = ["t", "e", "s", "w", "c", "l"]
        s.put(k, {"config_version": 3}); s.revoke(k)
        with self.assertRaises(ProviderFault):
            s.put(k, {"config_version": 3})
        s.put(k, {"config_version": 4})
        self.assertIsNotNone(s.get(k))

    def test_backup_restore_never_resurrects_revoked(self):
        w = World(); w.svc.start(); w.link("a"); w.link("b")
        arch = os.path.join(tempfile.mkdtemp(), "b.json")
        backup(w.svc.store, arch)
        w.unlink("a")
        with self.assertRaises(ValueError):
            restore(arch, w.tmp)  # older than live
        out = restore(arch, w.tmp, force_older=True)
        self.assertEqual(out["blocked_resurrections"], 1)
        s = LinkStateStore(w.tmp)
        self.assertEqual(len(s.links), 1)
        self.assertTrue(any("\"a\"" in k for k in s.revoked))

    def test_backup_integrity(self):
        w = World(); w.svc.start(); w.link("a")
        arch = os.path.join(tempfile.mkdtemp(), "b.json"); backup(w.svc.store, arch)
        doc = json.loads(rd(arch)); doc["seq"] = 999
        with open(arch, "w") as f:
            json.dump(doc, f)
        with self.assertRaises(ValueError):
            restore(arch, tempfile.mkdtemp())

    def test_v1_snapshot_migrates(self):
        from inv65_capability_providers.state.store import _ck
        d = tempfile.mkdtemp()
        body = {"schema_version": 1, "seq": 1, "links": {"orders|primary": {"bucket": "b", "user": "u"}}, "revoked": {}}
        body["checksum"] = _ck(body)
        with open(os.path.join(d, "snapshot.json"), "w") as f:
            json.dump(body, f)
        s = LinkStateStore(d)
        (k, v), = s.items()
        self.assertEqual(k[-2:], ["orders", "primary"]); self.assertEqual(v["migrated_from"], "v1")
