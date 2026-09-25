"""Service-level behaviour: semantics, lifecycle, integration, resilience, security."""
import json
import pathlib
import shutil
import tempfile
import unittest

from _support import HOSTS, covers, desired, make_env, mod, req

errors = mod("errors")
store = mod("store")
service = mod("service")
lifecycle = mod("lifecycle")


class SemanticsTest(unittest.TestCase):
    def setUp(self):
        self.env = make_env()

    @covers(11, 12, 14, 30, 82, 83)
    def test_desired_reconcile_converges_and_rests(self):
        r = req(self.env, "set_desired", desired(self.env))
        self.assertEqual(r["outcome"], "SUCCESS", r)
        r = req(self.env, "reconcile", {"tenant": "acme", "component": "api"})
        self.assertEqual((r["outcome"], r["result"]["started"]), ("SUCCESS", 3), r)
        zones = {HOSTS[h] for _, _, h in self.env.lattice.running}
        self.assertEqual(zones, {"z1", "z2", "z3"})
        r = req(self.env, "reconcile", {"tenant": "acme", "component": "api"})
        self.assertEqual((r["result"]["started"], r["result"]["stopped"]), (0, 0))
        self.assertEqual(self.env.svc.lifecycle.get("acme", "api"), lifecycle.State.CONVERGED)

    @covers(14, 26, 56, 60, 83)
    def test_partial_outcome_when_some_starts_fail(self):
        self.env.lattice.fail_hosts.add("h2")
        req(self.env, "set_desired", desired(self.env))
        r = req(self.env, "reconcile", {"tenant": "acme", "component": "api"})
        self.assertEqual(r["outcome"], "PARTIAL", r)
        self.assertEqual(r["result"]["failed"][0]["code"], "INV63-E-DEPENDENCY-UNAVAILABLE")
        self.assertEqual(self.env.svc.lifecycle.get("acme", "api"), lifecycle.State.DEGRADED)

    @covers(14, 26, 22, 82)
    def test_terminal_and_retryable_errors_are_structured(self):
        r = req(self.env, "reconcile", {"tenant": "acme", "component": "nope"})
        self.assertEqual(r["outcome"], "TERMINAL")
        mod("schema").validate(r["error"], "PK_DEPLOY_ERROR/1")
        self.env.lattice.partitioned = True
        req(self.env, "set_desired", desired(self.env))
        r = req(self.env, "rollout", {"tenant": "acme", "component": "api", "version": "v2", "max_unavailable": 1,
                                      "artifact": self.sign("api", "v2")})
        self.assertEqual(r["outcome"], "RETRYABLE")
        self.assertTrue(r["error"]["retryable"])
        self.assertIn("retry_after_s", r["error"])

    def sign(self, c, v):
        return self.env.security.sign_artifact(self.env.priv, "rel-1", c, v, f"{c}-{v}".encode())

    @covers(15)
    def test_illegal_transitions_rejected(self):
        lc = lifecycle.Lifecycle()
        lc.move("t", "c", lifecycle.State.PENDING, "new")
        with self.assertRaises(errors.DeploymentError) as cm:
            lc.move("t", "c", lifecycle.State.CONVERGED, "skip")
        self.assertEqual(cm.exception.code, errors.ErrorCode.ILLEGAL_TRANSITION)
        with self.assertRaises(errors.DeploymentError):
            lifecycle.Lifecycle().move("t", "c", lifecycle.State.CONVERGED, "must start pending")
        for src, dsts in lifecycle.TRANSITIONS.items():
            for d in dsts:
                lifecycle.check_transition(src, d)

    @covers(17, 64)
    def test_tenant_quota_enforced(self):
        env = make_env(config_over={"tenant_quotas": {"acme": {"max_instances": 4}}})
        self.assertEqual(req(env, "set_desired", desired(env, count=3))["outcome"], "SUCCESS")
        r = req(env, "set_desired", desired(env, component="web", count=2))
        self.assertEqual(r["error"]["code"], "INV63-E-QUOTA")
        self.assertEqual(req(env, "set_desired", desired(env, component="web", count=1))["outcome"], "SUCCESS")

    @covers(19, 55)
    def test_precedence_residency_over_spread(self):
        req(self.env, "set_desired", desired(self.env, count=2, residency=["eu"]))
        r = req(self.env, "reconcile", {"tenant": "acme", "component": "api"})
        self.assertEqual(r["outcome"], "SUCCESS")
        self.assertTrue(all(h in ("h1", "h2") for *_, h in self.env.lattice.running))
        r = req(self.env, "set_desired", desired(self.env, component="x", count=1, residency=["mars"]))
        self.assertEqual(r["error"]["code"], "INV63-E-POLICY")

    @covers(18, 56, 89)
    def test_offline_mode_queues_intent_then_resyncs(self):
        req(self.env, "set_desired", desired(self.env))
        self.env.lattice.partitioned = True
        r = req(self.env, "reconcile", {"tenant": "acme", "component": "api"})
        self.assertEqual(r["outcome"], "DEGRADED", r)
        self.assertEqual(len(self.env.svc.pending), 1)
        self.assertTrue(self.env.svc.status()["degraded"])
        self.env.lattice.partitioned = False
        self.env.mono.advance(11)  # let breaker half-open
        out = self.env.svc.resync()
        self.assertEqual(out, {"resynced": ["acme/api"], "pending": 0})
        self.assertEqual(len(self.env.lattice.running), 3)

    @covers(18, 89)
    def test_offline_beyond_autonomy_window_is_retryable_failure(self):
        req(self.env, "set_desired", desired(self.env))
        self.env.lattice.partitioned = True
        req(self.env, "reconcile", {"tenant": "acme", "component": "api"})
        self.env.mono.advance(self.env.cfg["offline_autonomy_s"] + 1)
        r = req(self.env, "reconcile", {"tenant": "acme", "component": "api"})
        self.assertEqual(r["error"]["code"], "INV63-E-CONTROL-PLANE-OFFLINE")


