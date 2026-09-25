"""Production-component tests for INV-06 v4.3.0 (MC-010 … MC-071 package-local references).

Test classes map to checklist components; ``tests/TEST_MAP.json`` records the
mapping used by the traceability matrix.  Runs with the standard library only.
"""
from __future__ import annotations

import importlib
import io
import json
import multiprocessing as mp
import os
import pathlib
import random
import string
import sys
import tempfile
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
NAME = PKG_DIR.name
pkg = importlib.import_module(NAME)
durable = importlib.import_module(NAME + ".durable")
locking = importlib.import_module(NAME + ".locking")
graph = importlib.import_module(NAME + ".graph")
config = importlib.import_module(NAME + ".config")
security = importlib.import_module(NAME + ".security")
resilience = importlib.import_module(NAME + ".resilience")
policy = importlib.import_module(NAME + ".policy")
obs = importlib.import_module(NAME + ".observability")
execution = importlib.import_module(NAME + ".execution")
release = importlib.import_module(NAME + ".release")
service = importlib.import_module(NAME + ".service")

KEYS = security.StaticKeyProvider(
    {"k1": b"k" * 32, "k2": b"q" * 32},
    {"authn": "k1", "plan": "k1", "audit": "k1", "evidence": "k1"},
)


class Tmp(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._td.name)

    def tearDown(self) -> None:
        self._td.cleanup()


# ---------------------------------------------------------------- MC-010/012
class DurableBackendTest(Tmp):
    def test_commit_load_roundtrip_and_cas(self):
        be = durable.FileStateBackend(self.tmp / "s")
        s = pkg.IacState()
        s.apply(s.plan({"vm.a": {"size": 1}}))
        self.assertEqual(be.commit_state(s, expected_serial=None), 1)
        self.assertEqual(be.load()["resources"], {"vm.a": {"size": 1}})
        with self.assertRaises(durable.StateConflict):
            be.commit_state(s, expected_serial=None)  # stale writer
        s2 = be.load_state()
        s2.apply(s2.plan({"vm.a": {"size": 2}}))
        self.assertEqual(be.commit_state(s2, expected_serial=1), 2)
        self.assertTrue(be.verify_chain())

    def test_serial_must_advance(self):
        be = durable.FileStateBackend(self.tmp / "s")
        be.commit({"schema": pkg.STATE_SCHEMA, "serial": 3, "resources": {}, "protected": [], "audit_head": "0" * 64}, expected_serial=None)
        with self.assertRaises(durable.StateConflict):
            be.commit({"schema": pkg.STATE_SCHEMA, "serial": 3, "resources": {}, "protected": [], "audit_head": "0" * 64}, expected_serial=3)

    def test_corruption_detected_before_use(self):
        be = durable.FileStateBackend(self.tmp / "s")
        s = pkg.IacState({"vm.a": 1})
        be.commit_state(s, expected_serial=None)
        path = be._rev_path(0)
        rec = json.loads(path.read_text())
        rec["state"]["resources"]["vm.a"] = 999
        path.write_text(json.dumps(rec))
        with self.assertRaises(durable.StateCorrupt):
            be.load()

    def test_size_limit(self):
        be = durable.FileStateBackend(self.tmp / "s", max_state_bytes=200)
        with self.assertRaises(durable.StateTooLarge):
            be.commit_state(pkg.IacState({f"vm.r{i}": "x" * 50 for i in range(10)}), expected_serial=None)
        self.assertIsNone(be.head_serial())

    def test_crash_between_revision_and_head_rolls_back(self):
        be = durable.FileStateBackend(self.tmp / "s")
        be.commit_state(pkg.IacState({"vm.a": 1}), expected_serial=None)
        # Simulate a crash after intent + revision write but before HEAD moved.
        rec = durable.seal_snapshot({"schema": pkg.STATE_SCHEMA, "serial": 1, "resources": {"vm.a": 2}, "protected": [], "audit_head": "0" * 64}, parent_digest=be.read_revision(0)["digest"])
        be._journal({"op": "intent", "txid": rec["digest"][:16], "serial": 1, "parent": 0, "digest": rec["digest"]})
        durable.atomic_write(be._rev_path(1), json.dumps(rec).encode())
        out = durable.FileStateBackend(self.tmp / "s").recover()
        self.assertEqual(out["rolled_back"], [1])
        self.assertEqual(be.head_serial(), 0)
        self.assertFalse(be._rev_path(1).exists())

    def test_crash_after_head_before_commit_rolls_forward(self):
        be = durable.FileStateBackend(self.tmp / "s")
        be.commit_state(pkg.IacState({"vm.a": 1}), expected_serial=None)
        rec = durable.seal_snapshot({"schema": pkg.STATE_SCHEMA, "serial": 1, "resources": {"vm.a": 2}, "protected": [], "audit_head": "0" * 64}, parent_digest=be.read_revision(0)["digest"])
        be._journal({"op": "intent", "txid": rec["digest"][:16], "serial": 1, "parent": 0, "digest": rec["digest"]})
        durable.atomic_write(be._rev_path(1), durable._canonical_bytes(rec))
        durable.atomic_write(be.head_path, b"1")
        out = be.recover()
        self.assertEqual(out["rolled_forward"], [1])
        self.assertEqual(be.load()["resources"], {"vm.a": 2})

    def test_torn_journal_line_is_tolerated(self):
        be = durable.FileStateBackend(self.tmp / "s")
        be.commit_state(pkg.IacState({"vm.a": 1}), expected_serial=None)
        with open(be.journal_path, "ab") as fh:
            fh.write(b'{"op":"inte')
        self.assertEqual(be.load()["serial"], 0)

    def test_migration_from_v0_and_refusal_of_unknown(self):
        snap = durable.migrate_snapshot({"resources": {"a.b": 1}, "serial": 4, "protected": ["a.b"]})
        self.assertEqual(snap["schema"], pkg.STATE_SCHEMA)
        with self.assertRaises(pkg.InvalidState):
            durable.migrate_snapshot({"schema": "PK_IAC_STATE/9", "resources": {}, "serial": 0})


