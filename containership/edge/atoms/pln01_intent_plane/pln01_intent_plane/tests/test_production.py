"""PLN-01 v4.3.0 production-component suite (MC-009..MC-044). Standard library only."""
from __future__ import annotations

import json
import os
import random
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _support import (ApplicationPlaneFake, FakeClock, PlacementFake, SecurityPlaneFake, config, controls,
                      decl, errors, make_service, pkg, precedence, secret_guard, service, store, telemetry,
                      trust, validation)

A = ("t1", "prod", "network")
B = ("t1", "prod", "app")


class SchemaAndErrorContract(unittest.TestCase):          # MC-009, MC-013, MC-038
    def test_all_schemas_load_and_fixtures_validate(self):
        for name in validation.SCHEMA_FILES:
            self.assertIsInstance(validation.load_schema(name), dict)
        fx = Path(__file__).parent / "fixtures"
        for f in sorted(fx.glob("*.json")):
            doc = json.loads(f.read_text())
            problems = validation.errors(doc["document"], doc["schema"])
            self.assertEqual(bool(problems), not doc["valid"], f"{f.name}: {problems}")

    def test_unknown_schema_keyword_is_refused(self):
        with self.assertRaises(errors.UnsupportedSchemaError):
            validation._audit_keywords({"type": "object", "oneOf": []})

    def test_every_error_code_is_unique_and_schema_valid(self):
        self.assertEqual(len(errors.ERROR_CODES), len({c.code for c in errors.ERROR_CODES.values()}))
        for code in errors.ERROR_CODES:
            doc = {"schema": "PK_ERROR/1", "code": code, "http_status": 400, "retryable": False,
                   "terminal": True, "message": "x"}
            self.assertEqual(validation.errors(doc, "PK_ERROR/1"), [])

    def test_graph_exceptions_map_to_codes(self):
        self.assertEqual(errors.code_for(pkg.CycleError("x")), "PLN01-E0002")
        self.assertEqual(errors.code_for(pkg.VersionConflictError("x")), "PLN01-E0003")
        self.assertEqual(errors.code_for(KeyError("x")), "PLN01-E9999")
        self.assertEqual(errors.to_error(KeyError("secret=hunter2"))["message"], "Internal error")

    def test_error_codes_are_frozen_against_registry(self):
        frozen = json.loads((Path(__file__).resolve().parents[1] / "schemas" / "error_codes.v1.json").read_text())
        for code, meta in frozen.items():   # append-only compatibility rule
            self.assertIn(code, errors.ERROR_CODES)
            self.assertEqual(errors.ERROR_CODES[code].retryable, meta["retryable"])


class ServiceContract(unittest.TestCase):                  # MC-038 public interface contract tests
    def setUp(self):
        self.svc, self.sec, self.pol, _, self.clock = make_service()
        self.tok = self.sec.token()

    def test_declare_plan_graph_report_roundtrip(self):
        r = self.svc.submit(decl(A, {"cidr": "10.0.0.0/16", "site": "dc-1"}), credential=self.tok)
        self.assertTrue(r["ok"], r)
        r = self.svc.submit(decl(B, {"image": "svc:1"}, after=[A]), credential=self.tok)
        self.assertTrue(r["ok"], r)
        g = self.svc.graph_view(credential=self.tok)
        self.assertEqual(validation.errors(g["graph"], "PK_INTENT_GRAPH/1"), [])
        rep_tok = self.sec.token("reporter-1", "reporter", (("intent:report", "t1"),))
        rep = {"schema": "PK_ACTUAL_STATE/1", "reporter": "r1", "site": "dc-1", "observed_at": self.clock(),
               "sequence": 1, "nodes": [{"node": list(A), "spec": {"cidr": "10.0.0.0/16", "site": "dc-1"}}]}
        self.assertTrue(self.svc.report(rep, credential=rep_tok)["accepted"])
        p = self.svc.plan(credential=self.tok)
        self.assertEqual([s["action"] for s in p["steps"]], ["noop", "create"])
        self.assertEqual(p["drift"], [list(B)])
        self.assertIn("traceparent", p)

    def test_invalid_request_returns_pk_error(self):
        r = self.svc.submit({"schema": "PK_DECLARATION/1"}, credential=self.tok)
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["code"], "PLN01-E0001")
        self.assertEqual(validation.errors(r["error"], "PK_ERROR/1"), [])

    def test_retract_contract(self):
        self.svc.submit(decl(A), credential=self.tok)
        r = self.svc.submit({"schema": "PK_DECLARATION/1", "operation": "retract", "node": list(A),
                             "request_id": "rt-1"}, credential=self.tok)
        self.assertEqual(r["removed"], [list(A)])


