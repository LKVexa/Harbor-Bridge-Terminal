"""Items 16, 17, 19, 23, 25, 27: provenance records, atomic activation/rollback, audit,
telemetry, concurrency and emergency disable (C036-C038, C049, C071-C080, C086, C092)."""
import json
import os
import tempfile
import threading
import unittest

from _support import ALL, model, Clock, audit, authz, errors, schema, schemavalidate, spec, store, token, verifier

ACT = schema("PK_DEVICE_CONFIG_ACTIVATION_1.schema.json")
EVT = schema("PK_DEVICE_AUDIT_EVENT_1.schema.json")


def mkstore(**kw):
    v = verifier(Clock())
    return store.CatalogueStore("prod", v, source_revision="test-rev", mutation_burst=10_000, **kw), v


def cycle(s, v, op, sp, *, proposer="alice", approver="bob"):
    c = s.propose(token(v, proposer, ALL), op, sp)
    s.approve(token(v, approver, ["catalogue.approve"]), c["candidate"])
    return s.activate(token(v, proposer, ALL), c["candidate"], expected_digest=c["base"])


class ActivationTest(unittest.TestCase):
    def test_full_cycle_emits_valid_record_and_audit(self):
        s, v = mkstore()
        g = s.active.digest
        rec = cycle(s, v, "register", spec())
        self.assertEqual(schemavalidate.validate(rec, ACT), [])
        self.assertEqual(rec["previous_digest"], g)
        self.assertEqual(rec["digest"], s.active.digest)
        self.assertEqual(rec["approvers"], ["bob"])
        self.assertTrue(s.permits("virtio-net"))
        for ev in s.audit.events:
            self.assertEqual(schemavalidate.validate(ev, EVT), [], ev["event_type"])
        self.assertEqual(audit.AuditLog.verify_chain(s.audit.events), len(s.audit.events))
        self.assertIn("why", s.explain(rec["activation_id"]))

    def test_proposal_does_not_change_active(self):
        s, v = mkstore()
        g = s.active.digest
        s.propose(token(v, "alice", ALL), "register", spec())
        self.assertEqual(s.active.digest, g)
        self.assertFalse(s.permits("virtio-net"))

    def test_separation_of_duties(self):
        s, v = mkstore()
        c = s.propose(token(v, "alice", ALL), "register", spec())
        with self.assertRaises(authz.Unauthorized):
            s.activate(token(v, "alice", ALL), c["candidate"], expected_digest=c["base"])  # unapproved
        with self.assertRaises(authz.Unauthorized):
            s.approve(token(v, "alice", ["catalogue.approve"]), c["candidate"])  # self-approval

    def test_widening_requires_widen_capability(self):
        s, v = mkstore()
        cycle(s, v, "register", spec())
        narrow = [c for c in ALL if c != "catalogue.widen"]
        with self.assertRaises(authz.Unauthorized):
            s.propose(token(v, "alice", narrow), "replace", spec(version="1.1", regs=("status", "feat")))
        rec = cycle(s, v, "replace", spec(version="1.1", regs=("status", "feat")))
        self.assertTrue(rec["surface_diff"]["widened"])
        self.assertEqual(s.signals()["surface_growth"], 1)
        self.assertIn("surface.widened", [e["event_type"] for e in s.audit.events])

    def test_digest_semantics(self):
        s1, v1 = mkstore()
        s2, v2 = mkstore()
        cycle(s1, v1, "register", spec(regs=("b", "a")))
        cycle(s2, v2, "register", spec(regs=("a", "b")))
        self.assertEqual(s1.active.digest, s2.active.digest)  # canonical
        s3, v3 = mkstore()
        cycle(s3, v3, "register", spec(regs=("a", "c")))
        self.assertNotEqual(s1.active.digest, s3.active.digest)

    def test_failed_validation_emits_no_success(self):
        s, v = mkstore()
        with self.assertRaises(errors.Inv25Error):
            s.propose(token(v, "alice", ALL), "register",
                      model.DeviceSpec("x", "host-passthrough", "1.0", frozenset(), "r", "s"))
        self.assertEqual(s.history(), [])
        self.assertEqual([e["event_type"] for e in s.audit.events], ["forbidden_class.attempt"])

    def test_cas_prevents_lost_update(self):
        s, v = mkstore()
        c1 = s.propose(token(v, "alice", ALL), "register", spec(name="a"))
        c2 = s.propose(token(v, "alice", ALL), "register", spec(name="b"))
        for c in (c1, c2):
            s.approve(token(v, "bob", ["catalogue.approve"]), c["candidate"])
        s.activate(token(v, "alice", ALL), c1["candidate"], expected_digest=c1["base"])
        with self.assertRaises(store.ConcurrentModification):
            s.activate(token(v, "alice", ALL), c2["candidate"], expected_digest=c2["base"])
        self.assertTrue(s.permits("a"))
        self.assertFalse(s.permits("b"))

    def test_idempotent_activation_replay(self):
        s, v = mkstore()
        c = s.propose(token(v, "alice", ALL), "register", spec())
        s.approve(token(v, "bob", ["catalogue.approve"]), c["candidate"])
        r1 = s.activate(token(v, "alice", ALL), c["candidate"], expected_digest=c["base"])
        r2 = s.activate(token(v, "alice", ALL), c["candidate"], expected_digest=c["base"])
        self.assertEqual(r1, r2)
        self.assertEqual(len(s.history()), 1)

    def test_rollback_restores_exact_digest(self):
        s, v = mkstore()
        r1 = cycle(s, v, "register", spec())
        good = s.active.digest
        cycle(s, v, "replace", spec(version="1.1", regs=("status", "x")))
        rb = s.rollback(token(v, "alice", ALL), r1["digest"], expected_digest=s.active.digest, reason="bad canary")
        self.assertEqual(s.active.digest, good)
        self.assertEqual(rb["kind"], "rollback")
        self.assertEqual(schemavalidate.validate(rb, ACT), [])
        with self.assertRaises(errors.Inv25Error):
            s.rollback(token(v, "alice", ALL), "sha256:" + "f" * 64, expected_digest=s.active.digest, reason="x")

    def test_rollback_requires_capability(self):
        s, v = mkstore()
        r1 = cycle(s, v, "register", spec())
        with self.assertRaises(authz.Unauthorized):
            s.rollback(token(v, "eve", ["catalogue.activate"]), r1["previous_digest"],
                       expected_digest=s.active.digest, reason="x")

    def test_emergency_disable(self):
        s, v = mkstore()
        cycle(s, v, "register", spec())
        with self.assertRaises(authz.Unauthorized):
            s.emergency_disable(token(v, "op", ["catalogue.emergency_disable"]), "virtio-net",
                                reason="cve", incident_id="INC-1", expires="2026-10-01T00:00:00Z")
        digest = s.active.digest
        s.emergency_disable(token(v, "op", ["catalogue.emergency_disable"], bg=True), "virtio-net",
                            reason="cve", incident_id="INC-1", expires="2026-10-01T00:00:00Z")
        self.assertFalse(s.permits("virtio-net"))
        self.assertEqual(s.active.digest, digest)          # evidence and catalogue untouched
        self.assertEqual(len(s.history()), 1)
        s.restore_device(token(v, "op", ALL), "virtio-net")
        self.assertTrue(s.permits("virtio-net"))

    def test_health_and_signals(self):
        s, v = mkstore(dependency_probe=lambda: {"policy-engine": True})
        cycle(s, v, "register", spec(regs=("a", "b")))
        h = s.health()
        self.assertTrue(h["ready"])
        self.assertEqual(h["active_digest"], s.active.digest)
        sig = s.signals()
        self.assertEqual((sig["catalogue_size"], sig["surface_registers"], sig["unreviewed_entries"]), (1, 2, 0))
        s2, _ = mkstore(dependency_probe=lambda: {"policy-engine": False})
        self.assertFalse(s2.health()["ready"])

    def test_authn_failure_audited_and_counted(self):
        s, v = mkstore()
        with self.assertRaises(authz.Unauthenticated):
            s.propose("junk", "register", spec())
        self.assertEqual(s.signals()["authn_denied"], 1)
        self.assertEqual(s.signals()["errors_by_code"], {"INV25_UNAUTHENTICATED": 1})

    def test_rate_limit(self):
        v = verifier(Clock())
        s = store.CatalogueStore("prod", v, mutation_rate=0.0, mutation_burst=2)
        s.propose(token(v, "a", ALL), "register", spec(name="x1"))
        s.propose(token(v, "a", ALL), "register", spec(name="x2"))
        with self.assertRaises(store.RateLimited):
            s.propose(token(v, "a", ALL), "register", spec(name="x3"))