# ---------------------------------------------------------------- MC-013/014
class RollbackBackupTest(Tmp):
    def _be(self):
        be = durable.FileStateBackend(self.tmp / "s")
        s = pkg.IacState()
        for v in (1, 2, 3):
            s.apply(s.plan({"vm.a": v}))
            be.commit_state(s, expected_serial=be.head_serial())
        return be

    def test_rollback_creates_new_serial(self):
        be = self._be()
        new = be.rollback_to(1, expected_serial=3, actor="ops", reason="bad change")
        self.assertEqual(new, 4)
        self.assertEqual(be.load()["resources"], {"vm.a": 1})
        self.assertEqual(be.read_revision(4)["meta"]["restored_from"], 1)
        with self.assertRaises(durable.RollbackRefused):
            be.rollback_to(1, expected_serial=4, actor="", reason="")
        with self.assertRaises(durable.StateConflict):
            be.rollback_to(1, expected_serial=3, actor="ops", reason="x")

    def test_backup_restore_verifies(self):
        be = self._be()
        arc = self.tmp / "b.tgz"
        man = be.backup(arc)
        self.assertEqual(man["head"], 3)
        be2 = durable.FileStateBackend.restore(arc, self.tmp / "r")
        self.assertEqual(be2.load(), be.load())
        with self.assertRaises(durable.RollbackRefused):
            durable.FileStateBackend.restore(arc, self.tmp / "r")

    def test_restore_rejects_tampered_archive(self):
        import tarfile

        be = self._be()
        arc = self.tmp / "b.tgz"
        be.backup(arc)
        bad = self.tmp / "bad.tgz"
        with tarfile.open(arc) as src, tarfile.open(bad, "w:gz") as dst:
            for m in src.getmembers():
                data = src.extractfile(m).read()
                if m.name.endswith("000000000003.json"):
                    tampered = data.replace(b'"vm.a":3', b'"vm.a":9')
                    self.assertNotEqual(tampered, data)
                    data = tampered
                m.size = len(data)
                dst.addfile(m, io.BytesIO(data))
        with self.assertRaises(durable.StateCorrupt):
            durable.FileStateBackend.restore(bad, self.tmp / "r2")


# ---------------------------------------------------------------- MC-011
def _contend(root: str, q: "mp.Queue") -> None:
    sys.path.insert(0, str(ROOT))
    lk = importlib.import_module(NAME + ".locking")
    try:
        lease = lk.FileLeaseLock(root).acquire(f"p{os.getpid()}", ttl=30)
        q.put(("ok", lease.token))
    except lk.LockUnavailable:
        q.put(("busy", None))


class LockingTest(Tmp):
    def test_mutual_exclusion_and_fencing(self):
        now = [1000.0]
        lk = locking.FileLeaseLock(self.tmp / "l", clock=lambda: now[0])
        be = durable.FileStateBackend(self.tmp / "s")
        fb = locking.FencedBackend(be, lk)
        a = lk.acquire("a", ttl=10)
        with self.assertRaises(locking.LockUnavailable):
            lk.acquire("b", ttl=10)
        now[0] += 11  # a's lease expires while "paused"
        b = lk.acquire("b", ttl=10)
        self.assertGreater(b.token, a.token)
        snap = pkg.IacState({"vm.x": 1}).snapshot()
        with self.assertRaises(locking.LeaseLost):
            fb.commit(snap, lease=a, expected_serial=None)
        self.assertEqual(fb.commit(snap, lease=b, expected_serial=None), 0)
        lk.release(b)
        self.assertIsNone(lk.current())

    def test_renew_after_takeover_fails(self):
        now = [0.0]
        lk = locking.FileLeaseLock(self.tmp / "l", clock=lambda: now[0])
        a = lk.acquire("a", ttl=1)
        now[0] = 2
        lk.acquire("b", ttl=5)
        with self.assertRaises(locking.LeaseLost):
            lk.renew(a)

    def test_cross_process_exclusion(self):
        ctx = mp.get_context("spawn")
        q = ctx.Queue()
        procs = [ctx.Process(target=_contend, args=(str(self.tmp / "l"), q)) for _ in range(4)]
        for p in procs:
            p.start()
        for p in procs:
            p.join(30)
        results = [q.get(timeout=5) for _ in procs]
        self.assertEqual(sum(1 for r in results if r[0] == "ok"), 1, results)


# ---------------------------------------------------------------- MC-016/017/024/025
HCL = '''
# comment
resource "net" "vpc" { cidr = "10.0.0.0/16" }
resource "vm" "web" {
  size = "small"
  subnet = "${net.vpc.id}"
  count = 2
  tags = ["a", "b"]
  meta = { owner = "team", ha = true }
}
resource "dns" "www" { target = "${vm.web.ip}" depends_on = ["net.vpc"] }
'''


