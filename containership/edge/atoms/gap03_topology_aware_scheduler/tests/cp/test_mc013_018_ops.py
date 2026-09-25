import json
import os
import threading
import time
import unittest
import urllib.request

from gap03_topology_aware_scheduler import ShareViolation, StaleFairShare, NotInTopology, TopologyConflict, ReservationOversubscribed
from gap03_topology_aware_scheduler.controlplane import config as cfgmod, errors
from gap03_topology_aware_scheduler.controlplane.audit import AuditLog
from gap03_topology_aware_scheduler.controlplane.config import ConfigManager, ConfigStore
from gap03_topology_aware_scheduler.controlplane.controls import Controls, ControlStore
from gap03_topology_aware_scheduler.controlplane.degraded import DegradedPolicy, MATRIX
from gap03_topology_aware_scheduler.controlplane.errors import SchedulerError
from gap03_topology_aware_scheduler.controlplane.faults import StoreFault
from gap03_topology_aware_scheduler.controlplane.health import Health, serve
from gap03_topology_aware_scheduler.controlplane import identity
from gap03_topology_aware_scheduler.tests.cp._util import TmpCase, covers

OPS = {"sub": "spiffe://prod.example/operator/ops", "perms": {"control.write"}}
CFG = {"sub": "spiffe://prod.example/operator/cfg", "perms": {"config.write"}}
BG = {"sub": "spiffe://prod.example/operator/bg", "perms": {"control.write", "control.hard_stop", "degraded.override"}}


class Audit(TmpCase):
    @covers("MC-013", 6, 7, 8, 9, 25)
    def test_mc013_schema_chain_and_signed_checkpoints(self):
        t, key = self.trust()
        a = AuditLog(self.d("audit"), signer=key, clock=self.clock)
        for i in range(70):
            a.append(actor="spiffe://p/operator/x", action="topology.mutate", target=f"n{i}", result="ok", request_id=f"r{i}",
                     generation=i, before={"a": 1}, after={"a": 2})
        self.assertEqual(len(a._store.state["checkpoints"]), 1)
        v = a.verify(trust_store=t)
        self.assertTrue(v["ok"], v)
        ev = a.export(principal_roles={"audit.export"})["events"][0]
        for k in ("event_id", "actor", "action", "target", "result", "ts_wall", "ts_mono_ns", "clock_source",
                  "clock_uncertainty_ms", "request_id", "generation", "before_digest", "after_digest"):
            self.assertIn(k, ev)
        self.assertFalse(hasattr(a, "delete"))
        self.assertFalse(hasattr(a, "rewrite"))

    @covers("MC-013", 14, 15, 27)
    def test_mc013_tamper_detection_and_alert(self):
        alerts = []
        a = AuditLog(self.d("audit"), clock=self.clock, alert=alerts.append)
        for i in range(5):
            a.append(actor="x", action="control.create", target="t", result="ok")
        lines = open(a._store.wal_path, "rb").read().split(b"\n")
        lines[2] = lines[2].replace(b'"result":"ok"', b'"result":"no"')
        with open(a._store.wal_path, "wb") as fh:
            fh.write(b"\n".join(lines))
        self.assertFalse(a.verify()["ok"])
        self.assertIn("AUDIT_INTEGRITY_FAILURE", alerts)
        with self.assertRaises(SchedulerError):
            AuditLog(self.d("audit"), clock=self.clock)  # reopen refuses the broken chain

    @covers("MC-013", 10, 11, 27)
    def test_mc013_privileged_events_redacted(self):
        a = AuditLog(self.d("audit"), clock=self.clock)
        a.append(actor="x", action="trust.key_added", target="t", result="ok",
                 detail={"token": "eyJhbGciOi", "nested": {"password": "p", "ok": "fine\nline"}, "path": "/etc/shadow/x"})
        ev = a.export(principal_roles={"audit.export"})["events"][0]
        s = json.dumps(ev)
        self.assertNotIn("eyJhbGciOi", s)
        self.assertNotIn('"p"', s)
        self.assertIn("<redacted>", s)
        self.assertNotIn("\\n", ev["detail"]["nested"]["ok"])

    @covers("MC-013", 12, 13, 17, 27)
    def test_mc013_query_authz_pagination_retention_holds(self):
        """authorization: audit query without audit.read is denied; pagination; retention never deletes held or minimum security evidence."""
        a = AuditLog(self.d("audit"), clock=self.clock)
        for i in range(25):
            a.append(actor="alice" if i % 2 else "bob", action="config.activate", target="c", result="ok", request_id=f"r{i}", generation=i)
        with self.assertRaises(SchedulerError):
            a.query(principal_roles=set())
        p1 = a.query(principal_roles={"audit.read"}, actor="alice", page_size=5)
        self.assertEqual(len(p1["events"]), 5)
        p2 = a.query(principal_roles={"audit.read"}, actor="alice", page_size=5, page_token=p1["next_page_token"])
        self.assertTrue(set(e["event_id"] for e in p1["events"]).isdisjoint(e["event_id"] for e in p2["events"]))
        self.assertEqual(len(a.query(principal_roles={"audit.read"}, generation=3)["events"]), 1)
        a.place_hold(actor="legal", scope="all", reason="case-1", until_ms=int((self.clock() + 10**9) * 1000))
        plan = a.retention_plan(now_ms=int((self.clock() + 900 * 86400) * 1000), retention_days=30)
        self.assertEqual(plan["effective_retention_days"], 400)
        self.assertEqual(plan["deleted"], 0)
        self.assertEqual(plan["eligible_for_cold_archive"], 0)  # hold protects everything

    @covers("MC-013", 15, 21, 27)
    def test_mc013_storage_outage_fails_closed(self):
        alerts = []
        a = AuditLog(self.d("audit"), clock=self.clock, fault=StoreFault("before_write", kind="disk_full"), alert=alerts.append)
        with self.assertRaises(SchedulerError):
            a.append(actor="x", action="y", target="z", result="ok")
        self.assertIn("AUDIT_WRITE_FAILURE", alerts)
        self.assertEqual(a.write_failures, 1)