class AuthAndAuthz(unittest.TestCase):                     # MC-010, MC-011
    def setUp(self):
        self.svc, self.sec, self.pol, self.adapter, self.clock = make_service()

    def test_missing_forged_expired_revoked_credentials(self):
        self.assertEqual(self.svc.submit(decl(A))["error"]["code"], "PLN01-E0008")
        forged = self.sec.token()[:-4] + "0000"
        self.assertEqual(self.svc.submit(decl(A), credential=forged)["error"]["code"], "PLN01-E0008")
        tok = self.sec.token(ttl=10)
        self.clock.advance(11)
        self.assertEqual(self.svc.submit(decl(A), credential=tok)["error"]["code"], "PLN01-E0008")

    def test_identity_unavailable_fails_closed(self):
        tok = self.sec.token()
        self.sec.keys.available = False
        r = self.svc.submit(decl(A), credential=tok)
        self.assertEqual(r["error"]["code"], "PLN01-E0010")
        self.assertTrue(r["error"]["retryable"])
        self.assertEqual(self.svc.health.readiness()["status"], "fail")
        self.assertEqual(len(self.svc.graph), 0)

    def test_capability_scoping_is_least_privilege(self):
        tok = self.sec.token("dev", grants=(("intent:declare", "t1/stage"),))
        self.assertEqual(self.svc.submit(decl(("t1", "prod", "x")), credential=tok)["error"]["code"], "PLN01-E0009")
        self.assertTrue(self.svc.submit(decl(("t1", "stage", "x")), credential=tok)["ok"])
        self.assertEqual(self.svc.submit({"schema": "PK_DECLARATION/1", "operation": "retract",
                                          "node": ["t1", "stage", "x"], "request_id": "r"}, credential=tok)
                         ["error"]["code"], "PLN01-E0009")

    def test_reporter_cannot_declare_and_humans_cannot_report(self):
        rep = self.sec.token("r", "reporter", (("intent:report", "t1"),))
        self.assertEqual(self.svc.submit(decl(A), credential=rep)["error"]["code"], "PLN01-E0009")
        human = self.sec.token("h", "human", (("intent:report", "t1"),))
        doc = {"schema": "PK_ACTUAL_STATE/1", "reporter": "x", "site": "dc-1", "observed_at": self.clock(), "nodes": []}
        self.assertFalse(self.svc.report(doc, credential=human)["ok"])

    def test_policy_engine_denial_and_outage_fail_closed(self):
        tok = self.sec.token()
        r = self.svc.submit(decl(A, {"forbidden": True}), credential=tok)
        self.assertEqual(r["error"]["code"], "PLN01-E0005")
        self.adapter.available = False
        self.assertEqual(self.svc.submit(decl(A), credential=tok)["error"]["code"], "PLN01-E0005")

    def test_key_rotation_keeps_old_tokens_until_destroyed(self):
        tok = self.sec.token()
        self.sec.keys.rotate()
        self.assertTrue(self.svc.submit(decl(A), credential=tok)["ok"])
        self.sec.keys.destroy(1)
        self.assertEqual(self.svc.submit(decl(B), credential=tok)["error"]["code"], "PLN01-E0008")