class PersistenceAndFaultTest(unittest.TestCase):
    def test_restart_restores_state(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "state.json")
            v = verifier(Clock())
            s = store.CatalogueStore("prod", v, state_path=p, mutation_burst=100)
            cycle(s, v, "register", spec())
            s2 = store.CatalogueStore("prod", v, state_path=p)
            self.assertEqual(s2.active.digest, s.active.digest)
            self.assertTrue(s2.permits("virtio-net"))

    def test_tampered_state_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "state.json")
            v = verifier(Clock())
            s = store.CatalogueStore("prod", v, state_path=p, mutation_burst=100)
            cycle(s, v, "register", spec())
            with open(p) as fh:
                st = json.load(fh)
            st["docs"][st["active"]]["devices"][0]["registers"].append("smuggled")
            with open(p, "w") as fh:
                json.dump(st, fh)
            with self.assertRaises(errors.Inv25Error):
                store.CatalogueStore("prod", v, state_path=p)

    def test_crash_points_leave_old_state(self):
        for point in ("before_audit", "before_persist", "before_rename"):
            with self.subTest(point), tempfile.TemporaryDirectory() as d:
                p = os.path.join(d, "state.json")
                armed = {"on": False}

                def fault(pt, point=point):
                    if armed["on"] and pt == point:
                        raise OSError(f"injected crash at {pt}")
                v = verifier(Clock())
                s = store.CatalogueStore("prod", v, state_path=p, mutation_burst=100, fault=fault)
                cycle(s, v, "register", spec())
                before = s.active.digest
                armed["on"] = True
                with self.assertRaises(OSError):
                    cycle(s, v, "register", spec(name="b"))
                self.assertEqual(s.active.digest, before)
                self.assertFalse(s.permits("b"))
                self.assertEqual([f for f in os.listdir(d) if f.startswith(".inv25")], [])
                if os.path.exists(p):  # durable state is one complete committed state
                    s2 = store.CatalogueStore("prod", v, state_path=p)
                    self.assertEqual(s2.active.digest, before)
                    self.assertFalse(s2.permits("b"))
                if point != "before_audit":
                    self.assertEqual(s.audit.events[-1]["event_type"], "config.activation_failed")

    def test_audit_sink_down_blocks_mutation(self):
        s, v = mkstore()
        c = s.propose(token(v, "alice", ALL), "register", spec())
        s.approve(token(v, "bob", ["catalogue.approve"]), c["candidate"])
        s.audit.fail = True
        with self.assertRaises(audit.AuditUnavailable):
            s.activate(token(v, "alice", ALL), c["candidate"], expected_digest=c["base"])
        self.assertFalse(s.permits("virtio-net"))
        self.assertFalse(s.health()["ready"])

    def test_dependency_down_blocks_activation(self):
        s, v = mkstore(dependency_probe=lambda: {"policy-engine": False})
        c = s.propose(token(v, "alice", ALL), "register", spec())
        s.approve(token(v, "bob", ["catalogue.approve"]), c["candidate"])
        with self.assertRaises(store.DependencyUnavailable):
            s.activate(token(v, "alice", ALL), c["candidate"], expected_digest=c["base"])
        self.assertEqual(s.history(), [])