class Errors(unittest.TestCase):
    @covers("MC-014", 6, 7, 13, 25)
    def test_mc014_catalog_complete_and_versioned(self):
        cat = errors.catalog()
        for c in [x for x in cat if "code" in x]:
            for k in ("category", "http_status", "grpc_status", "retryable", "severity", "owner", "template", "stability"):
                self.assertIn(k, c)
        self.assertEqual(errors.ERROR_NAMESPACE, "GAP03-ERR/1")
        self.assertEqual(errors.SchedulerError("PROTECTED_RESERVATION").code, "FAIRNESS_DENIED")
        with self.assertRaises(ValueError):
            errors.SchedulerError("MADE_UP")

    @covers("MC-014", 8, 9, 10, 15, 25, 26)
    def test_mc014_golden_mapping_of_every_public_failure(self):
        golden = [
            (StaleFairShare("x"), "STALE_STATE", 409, True), (ReservationOversubscribed("x"), "FAIRNESS_DENIED", 429, False),
            (ShareViolation("denied (capacity_exhausted)"), "NO_CAPACITY", 503, True),
            (ShareViolation("denied (protected_reservation)"), "FAIRNESS_DENIED", 429, False),
            (NotInTopology("n"), "NOT_IN_TOPOLOGY", 404, False), (TopologyConflict("x"), "CONFLICT", 409, False),
            (TimeoutError(), "DEADLINE_EXCEEDED", 504, True), (ValueError("bad"), "INVALID_ARGUMENT", 400, False),
            (RuntimeError("boom"), "INTERNAL", 500, False), (KeyError("k"), "INTERNAL", 500, False),
        ]
        for exc, code, status, retry in golden:
            ext = errors.to_external(exc, correlation_id="c1")
            self.assertEqual((ext["code"], ext["http_status"], ext["retryable"]), (code, status, retry), exc)
            self.assertNotIn("Traceback", json.dumps(ext))
            self.assertNotIn(type(exc).__name__, ext["message"])

    @covers("MC-014", 11, 12, 20, 27)
    def test_mc014_payloads_redacted_and_cause_depth_bounded(self):
        e = errors.SchedulerError("INVALID_ARGUMENT", "bad /srv/gap03/secret/path token=abc123 \x00" + "x" * 500)
        for _ in range(10):
            e = errors.SchedulerError("DEPENDENCY_UNAVAILABLE", "wrap", cause=e)
        ext = errors.to_external(e)
        self.assertLessEqual(len(ext["cause_chain"]), errors.MAX_CAUSE_DEPTH)
        inner = errors.to_external(errors.SchedulerError("INVALID_ARGUMENT", "bad /srv/gap03/secret/path token=abc123"))
        self.assertNotIn("/srv/gap03", inner["reason"])
        self.assertNotIn("abc123", inner["reason"])
        self.assertLessEqual(len(errors.to_external(errors.SchedulerError("INVALID_ARGUMENT", "y" * 9999))["reason"]), 256)

    @covers("MC-014", 14, 23)
    def test_mc014_error_counters_bounded_cardinality(self):
        from gap03_topology_aware_scheduler.controlplane.metrics import Metrics
        m = Metrics()
        for code in errors.CODES:
            m.inc("gap03_requests_total", op="score", code=code)
        self.assertEqual(m.get("gap03_requests_total", code="OVERLOADED", op="score"), 1)
        with self.assertRaises(ValueError):
            m.inc("gap03_requests_total", op="score", code="x", tenant="t1")