class SecretsAndArtifacts(unittest.TestCase):              # MC-018, MC-020
    def setUp(self):
        self.svc, self.sec, *_ = make_service()
        self.tok = self.sec.token()

    def test_raw_secrets_refused_refs_allowed(self):
        for spec in ({"db_password": "hunter22"}, {"env": {"API_KEY": "abc"}},
                     {"note": "-----BEGIN RSA PRIVATE KEY-----"}, {"x": "AKIAABCDEFGHIJKLMNOP"}):
            r = self.svc.submit(decl(A, spec), credential=self.tok)
            self.assertEqual(r["error"]["code"], "PLN01-E0017", spec)
            self.assertNotIn("hunter22", json.dumps(r))
        self.assertTrue(self.svc.submit(decl(A, {"db_password_ref": "vault://kv/db"}), credential=self.tok)["ok"])
        self.assertTrue(self.svc.submit(decl(B, {"token": "vault://kv/t"}), credential=self.tok)["ok"])

    def test_logs_and_errors_are_redacted(self):
        self.svc.log.log("INFO", "x", password="p@ss", nested={"token": "t"}, text="password=abcdef")
        rec = self.svc.log.records[-1]
        self.assertEqual(rec["password"], "[REDACTED]")
        self.assertEqual(rec["nested"]["token"], "[REDACTED]")
        self.assertNotIn("abcdef", rec["text"])

    def test_artifact_verification(self):
        policy = trust.ArtifactPolicy(keys=self.sec.keys, trusted_signers={"ci@build"})
        self.svc.artifact_policy = policy
        digest = "sha256:" + "a" * 64
        policy.approved_digests["svc"] = {digest}
        good = {"name": "svc", "digest": digest, "signer": "ci@build", "signature": policy.sign("svc", digest, "ci@build"),
                "provenance": {"builder": "ci", "source": "git+https://example/svc@abc"}}
        self.assertTrue(self.svc.submit(decl(A, artifacts=[good]), credential=self.tok)["ok"])
        for bad in (dict(good, digest="sha256:" + "b" * 64), dict(good, signer="mallory"),
                    dict(good, signature="v1:" + "0" * 64), {k: v for k, v in good.items() if k != "provenance"}):
            r = self.svc.submit(decl(B, artifacts=[bad]), credential=self.tok)
            self.assertEqual(r["error"]["code"], "PLN01-E0018", bad)
        policy.revoked_digests.add(digest)
        self.assertEqual(self.svc.submit(decl(B, artifacts=[good]), credential=self.tok)["error"]["code"], "PLN01-E0018")


class FlowControl(unittest.TestCase):                      # MC-007, MC-012
    def test_tenant_rate_quota_is_isolated(self):
        cfg = config.build_config([("q", {"quotas": {"tenant_rate_per_second": 1.0, "tenant_burst": 2}})], author="t")
        svc, sec, *_ = make_service(config=cfg)
        tok = sec.token()
        codes = [svc.submit(decl(("t1", "prod", f"n{i}")), credential=tok).get("error", {}).get("code") for i in range(3)]
        self.assertEqual(codes, [None, None, "PLN01-E0011"])
        self.assertTrue(svc.submit(decl(("t2", "prod", "n")), credential=tok)["ok"])  # fairness: t2 unaffected

    def test_tenant_node_quota(self):
        cfg = config.build_config([("q", {"quotas": {"tenant_max_nodes": 2}})], author="t")
        svc, sec, *_ = make_service(config=cfg)
        tok = sec.token()
        for i in range(2):
            self.assertTrue(svc.submit(decl(("t1", "p", f"n{i}")), credential=tok)["ok"])
        self.assertEqual(svc.submit(decl(("t1", "p", "n9")), credential=tok)["error"]["code"], "PLN01-E0011")
        self.assertTrue(svc.submit(decl(("t1", "p", "n0"), {"v": 2}), credential=tok)["ok"])  # updates allowed

    def test_bulkhead_sheds_when_full(self):
        bh = controls.Bulkhead(1, 0)
        gate = threading.Event()
        t = threading.Thread(target=lambda: bh.run(gate.wait))
        t.start()
        while bh.in_flight == 0:
            time.sleep(0.001)
        with self.assertRaises(errors.OverloadedError):
            bh.run(lambda: None)
        gate.set()
        t.join()
        self.assertEqual(bh.shed, 1)

    def test_deadline_and_cancellation(self):
        clk = FakeClock()
        d = controls.Deadline(1.0, clock=clk)
        d.check()
        clk.advance(2)
        with self.assertRaises(errors.DeadlineExceededError):
            d.check()
        d2 = controls.Deadline(5, clock=clk)
        d2.cancel()
        with self.assertRaises(errors.CancelledError):
            d2.check()

    def test_retry_only_retryable_with_bounded_jitter(self):
        sleeps, calls = [], []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise errors.OverloadedError()
            return "ok"
        self.assertEqual(controls.retry(flaky, attempts=4, base=0.1, cap=0.3, sleep=sleeps.append,
                                        rng=random.Random(1)), "ok")
        self.assertTrue(all(0 <= s <= 0.3 for s in sleeps))
        calls.clear()
        with self.assertRaises(pkg.ValidationError):
            controls.retry(lambda: (_ for _ in ()).throw(pkg.ValidationError("x")), attempts=4, base=0.1, cap=1,
                           sleep=sleeps.append)

    def test_circuit_breaker(self):
        clk = FakeClock()
        cb = controls.CircuitBreaker(failure_threshold=2, reset_seconds=5, clock=clk)
        for _ in range(2):
            with self.assertRaises(ZeroDivisionError):
                cb.call(lambda: 1 / 0)
        with self.assertRaises(errors.CircuitOpenError):
            cb.call(lambda: 1)
        clk.advance(6)
        self.assertEqual(cb.call(lambda: 1), 1)
        self.assertEqual(cb.state, "closed")


