"""C02 trusted time, C03 journal, C04 audit chain, C15 encryption/keys, C16 fencing,
C17 persisted epoch/generation, C18 atomic transactions, C20 storage exhaustion."""
import json, os, unittest
from pathlib import Path
from _util import T, Tmp, node, code, Gap04Error
from gap04_disconnected_operation_controller.runtime import crypto
from gap04_disconnected_operation_controller.runtime.clock import TrustedClock, sign_time_token
from gap04_disconnected_operation_controller.runtime.journal import Journal, JournalLimits
from gap04_disconnected_operation_controller.runtime.storage import FileKeyProvider, Keyring
from gap04_disconnected_operation_controller.runtime.fencing import OwnershipLock, FencingValidator
from gap04_disconnected_operation_controller.runtime.config import default_config


def jr(d, gen=lambda: 1, **kw):
    kr = Keyring.open(FileKeyProvider(Path(d) / "k.json"))
    return Journal(Path(d) / "j", kr, generation=gen, **kw), kr


class TrustedTime(unittest.TestCase):
    def test_T_C02_rollback_detected(self):
        m = T.FakeMono(); c = TrustedClock(monotonic=m)
        c.anchor_trusted(1000); m.t += 50
        self.assertEqual(c.now(), 1050)
        code(self, "GAP04-E0300", c.anchor_trusted, 900)

    def test_T_C02_jump_detected(self):
        m = T.FakeMono(); c = TrustedClock(monotonic=m, max_drift_s=30)
        c.anchor_trusted(1000); m.t += 10
        code(self, "GAP04-E0300", c.anchor_trusted, 2000)

    def test_T_C02_unanchored_fails_closed(self):
        code(self, "GAP04-E0300", TrustedClock().now)
        code(self, "GAP04-E0300", TrustedClock().anchor_rtc)

    def test_T_C02_restored_hwm_is_conservative(self):
        c = TrustedClock.restored(5000, persist_interval_s=10)
        self.assertEqual(c.hwm, 5010)
        code(self, "GAP04-E0300", c.anchor_trusted, 4000)   # VM snapshot restore / RTC rewind

    def test_T_C02_signed_time_token(self):
        cp = T.ControlPlane(); ts = cp.trust(); c = TrustedClock(monotonic=T.FakeMono())
        n = c.challenge()
        tok = sign_time_token(cp.t0, n, cp.issuer, cp.key_id, cp.seed)
        self.assertEqual(c.anchor_signed(tok, ts), cp.t0)
        code(self, "GAP04-E0300", c.anchor_signed, tok, ts)          # replay
        n2 = c.challenge(); bad = dict(sign_time_token(cp.t0 + 1, n2, cp.issuer, cp.key_id, cp.seed), time=cp.t0 + 99)
        code(self, "GAP04-E0300", c.anchor_signed, bad, ts)          # tampered

    def test_T_C02_rtc_fallback_caps_to_freeze(self):
        with Tmp() as d:
            cfg = default_config(); cfg["clock"]["allow_rtc_after_reboot"] = True
            n, cp, m = node(d, config=cfg)
            T.bring_up(n, cp, m)
            n.close()
            n2, _, _ = node(d, cp=cp, mono=m, config=cfg)
            n2.clock.rtc = lambda: n2.clock.hwm + 5
            n2.clock.allow_rtc_after_reboot = True
            n2.clock.anchor_rtc()
            T.go_dark(n2, m)
            self.assertEqual(n2.health()["tier"], "freeze")
            code(self, "GAP04-E0101", n2.decide, "admit-new", "ns/a", "req-00000001")
            n2.decide("restart", "ns/a", "req-00000002")
            n2.close()

    def test_T_C02_reboot_cannot_extend_lease(self):
        with Tmp() as d:
            n, cp, m = node(d)
            T.bring_up(n, cp, m, ttl=600)
            T.go_dark(n, m); m.t += 500; n.health()
            hwm = n.clock.hwm
            n.close()
            m2 = T.FakeMono()   # monotonic resets on reboot
            n2, _, _ = node(d, cp=cp, mono=m2)
            code(self, "GAP04-E0300", n2.decide, "restart", "ns/a", "req-00000001")
            code(self, "GAP04-E0300", n2.clock.anchor_trusted, hwm - 400)  # rewound RTC
            n2.close()