class ConfigGraphTest(Tmp):
    def test_parse_compile_order(self):
        res = config.parse_hcl_subset(HCL)
        self.assertEqual(res["vm.web"]["meta"], {"owner": "team", "ha": True})
        c = config.compile_config(res, {"environment": {"vm.web": {"size": "large"}}, "site": {"vm.web": {"meta": {"ha": False}}}})
        self.assertEqual(c["order"], ["net.vpc", "vm.web", "dns.www"])
        self.assertEqual(c["desired"]["vm.web"]["size"], "large")
        self.assertEqual(c["desired"]["vm.web"]["meta"], {"owner": "team", "ha": False})

    def test_parser_refuses_outside_subset(self):
        for bad in ['variable "x" {}', 'resource "a" "b" { x = var.y }', 'resource "a" "b" { x = 1 x = 2 }',
                    'resource "a" "b" {} resource "a" "b" {}', 'resource "a b" "c" {}', 'resource "a" "b" { x = <<EOF }']:
            with self.assertRaises(config.ConfigError, msg=bad):
                config.parse_hcl_subset(bad)

    def test_overlay_cannot_add_resources_or_unknown_layer(self):
        res = config.parse_hcl_subset(HCL)
        with self.assertRaises(config.ConfigError):
            config.compile_config(res, {"site": {"vm.evil": {}}})
        with self.assertRaises(config.ConfigError):
            config.compile_config(res, {"tenant": {}})

    def test_graph_cycles_dangling_and_dependents(self):
        with self.assertRaises(graph.GraphError):
            graph.ResourceGraph({"a.a": "${b.b.x}", "b.b": "${a.a.x}"})
        with self.assertRaises(graph.GraphError):
            graph.ResourceGraph({"a.a": "${z.z.x}"})
        g = graph.ResourceGraph(config.parse_hcl_subset(HCL))
        self.assertEqual(g.dependents("net.vpc"), {"vm.web", "dns.www"})
        self.assertEqual(g.destroy_order(), ["dns.www", "vm.web", "net.vpc"])

    def test_provenance_ledger(self):
        led = config.ProvenanceLedger(self.tmp / "prov.jsonl")
        a = led.record(config_digest="d1", source_revision="r1", actor="alice", environment="prod", approval="CR-1")
        b = led.record(config_digest="d2", source_revision="r2", actor="bob", environment="prod", approval="CR-2")
        self.assertIsNone(a["rollback_to"])
        self.assertEqual(b["rollback_to"], "d1")
        self.assertTrue(led.verify())
        with self.assertRaises(config.ConfigError):
            led.record(config_digest="d3", source_revision="r3", actor="", environment="prod", approval="x")
        lines = led.path.read_text().splitlines()
        lines[0] = lines[0].replace("alice", "mallory")
        led.path.write_text("\n".join(lines) + "\n")
        self.assertFalse(led.verify())


# ---------------------------------------------------------------- MC-009/022/023
class PolicyTest(unittest.TestCase):
    def setUp(self):
        self.s = pkg.IacState({"vm.a": 1})
        self.plan = self.s.plan({"sg.web": {"ingress": "0.0.0.0/0"}})

    def test_deny_with_reasons(self):
        gate = policy.PolicyGate(policy.RulePolicyEngine("p-1", {"ingress": policy.forbid_public_ingress, "del": policy.no_delete_in_prod}))
        with self.assertRaises(policy.PolicyDenied) as cm:
            gate.check(self.plan)
        self.assertEqual(len(cm.exception.details["reasons"]), 2)

    def test_fail_closed(self):
        class Boom:
            def evaluate(self, r):
                raise TimeoutError()

        class Unbound:
            def evaluate(self, r):
                return {"schema": policy.DECISION_SCHEMA, "allow": True, "plan_digest": "x", "policy_version": "v"}

        for eng in (Boom(), Unbound()):
            with self.assertRaises(policy.PolicyUnavailable):
                policy.PolicyGate(eng).check(self.plan)
        ok = policy.RulePolicyEngine("p-2", {})
        with self.assertRaises(policy.PolicyUnavailable):
            policy.PolicyGate(ok, required_version="p-1").check(self.plan)
        self.assertTrue(policy.PolicyGate(ok, required_version="p-2").check(self.plan)["allow"])

    def test_constraint_precedence(self):
        r = policy.resolve_constraints([
            {"class": "operator_override", "key": "region", "value": "us"},
            {"class": "residency", "key": "region", "value": "eu"},
            {"class": "cost", "key": "size", "value": "small"},
        ])
        self.assertEqual(r["region"], {"value": "eu", "decided_by": "residency"})
        with self.assertRaises(policy.ConstraintConflict):
            policy.resolve_constraints([{"class": "security", "key": "k", "value": 1}, {"class": "security", "key": "k", "value": 2}])

    def test_inv_adapters(self):
        d = policy.InventoryIngest.to_desired({"schema": policy.INVENTORY_SCHEMA, "hosts": [{"id": "h1", "os": "linux"}]})
        self.assertEqual(d, {"host.h1": {"os": "linux"}})
        with self.assertRaises(policy.HandoffInvalid):
            policy.InventoryIngest.to_desired({"schema": policy.INVENTORY_SCHEMA, "hosts": [{"id": "../x"}]})
        s = pkg.IacState()
        p = s.plan(d)
        serial = s.apply(p)
        doc = policy.GitOpsHandoff.build(p, applied_serial=serial, source_revision="abc")
        policy.GitOpsHandoff.verify(doc)
        doc["changes"]["delete"].append("host.h1")
        with self.assertRaises(policy.HandoffInvalid):
            policy.GitOpsHandoff.verify(doc)
        h = policy.DynamicPoolHandoff.build(s.snapshot(), ["host.h1"], "pool-a")
        self.assertEqual(h["from_serial"], 1)


