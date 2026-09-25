"""Registry lifecycle, CAS concurrency, integrity, persistence, rollback, emergency disable
(MC-027..MC-030, MC-047, MC-067, MC-069, MC-070)."""
import json
import tempfile
import threading
import unittest

from harness import F, Reason, RegistryError, ValidationError, refusal
from inv28_unikernel_implementations.registry import Authorizer, FileStore, Registry, verify_snapshot
from inv28_unikernel_implementations.trust import KeyRing

R = Reason
REF = "rumprun@1.0.0-fixture"


class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.w = F.world()
        self.reg = self.w["registry"]

    def rev(self):
        return self.reg.revision

    def test_update_changes_attributes_and_is_audited(self):
        new = self.reg.get(REF).replace(features=["net-stack", "posix-subset", "tls"])
        self.reg.update(new, actor="operator", expected_revision=self.rev())
        self.assertIn("tls", self.reg.get(REF).features)
        self.assertEqual(self.reg.history[-1]["op"], "update")
        self.assertTrue(self.w["audit"].entries("registry.update"))

    def test_update_cannot_change_lifecycle_or_artifact(self):
        rec = self.reg.get(REF)
        with self.assertRaises(RegistryError) as cm:
            self.reg.update(rec.replace(lifecycle="deprecated"), actor="operator", expected_revision=self.rev())
        self.assertEqual(cm.exception.code, R.REGISTRY_TRANSITION)
        bad = rec.replace(integrity={**rec.integrity.to_dict(), "artifact_sha256": "e" * 64})
        with self.assertRaises(RegistryError):
            self.reg.update(bad, actor="operator", expected_revision=self.rev())

    def test_update_unknown(self):
        with self.assertRaises(RegistryError) as cm:
            self.reg.update(F.record("ghost"), actor="operator", expected_revision=self.rev())
        self.assertEqual(cm.exception.code, R.REGISTRY_UNKNOWN)

    def test_legal_and_illegal_transitions(self):
        self.reg.transition(REF, "deprecated", actor="operator", expected_revision=self.rev(), reason="x")
        self.reg.transition(REF, "eol", actor="operator", expected_revision=self.rev(), reason="x")
        with self.assertRaises(RegistryError) as cm:
            self.reg.transition(REF, "active", actor="operator", expected_revision=self.rev(), reason="x")
        self.assertEqual(cm.exception.code, R.REGISTRY_TRANSITION)
        self.reg.transition(REF, "retired", actor="operator", expected_revision=self.rev(), reason="x")
        self.reg.remove(REF, actor="operator", expected_revision=self.rev())
        with self.assertRaises(RegistryError):
            self.reg.get(REF)
        self.assertEqual([h["op"] for h in self.reg.history][-4:],
                         ["transition:active->deprecated", "transition:deprecated->eol", "transition:eol->retired", "remove"])

    def test_remove_requires_retired(self):
        with self.assertRaises(RegistryError) as cm:
            self.reg.remove(REF, actor="operator", expected_revision=self.rev())
        self.assertEqual(cm.exception.code, R.REGISTRY_TRANSITION)

    def test_new_entries_must_start_candidate_or_active(self):
        with self.assertRaises(RegistryError):
            self.reg.register(F.record("n", lifecycle="deprecated"), actor="operator", expected_revision=self.rev())

    def test_duplicate_is_case_insensitive(self):
        with self.assertRaises(RegistryError) as cm:
            self.reg.register(F.record("RUMPRUN"), actor="operator", expected_revision=self.rev())
        self.assertEqual(cm.exception.code, R.REGISTRY_DUPLICATE)

    def test_entries_snapshot_is_immutable_tuple(self):
        self.assertIsInstance(self.reg.entries, tuple)

    def test_bad_ref(self):
        with self.assertRaises(ValidationError):
            self.reg.get("no-version")


class Authorization(unittest.TestCase):
    def test_capabilities_enforced(self):
        ring = KeyRing.ephemeral()
        reg = Registry(ring, Authorizer({"writer": {"register"}, "oncall": {"emergency"}}))
        reg.register(F.record("t"), actor="writer", expected_revision=0)
        for actor, call in (("writer", lambda: reg.emergency_disable("t@1.0.0-fixture", actor="writer", reason="x")),
                            ("oncall", lambda: reg.register(F.record("u"), actor="oncall", expected_revision=1)),
                            ("nobody", lambda: reg.transition("t@1.0.0-fixture", "deprecated", actor="nobody",
                                                              expected_revision=1, reason="x")),
                            ("", lambda: reg.register(F.record("u"), actor="", expected_revision=1))):
            with self.subTest(actor=actor), self.assertRaises(RegistryError) as cm:
                call()
            self.assertEqual(cm.exception.code, R.REGISTRY_UNAUTHORIZED)
        reg.emergency_disable("t@1.0.0-fixture", actor="oncall", reason="x")

    def test_disable_via_transition_needs_emergency_capability(self):
        reg = Registry(KeyRing.ephemeral(), Authorizer({"w": {"register", "lifecycle"}}))
        reg.register(F.record("t"), actor="w", expected_revision=0)
        with self.assertRaises(RegistryError):
            reg.transition("t@1.0.0-fixture", "disabled", actor="w", expected_revision=1, reason="x")