class SafetyControlsTest(unittest.TestCase):               # MC-029, MC-044
    def test_freeze_quarantine_disable(self):
        svc, sec, *_ = make_service()
        tok = sec.token()
        svc.submit(decl(A), credential=tok)
        svc.controls.freeze("t1/prod", actor="oncall", reason="incident 42")
        self.assertEqual(svc.submit(decl(B), credential=tok)["error"]["code"], "PLN01-E0016")
        self.assertTrue(svc.submit(decl(("t1", "stage", "x")), credential=tok)["ok"])
        svc.controls.unfreeze("t1/prod", actor="oncall", reason="resolved")
        svc.controls.quarantine("t1", actor="sec", reason="suspected compromise")
        p = svc.plan(credential=tok)
        self.assertTrue(all(s.get("held") == "quarantined" for s in p["steps"]))
        svc.controls.release("t1", actor="sec", reason="cleared")
        svc.controls.disable(actor="ic", reason="emergency stop")
        self.assertEqual(svc.plan(credential=tok, release=True)["error"]["code"], "PLN01-E0016")
        self.assertEqual(svc.submit(decl(B), credential=tok)["error"]["code"], "PLN01-E0016")
        with self.assertRaises(ValueError):
            svc.controls.enable(actor="", reason="")
        svc.controls.enable(actor="ic", reason="all clear")
        self.assertTrue(svc.submit(decl(B, after=[A]), credential=tok)["ok"])
        self.assertEqual([e["action"] for e in svc.controls.log],
                         ["freeze", "unfreeze", "quarantine", "release", "disable", "enable"])


class Transactions(unittest.TestCase):                     # MC-017
    def test_all_or_nothing(self):
        svc, sec, *_ = make_service()
        tok = sec.token()
        svc.submit(decl(A), credential=tok)
        v0 = svc.graph.version
        r = svc.transaction([decl(B, {"v": 1}, after=[A]), decl(("t1", "prod", "bad"), {"password": "x1234"})],
                            credential=tok)
        self.assertEqual(r["error"]["code"], "PLN01-E0022")
        self.assertEqual(svc.graph.snapshot()["nodes"], svc.graph.snapshot(v0)["nodes"])
        r = svc.transaction([decl(B, {"v": 1}, after=[A]), decl(("t1", "prod", "c"), after=[B])], credential=tok)
        self.assertTrue(r["ok"], r)
        self.assertEqual(len(svc.graph), 3)

    def test_stale_transaction_refused(self):
        svc, sec, *_ = make_service()
        r = svc.transaction([decl(A)], credential=sec.token(), expected_version=7)
        self.assertEqual(r["error"]["code"], "PLN01-E0003")