# ---------------------------------------------------------------- MC-033…041
class SecurityTest(Tmp):
    def test_authn_authz_tenant_and_sod(self):
        now = [100.0]
        auth = security.TokenAuthenticator(KEYS, "inv06", clock=lambda: now[0])
        tok = auth.issue("alice", "operator", "t1", ["planner"])
        p = auth.authenticate(tok)
        az = security.Authorizer()
        az.check(p, "plan.create", tenant="t1")
        with self.assertRaises(security.AccessDenied):
            az.check(p, "apply", tenant="t1")
        with self.assertRaises(security.TenantBoundaryViolation):
            az.check(p, "plan.create", tenant="t2")
        with self.assertRaises(security.AccessDenied):
            az.check(p, "root.shell", tenant="t1")
        with self.assertRaises(security.AccessDenied):
            security.Authorizer.separation_of_duties("alice", "alice")
        now[0] += 10_000
        with self.assertRaises(security.AuthenticationFailed):
            auth.authenticate(tok)

    def test_authn_rejects_forged_and_malformed(self):
        auth = security.TokenAuthenticator(KEYS, "inv06")
        other = security.TokenAuthenticator(security.StaticKeyProvider({"k1": b"z" * 32}, {"authn": "k1"}), "inv06")
        for bad in (None, "", "garbage", other.issue("eve", "operator", "t1", ["applier"]), "A" * 9000,
                    security.TokenAuthenticator(KEYS, "other-aud").issue("eve", "operator", "t1", [])):
            with self.assertRaises(security.AuthenticationFailed):
                auth.authenticate(bad)

    def test_signed_plan_and_key_rotation(self):
        signer = security.Signer(KEYS, "plan")
        s = pkg.IacState()
        sp = security.sign_plan(s.plan({"vm.a": 1}), signer, approver="bob")
        s.apply(security.verify_signed_plan(sp, signer))
        forged = dict(sp)
        forged["authorization"] = dict(sp["authorization"], approver="mallory")
        with self.assertRaises(security.SignatureInvalid):
            security.verify_signed_plan(forged, signer)
        keys = security.StaticKeyProvider({"k1": b"k" * 32}, {"plan": "k1"})
        sg = security.Signer(keys, "plan")
        env = sg.sign({"x": 1})
        keys.rotate("plan", "k2", b"n" * 32)
        sg.verify({"x": 1}, env)  # old key still verifies
        keys.revoke("k1")
        with self.assertRaises(security.SignatureInvalid):
            sg.verify({"x": 1}, env)
        with self.assertRaises(security.SignatureInvalid):
            security.Signer(KEYS, "audit").verify({"x": 1}, security.Signer(KEYS, "plan").sign({"x": 1}))  # purpose binding

    def test_artifact_verification(self):
        f = self.tmp / "bin"
        f.write_bytes(b"engine")
        import hashlib

        d = hashlib.sha256(b"engine").hexdigest()
        security.verify_artifact(f, expected_sha256=d, allowlist={"tf": d}, name="tf")
        with self.assertRaises(security.SignatureInvalid):
            security.verify_artifact(f, expected_sha256="0" * 64)
        with self.assertRaises(security.SignatureInvalid):
            security.verify_artifact(f, expected_sha256=d, allowlist={}, name="tf")

    def test_redaction(self):
        v = {"password": "hunter2", "nested": {"api_key": "x"}, "url": "postgres://u:pw@db/x", "aws": "AKIAABCDEFGHIJKLMNOP", "ok": "fine", "list": ["-----BEGIN RSA PRIVATE KEY-----"]}
        r = security.redact(v)
        self.assertEqual(r["ok"], "fine")
        self.assertNotIn("hunter2", json.dumps(r))
        self.assertNotIn("AKIA", json.dumps(r))
        self.assertTrue(security.contains_secret(v))

    def test_tenant_isolation(self):
        reg = security.TenantRegistry(self.tmp / "t", max_resources=2)
        a, b = reg.backend("alpha"), reg.backend("beta")
        a.commit_state(pkg.IacState({"vm.a": 1}), expected_serial=None)
        self.assertIsNone(b.load())
        for bad in ("../beta", "Alpha", "", "a/b"):
            with self.assertRaises(security.TenantBoundaryViolation):
                reg.backend(bad)
        with self.assertRaises(security.TenantBoundaryViolation):
            reg.enforce_quota("alpha", {"a.a": 1, "b.b": 2, "c.c": 3})

    def test_outage_policy(self):
        security.outage_decision(set(), "mutate")
        with self.assertRaises(security.SecurityDependencyUnavailable):
            security.outage_decision({"policy"}, "mutate")
        security.outage_decision({"policy"}, "read")
        security.outage_decision({"keys"}, "emergency", "emergency.freeze")
        with self.assertRaises(security.SecurityDependencyUnavailable):
            security.outage_decision({"identity"}, "read")
        with self.assertRaises(security.SecurityDependencyUnavailable):
            security.outage_decision({"unknown-dep"}, "read")

    def test_signed_audit_log(self):
        log = security.SignedAuditLog(self.tmp / "audit.jsonl", security.Signer(KEYS, "audit"))
        log.append("apply", "alice", {"serial": 1, "token": "secret"})
        log.append("apply", "alice", {"serial": 2})
        self.assertEqual(log.verify(), 2)
        self.assertNotIn("secret", log.path.read_text())
        self.assertEqual(log.export()["events"], 2)
        lines = log.path.read_text().splitlines()
        lines[0] = lines[0].replace('"serial": 1', '"serial": 7')
        log.path.write_text("\n".join(lines) + "\n")
        with self.assertRaises(security.SignatureInvalid):
            log.verify()