class JournalWAL(unittest.TestCase):
    def test_T_C03_append_recover_torn_tail(self):
        with Tmp() as d:
            j, kr = jr(d)
            for i in range(10):
                j.append("decision", {"i": i})
            with open(j.path, "ab") as f:
                f.write(b"deadbeef {\"partial")   # crash mid-append
            j2 = Journal(j.dir, kr, generation=lambda: 1)
            self.assertEqual(j2.seq, 10); self.assertGreater(j2.truncated_tail, 0)
            self.assertEqual([f["body"]["i"] for f in j2.frames()], list(range(10)))

    def test_T_C03_mid_file_corruption_fails_closed(self):
        with Tmp() as d:
            j, kr = jr(d)
            for i in range(5):
                j.append("decision", {"i": i})
            data = bytearray(j.path.read_bytes()); data[40] ^= 0x01
            j.path.write_bytes(bytes(data))
            code(self, "GAP04-E0401", Journal, j.dir, kr, generation=lambda: 1)

    def test_T_C03_compaction_bounded(self):
        with Tmp() as d:
            j, kr = jr(d)
            for i in range(50):
                j.append("decision", {"i": i})
            before = j.size
            j.compact(45, archive_dir=Path(d) / "arch")
            self.assertLess(j.size, before)
            self.assertTrue(list((Path(d) / "arch").iterdir()))
            j2 = Journal(j.dir, kr, generation=lambda: 1)
            self.assertEqual((j2.seq, j2.head), (50, j.head))
            j2.append("decision", {"i": 50})

    def test_T_C04_tamper_evidence(self):
        with Tmp() as d:
            j, kr = jr(d, encrypt=False)
            for i in range(5):
                j.append("decision", {"i": i})
            lines = j.path.read_bytes().splitlines(keepends=True)
            # delete a middle frame (re-crc'd so only the chain can catch it)
            j.path.write_bytes(b"".join(lines[:2] + lines[3:]))
            code(self, "GAP04-E0402", Journal, j.dir, kr, generation=lambda: 1)

    def test_T_C04_forged_frame_with_valid_crc_and_hash(self):
        import binascii, hashlib
        from gap04_disconnected_operation_controller.runtime import canonical
        with Tmp() as d:
            j, kr = jr(d, encrypt=False)
            j.append("decision", {"i": 0})
            fr = next(j.frames())
            fr["body"] = {"i": 999}
            core = {k: fr[k] for k in fr if k not in ("h", "mac")}
            fr["h"] = "sha256:" + hashlib.sha256(fr["prev"].encode() + canonical.dumps(core)).hexdigest()
            p = canonical.dumps(fr)
            j.path.write_bytes(f"{binascii.crc32(p) & 0xffffffff:08x} ".encode() + p + b"\n")
            code(self, "GAP04-E0402", Journal, j.dir, kr, generation=lambda: 1)  # MAC needs audit key

    def test_T_C04_verifiable_export(self):
        with Tmp() as d:
            j, kr = jr(d)
            for i in range(6):
                j.append("decision", {"i": i})
            ex = j.export(2)
            self.assertEqual(Journal.verify_export(ex, bytes(kr.audit_key)), j.head)
            ex["frames"].pop(1)
            code(self, "GAP04-E0402", Journal.verify_export, ex, bytes(kr.audit_key))

    def test_T_C20_reserved_capacity_and_freeze(self):
        with Tmp() as d:
            cfg = default_config(); cfg["journal"].update(max_bytes=64 * 1024, reserve_bytes=24 * 1024, min_disk_free_bytes=0)
            n, cp, m = node(d, config=cfg, encrypt_journal=False)
            T.bring_up(n, cp, m)
            T.go_dark(n, m)
            with self.assertRaises(Gap04Error) as cm:
                for i in range(10_000):
                    n.decide("restart", f"ns/w{i}", f"req-{i:08d}")
            self.assertEqual(cm.exception.code, "GAP04-E0400")
            h = n.health()
            self.assertFalse(h["ready"]); self.assertIn("storage_frozen", h["not_ready_reasons"])
            self.assertEqual(h["tier"], "freeze")
            n.quarantine("disk full containment", None)   # control frames still fit in reserve
            self.assertGreaterEqual(n.metrics.get("storage_alarms_total", reason="journal_full"), 1)
            n.close()

    def test_T_C20_failed_append_leaves_no_phantom_decision(self):
        with Tmp() as d:
            cfg = default_config(); cfg["journal"].update(max_bytes=64 * 1024, reserve_bytes=24 * 1024, min_disk_free_bytes=0)
            n, cp, m = node(d, config=cfg, encrypt_journal=False)
            T.bring_up(n, cp, m); T.go_dark(n, m)
            ok = 0
            try:
                for i in range(10_000):
                    n.decide("restart", f"ns/w{i}", f"req-{i:08d}"); ok += 1
            except Gap04Error:
                pass
            self.assertEqual(len(n.controller.decisions), ok)
            n.close()
            n2, _, _ = node(d, cp=cp, mono=m, config=cfg, encrypt_journal=False)
            self.assertEqual(len(n2.controller.decisions), ok)
            n2.close()


