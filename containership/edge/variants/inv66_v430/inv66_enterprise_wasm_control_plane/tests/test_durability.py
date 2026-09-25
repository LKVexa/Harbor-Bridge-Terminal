"""Durability, crash recovery, retention, anchoring, fault injection (MC-005/035/038/043/046/059/063/070)."""
from __future__ import annotations

import json
import os
import pathlib
import unittest

from support import ANCHOR_KEY, Harness, component, request
from inv66_enterprise_wasm_control_plane.adapters import FileWormSink
from inv66_enterprise_wasm_control_plane.errors import ControlPlaneError
from inv66_enterprise_wasm_control_plane.store import JournalStore


def strip_volatile(state):
    s = json.loads(json.dumps(state))
    s["idem"] = {k: {kk: vv for kk, vv in v.items()} for k, v in s["idem"].items()}
    return s


class DurabilityTest(unittest.TestCase):
    def test_restart_replays_identical_state(self):
        h = Harness()
        for i in range(5):
            h.svc.admit(h.tok(), request(rid=f"r{i}", idempotency_key=f"k{i}"))
        h.svc.admit(h.tok(), request([component("x", signer="nobody")], rid="bad"))
        before = strip_volatile(h.svc.snapshot_state())
        head = h.svc.store.head_hash
        svc = h.restart()
        self.assertEqual(strip_volatile(svc.snapshot_state()), before)
        self.assertEqual(svc.store.head_hash, head)
        # idempotency survives restart
        again = svc.admit(h.tok(), request(rid="r0-retry", idempotency_key="k0"))
        self.assertTrue(again["replayed"])
        h.close()

    def test_torn_tail_is_truncated_on_recovery(self):
        h = Harness()
        h.svc.admit(h.tok(), request())
        seq = h.svc.store.head_seq
        with open(pathlib.Path(h.path) / "journal.jsonl", "ab") as fh:
            fh.write(b'{"schema":"PK_ECP_AUDIT/1","sequ')           # crash mid-append
        svc = h.restart()
        self.assertGreater(svc.store.recovered_bytes, 0)
        self.assertEqual(svc.store.head_seq, seq)
        self.assertTrue(svc.health()["status"] == "ok")
        h.close()

    def test_mid_journal_corruption_refuses_to_start(self):
        h = Harness()
        for i in range(3):
            h.svc.admit(h.tok(), request(rid=f"r{i}"))
        p = pathlib.Path(h.path) / "journal.jsonl"
        lines = p.read_bytes().splitlines(keepends=True)
        rec = json.loads(lines[1])
        rec["entry"]["admitted"] = not rec["entry"].get("admitted", False)
        lines[1] = json.dumps(rec).encode() + b"\n"
        p.write_bytes(b"".join(lines))
        with self.assertRaises(ControlPlaneError) as cm:
            h.restart()
        self.assertEqual(cm.exception.error.code, "STORE_UNAVAILABLE")
        h.close()

    def test_disk_full_fails_closed_and_forwards_nothing(self):
        state = {"armed": False}

        def fault(op):
            if state["armed"] and op == "append":
                raise OSError(28, "No space left on device")
        h = Harness(fault=fault)
        state["armed"] = True
        with self.assertRaises(ControlPlaneError) as cm:
            h.svc.admit(h.tok(), request())
        self.assertEqual(cm.exception.error.code, "STORE_UNAVAILABLE")
        self.assertEqual(h.deployer.received, {})
        self.assertFalse(h.svc.readiness()["ready"])
        state["armed"] = False
        self.assertTrue(h.svc.admit(h.tok(), request(rid="after"))["admitted"])
        self.assertTrue(h.svc.readiness()["ready"])
        h.close()

    def test_crash_during_delivery_resumes_idempotently(self):
        h = Harness()

        class Crash(Exception):
            pass
        orig = h.deployer.deliver

        def crash(*a, **k):
            orig(*a, **k)                  # INV-63 received it...
            raise KeyboardInterrupt        # ...but we died before journalling the ack
        h.deployer.deliver = crash
        with self.assertRaises(KeyboardInterrupt):
            h.svc.admit(h.tok(), request())
        h.deployer.deliver = orig
        svc = h.restart()
        (did, st), = [(i, d["state"]) for i, d in svc.state["decisions"].items()]
        self.assertEqual(st, "delivering")
        self.assertEqual(svc.drain_outbox(), {did: "deployed"})
        self.assertEqual(len(h.deployer.received), 1)                  # idempotent downstream
        h.close()

    def test_compaction_retention_and_restart(self):
        h = Harness()
        for i in range(10):
            h.svc.admit(h.tok(), request(rid=f"r{i}"))
        before = strip_volatile(h.svc.snapshot_state())
        out = h.svc.compact()
        self.assertGreater(out["sealed"], 0)
        self.assertEqual((pathlib.Path(h.path) / "journal.jsonl").read_bytes(), b"")
        svc = h.restart()
        self.assertEqual(strip_volatile(svc.snapshot_state()), before)
        svc.admit(h.tok(), request(rid="post"))
        ok, detail = svc.store.verify_all()
        self.assertTrue(ok, detail)
        # legal hold blocks purge; otherwise sealed segments below the floor are removed
        self.assertEqual(svc.store.purge_archives(10**9, legal_hold=True), [])
        self.assertEqual(len(svc.store.purge_archives(10**9, legal_hold=False)), 1)
        self.assertTrue(svc.store.verify_all()[0])
        h.close()

    def test_anchor_detects_full_chain_rewrite(self):
        h = Harness()
        sink_path = pathlib.Path(h.path).parent / (pathlib.Path(h.path).name + "-worm.jsonl")
        h.svc.store.anchor_sink = FileWormSink(sink_path)
        h.svc.admit(h.tok(), request(rid="a"))
        h.svc.admit(h.tok(), request([component("x", signer="nobody")], rid="b"))
        h.svc.anchor()
        self.assertEqual(h.svc.store.verify_anchors(), (True, "ok"))
        # attacker with file access rewrites the refusal into an admission AND recomputes the whole chain
        from inv66_enterprise_wasm_control_plane.store import record_hash, ZERO
        from inv66_enterprise_wasm_control_plane.canonical import canonical_json
        p = pathlib.Path(h.path) / "journal.jsonl"
        recs = [json.loads(l) for l in p.read_text().splitlines()]
        prev = ZERO
        for r in recs:
            if r["entry"].get("request_id") == "b":
                r["entry"]["admitted"] = True
            r["previous_hash"] = prev
            r["hash"] = record_hash(r["sequence"], prev, r["epoch"], r["entry"])
            prev = r["hash"]
        p.write_bytes(b"".join(canonical_json(r) + b"\n" for r in recs))
        store = JournalStore(h.path, "n1", anchor_key=ANCHOR_KEY, fsync=False)
        self.assertTrue(store.verify_all()[0])                 # chain alone is fooled...
        ok, why = store.verify_anchors(FileWormSink(sink_path).read())
        self.assertFalse(ok)                                   # ...the external anchor is not
        self.assertIn("rewritten", why)
        os.unlink(sink_path)
        h.close()

    def test_backup_restore_reconstruction(self):
        import shutil
        import tempfile
        from inv66_enterprise_wasm_control_plane.backup import backup, restore
        h = Harness()
        for i in range(3):
            h.svc.admit(h.tok(), request(rid=f"r{i}"))
        h.svc.anchor()
        work = tempfile.mkdtemp()
        m = backup(h.path, os.path.join(work, "bk"), ANCHOR_KEY)
        self.assertEqual(m["head_sequence"], h.svc.store.head_seq)
        expect = strip_volatile(h.svc.snapshot_state())
        out = restore(os.path.join(work, "bk"), os.path.join(work, "restored"), ANCHOR_KEY)
        self.assertEqual(out["anchors"], "ok")
        restored = Harness(path=os.path.join(work, "restored"), node="dr-site")
        self.assertEqual(strip_volatile(restored.svc.snapshot_state()), expect)
        self.assertTrue(restored.svc.admit(restored.tok(), request(rid="dr"))["admitted"])
        # tampered backup is refused
        j = pathlib.Path(work, "bk", "journal.jsonl")
        j.write_bytes(j.read_bytes().replace(b"r1", b"r9"))
        with self.assertRaises(ValueError):
            restore(os.path.join(work, "bk"), os.path.join(work, "again"), ANCHOR_KEY)
        shutil.rmtree(work)
        h.close()


if __name__ == "__main__":
    unittest.main()