class DurableState(unittest.TestCase):                     # MC-027, MC-022, MC-028, MC-030
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dir = os.path.join(self.tmp, "state")

    def test_restart_resume_preserves_graph_and_audit(self):
        svc, sec, *_ = make_service(self.dir)
        tok = sec.token()
        svc.submit(decl(A, {"cidr": "10/8"}), credential=tok)
        svc.submit(decl(B, after=[A]), credential=tok)
        svc.store.snapshot()
        svc.submit(decl(B, {"image": "v2"}, after=[A]), credential=tok)
        before = svc.graph.snapshot()
        st2 = store.DurableStore(self.dir, sec.keys, fsync=False)
        g2 = st2.open_graph()
        self.assertEqual(g2.snapshot(), before)
        self.assertEqual(st2.verify()["audit_records"], 3)

    def test_torn_tail_is_repaired_but_mid_corruption_fails_stop(self):
        svc, sec, *_ = make_service(self.dir)
        tok = sec.token()
        for i in range(3):
            svc.submit(decl(("t", "e", f"n{i}")), credential=tok)
        wal = Path(self.dir, "wal.jsonl")
        with open(wal, "ab") as h:
            h.write(b'{"v": 4, "partial')              # crash mid-append
        g = store.DurableStore(self.dir, sec.keys, fsync=False).open_graph()
        self.assertEqual(g.version, 3)
        lines = wal.read_bytes().splitlines()
        tampered = json.loads(lines[1])
        tampered["nodes"] = {"t\x1fe\x1fn1": {"evil": True}}
        lines[1] = json.dumps(tampered).encode()
        wal.write_bytes(b"\n".join(lines) + b"\n")
        with self.assertRaises(errors.StoreIntegrityError):
            store.DurableStore(self.dir, sec.keys, fsync=False).open_graph()

    def test_crash_between_snapshot_and_compaction(self):
        svc, sec, *_ = make_service(self.dir)
        tok = sec.token()
        for i in range(3):
            svc.submit(decl(("t", "e", f"n{i}")), credential=tok)
        wal_before = Path(self.dir, "wal.jsonl").read_bytes()
        svc.store.snapshot()
        Path(self.dir, "wal.jsonl").write_bytes(wal_before)      # compaction never happened
        g = store.DurableStore(self.dir, sec.keys, fsync=False).open_graph()
        self.assertEqual(g.snapshot(), svc.graph.snapshot())

    def test_store_write_failure_aborts_mutation(self):         # fault injection
        svc, sec, *_ = make_service(self.dir)
        tok = sec.token()
        svc.submit(decl(A), credential=tok)
        orig = svc.store.wal.append
        svc.store.wal.append = lambda body: (_ for _ in ()).throw(OSError("disk full"))
        r = svc.submit(decl(B, after=[A]), credential=tok)
        self.assertFalse(r["ok"])
        self.assertEqual(svc.graph.version, 1)
        self.assertEqual(len(svc.graph), 1)
        svc.store.wal.append = orig
        self.assertTrue(svc.submit(decl(B, after=[A], rid="again"), credential=tok)["ok"])
        self.assertEqual(store.DurableStore(self.dir, sec.keys, fsync=False).open_graph().version, 2)

    def test_backup_restore_and_digest_check(self):
        svc, sec, *_ = make_service(self.dir)
        svc.submit(decl(A), credential=sec.token())
        man = svc.store.backup(os.path.join(self.tmp, "b.tgz"))
        with self.assertRaises(errors.StoreIntegrityError):
            store.DurableStore.restore(os.path.join(self.tmp, "b.tgz"), os.path.join(self.tmp, "r0"), expected_sha256="0" * 64)
        target = store.DurableStore.restore(os.path.join(self.tmp, "b.tgz"), os.path.join(self.tmp, "r1"),
                                            expected_sha256=man["sha256"])
        self.assertEqual(store.DurableStore(target, sec.keys, fsync=False).open_graph().snapshot(), svc.graph.snapshot())

    def test_migration_and_downgrade_refusal(self):
        os.makedirs(self.dir)
        Path(self.dir, "state.json").write_text("{}")
        store.migrate(Path(self.dir))
        self.assertEqual(Path(self.dir, "FORMAT").read_text().strip(), str(store.FORMAT_VERSION))
        Path(self.dir, "FORMAT").write_text("99\n")
        with self.assertRaises(errors.StoreIntegrityError):
            store.migrate(Path(self.dir))

    def test_lease_fencing_prevents_split_brain(self):
        clk = FakeClock()
        path = os.path.join(self.tmp, "LEASE")
        a = store.FileLease(path, "node-a", ttl=10, clock=clk)
        b = store.FileLease(path, "node-b", ttl=10, clock=clk)
        ta = a.acquire()
        with self.assertRaises(errors.LeaseError):
            b.acquire()
        clk.advance(11)                          # a partitioned; lease expires
        tb = b.acquire()
        self.assertGreater(tb, ta)
        with self.assertRaises(errors.LeaseError):
            a.check()                            # stale holder refused
        svc, sec, *_ = make_service(self.dir, lease=a)
        self.assertEqual(svc.submit(decl(A), credential=sec.token())["error"]["code"], "PLN01-E0019")