class Config(TmpCase):
    def mgr(self, **kw):
        return ConfigManager(ConfigStore(self.d("cfg"), clock=self.clock), clock=self.clock, **kw)

    @covers("MC-015", 6, 8, 25)
    def test_mc015_schema_validation(self):
        good = cfgmod.validate({"scoring": {"weight_gravity": 10}})
        self.assertEqual(good["scoring"]["weight_locality"], 1000)
        for bad in [{"scoring": {"weight_locality": -1}}, {"nope": {}}, {"scoring": {"zzz": 1}},
                    {"scoring": {"weight_cost": 1}}, {"secrets": {"signing_key": "plaintext"}},
                    {"features": {"latency_refinement": True}, "safety": {"fail_open_scoring": True}},
                    {"scoring": {"weight_locality": 0}}, {"schema_version": 7}]:
            with self.assertRaises(SchedulerError, msg=bad):
                cfgmod.validate(bad)
        self.assertEqual(cfgmod.validate({"schema_version": 1, "scoring": {"weight_cost": 5}})["scoring"]["weight_latency"], 5)

    @covers("MC-015", 7, 25)
    def test_mc015_precedence(self):
        t, key = self.trust()
        m = self.mgr(trust=t)
        doc = {"scoring": {"weight_gravity": 5}, "ttl": {"inventory_s": 100}}
        env = identity.sign_artifact(key, "config", doc)
        v = m.build(document=doc, envelope=env, environ={"GAP03_CFG__TTL__INVENTORY_S": "200"}, cli={"ttl": {"inventory_s": 300}})
        self.assertEqual(v["ttl"]["inventory_s"], 300)
        v = m.build(document=doc, envelope=env, environ={"GAP03_CFG__TTL__INVENTORY_S": "200"})
        self.assertEqual(v["ttl"]["inventory_s"], 200)
        self.assertEqual(v["scoring"]["weight_gravity"], 5)
        with self.assertRaises(SchedulerError):
            m.build(document=dict(doc, ttl={"inventory_s": 11}), envelope=env)  # tampered signed doc

    @covers("MC-015", 9, 10, 12, 25)
    def test_mc015_transactional_activation_and_rollback(self):
        audit = self.audit()
        m = self.mgr(audit=audit)
        g1 = m.current.generation
        s2 = m.activate(cfgmod.validate({"scoring": {"weight_gravity": 7}}), actor="ops", source="file", principal=CFG)
        self.assertEqual(s2.generation, g1 + 1)
        self.assertEqual(s2.get("scoring.weight_gravity"), 7)
        with self.assertRaises(TypeError):
            s2.values["scoring"]["weight_gravity"] = 1  # immutable
        s3 = m.rollback(g1, principal=CFG)
        self.assertEqual(s3.get("scoring.weight_gravity"), 0)
        self.assertEqual(m.store.state["history"][str(s3.generation)]["rollback_of"], g1)
        self.assertIn("config.rollback", [e["action"] for e in audit.export(principal_roles={"audit.export"})["events"]])
        m2 = self.mgr()
        self.assertEqual(m2.current.generation, s3.generation)  # survives restart

    @covers("MC-015", 11, 13, 25)
    def test_mc015_dry_run_risk_ack_and_redaction(self):
        m = self.mgr()
        risky = cfgmod.validate({"safety": {"require_attestation": False}})
        dr = m.dry_run(risky)
        self.assertTrue(any(x["field"] == "safety.require_attestation" for x in dr["risky"]))
        with self.assertRaises(SchedulerError):
            m.activate(risky, actor="ops", source="cli", principal=CFG)
        m.activate(risky, actor="ops", source="cli", acknowledge_risk=True, principal=CFG)
        self.assertEqual(cfgmod.redacted(cfgmod.defaults())["secrets"]["signing_key"], "<secret-ref>")

    @covers("MC-015", 14, 15, 22, 27)
    def test_mc015_concurrent_updates_and_partial_source_failure(self):
        m = self.mgr()
        g = m.current.generation
        ok = []

        def w(i):
            try:
                m.activate(cfgmod.validate({"scoring": {"weight_gravity": i}}), actor="a", source="x", expected_generation=g, principal=CFG)
                ok.append(i)
            except SchedulerError:
                pass
        ts = [threading.Thread(target=w, args=(i,)) for i in range(1, 7)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(ok), 1)
        before = m.current
        with self.assertRaises(SchedulerError):
            m.build(environ={"GAP03_CFG__TTL__INVENTORY_S": "abc"})
        self.assertIs(m.current, before)  # failed source never half-applies


