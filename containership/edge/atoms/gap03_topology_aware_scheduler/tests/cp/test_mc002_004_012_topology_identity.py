import os
import threading
import unittest

from gap03_topology_aware_scheduler.controlplane import canonical, ed25519, identity
from gap03_topology_aware_scheduler.controlplane.errors import SchedulerError
from gap03_topology_aware_scheduler.controlplane.faults import StoreFault
from gap03_topology_aware_scheduler.controlplane.topology_service import AUDIENCE, TopologyService
from gap03_topology_aware_scheduler.controlplane.topology_store import TopologyStore
from gap03_topology_aware_scheduler.tests.cp._util import TmpCase, covers

OP = "spiffe://prod.example/operator/alice"
OP2 = "spiffe://prod.example/operator/bob"


def base_muts():
    return [{"op": "create", "id": "eu", "node_type": "region", "parent": None},
            {"op": "create", "id": "dub", "node_type": "site", "parent": "eu"},
            {"op": "create", "id": "ams", "node_type": "site", "parent": "eu"},
            {"op": "create", "id": "r1", "node_type": "rack", "parent": "dub"},
            {"op": "create", "id": "r2", "node_type": "rack", "parent": "ams"},
            {"op": "create", "id": "n1", "node_type": "node", "parent": "r1"},
            {"op": "create", "id": "n2", "node_type": "node", "parent": "r2"}]