class DisconnectedSites(unittest.TestCase):                # MC-004, MC-026
    def test_stale_site_holds_steps_and_out_of_order_reports_ignored(self):
        svc, sec, _, _, clock = make_service()
        tok = sec.token()
        rtok = sec.token("r", "reporter", (("intent:report", "t1"),))
        svc.submit(decl(A, {"site": "edge-1"}), credential=tok)
        rep = {"schema": "PK_ACTUAL_STATE/1", "reporter": "r", "site": "edge-1", "observed_at": clock(),
               "sequence": 5, "nodes": [{"node": list(A), "spec": {"site": "edge-1"}}]}
        self.assertTrue(svc.report(rep, credential=rtok)["accepted"])
        self.assertFalse(svc.report(dict(rep, sequence=4), credential=rtok)["accepted"])
        clock.advance(150)
        self.assertEqual(svc.site_status()["edge-1"]["state"], "disconnected")
        p = svc.plan(credential=tok)
        self.assertEqual(p["stale_sites"], ["edge-1"])
        self.assertEqual(p["steps"][0]["held"], "site-disconnected")
        rep2 = dict(rep, sequence=6, observed_at=clock())
        svc.report(rep2, credential=rtok)
        self.assertEqual(svc.site_status()["edge-1"]["state"], "connected")
        fut = dict(rep, sequence=7, observed_at=clock() + 10_000)
        self.assertEqual(svc.report(fut, credential=rtok)["error"]["code"], "PLN01-E0001")


class PlanReleaseAndExplain(unittest.TestCase):            # MC-036, threat "plan replay"
    def test_release_replay_refused_and_downstream_consumes(self):
        svc, sec, *_ = make_service()
        tok = sec.token()
        svc.submit(decl(A, {"site": "dc-1"}), credential=tok)
        p = svc.plan(credential=tok, release=True)
        app = ApplicationPlaneFake(svc)
        self.assertEqual(app.consume(p), 1)
        self.assertEqual(PlacementFake().placements(svc.graph.snapshot()), {A: "dc-1"})
        svc.submit(decl(B, after=[A]), credential=tok)
        with self.assertRaises(pkg.VersionConflictError):
            app.consume(p)

    def test_explain_carries_decisions_and_lineage(self):
        svc, sec, *_ = make_service()
        tok = sec.token()
        spec = {"constraints": [{"kind": "cost", "key": "region", "value": "us"},
                                {"kind": "residency", "key": "region", "value": "eu", "hard": True}]}
        svc.submit(decl(A, spec), credential=tok)
        e = svc.explain(A)
        self.assertEqual(e["decisions"][0]["outcome"], "admitted")
        res = e["decisions"][1]["constraint_resolution"]["region"]
        self.assertEqual(res["winner"]["value"], "eu")
        self.assertEqual(e["lineage"]["component_version"], "4.3.0")
        self.assertEqual(e["lineage"]["config"]["digest"], svc.config.digest)


class Precedence(unittest.TestCase):                       # MC-008
    def test_order_and_hard_conflict(self):
        r = precedence.resolve([{"kind": "slo", "key": "zone", "value": "a"},
                                {"kind": "security", "key": "zone", "value": "b"}])
        self.assertEqual(r["zone"]["winner"]["kind"], "security")
        with self.assertRaises(pkg.ValidationError):
            precedence.resolve([{"kind": "security", "key": "z", "value": 1, "hard": True},
                                {"kind": "security", "key": "z", "value": 2, "hard": True}])
        a = precedence.resolve([{"kind": "cost", "key": "k", "value": "y"}, {"kind": "cost", "key": "k", "value": "x"}])
        b = precedence.resolve([{"kind": "cost", "key": "k", "value": "x"}, {"kind": "cost", "key": "k", "value": "y"}])
        self.assertEqual(a, b)


class Configuration(unittest.TestCase):                    # MC-016
    def test_overlays_provenance_and_immutability(self):
        base = config.build_config(author="alice", now=1.0)
        env = config.build_config([("env/prod", {"limits": {"max_nodes": 20000}}),
                                   ("site/edge-1", {"sites": {"edge-1": {"context": "far-edge"}}})],
                                  author="bob", previous=base, now=2.0)
        self.assertEqual(env.get("limits", "max_nodes"), 20000)
        self.assertEqual(env.layers, ("defaults", "env/prod", "site/edge-1"))
        self.assertEqual(env.provenance()["previous_digest"], base.digest)
        self.assertEqual(env.staleness_for("edge-1"), 3600.0)
        with self.assertRaises(TypeError):
            env.values["limits"]["max_nodes"] = 1
        self.assertEqual(config.DEFAULTS["limits"]["max_nodes"], 10000)

    def test_invalid_config_refused(self):
        for bad in ({"limits": {"max_nodes": 0}}, {"unknown": 1}, {"quotas": {"tenant_max_nodes": 10**9}},
                    {"timeouts": {"retry_base_seconds": 5.0, "retry_cap_seconds": 1.0}}):
            with self.assertRaises(errors.ConfigError):
                config.build_config([("bad", bad)], author="x")
        with self.assertRaises(errors.ConfigError):
            config.build_config(author=" ")