# ---------------------------------------------------------------- MC-021, 026…031
class ResilienceTest(unittest.TestCase):
    def test_retry_backoff_and_classification(self):
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise resilience.RetryableError("transient")
            return "ok"

        self.assertEqual(resilience.retry_call(flaky, sleep=lambda s: None, rng=random.Random(1)), "ok")
        with self.assertRaises(ValueError):
            resilience.retry_call(lambda: (_ for _ in ()).throw(ValueError("fatal")), sleep=lambda s: None)
        tok = resilience.CancelToken(); tok.cancel("operator")
        with self.assertRaises(resilience.Cancelled):
            resilience.retry_call(lambda: 1, cancel=tok)
        t = [0.0]
        dl = resilience.Deadline(1.0, clock=lambda: t[0]); t[0] = 2
        with self.assertRaises(resilience.DeadlineExceeded):
            resilience.retry_call(lambda: 1, deadline=dl)

    def test_idempotency(self):
        store = resilience.IdempotencyStore()
        s = pkg.IacState()
        p = s.plan({"vm.a": 1})
        r1 = store.run("k1", p["integrity"]["digest"], lambda: s.apply(p))
        r2 = store.run("k1", p["integrity"]["digest"], lambda: s.apply(p))  # replay: no second apply
        self.assertEqual((r1, r2, s.serial), (1, 1, 1))
        with self.assertRaises(pkg.IacError):
            store.run("k1", "different", lambda: None)

    def test_admission_and_breaker(self):
        ac = resilience.AdmissionController(max_concurrent=1, max_queue=0, queue_timeout=0.01)
        with ac:
            with self.assertRaises(resilience.Overloaded):
                with ac:
                    pass
        t = [0.0]
        cb = resilience.CircuitBreaker("provider", failure_threshold=2, reset_after=5, clock=lambda: t[0])
        for _ in range(2):
            with self.assertRaises(ConnectionError):
                cb.call(lambda: (_ for _ in ()).throw(ConnectionError()))
        with self.assertRaises(resilience.CircuitOpen):
            cb.call(lambda: 1)
        t[0] = 6
        self.assertEqual(cb.call(lambda: 1), 1)
        self.assertEqual(cb.state, "closed")

    def test_degraded_freeze_watchdog(self):
        dm = resilience.DegradedMode(["state", "policy"], ["telemetry"])
        dm.mark("telemetry", False)
        self.assertEqual(dm.mode, "degraded"); dm.require_mutation()
        dm.mark("policy", False)
        with self.assertRaises(resilience.Degraded):
            dm.require_mutation()
        events = []
        fc = resilience.FreezeController(lambda *a: events.append(a))
        fc.freeze("prod", actor="ic", reason="incident 42")
        with self.assertRaises(resilience.Frozen):
            fc.check("prod")
        fc.check("dev")
        with self.assertRaises(resilience.Frozen):
            fc.unfreeze("prod", actor="ic", reason="done", second_approver="ic")
        fc.unfreeze("prod", actor="ic", reason="done", second_approver="sre")
        fc.check("prod")
        self.assertEqual(len(events), 2)
        t = [0.0]
        wd = resilience.Watchdog(10, clock=lambda: t[0])
        wd.begin("apply-1"); t[0] = 11
        self.assertEqual(wd.stalled(), ["apply-1"])
        wd.progress("apply-1"); self.assertEqual(wd.stalled(), [])

    def test_offline_queue_and_failover(self):
        t = [0.0]
        s = pkg.IacState()
        q = resilience.OfflineQueue(max_staleness=100, clock=lambda: t[0])
        p1 = s.plan({"vm.a": 1}); q.enqueue(p1)
        p2 = s.plan({"vm.b": 1}); q.enqueue(p2)  # same serial as p1 -> conflicts after p1
        t[0] = 50
        out = q.reconcile(s)
        self.assertEqual(out["applied"], [1]); self.assertEqual(len(out["conflicts"]), 1)
        q.enqueue(s.plan({"vm.c": 1})); t[0] = 500
        self.assertEqual(len(q.reconcile(s)["expired"]), 1)
        fo = resilience.FailoverController({"eu1": {"region": "eu", "healthy": True, "serial": 5},
                                            "us1": {"region": "us", "healthy": True, "serial": 9},
                                            "eu2": {"region": "eu", "healthy": True, "serial": 3}})
        self.assertEqual(fo.choose(primary="eu0", allowed_regions={"eu"}, committed_serial=5), "eu1")
        with self.assertRaises(resilience.ResidencyViolation):
            fo.choose(primary="eu0", allowed_regions={"eu"}, committed_serial=6)


# ---------------------------------------------------------------- MC-043…048
class ObservabilityTest(unittest.TestCase):
    def test_health(self):
        h = obs.health_status(version="4.3.0", config_digest="d", dependencies={"policy": False, "telemetry": False}, critical={"policy"},
                              backend_ok=True, lock_holder=None, frozen={}, watchdog={"stalled": []})
        self.assertFalse(h["ready"]); self.assertIn("critical dependency down: policy", h["readiness_reasons"])

    def test_metrics_exposition_and_guards(self):
        m = obs.MetricsRegistry(max_series=10)
        m.inc("pk_iac_applies_total", labels={"tenant": "t1", "outcome": "ok"})
        with m.time("pk_iac_apply_seconds", {"tenant": "t1"}):
            pass
        m.ingest_state_metrics(pkg.IacState().metrics())
        text = m.exposition()
        self.assertIn('pk_iac_applies_total{outcome="ok",tenant="t1"} 1', text)
        self.assertIn("pk_iac_apply_seconds_bucket", text)
        with self.assertRaises(ValueError):
            m.inc("x", labels={"user_email": "a@b"})
        with self.assertRaises(ValueError):
            m.inc("x", labels={"tenant": "AKIAABCDEFGHIJKLMNOP"})
        for i in range(20):
            m.inc("y", labels={"tenant": f"t{i}"})
        self.assertGreater(m.dropped, 0)

    def test_logging_and_trace(self):
        buf = io.StringIO()
        lg = obs.StructuredLogger(stream=buf, node="n1")
        tc = obs.TraceContext.from_traceparent("00-" + "a" * 32 + "-" + "b" * 16 + "-01")
        self.assertEqual((tc.trace_id, tc.parent), ("a" * 32, "b" * 16))
        lg.log("INFO", "apply", tenant="t1", operation="apply", trace=tc.child(), password="p", serial=3)
        rec = json.loads(buf.getvalue())
        self.assertEqual(rec["trace_id"], "a" * 32)
        self.assertEqual(rec["fields"]["password"], security.REDACTED)
        self.assertNotEqual(obs.TraceContext.from_traceparent("garbage").trace_id, "a" * 32)

    def test_explain_and_lineage(self):
        s = pkg.IacState({"vm.a": {"size": 1, "x": 1}, "vm.b": 1})
        desired = {"vm.a": {"size": 2, "x": 1}, "vm.c": 1}
        p = s.plan(desired)
        e = obs.explain_plan(p, current=s.resources, desired=desired, policy_decision={"policy_version": "p1", "allow": True})
        txt = obs.render_explanation(e)
        self.assertIn("UPDATE  vm.a", txt); self.assertIn("fields: size", txt); self.assertIn("DELETE  vm.b", txt)
        lr = obs.lineage_record(plan=p, applied_serial=s.apply(p), release_id="rel-9", artifact_versions={"app": "1.2"}, config_digest="c")
        self.assertEqual(lr["to_serial"], 1)