class RolloutTest(unittest.TestCase):
    def setUp(self):
        self.env = make_env()
        req(self.env, "set_desired", desired(self.env, count=4))
        req(self.env, "reconcile", {"tenant": "acme", "component": "api"})

    def art(self, v):
        return self.env.security.sign_artifact(self.env.priv, "rel-1", "api", v, f"api-{v}".encode())

    @covers(38, 92, 83)
    def test_canary_then_bounded_batches(self):
        r = req(self.env, "rollout", {"tenant": "acme", "component": "api", "version": "v2", "max_unavailable": 2,
                                      "canary": 1, "artifact": self.art("v2")})
        self.assertEqual(r["outcome"], "SUCCESS", r)
        self.assertEqual(r["result"]["batches"], 3)       # 1 canary + 2 + 1
        self.assertLessEqual(r["result"]["worst_unavailable"], 2)
        self.assertTrue(all(v == "v2" for _, v, _ in self.env.lattice.running))

    @covers(38, 60, 92, 89)
    def test_failed_rollout_rolls_back_automatically(self):
        self.env.lattice.unhealthy_versions.add(("acme/api", "v2"))
        r = req(self.env, "rollout", {"tenant": "acme", "component": "api", "version": "v2", "max_unavailable": 1,
                                      "artifact": self.art("v2")})
        self.assertEqual(r["error"]["code"], "INV63-E-ROLLOUT-FAILED", r)
        self.assertEqual(sorted(v for _, v, _ in self.env.lattice.running), ["v1"] * 4)
        self.assertEqual(self.env.svc.desired["acme/api"]["version"], "v1")
        self.assertEqual(self.env.svc.metrics.get("rollbacks", kind="automatic"), 1)

    @covers(38, 92)
    def test_operator_rollback(self):
        req(self.env, "rollout", {"tenant": "acme", "component": "api", "version": "v2", "max_unavailable": 2,
                                  "artifact": self.art("v2")})
        r = req(self.env, "rollback", {"tenant": "acme", "component": "api"}, roles=("sre-operator",))
        self.assertEqual(r["result"]["rolled_back_to"], "v1", r)
        self.assertTrue(all(v == "v1" for _, v, _ in self.env.lattice.running))

    @covers(45, 87)
    def test_rollout_requires_signed_new_version(self):
        r = req(self.env, "rollout", {"tenant": "acme", "component": "api", "version": "v2", "max_unavailable": 1})
        self.assertEqual(r["error"]["code"], "INV63-E-ARTIFACT-UNTRUSTED")
        r = req(self.env, "rollout", {"tenant": "acme", "component": "api", "version": "v3", "max_unavailable": 1,
                                      "artifact": self.art("v2")})
        self.assertEqual(r["error"]["code"], "INV63-E-ARTIFACT-UNTRUSTED")


