"""WS 6, 7, 10, 14 -- durable state, audit anchoring, fencing, crash/fault injection and recovery."""
from __future__ import annotations

import json
import pathlib
import tempfile
import threading
import unittest

from _support import AUDIT_KEY, HOST, E, FakeClock, FakeHypervisor, Rig
from inv32_elastic_virtualization.fencing import FileLeaseStore, Ownership
from inv32_elastic_virtualization.store import PHASES, DurableStore


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name) / "s"

    def tearDown(self):
        self.tmp.cleanup()

    def test_restart_restores_ops_audit_quarantine_state(self):
        s = DurableStore(self.dir, signing_key=AUDIT_KEY)
        s.op_phase("op1", "prepared", guest="g1")
        s.append_audit({"kind": "memory", "guest": "g1"})
        s.set_quarantine("guest:g1", {"ticket": "T"})
        s.put_guest_state("g1", memory_mib=5)
        s2 = DurableStore(self.dir, signing_key=AUDIT_KEY)
        self.assertEqual(s2.ops["op1"]["phase"], "prepared")
        self.assertEqual(s2.audit_head, s.audit_head)
        self.assertIn("guest:g1", s2.quarantine)
        self.assertEqual(s2.guest_state("g1")["memory_mib"], 5)
        self.assertEqual(s2.guest_state("g1")["version"], 1)

    def test_torn_tail_is_quarantined_not_trusted(self):
        s = DurableStore(self.dir, signing_key=AUDIT_KEY)
        s.op_phase("op1", "prepared", guest="g1")
        with open(self.dir / "journal.jsonl", "ab") as fh:
            fh.write(b'{"rec":{"t":"op","operation_id":"op2"')  # crash mid-write
        s2 = DurableStore(self.dir, signing_key=AUDIT_KEY)
        self.assertNotIn("op2", s2.ops)
        self.assertTrue((self.dir / "journal.jsonl.torn").exists())
        s2.op_phase("op3", "prepared")
        self.assertIn("op3", DurableStore(self.dir, signing_key=AUDIT_KEY).ops)

    def test_mid_file_corruption_blocks(self):
        s = DurableStore(self.dir, signing_key=AUDIT_KEY)
        for i in range(3):
            s.op_phase(f"op{i}", "prepared")
        lines = (self.dir / "journal.jsonl").read_text().splitlines()
        lines[1] = lines[1].replace("op1", "opX")
        (self.dir / "journal.jsonl").write_text("\n".join(lines) + "\n")
        with self.assertRaises(E.StoreIntegrityError):
            DurableStore(self.dir, signing_key=AUDIT_KEY)

    def test_audit_rotation_signed_heads_and_linkage(self):
        s = DurableStore(self.dir, signing_key=AUDIT_KEY, segment_max_events=4)
        for i in range(10):
            s.append_audit({"kind": "memory", "n": i})
        segs = sorted((self.dir / "audit").glob("seg-*.jsonl"))
        self.assertEqual(len(segs), 3)
        self.assertEqual(len(list((self.dir / "audit").glob("*.head"))), 2)
        s2 = DurableStore(self.dir, signing_key=AUDIT_KEY, segment_max_events=4)
        self.assertEqual(len(s2.audit_events), 10)
        self.assertTrue(s2.verify())
        head = segs[0].with_suffix(".head")
        doc = json.loads(head.read_text())
        doc["head_hash"] = "0" * 64
        head.write_text(json.dumps(doc))
        with self.assertRaises(E.StoreIntegrityError):
            DurableStore(self.dir, signing_key=AUDIT_KEY)

    def test_missing_audit_segment_detected(self):
        s = DurableStore(self.dir, signing_key=AUDIT_KEY, segment_max_events=2)
        for i in range(6):
            s.append_audit({"kind": "memory", "n": i})
        sorted((self.dir / "audit").glob("seg-*.jsonl"))[1].unlink()
        with self.assertRaises(E.StoreIntegrityError):
            DurableStore(self.dir, signing_key=AUDIT_KEY)

    def test_external_anchor_detects_whole_chain_rewrite(self):
        external: list[dict] = []
        s = DurableStore(self.dir, signing_key=AUDIT_KEY, anchor_sink=external.append)
        for i in range(3):
            s.append_audit({"kind": "memory", "n": i})
        s.anchor()
        # attacker rewrites the local chain consistently *and* deletes the local anchor copy
        for p in (self.dir / "audit").glob("*"):
            p.unlink()
        (self.dir / "anchors.jsonl").unlink()
        forged = DurableStore(self.dir, signing_key=AUDIT_KEY)
        for i in range(3):
            forged.append_audit({"kind": "memory", "n": 100 + i})
        with self.assertRaises(E.StoreIntegrityError):
            forged.verify_against_external(external)

    def test_backup_restore_clean_env_and_partial_restore(self):
        s = DurableStore(self.dir, signing_key=AUDIT_KEY)
        s.append_audit({"kind": "memory"})
        s.put_guest_state("g1", memory_mib=7)
        bk = pathlib.Path(self.tmp.name) / "bk"
        s.backup(bk)
        r = DurableStore.restore(bk, pathlib.Path(self.tmp.name) / "r", signing_key=AUDIT_KEY)
        self.assertEqual((r.audit_head, r.guest_state("g1")["memory_mib"]), (s.audit_head, 7))
        (bk / "state.json").unlink()
        with self.assertRaises(E.StoreIntegrityError):
            DurableStore.restore(bk, pathlib.Path(self.tmp.name) / "r2", signing_key=AUDIT_KEY)
        with self.assertRaises(E.StoreIntegrityError):
            DurableStore.restore(bk, pathlib.Path(self.tmp.name) / "r3", signing_key=b"z" * 32)

    def test_stale_backup_is_reconciled_before_writes(self):
        r = Rig()
        r.guest()
        tok = r.tenant_token()
        r.store.backup(r.dir / "bk")
        r.ctl.handle(r.mem("a", 2048), tok)  # happens after the backup
        restored_dir = r.dir / "state-c1"
        import shutil
        shutil.rmtree(restored_dir)
        DurableStore.restore(r.dir / "bk", restored_dir, signing_key=AUDIT_KEY)
        r2 = Rig(fake=r.fake, tmp=str(r.dir), lease_dir=str(r.dir / "leases"), clock=r.clock)
        self.assertEqual(r2.store.guest_state("g1")["memory_mib"], 1024)  # stale expected state
        ev = r2.ctl.handle(r2.mem("b", 1152), r2.tenant_token())["event"]
        self.assertEqual(ev["from_mib"], 2048)  # decision used live hypervisor state, not the stale backup
        r.close()

    def test_idempotency_retention_pruning(self):
        clock = FakeClock()
        s = DurableStore(self.dir, signing_key=AUDIT_KEY, clock=clock)
        s.op_phase("old", "audit_committed", created=clock())
        s.op_phase("pending", "provider_requested", created=clock())
        clock.advance(8 * 86400)
        self.assertEqual(s.prune_idempotency(7 * 86400), 1)
        self.assertNotIn("old", DurableStore(self.dir, signing_key=AUDIT_KEY).ops)
        self.assertIn("pending", s.ops)  # never prune non-terminal