class Degraded(TmpCase):
    @covers("MC-016", 6, 7, 10, 25)
    def test_mc016_matrix_complete_and_commit_blocked_without_proof(self):
        for dep, (rules, ttl) in MATRIX.items():
            self.assertEqual(set(rules), {"score", "commit", "topology_mutate", "explain", "health"}, dep)
        p = DegradedPolicy(clock=self.clock)
        for dep in ("identity", "coordination", "audit", "ledger", "topology_store", "time", "sch01"):
            with self.subTest(dep=dep):
                p = DegradedPolicy(clock=self.clock)
                p.report(dep, False)
                self.assertFalse(p.decide("commit")["allowed"])
                self.assertTrue(p.decide("explain")["allowed"] or dep == "identity")

    @covers("MC-016", 11, 27)
    def test_mc016_stale_ttl_and_generation_provenance(self):
        p = DegradedPolicy(clock=self.clock)
        p.report("gap02", True, generation=5)
        p.report("gap02", False)
        self.assertTrue(p.decide("score")["allowed"])
        self.clock.advance(301)
        self.assertFalse(p.decide("score")["allowed"])
        self.assertTrue(p.is_stale_generation("gap02", 4))
        self.assertFalse(p.is_stale_generation("gap02", 5))

    @covers("MC-013", 10)

    @covers("MC-016", 12, 17, 27)
    def test_mc016_override_scoped_authorized_audited_expiring(self):
        audit = self.audit()
        p = DegradedPolicy(clock=self.clock, audit=audit)
        p.report("gap02", False)
        self.clock.advance(400)
        with self.assertRaises(SchedulerError):
            p.override(principal=OPS, dependency="gap02", op="score", scope={}, duration_s=60, risk_ack="x" * 25)
        with self.assertRaises(SchedulerError):
            p.override(principal=BG, dependency="gap02", op="score", scope={}, duration_s=60, risk_ack="short")
        with self.assertRaises(SchedulerError):
            p.override(principal=BG, dependency="identity", op="commit", scope={}, duration_s=60, risk_ack="x" * 25)
        p.override(principal=BG, dependency="gap02", op="score", scope={"tenant": "t1"}, duration_s=60,
                   risk_ack="inventory feed down; scoring with stale hardware facts for t1")
        self.assertTrue(p.decide("score", scope={"tenant": "t1"})["allowed"])
        self.assertFalse(p.decide("score", scope={"tenant": "t2"})["allowed"])
        self.clock.advance(61)
        self.assertFalse(p.decide("score", scope={"tenant": "t1"})["allowed"])
        self.assertEqual(audit.export(principal_roles={"audit.export"})["events"][-1]["action"], "degraded.override")

    @covers("MC-016", 13, 14)
    def test_mc016_recovery_requires_reconciliation(self):
        p = DegradedPolicy(clock=self.clock)
        p.report("ledger", False)
        p.report("ledger", True)
        self.assertEqual(p.decide("commit")["reason"], "recovery_reconciliation_pending")
        p.mark_reconciled()
        self.assertTrue(p.decide("commit")["allowed"])
        h = p.health()
        self.assertIn("_recovery_order", h)
        self.assertIn("stale_age_s", h["ledger"])

    @covers("MC-016", 8)
    def test_mc016_breaker_bounds_dependency_calls(self):
        from gap03_topology_aware_scheduler.controlplane.admission import CircuitBreaker
        br = CircuitBreaker("gap14", threshold=3, cooldown=10, clock=self.clock)
        calls = []

        def bad():
            calls.append(1)
            raise ConnectionError()
        for _ in range(10):
            try:
                br.call(bad)
            except Exception:
                pass
        self.assertEqual(len(calls), 3)
        self.assertEqual(br.state, "open")