# ---------------------------------------------------------------- MC-015/018/019/035
class ExecutionTest(Tmp):
    def test_runner_refuses_without_pinned_engine(self):
        with self.assertRaises(execution.EngineUnavailable):
            execution.TerraformRunner(None, expected_sha256=None, version="1.9.0", plugin_dir=None)
        f = self.tmp / "terraform"; f.write_bytes(b"#!/bin/sh\n")
        with self.assertRaises(execution.EngineUnavailable):
            execution.TerraformRunner(f, expected_sha256="0" * 64, version="1.9.0", plugin_dir=None)
        with self.assertRaises(security.SignatureInvalid):
            execution.TerraformRunner(f, expected_sha256="0" * 64, version="1.9.0", plugin_dir=self.tmp)

    @unittest.skipIf(sys.platform.startswith("win"), "POSIX shell stub")
    def test_runner_with_stub_engine(self):
        import hashlib

        stub = self.tmp / "terraform"
        stub.write_text("#!/bin/sh\necho '{\"format_version\":\"1.2\",\"resource_changes\":[]}'\n")
        stub.chmod(0o755)
        r = execution.TerraformRunner(stub, expected_sha256=hashlib.sha256(stub.read_bytes()).hexdigest(), version="stub", plugin_dir=self.tmp)
        cmd = r.command("plan", self.tmp)
        self.assertIn("-input=false", cmd)
        out = r.run("show", self.tmp / "wd")
        self.assertEqual(out["json"]["format_version"], "1.2")

    def test_plan_json_parser(self):
        doc = {"format_version": "1.2", "resource_changes": [
            {"address": "a.x", "change": {"actions": ["create"]}},
            {"address": "a.y", "change": {"actions": ["delete", "create"]}},
            {"address": "a.z", "change": {"actions": ["no-op"]}}]}
        self.assertEqual(execution.parse_terraform_plan_json(doc)["replace"], ["a.y"])
        with self.assertRaises(execution.EngineFailed):
            execution.parse_terraform_plan_json({"format_version": "2.0"})
        with self.assertRaises(execution.EngineFailed):
            execution.parse_terraform_plan_json({"format_version": "1.0", "resource_changes": [{"address": "a", "change": {"actions": ["explode"]}}]})

    def test_provider_pins(self):
        reg = execution.ProviderRegistry({"hashicorp/aws": {"version": "5.1.0", "sha256": "a" * 64}})
        reg.check_lock({"hashicorp/aws": {"version": "5.1.0", "sha256": "A" * 64}})
        for lock in ({"hashicorp/aws": {"version": "5.2.0", "sha256": "a" * 64}}, {"evil/x": {"version": "1", "sha256": "b" * 64}}):
            with self.assertRaises(execution.ProviderRefused):
                reg.check_lock(lock)
        with self.assertRaises(execution.ProviderRefused):
            execution.ProviderRegistry({"x/y": {"version": "~> 5.0", "sha256": "a" * 64}})

    def test_sandbox_env(self):
        os.environ["INV06_TEST_SECRET"] = "s3cret"
        try:
            env = execution.sandbox_env(execution.SandboxPolicy(), self.tmp)
            self.assertNotIn("INV06_TEST_SECRET", env)
            self.assertEqual(env["CHECKPOINT_DISABLE"], "1")
            with self.assertRaises(execution.ProviderRefused):
                execution.sandbox_env(execution.SandboxPolicy(extra_env={"AWS_SECRET_ACCESS_KEY": "x"}), self.tmp)
        finally:
            del os.environ["INV06_TEST_SECRET"]

    def test_provider_contract_and_partial_failure(self):
        prov = execution.InMemoryProvider(initial={"net.vpc": {"cidr": "10/8"}})
        s = pkg.IacState(prov.list())
        desired = {"net.vpc": {"cidr": "10/8"}, "vm.web": {"subnet": "${net.vpc.id}"}, "dns.www": {"t": "${vm.web.ip}"}}
        p = s.plan(desired)
        prov.fail_on["create:dns.www"] = ConnectionError("provider 503")
        out = execution.execute_plan(p, prov, desired=desired, current=s.resources)
        self.assertFalse(out["complete"])
        self.assertEqual(out["done"], [("create", "vm.web")])
        drift = s.drift(prov.list())  # caller reconciles instead of committing a partial apply
        self.assertEqual(sorted(drift), ["vm.web"])
        prov.fail_on.clear()
        self.assertTrue(execution.execute_plan(s.plan(desired), execution.InMemoryProvider(initial=s.resources), desired=desired, current=s.resources)["complete"])

    def test_platform_check(self):
        r = execution.check_platform()
        self.assertIn(r["status"], ("validated", "declared"))