class FencingTest(unittest.TestCase):
    def test_duplicate_controller_startup(self):
        with tempfile.TemporaryDirectory() as d:
            clock = FakeClock()
            ls = FileLeaseStore(d, clock=clock)
            a = Ownership(ls, HOST, "a", clock=clock)
            b = Ownership(ls, HOST, "b", clock=clock)
            a.acquire()
            with self.assertRaises(E.NotOwner):
                b.acquire()

    def test_stale_controller_cannot_commit_after_takeover(self):
        r1 = Rig(controller_id="c1")
        r1.guest()
        tok = r1.tenant_token()
        r1.clock.advance(16)  # c1's lease expires (e.g. GC pause / partition)
        r2 = Rig(controller_id="c2", fake=r1.fake, tmp=str(r1.dir), lease_dir=str(r1.dir / "leases"), clock=r1.clock)
        r2.ctl.register_guest("g1", tenant="t1", floor_mib=256, ceiling_mib=4096, vcpu_max=4)
        res = r1.ctl.handle(r1.mem("late", 2048), tok)
        self.assertIn(res["error"]["code"], ("not_owner", "fencing_rejected"))
        self.assertEqual(r1.fake.get_guest("g1").memory_mib, 1024)
        self.assertEqual(r2.ctl.handle(r2.mem("new", 2048), r2.tenant_token())["outcome"], "success")
        self.assertFalse(r1.ctl.health().ready)
        r1.close()

    def test_delayed_packet_from_stale_epoch_rejected_by_provider(self):
        fake = FakeHypervisor(16384, overhead_mib=0)
        g = fake.create_guest("g1", "t1", 1024)
        fake.set_memory("g1", 1152, expected_version=g.state_version, incarnation=g.incarnation,
                        idempotency_key="k2", fencing_token=2, deadline=1e18)
        g = fake.get_guest("g1")
        with self.assertRaises(E.FencingRejected):
            fake.set_memory("g1", 2048, expected_version=g.state_version, incarnation=g.incarnation,
                            idempotency_key="k1", fencing_token=1, deadline=1e18)

    def test_partition_from_lease_store_freezes_writes(self):
        r = Rig()
        r.guest()
        r.leases.available = False
        res = r.ctl.handle(r.mem("a", 2048), r.tenant_token())
        self.assertEqual(res["error"]["code"], "not_owner")
        self.assertFalse(r.ctl.health().ready)
        r.close()

    def test_at_most_one_writer_per_state_version(self):
        """Many threads race the same guest state version: exactly one commit wins."""
        r = Rig()
        r.guest()
        v = r.fake.get_guest("g1").state_version
        tok = r.tenant_token()
        results = []

        def go(i):
            results.append(r.ctl.handle(r.mem(f"race-{i}", 1152 + 128 * i, expected_version=v), tok))
        threads = [threading.Thread(target=go, args=(i,)) for i in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        wins = [x for x in results if x["outcome"] == "success"]
        self.assertEqual(len(wins), 1)
        codes = [x["error"]["code"] for x in results if x not in wins]
        self.assertTrue(set(codes) <= {"stale_expected_state", "guest_busy"}, codes)
        r.close()

    def test_rollback_records_do_not_cross_epochs(self):
        r = Rig()
        r.guest()
        ev = r.ctl.handle(r.mem("a", 2048), r.tenant_token())["event"]
        r.ownership.acquire()  # new epoch (e.g. restart)
        res = r.ctl.handle(r.revert("b", ev["event_hash"]), r.operator_token())
        self.assertEqual(res["error"]["code"], "stale_adjustment")
        r.close()

    def test_ownership_events_audited(self):
        r = Rig()
        audit = []
        o = Ownership(r.leases, "host-x", "cx", clock=r.clock, audit=audit.append)
        o.acquire()
        o.renew()
        o.release()
        self.assertEqual([a["kind"] for a in audit], ["ownership_acquired", "ownership_released"])
        r.close()


class CrashInjectionTest(unittest.TestCase):
    """Kill the controller at every journal phase, restart, reconcile; invariants must hold."""

    class Crash(BaseException):
        pass

    def _run(self, crash_phase: str):
        r = Rig()
        r.guest()
        tok = r.tenant_token()
        real = r.store.op_phase

        def crashing(op, phase, **kw):
            out = real(op, phase, **kw)
            if phase == crash_phase:
                raise self.Crash()
            return out
        r.store.op_phase = crashing
        with self.assertRaises(self.Crash):
            r.ctl._handle(__import__("inv32_elastic_virtualization.validation", fromlist=["x"]).decode_request(
                json.dumps(r.mem("op-crash", 2048))), tok, __import__(
                "inv32_elastic_virtualization.telemetry", fromlist=["x"]).TraceContext.new())
        # restart: fresh store + controller on the same state dir; same hypervisor
        r2 = Rig(fake=r.fake, tmp=str(r.dir), lease_dir=str(r.dir / "leases"), clock=r.clock)
        report = r2.ctl.recover()
        g = r.fake.get_guest("g1")
        self.assertTrue(256 <= g.memory_mib <= 4096)
        calls = [c for c in r.fake.calls if c[0] == "memory"]
        self.assertLessEqual(len(calls), 1, "a crashed mutation was replayed")
        self.assertTrue(r2.ctl.health().checks["no_unknown_outcomes"])
        res = r2.ctl.handle(r2.mem("op-crash", 2048), r2.tenant_token())
        self.assertEqual(res["outcome"], "success")
        # not-applied ops are safely re-executed under the same ID; applied ones are replayed, never re-mutated
        self.assertEqual(res["replayed"], crash_phase not in ("prepared", "provider_requested"))
        self.assertEqual(len([c for c in r.fake.calls if c[0] == "memory"]), 1)
        return report

    def test_crash_at_every_phase(self):
        for phase in PHASES:
            with self.subTest(phase=phase):
                report = self._run(phase)
                if phase in ("prepared", "provider_requested"):
                    self.assertEqual(report[0]["result"], "not_applied")
                elif phase in ("provider_confirmed", "state_committed"):
                    self.assertEqual(report[0]["result"], "applied")
                else:
                    self.assertEqual(report, [])

    def test_unknown_outcome_blocks_blind_retry_until_reconciled(self):
        r = Rig()
        r.guest()
        tok = r.tenant_token()
        r.fake.inject("timeout_noapply")
        self.assertEqual(r.ctl.handle(r.mem("a", 2048), tok)["error"]["code"], "unknown_outcome_blocked")
        self.assertEqual(r.ctl.handle(r.mem("a", 2048), tok)["error"]["code"], "unknown_outcome_blocked")
        self.assertEqual(r.ctl.handle(r.mem("b", 1152), tok)["error"]["code"], "unknown_outcome_blocked")
        self.assertEqual(r.ctl.recover()[0]["result"], "not_applied")
        self.assertEqual(r.ctl.handle(r.mem("b", 1152), tok)["outcome"], "success")
        r.close()

    def test_ambiguous_reconciliation_quarantines(self):
        r = Rig()
        r.guest()
        r.fake.inject("timeout")
        r.ctl.handle(r.mem("a", 2048), r.tenant_token())
        r.fake.external_resize("g1", 1536)  # someone else touched it while unknown
        self.assertEqual(r.ctl.recover()[0]["result"], "ambiguous_quarantined")
        self.assertIn("guest:g1", r.ctl.quarantine.active())
        r.close()


class StoreFuzzAndDiskFaultTest(unittest.TestCase):
    def test_fuzz_audit_and_journal_import(self):
        """Random byte corruption of persisted files: load either succeeds with a verified chain or raises
        StoreIntegrityError -- never another exception, never a silently-accepted modified event."""
        import random
        rng = random.Random(4242)
        with tempfile.TemporaryDirectory() as d:
            base = pathlib.Path(d) / "base"
            s = DurableStore(base, signing_key=AUDIT_KEY, segment_max_events=5)
            for i in range(12):
                s.op_phase(f"op{i}", "prepared", guest="g")
                s.append_audit({"kind": "memory", "sequence_hint": i, "guest": "g"})
            s.anchor()
            files = [p for p in base.rglob("*") if p.is_file()]
            import shutil
            for n in range(300):
                work = pathlib.Path(d) / f"w{n}"
                shutil.copytree(base, work)
                victim = work / rng.choice(files).relative_to(base)
                data = bytearray(victim.read_bytes())
                if not data:
                    continue
                for _ in range(rng.randrange(1, 4)):
                    data[rng.randrange(len(data))] = rng.randrange(256)
                victim.write_bytes(bytes(data))
                try:
                    loaded = DurableStore(work, signing_key=AUDIT_KEY, segment_max_events=5)
                except E.StoreIntegrityError:
                    continue
                self.assertTrue(loaded.verify())
                # Anything accepted must be a prefix of the original chain (torn tail dropped at most).
                orig = [e["event_hash"] for e in s.audit_events]
                got = [e["event_hash"] for e in loaded.audit_events]
                self.assertEqual(got, orig[: len(got)])
                shutil.rmtree(work)

    def test_state_store_write_failure_never_acknowledges(self):
        r = Rig()
        r.guest()
        real = r.store.append_audit

        def disk_full(payload):
            if payload.get("kind") == "memory":
                raise OSError(28, "No space left on device")
            return real(payload)
        r.store.append_audit = disk_full
        res = r.ctl.handle(r.mem("a", 2048), r.tenant_token())
        self.assertNotEqual(res["outcome"], "success")
        self.assertEqual(res["error"]["code"], "internal_error")
        self.assertNotIn("space", json.dumps(res))
        r.store.append_audit = real
        # The provider change happened but was never acknowledged; restart reconciles it from the journal.
        r2 = Rig(fake=r.fake, tmp=str(r.dir), lease_dir=str(r.dir / "leases"), clock=r.clock)
        self.assertEqual(r2.ctl.recover()[0]["result"], "applied")
        r.close()

    def test_config_cannot_make_live_state_illegal(self):
        r = Rig(total_mib=8192)
        r.guest(mem=6144, ceiling=8192)
        with self.assertRaises(E.ConfigInvalid):
            r.config.stage({"site": [{"host_reserve_fraction": 0.3}]}, author="a", source="s")
        with self.assertRaises(E.ConfigInvalid):
            r.config.stage({"site": [{"feature_memory_hot_unplug": True}]}, author="a", source="s")
        r.close()


if __name__ == "__main__":
    unittest.main()