class Observability(unittest.TestCase):                    # MC-034, MC-035, MC-025
    def test_metrics_exposition_and_cardinality_cap(self):
        m = telemetry.Metrics(max_label_sets=3)
        for i in range(10):
            m.inc("c", tenant=f"t{i}")
        self.assertEqual(len(m.counters["c"]), 4)
        m.observe("h", 0.2)
        text = m.exposition()
        self.assertIn('h_bucket{le="0.25"} 1', text)
        self.assertIn("__overflow__", text)

    def test_service_emits_contract_signals(self):
        svc, sec, *_ = make_service()
        svc.submit(decl(A), credential=sec.token())
        svc.submit(decl(A), credential="bad")
        svc.plan(credential=sec.token())
        text = svc.metrics.exposition()
        for sig in ("declaration_admission", "plan_emission_seconds", "graph_version", "drift_open",
                    "pln01_requests_total", "pln01_request_seconds"):
            self.assertIn(sig, text)

    def test_trace_propagation(self):
        svc, sec, *_ = make_service()
        parent = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        r = svc.submit(decl(A), credential=sec.token(), traceparent=parent)
        self.assertTrue(r["traceparent"].startswith("00-" + "a" * 32))
        self.assertNotEqual(r["traceparent"].split("-")[2], "b" * 16)
        self.assertEqual(len(telemetry.TraceContext.parse("garbage").trace_id), 32)

    def test_health_readiness_and_stall(self):
        mono = FakeClock(0)
        h = telemetry.Health(stall_seconds=5, clock=mono)
        h.register_dependency("identity", required=True)
        h.ready_flag = True
        self.assertEqual(h.readiness()["blocking"], ["identity"])
        h.report_dependency("identity", "up")
        self.assertEqual(h.readiness()["status"], "pass")
        mono.advance(6)
        self.assertEqual(h.liveness()["status"], "fail")


class Adversarial(unittest.TestCase):                      # MC-023 fuzz + threat-derived
    def test_fuzzed_requests_never_crash_or_leak(self):
        svc, sec, *_ = make_service()
        tok = sec.token()
        rng = random.Random(1337)
        atoms = [None, True, 0, -1, 2**70, 1.5, float("nan"), "", " x", "a" * 300, "t1", [], {}, ["t1", "p"],
                 ["t1", "p", "n"], {"schema": "PK_DECLARATION/1"}, "PK_DECLARATION/1", "declare", "retract"]

        def rand(depth=0):
            c = rng.random()
            if depth > 3 or c < 0.5:
                return rng.choice(atoms)
            if c < 0.75:
                return [rand(depth + 1) for _ in range(rng.randint(0, 4))]
            return {rng.choice(["schema", "operation", "node", "spec", "after", "request_id", "x"]): rand(depth + 1)
                    for _ in range(rng.randint(0, 6))}
        for i in range(3000):
            doc = rand()
            if isinstance(doc, dict) and rng.random() < 0.5:
                doc = dict(decl(("t1", "p", f"f{i}")), **doc)
            r = svc.submit(doc, credential=tok)
            self.assertIn("ok", r)
            if not r["ok"]:
                self.assertEqual(validation.errors(r["error"], "PK_ERROR/1"), [], r)
                self.assertNotEqual(r["error"]["code"], "PLN01-E9999", doc)
        self.assertTrue(svc.graph.verify_audit_chain())

    def test_spoofed_actor_field_is_ignored(self):
        svc, sec, *_ = make_service()
        tok = sec.token("alice")
        r = svc.submit(dict(decl(A), actor="root"), credential=tok)
        self.assertFalse(r["ok"])     # unknown property rejected by schema
        svc.submit(decl(A), credential=tok)
        self.assertEqual(svc.graph.audit_events[-1].actor, "alice")

    def test_declaration_flood_is_bounded(self):
        cfg = config.build_config([("q", {"quotas": {"tenant_rate_per_second": 5.0, "tenant_burst": 5}})], author="t")
        svc, sec, *_ = make_service(config=cfg)
        tok = sec.token()
        ok = sum(svc.submit(decl(("t1", "p", f"n{i}")), credential=tok)["ok"] for i in range(200))
        self.assertEqual(ok, 5)