class EncryptionKeys(unittest.TestCase):
    def test_T_C15_at_rest_encrypted_and_rotation(self):
        with Tmp() as d:
            n, cp, m = node(d)
            T.bring_up(n, cp, m); T.go_dark(n, m)
            n.decide("restart", "ns/secret-workload", "req-00000001")
            raw = (Path(d) / "journal" / "journal.wal").read_bytes()
            self.assertNotIn(b"secret-workload", raw)
            self.assertNotIn(b"lease_id", raw)
            old = n.keyring.active
            n.keyring.rotate()
            n.decide("restart", "ns/b", "req-00000002")
            n.close()
            n2, _, _ = node(d, cp=cp, mono=m)
            self.assertEqual(len(n2.controller.decisions), 2)   # both key generations readable
            self.assertNotEqual(n2.keyring.active, old)
            n2.close()

    def test_T_C15_key_file_permissions_and_wrong_key(self):
        with Tmp() as d:
            p = Path(d) / "k.json"
            kr = Keyring.open(FileKeyProvider(p))
            os.chmod(p, 0o644)
            code(self, "GAP04-E0403", Keyring.open, FileKeyProvider(p))
            os.chmod(p, 0o600)
            env = kr.encrypt(b"x", b"aad")
            code(self, "GAP04-E0403", kr.decrypt, env, b"other-aad")
            buf = bytearray(b"secret"); crypto.zeroize(buf); self.assertEqual(bytes(buf), b"\0" * 6)


class Fencing(unittest.TestCase):
    def test_T_C16_duplicate_instance_rejected(self):
        with Tmp() as d:
            n, cp, m = node(d)
            code(self, "GAP04-E0501", node, d, cp=cp, mono=m, owner="node-dup")
            n.close()

    def test_T_C16_stale_generation_fenced(self):
        with Tmp() as d:
            lock = OwnershipLock(Path(d)); g = lock.acquire("a"); lock.release()
            j, kr = jr(d, gen=lock.current_generation)
            j.append("decision", {}, generation=g)
            OwnershipLock(Path(d)).acquire("b")   # new owner bumps generation
            code(self, "GAP04-E0500", j.append, "decision", {}, generation=g)
            code(self, "GAP04-E0500", lock.check)

    def test_T_C16_downstream_validator(self):
        v = FencingValidator(); v.admit(1, 2); v.admit(1, 3)
        code(self, "GAP04-E0500", v.admit, 1, 2)

    def test_T_C17_epoch_and_generation_persist(self):
        with Tmp() as d:
            n, cp, m = node(d)
            T.bring_up(n, cp, m); T.go_dark(n, m)
            ep, gen = n.controller.partition_epoch, n.generation
            n.close()
            n2, _, _ = node(d, cp=cp, mono=m)
            self.assertEqual(n2.controller.partition_epoch, ep)
            self.assertEqual(n2.generation, gen + 1)
            self.assertIsNotNone(n2.controller.partitioned_since)
            n2.close()


class NoSilentReset(unittest.TestCase):
    def test_T_C17_missing_journal_refused(self):
        import shutil
        with Tmp() as d:
            n, cp, m = node(d); T.bring_up(n, cp, m); n.close()
            shutil.rmtree(d / "journal")
            code(self, "GAP04-E0401", node, d, cp=cp, mono=m)

    def test_T_C20_explicit_freeze_exit(self):
        with Tmp() as d:
            cfg = default_config(); cfg["journal"].update(max_bytes=64 * 1024, reserve_bytes=24 * 1024, min_disk_free_bytes=0)
            n, cp, m = node(d, config=cfg, encrypt_journal=False)
            T.bring_up(n, cp, m); T.go_dark(n, m)
            try:
                for i in range(10_000):
                    n.decide("restart", f"ns/w{i}", f"req-{i:08d}")
            except Gap04Error:
                pass
            code(self, "GAP04-E0400", n.clear_storage_freeze)          # backlog still pending
            T.come_back(n, cp, m); n.reconnect()                        # reconcile + compaction frees space
            n.clear_storage_freeze()
            self.assertNotIn("storage_frozen", n.health()["not_ready_reasons"])
            n.close()


class AtomicTx(unittest.TestCase):
    def test_T_C18_delta_frame_is_atomic_and_recoverable(self):
        with Tmp() as d:
            n, cp, m = node(d)
            T.bring_up(n, cp, m); T.go_dark(n, m)
            r = n.decide("restart", "ns/a", "req-00000001")
            fr = [f for f in n.journal.frames() if f["kind"] == "decision"][-1]
            self.assertEqual(fr["body"]["decision"], r)             # decision + bindings in ONE frame
            for k in ("lease_id", "policy_digest", "authority_epoch", "partition_epoch", "generation",
                      "config_version", "code_version", "request_id"):
                self.assertIn(k, fr["body"]["decision"])
            n.owner.release()                                        # simulated crash: no close() frame
            n2, _, _ = node(d, cp=cp, mono=m)
            self.assertEqual(n2.controller.decisions[-1]["decision_id"], r["decision_id"])
            self.assertEqual(n2.state["requests"]["req-00000001"], r["decision_id"])
            n2.clock.anchor_trusted(n2.clock.hwm)
            self.assertTrue(n2.decide("restart", "ns/a", "req-00000001")["replayed"])
            n2.close()


if __name__ == "__main__":
    unittest.main()