class DurabilityTest(unittest.TestCase):
    @covers(57, 60, 89, 32)
    def test_crash_replay_restores_desired_lifecycle_controls(self):
        env = make_env()
        req(env, "set_desired", desired(env))
        req(env, "reconcile", {"tenant": "acme", "component": "api"})
        req(env, "freeze", {"tenant": "acme", "component": "api", "reason": "incident"}, roles=("sre-operator",))
        # simulate crash: torn write at the tail
        with open(env.journal.path, "ab") as fh:
            fh.write(b'{"seq": 999, "partial')
        j2 = store.Journal(env.journal.dir, clock=env.clock, sealer=env.sealer)
        self.assertTrue(j2.recovered_torn_tail)
        svc2 = service.DeploymentService(config=env.cfg, hosts=HOSTS, adapter=env.lattice, journal=j2,
                                         tokens=env.tokens, verifier=env.verifier, clock=env.clock, mono=env.mono)
        self.assertEqual(svc2.desired["acme/api"]["count"], 3)
        self.assertEqual(svc2.lifecycle.get("acme", "api"), lifecycle.State.FROZEN)
        self.assertIn("acme/api", svc2.controls.frozen)
        self.assertEqual(svc2.tick()["results"], {})   # frozen: no automated action

    @covers(57, 49)
    def test_mid_journal_corruption_refuses_start(self):
        env = make_env()
        req(env, "set_desired", desired(env))
        lines = env.journal.path.read_bytes().split(b"\n")
        lines[0] = lines[0].replace(b'"lifecycle"', b'"desired_set"')
        env.journal.path.write_bytes(b"\n".join(lines))
        with self.assertRaises(errors.DeploymentError) as cm:
            store.Journal(env.journal.dir, sealer=env.sealer)
        self.assertEqual(cm.exception.code, errors.ErrorCode.STATE_CORRUPT)

    @covers(58, 86, 89)
    def test_stale_controller_is_fenced(self):
        env = make_env()
        old = env.svc
        new_j = store.Journal(env.journal.dir, clock=env.clock, sealer=env.sealer)
        new = service.DeploymentService(config=env.cfg, hosts=HOSTS, adapter=env.lattice, journal=new_j,
                                        tokens=env.tokens, verifier=env.verifier, clock=env.clock, mono=env.mono)
        r = req(env, "set_desired", desired(env))       # env.svc is the OLD leader
        self.assertEqual(r["error"]["code"], "INV63-E-STALE-EPOCH", r)
        self.assertFalse(old.status()["ready"])
        self.assertTrue(new.status()["leader"])

    @covers(95, 57)
    def test_backup_and_restore(self):
        env = make_env()
        req(env, "set_desired", desired(env))
        bdir = pathlib.Path(env.tmp) / "backup"
        m = env.journal.backup(bdir)
        restored = store.Journal.restore(bdir, pathlib.Path(env.tmp) / "restored", sealer=env.sealer)
        self.assertEqual(restored.head, m["head"])
        (bdir / "journal.jsonl").write_bytes(b"tampered\n")
        with self.assertRaises(errors.DeploymentError):
            store.Journal.restore(bdir, pathlib.Path(env.tmp) / "restored2", sealer=env.sealer)