class Concurrency(unittest.TestCase):                                         # MC-029, MC-047
    def test_stale_revision_conflicts(self):
        w = F.world()
        r0 = w["registry"].revision
        w["registry"].register(F.record("a"), actor="operator", expected_revision=r0)
        with self.assertRaises(RegistryError) as cm:
            w["registry"].register(F.record("b"), actor="operator", expected_revision=r0)
        self.assertEqual(cm.exception.code, R.REGISTRY_CONFLICT)

    def test_racing_writers_exactly_one_wins(self):
        for _ in range(20):
            w = F.world()
            reg, rev, wins, conflicts = w["registry"], w["registry"].revision, [], []
            barrier = threading.Barrier(16)

            def go(i):
                barrier.wait()
                try:
                    reg.register(F.record(f"r{i}"), actor="operator", expected_revision=rev)
                    wins.append(i)
                except RegistryError as exc:
                    conflicts.append(exc.code)
            ts = [threading.Thread(target=go, args=(i,)) for i in range(16)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
            self.assertEqual(len(wins), 1)
            self.assertEqual(set(conflicts), {R.REGISTRY_CONFLICT})
            self.assertEqual(reg.revision, rev + 1)

    def test_retry_loop_converges(self):
        w = F.world()
        reg = w["registry"]

        def add(i):
            while True:
                try:
                    reg.register(F.record(f"x{i}"), actor="operator", expected_revision=reg.revision)
                    return
                except RegistryError as exc:
                    self.assertEqual(exc.code, R.REGISTRY_CONFLICT)
        ts = [threading.Thread(target=add, args=(i,)) for i in range(12)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(len(reg.entries), 4 + 12)
        self.assertEqual([h["revision"] for h in reg.history], list(range(1, reg.revision + 1)))

    def test_emergency_disable_never_loses_a_race(self):
        w = F.world()
        reg = w["registry"]
        stop = threading.Event()

        def churn():
            i = 0
            while not stop.is_set():
                try:
                    reg.register(F.record(f"c{i}"), actor="operator", expected_revision=reg.revision)
                except RegistryError:
                    pass
                i += 1
        t = threading.Thread(target=churn)
        t.start()
        reg.emergency_disable(REF, actor="operator", reason="race")
        stop.set()
        t.join()
        self.assertEqual(reg.get(REF).lifecycle, "disabled")

    def test_concurrent_selection_while_mutating(self):
        w = F.world()
        errors = []

        def sel():
            for _ in range(50):
                try:
                    w["selector"].select(F.request(), now=F.NOW)
                except Exception as exc:  # noqa: BLE001
                    if getattr(exc, "code", None) not in (R.NO_SUITABLE_TOOLCHAIN,):
                        errors.append(exc)

        def mut():
            for i in range(30):
                w["registry"].register(F.record(f"m{i}", languages=("ocaml",)), actor="operator",
                                       expected_revision=w["registry"].revision)
        ts = [threading.Thread(target=sel) for _ in range(4)] + [threading.Thread(target=mut)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(errors, [])


class IntegrityAndPersistence(unittest.TestCase):                             # MC-028, MC-030, MC-067
    def test_snapshot_roundtrip(self):
        w = F.world()
        snap = w["registry"].snapshot()
        fresh = Registry(w["ring"])
        fresh.load(snap)
        self.assertEqual(fresh.digest, w["registry"].digest)
        self.assertEqual(fresh.entries, w["registry"].entries)

    def test_tamper_wrong_key_unsigned(self):
        w = F.world()
        snap = w["registry"].snapshot()
        t1 = json.loads(json.dumps(snap))
        t1["entries"][0]["languages"].append("cobol")
        t2 = dict(snap)
        t2.pop("signature")
        for bad in (t1, t2):
            with self.subTest(), self.assertRaises(RegistryError) as cm:
                verify_snapshot(w["ring"], bad)
            self.assertEqual(cm.exception.code, R.REGISTRY_INTEGRITY)
        with self.assertRaises(RegistryError):
            verify_snapshot(KeyRing.ephemeral(), snap)

    def test_key_purpose_separation(self):
        w = F.world()
        body = {k: v for k, v in w["registry"].snapshot().items() if k != "signature"}
        forged = {**body, "signature": w["ring"].sign("advisory", body)}
        with self.assertRaises(RegistryError):
            verify_snapshot(w["ring"], forged)

    def test_rollback_attack_refused(self):
        w = F.world()
        old = w["registry"].snapshot()
        w["registry"].register(F.record("new"), actor="operator", expected_revision=w["registry"].revision)
        with self.assertRaises(RegistryError) as cm:
            w["registry"].load(old)
        self.assertEqual(cm.exception.code, R.REGISTRY_INTEGRITY)

    def test_chain_break_refused(self):
        w = F.world(records=F.standard_records()[::-1])   # same entries, different history -> different head
        other = F.world()
        other["registry"].register(F.record("z"), actor="operator", expected_revision=other["registry"].revision)
        # other's r5 does not chain onto w's r4 head (different history) - but signed by a different ring
        body = {k: v for k, v in other["registry"].snapshot().items() if k != "signature"}
        forged = {**body, "signature": w["ring"].sign("registry", body)}
        with self.assertRaises(RegistryError) as cm:
            w["registry"].load(forged)
        self.assertEqual(cm.exception.code, R.REGISTRY_INTEGRITY)

    def test_filestore_atomic_idempotent_and_conflicting(self):
        w = F.world()
        with tempfile.TemporaryDirectory() as d:
            fs = FileStore(d)
            snap = w["registry"].snapshot()
            p = fs.save(snap)
            self.assertEqual(fs.save(snap), p)                          # idempotent
            other = dict(snap, history=[])
            with self.assertRaises(RegistryError):
                fs.save(other)                                          # same revision, different content
            self.assertFalse(list(fs.dir.glob("*.tmp")))

    def test_backup_restore_reconstruct(self):
        w = F.world()
        with tempfile.TemporaryDirectory() as d:
            fs = FileStore(d)
            revs = []
            for i in range(3):
                w["registry"].register(F.record(f"b{i}"), actor="operator", expected_revision=w["registry"].revision)
                fs.save(w["registry"].snapshot())
                revs.append(w["registry"].revision)
            # corrupt newest two in two different ways
            fs.path(revs[2]).write_text("{not json")
            p = fs.path(revs[1])
            p.write_text(p.read_text().replace('"b1"', '"bX"'))
            snap, problems = fs.reconstruct(w["ring"])
            self.assertEqual(snap["revision"], revs[0])
            self.assertEqual(len(problems), 2)
            restored = Registry(w["ring"])
            restored.load(snap)
            self.assertEqual(len(restored.entries), 5)

    def test_reconstruct_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(FileStore(d).reconstruct(KeyRing.ephemeral()), (None, []))


class RollbackAndDisable(unittest.TestCase):                                   # MC-069, MC-070
    def test_rollback_republishes_old_state_as_new_revision(self):
        w = F.world()
        reg = w["registry"]
        good = reg.revision
        reg.update(reg.get(REF).replace(languages=["ocaml"]), actor="operator", expected_revision=reg.revision)
        refusal(lambda: w["selector"].select(F.request(), now=F.NOW))
        reg.rollback(good, actor="operator", expected_revision=reg.revision, reason="bad update")
        self.assertEqual(reg.revision, good + 2)
        self.assertEqual(reg.history[-1]["op"], "rollback")
        self.assertEqual(w["selector"].select(F.request(), now=F.NOW).toolchain, "rumprun")

    def test_rollback_unknown_revision(self):
        w = F.world()
        with self.assertRaises(RegistryError):
            w["registry"].rollback(999, actor="operator", expected_revision=w["registry"].revision, reason="x")

    def test_emergency_disable_idempotent_and_reversible(self):
        w = F.world()
        reg = w["registry"]
        r1 = reg.emergency_disable(REF, actor="operator", reason="CVE")
        self.assertEqual(reg.emergency_disable(REF, actor="operator", reason="again"), r1)
        _, ref = refusal(lambda: w["selector"].select(F.request(), now=F.NOW))
        self.assertIn(R.DISABLED.value, ref.unmet)
        reg.transition(REF, "active", actor="operator", expected_revision=reg.revision, reason="patched")
        self.assertEqual(w["selector"].select(F.request(), now=F.NOW).toolchain, "rumprun")

    def test_disable_retired_refused(self):
        w = F.world(records=[F.record("t", lifecycle="candidate")])
        reg = w["registry"]
        reg.transition("t@1.0.0-fixture", "retired", actor="operator", expected_revision=reg.revision, reason="x")
        with self.assertRaises(RegistryError):
            reg.emergency_disable("t@1.0.0-fixture", actor="operator", reason="x")


if __name__ == "__main__":
    unittest.main()