class ControlsT(TmpCase):
    def mk(self, audit=None):
        return Controls(ControlStore(self.d("ctl"), clock=self.clock), clock=self.clock, audit=audit)

    @covers("MC-017", 6, 7, 10, 25)
    def test_mc017_scopes_modes_and_commit_path(self):
        c = self.mk()
        c.create(OPS, control_id="c1", scope_kind="tenant", scope_value="t1", mode="freeze-new", reason="incident", ticket="INC-1", ttl_s=600)
        with self.assertRaises(SchedulerError) as cm:
            c.check("placement.commit", scope={"tenant": "t1"})
        self.assertEqual(cm.exception.code, "FROZEN")
        c.check("placement.commit", scope={"tenant": "t2"})
        c.check("explain", scope={"tenant": "t1"})
        c.create(OPS, control_id="c2", scope_kind="node", scope_value="n9", mode="quarantine", reason="bad disk", ticket="INC-2", ttl_s=600)
        with self.assertRaises(SchedulerError):
            c.check("placement.commit", scope={"tenant": "t2", "node": "n9"})

    @covers("MC-013", 10)

    @covers("MC-017", 8, 12, 17, 27)
    def test_mc017_authorization_break_glass_dual_approval(self):
        """authorization for high-blast-radius controls: break-glass + dual approval; denied attempts audited."""
        audit = self.audit()
        c = self.mk(audit=audit)
        with self.assertRaises(SchedulerError):
            c.create({"sub": "x", "perms": set()}, control_id="c", scope_kind="tenant", scope_value="t", mode="drain",
                     reason="r", ticket="t", ttl_s=60)
        with self.assertRaises(SchedulerError):
            c.create(OPS, control_id="c", scope_kind="global", scope_value="*", mode="hard-stop", reason="r", ticket="t", ttl_s=60)
        with self.assertRaises(SchedulerError):
            c.create(BG, control_id="c", scope_kind="global", scope_value="*", mode="hard-stop", reason="r", ticket="t", ttl_s=60)
        c.create(BG, control_id="c", scope_kind="global", scope_value="*", mode="hard-stop", reason="r", ticket="t", ttl_s=60,
                 approvers=("spiffe://prod.example/operator/second",))
        self.assertIn("denied", [e["result"] for e in audit.export(principal_roles={"audit.export"})["events"]])

    @covers("MC-017", 9, 14, 15, 27)
    def test_mc017_persistence_expiry_idempotency_occ(self):
        c = self.mk()
        g = c.create(OPS, control_id="c1", scope_kind="site", scope_value="dub", mode="disable-commit", reason="r", ticket="t", ttl_s=100)
        self.assertEqual(c.create(OPS, control_id="c1", scope_kind="site", scope_value="dub", mode="disable-commit", reason="r",
                                  ticket="t", ttl_s=100), g)  # idempotent
        c2 = self.mk()  # restart
        self.assertEqual(len(c2.active()), 1)
        with self.assertRaises(SchedulerError):
            c2.extend(OPS, "c1", 100, expected_generation=g - 1)
        c2.extend(OPS, "c1", 1000, expected_generation=g)
        self.clock.advance(500)
        self.assertEqual(len(c2.active()), 1)
        self.clock.advance(600)
        self.assertEqual(c2.active(), [])

    @covers("MC-017", 11, 20)
    def test_mc017_drain_and_redacted_summary(self):
        c = self.mk()
        c.create(OPS, control_id="d", scope_kind="tenant", scope_value="t1", mode="drain", reason="secret reason", ticket="INC-9",
                 ttl_s=600, drain_deadline_s=100)
        c.check("placement.commit", scope={"tenant": "t1"}, inflight=True)
        with self.assertRaises(SchedulerError):
            c.check("placement.commit", scope={"tenant": "t1"}, inflight=False)
        self.clock.advance(101)
        with self.assertRaises(SchedulerError):
            c.check("placement.commit", scope={"tenant": "t1"}, inflight=True)
        self.assertNotIn("secret reason", json.dumps(c.summary(privileged=False)))
        self.assertIn("secret reason", json.dumps(c.summary(privileged=True)))

    @covers("MC-007", 26)

    @covers("MC-017", 15, 27)
    def test_mc017_freeze_after_prepare_is_revalidated_before_commit(self):
        from gap03_topology_aware_scheduler import Topology
        from gap03_topology_aware_scheduler.controlplane.adapters.sch01 import SCH01Harness
        from gap03_topology_aware_scheduler.controlplane.ledger_store import LedgerStore
        from gap03_topology_aware_scheduler.controlplane.transactions import PlacementCoordinator, TxnJournal
        c = self.mk()
        led = LedgerStore(self.d("led"))
        led.submit({"type": "set_capacity", "capacity": 2})
        led.submit({"type": "set_reservations", "reserved": {"t1": 1}, "entitlement_generation": 1})
        topo = Topology()
        topo.place("a", "eu", "d", "r")
        topo.place("b", "eu", "d", "r2")
        down = SCH01Harness()

        class Racing:
            def __init__(s):
                s.n = 0

            def check(s, op, scope, inflight=False):
                s.n += 1
                if s.n == 2:  # a freeze lands between prepare and commit
                    c.create(OPS, control_id="race", scope_kind="tenant", scope_value="t1", mode="freeze-new",
                             reason="r", ticket="t", ttl_s=60)
                c.check(op, scope=scope, inflight=inflight)
        pc = PlacementCoordinator(journal=TxnJournal(self.d("j")), ledger=led, topology_snapshot=topo.snapshot, downstream=down,
                                  fence=lambda: 1, controls=Racing())
        r = pc.place(txn="x", workload={"id": "w"}, anchor="a", candidates=["b"], tenant="t1")
        self.assertEqual(r["state"], "ABORTED")
        self.assertEqual(r["reason"], "FROZEN")
        self.assertEqual(down.placements, {})
        self.assertEqual(led.state["claims"]["x"]["state"], "aborted")