class ControlsTest(unittest.TestCase):
    @covers(59, 92, 24)
    def test_freeze_quarantine_and_emergency_disable(self):
        env = make_env()
        req(env, "set_desired", desired(env))
        r = req(env, "quarantine", {"tenant": "acme", "component": "api"}, roles=("tenant-deployer",))
        self.assertEqual(r["error"]["code"], "INV63-E-FORBIDDEN")    # deployers cannot quarantine
        r = req(env, "quarantine", {"tenant": "acme", "component": "api"}, roles=("sre-operator",))
        self.assertEqual(r["outcome"], "SUCCESS", r)
        r = req(env, "reconcile", {"tenant": "acme", "component": "api"})
        self.assertEqual(r["error"]["code"], "INV63-E-QUARANTINED")
        req(env, "release_quarantine", {"tenant": "acme", "component": "api"}, roles=("sre-operator",))
        env.svc.emergency_disable(True, env.operator)
        self.assertEqual(req(env, "reconcile", {"tenant": "acme", "component": "api"})["error"]["code"], "INV63-E-FROZEN")
        self.assertFalse(env.svc.status()["ready"])
        env.svc.emergency_disable(False, env.operator)
        self.assertEqual(req(env, "reconcile", {"tenant": "acme", "component": "api"})["outcome"], "SUCCESS")

    @covers(59, 46)
    def test_host_quarantine_drains_node(self):
        env = make_env()
        req(env, "set_desired", desired(env, count=3))
        req(env, "reconcile", {"tenant": "acme", "component": "api"})
        env.svc.quarantine_host("h1", True, env.operator)
        req(env, "reconcile", {"tenant": "acme", "component": "api"})
        self.assertNotIn("h1", {h for *_, h in env.lattice.running})
        self.assertEqual(len(env.lattice.running), 3)


class IdempotencyTest(unittest.TestCase):
    @covers(25, 53, 86)
    def test_idempotency_key_replay_and_conflict(self):
        env = make_env()
        b = desired(env)
        r1 = req(env, "set_desired", b, key="same-key-0001")
        r2 = req(env, "set_desired", b, key="same-key-0001")
        self.assertEqual(r1["outcome"], r2["outcome"])
        self.assertEqual(env.svc.metrics.get("idempotent_replays"), 1)
        r3 = req(env, "set_desired", dict(b, count=1), key="same-key-0001")
        self.assertEqual(r3["error"]["code"], "INV63-E-CONFLICT")

    @covers(25)
    def test_deadline_exceeded(self):
        env = make_env()
        req(env, "set_desired", desired(env))
        orig = env.lattice.start

        def slow(inst):
            env.mono.advance(10)
            orig(inst)
        env.lattice.start = slow
        r = req(env, "reconcile", {"tenant": "acme", "component": "api"}, deadline_ms=5000)
        self.assertEqual(r["error"]["code"], "INV63-E-DEADLINE")


class HealthTest(unittest.TestCase):
    @covers(71, 40, 5)
    def test_status_exposes_health_readiness_version_config_deps_caps(self):
        env = make_env()
        st = env.svc.status(reference_time=env.clock())
        for k in ("live", "ready", "version", "config_digest", "dependencies", "capabilities", "preflight"):
            self.assertIn(k, st)
        self.assertTrue(st["ready"], st)
        self.assertEqual(st["version"], "4.3.0")
        st = env.svc.status(reference_time=env.clock() - 3600)   # 1h skew
        self.assertFalse(st["ready"])
        a05 = [c for c in st["preflight"] if c["id"] == "A-05"][0]
        self.assertEqual(a05["error_code"], "INV63-E-PRECONDITION")

    @covers(52)
    def test_stall_detection(self):
        env = make_env()
        req(env, "set_desired", desired(env))
        env.lattice.fail_hosts.update(HOSTS)
        env.svc.tick()
        env.mono.advance(env.cfg["stall_threshold_s"] + 1)
        self.assertEqual(env.svc.tick()["stalled"], ["acme/api"])
        self.assertEqual(env.svc.metrics.get("stalled_workloads"), 1)