# ---------------------------------------------------------------- MC-042/059
class AdversarialPropertyTest(unittest.TestCase):
    def _rand_value(self, rng, depth=0):
        k = rng.randrange(6 if depth < 3 else 4)
        if k == 0:
            return rng.randrange(-10**6, 10**6)
        if k == 1:
            return "".join(rng.choice(string.printable) for _ in range(rng.randrange(8)))
        if k == 2:
            return rng.choice([True, False, None])
        if k == 3:
            return rng.random()
        if k == 4:
            return [self._rand_value(rng, depth + 1) for _ in range(rng.randrange(4))]
        return {f"k{i}": self._rand_value(rng, depth + 1) for i in range(rng.randrange(4))}

    def test_property_plan_apply_reaches_desired(self):
        rng = random.Random(606)
        for _ in range(300):
            cur = {f"r.{i}": self._rand_value(rng) for i in rng.sample(range(20), rng.randrange(10))}
            des = {f"r.{i}": self._rand_value(rng) for i in rng.sample(range(20), rng.randrange(10))}
            s = pkg.IacState(cur)
            s.apply(s.plan(des))
            self.assertEqual(s.resources, json.loads(json.dumps(des)))
            self.assertEqual(s.drift(des), {})
            self.assertTrue(s.verify_audit_chain())

    def test_fuzz_plan_validation_never_mutates_on_bad_input(self):
        rng = random.Random(7)
        s = pkg.IacState({"a.a": 1})
        good = s.plan({"a.a": 2})
        before = s.snapshot()
        for _ in range(500):
            bad = json.loads(json.dumps(good))
            field = rng.choice(list(bad))
            bad[field] = self._rand_value(rng)
            try:
                s.apply(bad)
            except pkg.IacError:
                pass
            else:  # only an unchanged, valid plan may apply
                self.assertEqual(bad, good)
                break
        if s.serial == before["serial"]:
            self.assertEqual(s.snapshot()["resources"], before["resources"])

    def test_fuzz_hcl_parser_only_raises_config_error(self):
        rng = random.Random(11)
        alphabet = 'resource "{}[]=,#\n abc123$.-'
        for _ in range(2000):
            src = "".join(rng.choice(alphabet) for _ in range(rng.randrange(60)))
            try:
                config.parse_hcl_subset(src)
            except config.ConfigError:
                pass

    def test_hostile_inputs(self):
        s = pkg.IacState()
        for bad in ({"a": float("nan")}, {1: "x"}, {"": 1}, {"a": object()}, {"a": {"b": {1, 2}}}):
            with self.assertRaises(pkg.IacError):
                s.plan(bad)
        p = s.plan({"a.a": 1})
        s.apply(p)
        with self.assertRaises(pkg.StalePlan):  # replay of an applied plan
            s.apply(p)
        with self.assertRaises(config.ConfigError):
            config.parse_hcl_subset("x" * (config.MAX_SOURCE_BYTES + 1))
        deep = {"a.a": 1}
        cur = deep
        for _ in range(50):
            cur["n"] = {}
            cur = cur["n"]
        pkg.IacState().plan({"a.b": deep})  # deep but bounded nesting accepted