class ConcurrencyTest(unittest.TestCase):
    def test_concurrent_activations_one_winner_per_base(self):
        s, v = mkstore()
        cands = []
        for i in range(16):
            c = s.propose(token(v, "alice", ALL), "register", spec(name=f"d{i}"))
            s.approve(token(v, "bob", ["catalogue.approve"]), c["candidate"])
            cands.append((c, token(v, "alice", ALL)))
        wins, conflicts, lock = [], [], threading.Lock()

        def go(c, t):
            try:
                s.activate(t, c["candidate"], expected_digest=c["base"])
                with lock:
                    wins.append(c)
            except store.ConcurrentModification:
                with lock:
                    conflicts.append(c)
        ts = [threading.Thread(target=go, args=a) for a in cands]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(wins), 1)
        self.assertEqual(len(conflicts), 15)
        self.assertEqual(len(s.history()), 1)

    def test_readers_never_see_partial_state(self):
        s, v = mkstore()
        stop = threading.Event()
        bad = []

        def reader():
            while not stop.is_set():
                snap = s.active
                n = len(snap.document["devices"])
                if n not in (0, 1, 2, 3, 4, 5, 6, 7, 8):
                    bad.append(n)
                snap.catalogue()  # complete, valid document every time
        r = threading.Thread(target=reader)
        r.start()
        for i in range(8):
            cycle(s, v, "register", spec(name=f"d{i}"))
        stop.set()
        r.join()
        self.assertEqual(bad, [])

    def test_concurrent_replay_single_nonce_wins(self):
        v = verifier(Clock())
        t = token(v, "a", ["catalogue.read"])
        ok, lock = [], threading.Lock()

        def go():
            try:
                v.verify(t)
                with lock:
                    ok.append(1)
            except authz.ReplayDetected:
                pass
        ts = [threading.Thread(target=go) for _ in range(20)]
        [x.start() for x in ts]
        [x.join() for x in ts]
        self.assertEqual(len(ok), 1)


class AuditTamperTest(unittest.TestCase):
    def test_detects_edit_delete_insert_reorder(self):
        log = audit.AuditLog()
        for i in range(5):
            log.emit("registration.accepted", actor="a", result="ok", device=f"d{i}")
        evs = log.events
        edited = [dict(e) for e in evs]
        edited[2]["actor"] = "mallory"
        for name, bad in (("edit", edited), ("delete", evs[:2] + evs[3:]),
                          ("insert", evs[:2] + [evs[1]] + evs[2:]), ("reorder", [evs[1], evs[0]] + evs[2:])):
            with self.subTest(name), self.assertRaises(audit.AuditTampered):
                audit.AuditLog.verify_chain(bad)

    def test_file_sink_and_secret_fields_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "audit.jsonl")
            log = audit.AuditLog(p)
            log.emit("authn.failure", actor="x", result="denied")
            log.emit("authz.denied", actor="x", result="denied")
            self.assertEqual(audit.AuditLog.verify_file(p), 2)
            with self.assertRaises(ValueError):
                log.emit("authn.failure", actor="x", result="d", token="abc")


if __name__ == "__main__":
    unittest.main()