class ReviewFixesTest(unittest.TestCase):
    """Regressions for defects found in the 4.3.0 internal review."""

    @covers(59, 38)
    def test_operator_rollback_respects_freeze_and_emergency_disable(self):
        env = make_env()
        req(env, "set_desired", desired(env, count=2))
        req(env, "reconcile", {"tenant": "acme", "component": "api"})
        art = env.security.sign_artifact(env.priv, "rel-1", "api", "v2", b"api-v2")
        req(env, "rollout", {"tenant": "acme", "component": "api", "version": "v2", "max_unavailable": 1, "artifact": art})
        req(env, "freeze", {"tenant": "acme", "component": "api"}, roles=("sre-operator",))
        r = req(env, "rollback", {"tenant": "acme", "component": "api"}, roles=("sre-operator",))
        self.assertEqual(r["error"]["code"], "INV63-E-FROZEN")
        self.assertTrue(all(v == "v2" for _, v, _ in env.lattice.running))

    @covers(42, 59, 87)
    def test_operator_methods_require_platform_operator(self):
        env = make_env()
        tenant_user = env.security.Principal("alice", "acme", frozenset({"sre-operator"}))
        for bad in ("oncall", tenant_user, env.security.Principal("x", "*", frozenset({"tenant-viewer"}))):
            with self.assertRaises(errors.DeploymentError):
                env.svc.emergency_disable(True, bad)
            with self.assertRaises(errors.DeploymentError):
                env.svc.quarantine_host("h1", True, bad)
        self.assertFalse(env.svc.controls.global_disabled)

    @covers(47, 34)
    def test_encryption_at_rest_required_by_prod_config(self):
        env = make_env()
        plain = store.Journal(pathlib.Path(env.tmp) / "plain")
        with self.assertRaises(errors.DeploymentError) as cm:
            service.DeploymentService(config=env.cfg, hosts=HOSTS, adapter=env.lattice, journal=plain,
                                      tokens=env.tokens, verifier=env.verifier)
        self.assertEqual(cm.exception.code, errors.ErrorCode.CONFIG_INVALID)
        self.assertNotIn(b"acme", env.journal.path.read_bytes())

    @covers(15)
    def test_scale_to_zero_reaches_deleted(self):
        env = make_env()
        req(env, "set_desired", desired(env, count=2))
        req(env, "reconcile", {"tenant": "acme", "component": "api"})
        req(env, "set_desired", desired(env, count=0))
        req(env, "reconcile", {"tenant": "acme", "component": "api"})
        self.assertEqual(env.svc.lifecycle.get("acme", "api"), lifecycle.State.DELETED)
        self.assertEqual(env.lattice.running, [])

    @covers(38, 15, 60)
    def test_failed_rollback_marks_failed(self):
        env = make_env()
        req(env, "set_desired", desired(env, count=2))
        req(env, "reconcile", {"tenant": "acme", "component": "api"})
        env.lattice.unhealthy_versions.add(("acme/api", "v2"))
        env.lattice.fail_start.add(("acme/api", "v1"))      # old version cannot come back
        art = env.security.sign_artifact(env.priv, "rel-1", "api", "v2", b"api-v2")
        r = req(env, "rollout", {"tenant": "acme", "component": "api", "version": "v2", "max_unavailable": 1, "artifact": art})
        self.assertEqual(r["error"]["details"]["state"], "FAILED", r)
        self.assertEqual(env.svc.lifecycle.get("acme", "api"), lifecycle.State.FAILED)

    @covers(57, 67, 95)
    def test_compaction_preserves_state(self):
        env = make_env()
        req(env, "set_desired", desired(env))
        req(env, "reconcile", {"tenant": "acme", "component": "api"})
        req(env, "freeze", {"tenant": "acme", "component": "api"}, roles=("sre-operator",))
        before = len(env.journal.records)
        out = env.svc.compact()
        self.assertEqual((out["records_before"], out["records_after"]), (before, 1))
        j2 = store.Journal(env.journal.dir, clock=env.clock, sealer=env.sealer)
        svc2 = service.DeploymentService(config=env.cfg, hosts=HOSTS, adapter=env.lattice, journal=j2,
                                         tokens=env.tokens, verifier=env.verifier, clock=env.clock, mono=env.mono)
        self.assertEqual(svc2.desired, env.svc.desired)
        self.assertIn("acme/api", svc2.controls.frozen)
        self.assertEqual(svc2.lifecycle.get("acme", "api"), lifecycle.State.FROZEN)

    @covers(57, 38)
    def test_operator_rollback_still_works_after_compaction(self):
        env = make_env()
        req(env, "set_desired", desired(env, count=2))
        req(env, "reconcile", {"tenant": "acme", "component": "api"})
        art = env.security.sign_artifact(env.priv, "rel-1", "api", "v2", b"api-v2")
        req(env, "rollout", {"tenant": "acme", "component": "api", "version": "v2", "max_unavailable": 1, "artifact": art})
        env.svc.compact()
        j2 = store.Journal(env.journal.dir, clock=env.clock, sealer=env.sealer)
        svc2 = service.DeploymentService(config=env.cfg, hosts=HOSTS, adapter=env.lattice, journal=j2,
                                         tokens=env.tokens, verifier=env.verifier, clock=env.clock, mono=env.mono)
        env.svc = svc2
        r = req(env, "rollback", {"tenant": "acme", "component": "api"}, roles=("sre-operator",))
        self.assertEqual(r["result"]["rolled_back_to"], "v1", r)

    @covers(45)
    def test_artifact_content_rehashed_when_fetcher_configured(self):
        env = make_env()
        env.svc.artifact_fetcher = lambda digest: b"tampered bytes"
        self.assertEqual(req(env, "set_desired", desired(env))["error"]["code"], "INV63-E-ARTIFACT-UNTRUSTED")
        env.svc.artifact_fetcher = lambda digest: b"api-v1"
        self.assertEqual(req(env, "set_desired", desired(env))["outcome"], "SUCCESS")

    @covers(18, 89)
    def test_tick_resyncs_automatically(self):
        env = make_env()
        req(env, "set_desired", desired(env))
        env.lattice.partitioned = True
        req(env, "reconcile", {"tenant": "acme", "component": "api"})
        env.lattice.partitioned = False
        env.mono.advance(11)
        env.svc.tick()
        self.assertEqual((len(env.svc.pending), len(env.lattice.running)), (0, 3))


class WadmAdapterContractTest(unittest.TestCase):
    @covers(30, 31, 83)
    def test_wadm_adapter_satisfies_lattice_protocol_with_fake_transport(self):
        adapter = mod("adapter")
        state = []

        def transport(op, p):
            if op == "ping":
                return {"ok": True}
            if op == "list":
                return {"instances": [list(i) for i in state]}
            if op == "start":
                state.append((p["component"], p["version"], p["host"])); return {"ok": True}
            if op == "stop":
                state.remove((p["component"], p["version"], p["host"])); return {"ok": True}
            if op == "health":
                return {"ok": True}
            if op == "capabilities":
                return {"capabilities": ["wasi-p2", "component-model"]}
            return {"ok": False}
        env = make_env()
        w = adapter.WadmAdapter(transport)
        env.svc.adapter = w
        req(env, "set_desired", desired(env))
        self.assertEqual(req(env, "reconcile", {"tenant": "acme", "component": "api"})["outcome"], "SUCCESS")
        self.assertEqual(len(state), 3)
        st = env.svc.status(reference_time=env.clock())
        self.assertTrue([c for c in st["preflight"] if c["id"] == "A-08"][0]["ok"])


if __name__ == "__main__":
    unittest.main()