# ---------------------------------------------------------------- MC-060/061
class FaultSoakTest(Tmp):
    def test_concurrent_writers_to_backend_one_wins_per_serial(self):
        be = durable.FileStateBackend(self.tmp / "s")
        be.commit_state(pkg.IacState(), expected_serial=None)
        wins, errs = [], []

        def writer(i):
            s = pkg.IacState({f"vm.{i}": i}, serial=1)
            try:
                wins.append(be.commit_state(s, expected_serial=0))
            except durable.StateConflict:
                errs.append(i)

        ts = [threading.Thread(target=writer, args=(i,)) for i in range(16)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual((len(wins), len(errs)), (1, 15))

    def test_soak_many_revisions_with_compaction(self):
        be = durable.FileStateBackend(self.tmp / "s", max_revisions=20)
        s = pkg.IacState()
        rng = random.Random(3)
        for i in range(200):
            s.apply(s.plan({f"vm.{j}": rng.randrange(5) for j in range(rng.randrange(1, 30))}))
            be.commit_state(s, expected_serial=be.head_serial())
        self.assertLessEqual(len(be.history()), 20)
        self.assertEqual(be.load()["serial"], s.serial)
        self.assertTrue(be.verify_chain())
        self.assertTrue(s.verify_audit_chain())

    def test_burst_load_is_shed_not_queued_unboundedly(self):
        ac = resilience.AdmissionController(max_concurrent=2, max_queue=2, queue_timeout=0.2)
        gate = threading.Event()
        shed = []

        def work():
            try:
                with ac:
                    gate.wait(1)
            except resilience.Overloaded:
                shed.append(1)

        ts = [threading.Thread(target=work) for _ in range(12)]
        [t.start() for t in ts]
        gate.set()
        [t.join() for t in ts]
        self.assertGreater(len(shed), 0)


# ---------------------------------------------------------------- MC-051…069
class ReleaseTest(Tmp):
    def test_bench_slo_capacity(self):
        b = release.run_benchmarks(sizes=(50, 1000), iterations=4)
        self.assertTrue(release.check_slos(b)["pass"], release.check_slos(b))
        self.assertIn("bytes_per_resource", release.capacity_model(b))
        self.assertGreater(release.copy_audit(50)["plan"]["calls"], 0)

    def test_evidence_roundtrip(self):
        sg = security.Signer(KEYS, "evidence")
        ev = release.build_evidence(version=pkg.__version__, tests={"passed": 1}, bench=None, signer=sg)
        release.verify_evidence(ev, sg)
        ev2 = dict(ev, version="9.9.9")
        with self.assertRaises(ValueError):
            release.verify_evidence(ev2, sg)

    def test_canary(self):
        ok = release.CanaryRollout("2", "1", health=lambda st, f: {"error_rate": 0, "p99": 0.1}).run()
        self.assertEqual(ok["result"], "promoted")
        bad = release.CanaryRollout("2", "1", health=lambda st, f: {"error_rate": 0.5 if st == "early" else 0, "p99": 0.1}).run()
        self.assertEqual((bad["result"], bad["version"]), ("rolled_back", "1"))

    def test_gate_never_go_with_open_items(self):
        g = release.production_gate(checklist_status={"totals": {"open": 3}}, readiness={"items": [{"id": "MC-002", "title": "owners", "status": "owner-required"}]},
                                    evidence_ok=True, tests_ok=True, slo_ok=True)
        self.assertEqual(g["verdict"], "CONDITIONAL_GO")
        g = release.production_gate(checklist_status={"totals": {}}, readiness={"items": [{"id": "MC-019", "title": "cloud", "status": "external"}]},
                                    evidence_ok=True, tests_ok=True, slo_ok=True)
        self.assertEqual(g["verdict"], "NO_GO")
        self.assertEqual(release.production_gate(checklist_status={"totals": {}}, readiness={"items": []}, evidence_ok=True, tests_ok=True, slo_ok=True)["verdict"], "GO")

    def test_packaging_metadata_consistent(self):
        py = (PKG_DIR / "pyproject.toml").read_text()
        self.assertIn(f'version = "{pkg.__version__}"', py)
        self.assertIn("dependencies = []", py)


# ---------------------------------------------------------------- wired path (all MC controls composed)
class ControlPlaneTest(Tmp):
    def _cp(self, provider=None, engine=None):
        auth = security.TokenAuthenticator(KEYS, "inv06")
        cp = service.ControlPlane(
            tenant="t1", backend=durable.FileStateBackend(self.tmp / "s"), lock=locking.FileLeaseLock(self.tmp / "l"),
            provider=provider or execution.InMemoryProvider(), authenticator=auth, authorizer=security.Authorizer(),
            policy=policy.PolicyGate(engine or policy.RulePolicyEngine("p1", {"ingress": policy.forbid_public_ingress})),
            plan_signer=security.Signer(KEYS, "plan"), audit=security.SignedAuditLog(self.tmp / "audit.jsonl", security.Signer(KEYS, "audit")),
            logger=obs.StructuredLogger(stream=io.StringIO()))
        tok = {r: auth.issue(r, "operator", "t1", [r]) for r in ("planner", "approver", "applier")}
        return cp, tok

    def test_end_to_end_and_controls(self):
        cp, tok = self._cp()
        desired = {"net.vpc": {"cidr": "10/8"}, "vm.web": {"subnet": "${net.vpc.id}"}}
        out = cp.plan(tok["planner"], desired)
        with self.assertRaises(security.SignatureInvalid):
            cp.apply(tok["applier"], out["plan"], desired=desired, idempotency_key="k0")  # unsigned -> refused
        with self.assertRaises(security.AccessDenied):
            cp.approve(tok["planner"], out["plan"], planner="planner")  # planner lacks approve
        signed = cp.approve(tok["approver"], out["plan"], planner="planner")
        r = cp.apply(tok["applier"], signed, desired=desired, idempotency_key="k1")
        self.assertEqual(r["serial"], 1)
        self.assertEqual(cp.apply(tok["applier"], signed, desired=desired, idempotency_key="k1")["serial"], 1)  # idempotent replay
        with self.assertRaises(pkg.StalePlan):
            cp.apply(tok["applier"], signed, desired=desired, idempotency_key="k2")
        self.assertEqual(cp.backend.load()["resources"], desired)
        self.assertEqual(cp.provider.list(), desired)
        self.assertGreaterEqual(cp.audit.verify(), 4)
        self.assertTrue(cp.health()["ready"])
        text = cp.metrics.exposition()
        for name in ("pk_iac_applies_total", "pk_iac_apply_seconds_bucket", "pk_iac_dependency_up", "pk_iac_admission_queue_depth", "pk_iac_state_stale_refusals"):
            self.assertIn(name, text)

    def test_policy_freeze_outage_partial(self):
        cp, tok = self._cp()
        with self.assertRaises(policy.PolicyDenied):
            cp.plan(tok["planner"], {"sg.x": {"ingress": "0.0.0.0/0"}})
        self.assertIn("pk_iac_policy_denied_total", cp.metrics.exposition())
        desired = {"vm.a": 1}
        signed = cp.approve(tok["approver"], cp.plan(tok["planner"], desired)["plan"], planner="planner")
        cp.freeze.freeze("t1", actor="ic", reason="incident")
        with self.assertRaises(resilience.Frozen):
            cp.apply(tok["applier"], signed, desired=desired, idempotency_key="a")
        self.assertFalse(cp.health()["ready"])
        cp.freeze.unfreeze("t1", actor="ic", reason="ok", second_approver="sre")
        cp.security_down = {"policy"}
        with self.assertRaises(security.SecurityDependencyUnavailable):
            cp.apply(tok["applier"], signed, desired=desired, idempotency_key="b")
        cp.security_down = set()
        cp.provider.fail_on["create"] = ConnectionError("503")
        with self.assertRaises(service.PartialApply):
            cp.apply(tok["applier"], signed, desired=desired, idempotency_key="c")
        self.assertIsNone(cp.backend.head_serial())  # nothing committed
        with self.assertRaises(security.AuthenticationFailed):
            cp.plan("forged", desired)


if __name__ == "__main__":
    unittest.main(verbosity=2)