class HealthT(TmpCase):
    def mk(self, checks):
        h = Health(checks=checks, info=lambda: {"config_generation": 3, "topology_generation": 7, "ledger_revision": 9,
                                                "coordination": {"role": "leader", "term": 4}})
        h.started = True
        return h

    @covers("MC-018", 6, 8, 25)
    def test_mc018_distinct_probes_and_readiness_semantics(self):
        state = {"lease": True}
        h = self.mk({"lease": lambda: (state["lease"], "held"), "audit": lambda: (True, "ok")})
        self.assertEqual(h.livez()["status"], "ok")
        self.assertEqual(h.readyz()["status"], "not_ready")  # hysteresis: needs 2 good
        self.assertEqual(h.readyz()["status"], "ready")
        state["lease"] = False
        r = h.readyz()
        self.assertEqual(r["status"], "not_ready")
        self.assertEqual(r["failing"], ["lease"])
        self.assertEqual(h.livez()["status"], "ok")  # liveness unaffected
        deep = h.deep(authorized=True)
        for k in ("version", "config_generation", "topology_generation", "ledger_revision", "coordination"):
            self.assertIn(k, deep)

    @covers("MC-018", 9, 12, 27)
    def test_mc018_hung_dependency_cannot_block_probe(self):
        ev = threading.Event()
        h = self.mk({"hung": lambda: (ev.wait(5), "x"), "ok": lambda: (True, "ok")})
        t = time.perf_counter()
        r = h.readyz()
        ev.set()
        self.assertLess(time.perf_counter() - t, 1.0)
        self.assertIn("hung", r["failing"])

    @covers("MC-018", 11, 13, 14, 26)
    def test_mc018_http_endpoints_and_deep_auth(self):
        """integration: real HTTP endpoints; readiness hysteresis on the wire; deep diagnostics need authorization; shutdown drops readiness."""
        h = self.mk({"ok": lambda: (True, "ok")})
        srv, _ = serve(h, deep_token="s3cret")
        try:
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            self.assertEqual(urllib.request.urlopen(base + "/livez").status, 200)
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(base + "/readyz")
            self.assertEqual(cm.exception.code, 503)
            self.assertEqual(urllib.request.urlopen(base + "/readyz").status, 200)
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(base + "/healthz/deep")
            self.assertEqual(cm.exception.code, 403)
            req = urllib.request.Request(base + "/healthz/deep", headers={"Authorization": "Bearer s3cret"})
            body = json.loads(urllib.request.urlopen(req).read())
            self.assertIn("slo", body)
            h.shutting_down = True
            with self.assertRaises(urllib.error.HTTPError):
                urllib.request.urlopen(base + "/readyz")
        finally:
            srv.shutdown()
            srv.server_close()