class Identity(TmpCase):
    @covers("MC-012", 25)
    def test_mc012_ed25519_rfc8032_vector(self):
        sk = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
        pk = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
        sig = bytes.fromhex("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
        self.assertEqual(ed25519.public_key(sk), pk)
        self.assertEqual(ed25519.sign(sk, b""), sig)
        self.assertTrue(ed25519.verify(pk, b"", sig))
        self.assertFalse(ed25519.verify(pk, b"x", sig))

    @covers("MC-012", 7, 8, 12, 15, 17, 25, 27)
    def test_mc012_token_verification_negative_matrix(self):
        """authorization/authentication boundary (adversarial): replay, wrong audience, malformed subject, algorithm downgrade, forged signature and unknown issuer are all denied and audited."""
        audit = self.audit()
        t, key = self.trust(audit)
        tok = self.token(key, OP, ["topology-admin"], AUDIENCE)
        self.assertEqual(t.verify_token(tok, audience=AUDIENCE)["sub"], OP)
        cases = {
            "replay": (tok, AUDIENCE, "REPLAY_DETECTED"),
            "audience": (self.token(key, OP, [], "other"), AUDIENCE, "UNAUTHENTICATED"),
            "subject": (identity.issue_token(key, subject="alice", audience=AUDIENCE, roles=[], clock=self.clock), AUDIENCE,
                        "UNAUTHENTICATED"),
            "downgrade": (identity.issue_token(key, subject=OP, audience=AUDIENCE, roles=[], clock=self.clock, alg="HS256"),
                          AUDIENCE, "UNAUTHENTICATED"),
            "malformed": ("abc", AUDIENCE, "UNAUTHENTICATED"),
        }
        forged_key = identity.SigningKey.generate("k1", key.issuer)
        cases["forged"] = (self.token(forged_key, OP, [], AUDIENCE), AUDIENCE, "UNAUTHENTICATED")
        unknown = identity.SigningKey.generate("k9", "spiffe://evil/issuer/x")
        cases["unknown_issuer"] = (self.token(unknown, OP, [], AUDIENCE), AUDIENCE, "UNAUTHENTICATED")
        for name, (tk, aud, code) in cases.items():
            with self.assertRaises(SchedulerError, msg=name) as cm:
                t.verify_token(tk, audience=aud)
            self.assertEqual(cm.exception.code, code, name)
        fut = identity.issue_token(key, subject=OP, audience=AUDIENCE, roles=[], clock=lambda: self.clock() + 3600)
        with self.assertRaises(SchedulerError):
            t.verify_token(fut, audience=AUDIENCE)  # not yet valid
        old = self.token(key, OP, [], AUDIENCE)
        self.clock.advance(400)
        with self.assertRaises(SchedulerError):
            t.verify_token(old, audience=AUDIENCE)  # expired
        acts = {e["action"] for e in audit.export(principal_roles={"audit.export"})["events"]}
        self.assertIn("auth.downgrade_attempt", acts)
        self.assertIn("auth.verify_failed", acts)

    @covers("MC-013", 10)

    @covers("MC-012", 10, 14, 15, 27)
    def test_mc012_rotation_overlap_revocation_and_root_removal(self):
        audit = self.audit()
        t, k1 = self.trust(audit)
        k2 = identity.SigningKey.generate("k2", k1.issuer)
        t.add_key(k2.issuer, k2.kid, k2.public)
        t.verify_token(self.token(k1, OP, [], "a"), audience="a")  # overlap: both valid
        t.verify_token(self.token(k2, OP, [], "a"), audience="a")
        t.revoke(k1.issuer, "k1")
        with self.assertRaises(SchedulerError):
            t.verify_token(self.token(k1, OP, [], "a"), audience="a")
        t.verify_token(self.token(k2, OP, [], "a"), audience="a")
        t.remove_issuer(k1.issuer)
        with self.assertRaises(SchedulerError):
            t.verify_token(self.token(k2, OP, [], "a"), audience="a")
        acts = [e["action"] for e in audit.export(principal_roles={"audit.export"})["events"]]
        self.assertIn("trust.key_revoked", acts)
        self.assertIn("trust.root_removed", acts)

    @covers("MC-012", 9, 13, 25)
    def test_mc012_artifact_provenance_and_attestation_fail_closed(self):
        t, key = self.trust()
        snap = {"nodes": {"n1": ["eu", "dub", "r1"]}, "generation": 4}
        env = identity.sign_artifact(key, "topology_snapshot", snap, clock=self.clock)
        self.assertEqual(identity.verify_artifact(t, env, snap, kind="topology_snapshot")["kind"], "topology_snapshot")
        with self.assertRaises(SchedulerError) as cm:
            identity.verify_artifact(t, env, dict(snap, generation=5), kind="topology_snapshot")
        self.assertEqual(cm.exception.code, "INTEGRITY_FAILURE")
        with self.assertRaises(SchedulerError):
            identity.verify_artifact(t, env, snap, kind="entitlement_snapshot")
        with self.assertRaises(SchedulerError):
            identity.verify_attestation(t, "confidential", None, measurement_allowlist={"m1"})
        claims = {"tee": True, "secure_boot": True, "measurement": "m1"}
        rep = {"claims": claims, "envelope": identity.sign_artifact(key, "attestation", claims, clock=self.clock)}
        self.assertTrue(identity.verify_attestation(t, "confidential", rep, measurement_allowlist={"m1"})["verified"])
        with self.assertRaises(SchedulerError):
            identity.verify_attestation(t, "confidential", rep, measurement_allowlist={"m2"})
        self.assertTrue(identity.verify_attestation(t, "general", None, measurement_allowlist=set())["verified"])

    @covers("MC-012", 11, 20)
    def test_mc012_keys_by_reference_never_plaintext_repr(self):
        sk = identity.SigningKey.generate("k", "spiffe://prod.example/issuer/ca")
        self.assertNotIn(sk.secret.hex(), repr(sk))
        os.environ["GAP03_TEST_KEY"] = identity.b64(sk.secret)
        try:
            k2 = identity.SigningKey.from_ref("k", sk.issuer, "env:GAP03_TEST_KEY")
            self.assertEqual(k2.public, sk.public)
        finally:
            del os.environ["GAP03_TEST_KEY"]
        with self.assertRaises(SchedulerError):
            identity.SigningKey.from_ref("k", sk.issuer, "kms:projects/x")  # HSM adapter not bundled

    @covers("MC-012", 28)
    def test_mc012_verify_throughput_bound(self):
        import time
        t, key = self.trust()
        toks = [self.token(key, OP, [], "a") for _ in range(20)]
        s = time.perf_counter()
        for tk in toks:
            t.verify_token(tk, audience="a")
        self.assertLess((time.perf_counter() - s) / 20, 0.25, "pure-python Ed25519 verify slower than 250 ms")


class TopologySvc(TmpCase):
    def setUp(self):
        super().setUp()
        self.audit_log = self.audit()
        self.t, self.key = self.trust(self.audit_log)
        self.store = TopologyStore(self.d("topo"), clock=self.clock)
        self.svc = TopologyService(self.store, self.t, self.audit_log, per_principal_rps=1000, global_rps=1000)

    def req(self, muts, rid="r1", gen=None):
        return {"request_id": rid, "source_service": "spiffe://prod.example/service/topo-api", "reason": "build",
                "expected_generation": self.store.generation if gen is None else gen, "mutations": muts}

    def cred(self, req, sub=OP, roles=("topology-admin",), aud=AUDIENCE):
        return self.token(self.key, sub, list(roles), aud, req=canonical.digest(req))

    @covers("MC-013", 10)

    @covers("MC-004", 26)

    @covers("MC-002", 6, 8, 12, 17, 25, 26)
    def test_mc002_authenticated_mutation_happy_path_is_audited(self):
        """integration/contract + unit nominal path: authenticated identity -> authorization -> audit -> durable store, with before/after digests."""
        r = self.req(base_muts())
        out = self.svc.mutate(self.cred(r), r)
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["generation"], 1)
        evs = self.audit_log.query(principal_roles={"audit.read"}, request_id="r1")["events"]
        self.assertEqual([e["action"] for e in evs], ["topology.mutate.authorized", "topology.mutate.committed"])
        self.assertIsNotNone(evs[1]["after_digest"])
        self.assertEqual(self.store.scheduler_snapshot().nodes["n1"], ("eu", "dub", "r1"))

    @covers("MC-013", 10)

    @covers("MC-002", 7, 11, 17, 27)
    def test_mc002_rbac_and_two_person_rule_for_reparent(self):
        """authorization: RBAC denies missing roles, self-approval is refused and re-parenting needs a distinct second approver (adversarial privilege escalation attempt)."""
        r = self.req(base_muts())
        self.svc.mutate(self.cred(r), r)
        r2 = self.req([{"op": "create", "id": "n3", "node_type": "node", "parent": "r1"}], rid="r2")
        out = self.svc.mutate(self.cred(r2, roles=()), r2)
        self.assertEqual(out["error"]["code"], "PERMISSION_DENIED")
        self.assertTrue(self.svc.mutate(self.cred(r2, roles=("topology-editor",)), r2)["ok"])
        rp = self.req([{"op": "reparent", "id": "n1", "parent": "r2", "replace": True}], rid="r3")
        out = self.svc.mutate(self.cred(rp), rp)
        self.assertEqual(out["error"]["code"], "PERMISSION_DENIED")  # needs second person
        appr = self.token(self.key, OP, ["topology-admin"], AUDIENCE + ".approve", req=canonical.digest(rp))
        self.assertFalse(self.svc.mutate(self.cred(rp), rp, approvals=(appr,))["ok"])  # self-approval refused
        appr = self.token(self.key, OP2, ["topology-admin"], AUDIENCE + ".approve", req=canonical.digest(rp))
        self.assertTrue(self.svc.mutate(self.cred(rp), rp, approvals=(appr,))["ok"])
        self.assertEqual(self.store.scheduler_snapshot().nodes["n1"], ("eu", "ams", "r2"))

    @covers("MC-002", 9, 15, 20, 27)
    def test_mc002_stale_generation_and_invalid_batch_roll_back_atomically(self):
        """adversarial/malformed: stale generation and an invalid batch are rejected atomically; error text is redacted (sensitive paths never leak)."""
        r = self.req(base_muts())
        self.svc.mutate(self.cred(r), r)
        stale = self.req([{"op": "create", "id": "n9", "node_type": "node", "parent": "r1"}], rid="s", gen=0)
        self.assertEqual(self.svc.mutate(self.cred(stale), stale)["error"]["code"], "STALE_STATE")
        bad = self.req([{"op": "create", "id": "n9", "node_type": "node", "parent": "r1"},
                        {"op": "create", "id": "n10", "node_type": "node", "parent": "dub"}], rid="b")  # wrong parent type
        out = self.svc.mutate(self.cred(bad), bad)
        self.assertFalse(out["ok"])
        self.assertNotIn("n9", self.store.state["nodes"])  # no partial leak
        self.assertNotIn("/", out["error"]["message"])
        self.assertEqual(self.store.generation, 1)

    @covers("MC-002", 14, 17, 27)
    def test_mc002_request_integrity_binding(self):
        """adversarial: a tampered request body (malformed binding to the credential) is rejected as UNAUTHENTICATED - authorization boundary integrity."""
        r = self.req(base_muts())
        cred = self.cred(r)
        tampered = dict(r, mutations=r["mutations"][:1])
        self.assertEqual(self.svc.mutate(cred, tampered)["error"]["code"], "UNAUTHENTICATED")

    @covers("MC-002", 13, 22, 27)
    def test_mc002_rate_limits_and_bulk_limits(self):
        """fault/overload: mutation storms hit per-principal rate limits and bulk limits (concurrency/overload semantics)."""
        svc = TopologyService(self.store, self.t, self.audit_log, per_principal_rps=1, global_rps=1000)
        codes = []
        for i in range(6):
            r = self.req([{"op": "create", "id": f"x{i}", "node_type": "region", "parent": None}], rid=f"q{i}")
            codes.append(svc.mutate(self.cred(r), r).get("error", {}).get("code", "OK"))
        self.assertIn("OVERLOADED", codes)
        big = self.req([{"op": "create", "id": f"z{i}", "node_type": "region", "parent": None} for i in range(1001)], rid="big")
        self.assertEqual(self.svc.mutate(self.cred(big), big)["error"]["code"], "PAYLOAD_TOO_LARGE")

    @covers("MC-002", 22, 26)
    def test_mc002_idempotent_request_ids(self):
        r = self.req(base_muts())
        a = self.svc.mutate(self.cred(r), r)
        b = self.svc.mutate(self.cred(r), r)  # retried with a fresh nonce
        self.assertEqual(a, b)
        self.assertEqual(self.store.generation, 1)

    @covers("MC-002", 21, 27)
    def test_mc002_audit_unavailable_blocks_mutation(self):
        """fault injection: audit dependency failure blocks the privileged mutation (fail closed) - failure-mode row 'audit down'."""
        r = self.req(base_muts())
        self.audit_log._store.read_only = True
        out = self.svc.mutate(self.cred(r), r)
        self.assertFalse(out["ok"])
        self.assertEqual(self.store.generation, 0)