class Concurrency(unittest.TestCase):                      # MC-040
    def test_concurrent_service_writers_keep_invariants(self):
        svc, sec, *_ = make_service()
        tok = sec.token()

        def worker(i):
            return svc.submit(decl(("t1", "p", f"n{i % 20}"), {"w": i}), credential=tok)["ok"]
        with ThreadPoolExecutor(16) as ex:
            results = list(ex.map(worker, range(400)))
        self.assertTrue(all(results))
        self.assertEqual(len(svc.graph), 20)
        self.assertTrue(svc.graph.verify_audit_chain())
        self.assertEqual(svc.graph.version, sum(1 for e in svc.graph.audit_events if e.outcome == "admitted"))

    def test_concurrent_transactions_are_serialized(self):
        svc, sec, *_ = make_service()
        tok = sec.token()

        def worker(i):
            return svc.transaction([decl(("t1", "p", f"a{i}")), decl(("t1", "p", f"b{i}"), after=[("t1", "p", f"a{i}")])],
                                   credential=tok)["ok"]
        with ThreadPoolExecutor(8) as ex:
            self.assertTrue(all(ex.map(worker, range(40))))
        self.assertEqual(len(svc.graph), 80)
        order = svc.graph.order()
        for i in range(40):
            self.assertLess(order.index(("t1", "p", f"a{i}")), order.index(("t1", "p", f"b{i}")))


class Compatibility(unittest.TestCase):                    # MC-039, MC-006
    def test_v42_api_surface_unchanged(self):
        g = pkg.IntentGraph()
        a = g.declare("t1", "prod", "a", {"v": 1}, expected_version=0, request_id="r1", actor="op")
        self.assertEqual(pkg.plan(g)["schema"], "PK_RECONCILIATION_PLAN/1")
        for name in ("IntentGraph", "plan", "AuditEvent", "CycleError", "ValidationError", "VersionConflictError",
                     "DependencyInUseError", "AdmissionRejectedError", "ReplayError", "HistoryUnavailableError",
                     "ELEMENT_ID", "ELEMENT_NAME", "build_contract", "IntentPlaneService"):
            self.assertTrue(hasattr(pkg, name), name)
        self.assertEqual(g.node_spec(a), {"v": 1})

    def test_compat_matrix_is_machine_readable(self):
        root = Path(__file__).resolve().parents[1]
        m = json.loads((root / "docs" / "compatibility_matrix.json").read_text())
        self.assertEqual(m["component_version"], pkg.__version__)
        self.assertIn("PK_DECLARATION/1", m["interfaces"])

    def test_contract_builds_without_pk_core(self):
        c = pkg.build_contract()
        self.assertEqual(c.element, "PLN-01")
        self.assertIn("plan_emission_seconds", c.signals)


class Endurance(unittest.TestCase):                        # MC-041 (bounded CI variant)
    def test_soak_churn_with_durable_store_stays_bounded(self):
        tmp = tempfile.mkdtemp()
        svc, sec, *_ = make_service(os.path.join(tmp, "s"))
        svc.store.snapshot_every = 100
        tok = sec.token()
        rng = random.Random(7)
        for i in range(1500):
            n = ("t1", "p", f"n{rng.randint(0, 49)}")
            if rng.random() < 0.8:
                svc.submit(decl(n, {"i": i}), credential=tok)
            else:
                svc.submit({"schema": "PK_DECLARATION/1", "operation": "retract", "node": list(n),
                            "request_id": f"r{i}"}, credential=tok)
        self.assertLessEqual(len(svc.graph._history), svc.graph.max_history)
        self.assertLessEqual(len(svc.graph.audit_events), svc.graph.max_audit_events)
        g2 = store.DurableStore(os.path.join(tmp, "s"), sec.keys, fsync=False).open_graph()
        self.assertEqual(g2.snapshot(), svc.graph.snapshot())
        actual = len(svc.graph.snapshot()["nodes"])
        self.assertEqual(svc.graph.tenant_node_count("t1"), actual)
        self.assertEqual(g2.tenant_node_count("t1"), actual)
        svc.graph.rollback(svc.graph.oldest_retained_version, actor="op")
        self.assertEqual(svc.graph.tenant_node_count("t1"), len(svc.graph.snapshot()["nodes"]))


if __name__ == "__main__":
    unittest.main()