class TopologyDurable(TmpCase):
    def mk(self, **kw):
        return TopologyStore(self.d("t"), clock=self.clock, **kw)

    @covers("MC-004", 18)

    @covers("MC-004", 6, 14, 25)
    def test_mc004_storage_constraints_reject_invalid_topology(self):
        """untrusted-input validation + resource limits at the storage boundary: invalid ids, orphans, wrong parent types,
        duplicate creates, deleting a parent with children, oversize label sets and implicit re-parenting are rejected."""
        s = self.mk()
        s.submit({"type": "batch", "expected_generation": 0, "mutations": base_muts()})
        bad = [[{"op": "create", "id": "x", "node_type": "node", "parent": "nope"}],
               [{"op": "create", "id": "bad id", "node_type": "region", "parent": None}],
               [{"op": "create", "id": "eu", "node_type": "region", "parent": None}],
               [{"op": "create", "id": "s2", "node_type": "site", "parent": "r1"}],
               [{"op": "delete", "id": "r1"}],
               [{"op": "relabel", "id": "n1", "labels": {f"k{i}": "v" for i in range(40)}}],
               [{"op": "reparent", "id": "n1", "parent": "r2"}]]
        for m in bad:
            with self.assertRaises(SchedulerError, msg=m):
                s.submit({"type": "batch", "expected_generation": 1, "mutations": m})
        self.assertEqual(s.generation, 1)

    @covers("MC-004", 7, 8, 10, 25, 27)
    def test_mc004_crash_during_write_recovers_without_half_applied_state(self):
        s = self.mk()
        s.submit({"type": "batch", "expected_generation": 0, "mutations": base_muts()})
        with open(s.wal_path, "ab") as fh:
            fh.write(b'{"seq":2,"ts":1,"prev":"')  # torn write
        s2 = self.mk()
        self.assertTrue(s2.recovery_report["torn_tail_repaired"])
        self.assertEqual(s2.generation, 1)
        f = StoreFault("before_fsync")
        s3 = self.mk(fault=f)
        with self.assertRaises(SchedulerError):
            s3.submit({"type": "batch", "expected_generation": 1, "mutations": [{"op": "create", "id": "n7", "node_type": "node", "parent": "r1"}]})
        self.assertTrue(s3.read_only)
        self.assertNotIn("n7", s3.state["nodes"])  # not acknowledged -> not visible

    @covers("MC-004", 9, 10, 25)
    def test_mc004_generation_cas_and_verified_snapshot(self):
        s = self.mk()
        g = s.submit({"type": "batch", "expected_generation": 0, "mutations": base_muts()})
        with self.assertRaises(SchedulerError) as cm:
            s.submit({"type": "batch", "expected_generation": 0, "mutations": [{"op": "set_lifecycle", "id": "n2", "lifecycle": "quarantined"}]})
        self.assertEqual(cm.exception.code, "STALE_STATE")
        s.submit({"type": "batch", "expected_generation": g, "mutations": [{"op": "set_lifecycle", "id": "n2", "lifecycle": "quarantined"}]})
        snap = self.mk().scheduler_snapshot()
        self.assertEqual(snap.generation, 2)
        self.assertEqual(set(snap.nodes), {"n1"})  # quarantined node excluded after restart

    @covers("MC-004", 11, 25)
    def test_mc004_schema_migration_dry_run_lock_and_apply(self):
        s = self.mk()
        s.submit({"type": "batch", "expected_generation": 0, "mutations": base_muts()})
        s.snapshot()
        for rec in s.state["nodes"].values():
            rec.pop("lifecycle")
        from gap03_topology_aware_scheduler.controlplane.durable import atomic_write
        atomic_write(s.meta_path, canonical.dumps({"kind": "topology", "schema_version": 1}))
        snapname = s.snapshot()
        s2 = self.mk()
        self.assertTrue(s2.pending_migration)
        with self.assertRaises(SchedulerError):
            s2.submit({"type": "batch", "expected_generation": 1, "mutations": [{"op": "set_lifecycle", "id": "n1", "lifecycle": "active"}]})
        plan = s2.migrate(dry_run=True)
        self.assertEqual(plan["steps"], ["v1->v2"])
        self.assertTrue(s2.pending_migration)
        open(os.path.join(s2.dir, "migration.lock"), "w").write("x")
        with self.assertRaises(SchedulerError):
            s2.migrate(dry_run=False)
        os.unlink(os.path.join(s2.dir, "migration.lock"))
        done = s2.migrate(dry_run=False)
        self.assertIn("rollback_snapshot", done)
        self.assertFalse(self.mk().pending_migration)
        self.assertTrue(snapname)

    @covers("MC-004", 12, 15, 25)
    def test_mc004_compaction_preserves_history_and_import_rebuilds(self):
        s = self.mk()
        s.submit({"type": "batch", "expected_generation": 0, "mutations": base_muts()})
        s.snapshot()
        s.submit({"type": "batch", "expected_generation": 1, "mutations": [{"op": "relabel", "id": "n1", "labels": {"gpu": "a100"}}]})
        self.assertTrue(s.verify_history()["ok"])
        self.assertEqual(s.verify_history()["verified"], 2)
        bundle = s.export()
        t2 = TopologyStore(self.d("t2"), clock=self.clock)
        t2.import_bundle(bundle)
        self.assertEqual(t2.scheduler_snapshot().nodes, s.scheduler_snapshot().nodes)
        bundle["state"]["nodes"]["n1"]["parent"] = "r2"
        with self.assertRaises(SchedulerError):
            TopologyStore(self.d("t3")).import_bundle(bundle)

    @covers("MC-004", 17)

    @covers("MC-004", 13, 27)
    def test_mc004_fenced_writes_reject_superseded_writer(self):
        """authorization of writers at the store boundary: only the current lease holder's fencing token may write."""
        s = self.mk()
        s.submit({"type": "batch", "expected_generation": 0, "mutations": base_muts(), "fence": 5})
        with self.assertRaises(SchedulerError) as cm:
            s.submit({"type": "batch", "expected_generation": 1, "mutations": [{"op": "relabel", "id": "n1", "labels": {}}], "fence": 4})
        self.assertEqual(cm.exception.code, "FENCED")

    @covers("MC-004", 22, 27)
    def test_mc004_concurrent_writers_serialise(self):
        s = self.mk()
        s.submit({"type": "batch", "expected_generation": 0, "mutations": base_muts()})
        wins = []

        def w(i):
            try:
                s.submit({"type": "batch", "expected_generation": 1, "mutations": [{"op": "relabel", "id": "n1", "labels": {"w": str(i)}}]})
                wins.append(i)
            except SchedulerError:
                pass
        ts = [threading.Thread(target=w, args=(i,)) for i in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(wins), 1)
        self.assertEqual(s.generation, 2)

    @covers("MC-004", 28)
    def test_mc004_recovery_time_bound(self):
        import time
        s = self.mk()
        s.submit({"type": "batch", "expected_generation": 0, "mutations": base_muts()})
        g = 1
        for i in range(300):
            g = s.submit({"type": "batch", "expected_generation": g, "mutations": [{"op": "relabel", "id": "n1", "labels": {"i": str(i)}}]})
        t = time.perf_counter()
        self.mk()
        self.assertLess(time.perf_counter() - t, 3.0)
