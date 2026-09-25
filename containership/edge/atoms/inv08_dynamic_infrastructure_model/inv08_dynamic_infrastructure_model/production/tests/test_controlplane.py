"""Tests for the controlplane group: components 26-33 and 41-46."""
from __future__ import annotations

import json
import os
import random
import stat
import tempfile
import unittest
from pathlib import Path

from ...model import Pool
from .. import adapters as ad
from ..audit import AuditLog, verify_file
from ..bootstrap import bootstrap, main as bootstrap_main
from ..config import SECURE_DEFAULTS, ConfigDeployer, validate, verify_envelope, with_provenance
from ..controller import Controller
from ..controls import Controls
from ..core import Inv08Error, redact
from ..faults import (Crash, FakeClock, Fault, FaultPlan, FaultyProvider, Partition, crash_at,
                      rounds_to_converge, rpo_lost_ops)
from ..health import (DEGRADED, HEALTHY, UNHEALTHY, Check, DependencyHealth, Heartbeats, aggregate,
                      lease_store_health, stuck_ops)
from ..journal import Journal
from ..leader import LEADER_KEY, FenceGate, LeaderElector, detect_split_brain
from ..leasestore import REPLICATION_MODEL, LeaseRecord, LeaseStore
from ..resilience import AdmissionController, CircuitBreaker, RetryBudget, RetryPolicy, call_with_retry
from ..secrets import EnvSecretProvider, FileSecretProvider, SecretRef, SecretResolver

POOL = {"min_nodes": 1, "max_nodes": 6, "per_node": 4, "lease_ttl": 10}


def raw_cfg(**over):
    c = {"env": "dev", "site": "lab-1",
         "providers": [{"name": "cloud-a", "kind": "cloud", "credentials": "secretref://cloud-a/api#1"}]}
    c.update(over)
    return c


class Env:
    """Controller wired to doubles in a temp dir."""

    def __init__(self, tmp: str, *, kind="cloud", provider=None, identity="ctl-a", controls=None,
                 crash_hook=None, store=None, clock=None, op_timeout=300.0):
        self.tmp = Path(tmp)
        self.clock = clock or FakeClock()
        self.store = store or LeaseStore(self.tmp / "leases.json")
        self.inner = ad.make_provider(kind)
        self.provider = provider or self.inner
        self.journal = Journal(self.tmp / "journal")
        self.elector = LeaderElector(self.store, identity, clock=self.clock, ttl=30.0)
        self.ctl = Controller(Pool(**POOL), self.provider, self.journal, self.elector, clock=self.clock,
                              controls=controls, sleep=self.clock.sleep, crash_hook=crash_hook,
                              op_timeout=op_timeout, rng=random.Random(1))

    def restart(self, **kw):
        self.journal = Journal(self.tmp / "journal")
        self.elector = LeaderElector(self.store, "ctl-a", clock=self.clock, ttl=30.0)
        self.ctl = Controller.recover(POOL, self.provider, self.journal, self.elector, clock=self.clock,
                                      sleep=self.clock.sleep, rng=random.Random(2), **kw)
        return self.ctl


class TmpCase(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.tmp = self._td.name

    def tearDown(self):
        self._td.cleanup()


# ======================================================================= 26 adjacent layers
class TestAdjacentAdapters(unittest.TestCase):
    def test_inv06_inventory_positive_and_pinned_respected(self):
        msg = ad.AdjacentLayerDouble("INV-06").emit(nodes=[{"node_id": "static-1", "pinned": True}])
        self.assertEqual(ad.parse_inv06_inventory(msg), {"static-1": True})

    def test_inv06_rejects_duplicates_and_bad_entries(self):
        for nodes in ([{"node_id": "a", "pinned": True}] * 2, [{"node_id": "", "pinned": True}],
                      [{"node_id": "a", "pinned": "yes"}], "x"):
            with self.assertRaises(Inv08Error):
                ad.parse_inv06_inventory({"schema": "PK_DYN_ADJ_INV06/1", "nodes": nodes})

    def test_pln05_demand_positive_boundary_negative(self):
        base = {"schema": "PK_DYN_ADJ_PLN05/1", "pool": "p", "demand": 0, "min_nodes": 0, "max_nodes": 0, "ts": 1}
        self.assertEqual(ad.parse_pln05_demand(base)["demand"], 0)
        for bad in ({"demand": -1}, {"demand": float("nan")}, {"min_nodes": 2}, {"max_nodes": True}, {"pool": ""}):
            with self.assertRaises(Inv08Error):
                ad.parse_pln05_demand(dict(base, **bad))
        with self.assertRaises(Inv08Error):
            ad.parse_pln05_demand({k: v for k, v in base.items() if k != "ts"})

    def test_version_negotiation(self):
        with self.assertRaises(Inv08Error) as cm:
            ad.parse_pln05_demand({"schema": "PK_DYN_ADJ_PLN05/2"})
        self.assertEqual(cm.exception.code, "INV08.ADAPTER.UNSUPPORTED_VERSION")
        with self.assertRaises(Inv08Error) as cm:
            ad.parse_pln05_demand({"schema": "OTHER/1"})
        self.assertEqual(cm.exception.code, "INV08.ADAPTER.INVALID")

    def test_inv68_export_and_busy_feedback(self):
        pool = Pool(1, 3)
        pool.tick(0, 8)
        out = ad.export_inv68_membership("p", pool, epoch=3)
        peer = ad.AdjacentLayerDouble("INV-68")
        peer.receive(out)
        self.assertEqual(len(peer.inbox[0]["nodes"]), 2)
        ad.apply_inv68_busy(pool, {"schema": "PK_DYN_ADJ_INV68/1", "node_id": "node-1", "busy": True})
        self.assertTrue(pool.nodes["node-1"]["busy"])
        with self.assertRaises(Inv08Error) as cm:
            ad.apply_inv68_busy(pool, {"schema": "PK_DYN_ADJ_INV68/1", "node_id": "nope", "busy": True})
        self.assertTrue(cm.exception.retryable)
        with self.assertRaises(Inv08Error):
            ad.apply_inv68_busy(pool, {"schema": "PK_DYN_ADJ_INV68/1", "node_id": "node-1", "busy": 1})

    def test_inv32_hint(self):
        self.assertEqual(ad.parse_inv32_hint({"schema": "PK_DYN_ADJ_INV32/1", "host": "h", "free_slots": 0})
                         ["free_slots"], 0)
        with self.assertRaises(Inv08Error):
            ad.parse_inv32_hint({"schema": "PK_DYN_ADJ_INV32/1", "host": "h", "free_slots": -1})

    def test_provider_double_contract_roundtrip(self):
        p = ad.make_provider("cloud")
        p.create("n1", {}, idempotency_key="k1", fence=1)
        self.assertEqual(p.list()["n1"]["state"], "RUNNING")
        p.delete("n1", idempotency_key="k2", fence=1)
        self.assertEqual(p.list(), {})


# ======================================================================= 28 providers
class TestProviderAdapters(unittest.TestCase):
    def _lifecycle(self, kind):
        p = ad.make_provider(kind)
        caps = p.capabilities()
        self.assertEqual(set(caps), set(ad.CAPABILITY_KEYS))
        v = p.create("n1", {}, idempotency_key="c1", fence=1)
        self.assertEqual((v["state"], v["kind"]), ("RUNNING", kind))
        self.assertEqual(p.create("n1", {}, idempotency_key="c1", fence=1), v)  # idempotent replay
        with self.assertRaises(Inv08Error) as cm:
            p.create("n1", {}, idempotency_key="c-other", fence=1)
        self.assertEqual(cm.exception.code, "INV08.PROVIDER.CONFLICT")
        self.assertEqual(p.drain("n1", idempotency_key="d1", fence=1)["state"], "DRAINING")
        self.assertEqual(p.delete("n1", idempotency_key="x1", fence=1)["state"], "DELETED")
        self.assertNotIn("n1", p.list())

    def test_cloud_adapter(self):
        self._lifecycle("cloud")

    def test_hypervisor_adapter(self):
        self._lifecycle("hypervisor")

    def test_baremetal_adapter_finite_inventory(self):
        self._lifecycle("baremetal")
        p = ad.make_provider("baremetal", max_nodes=1)
        p.create("a", {}, idempotency_key="1", fence=1)
        with self.assertRaises(Inv08Error) as cm:
            p.create("b", {}, idempotency_key="2", fence=1)
        self.assertEqual(cm.exception.code, "INV08.PROVIDER.TERMINAL")

    def test_edge_adapter_intermittent(self):
        self._lifecycle("edge")
        p = ad.make_provider("edge")
        self.assertTrue(p.capabilities()["intermittent"])
        p.online = False
        with self.assertRaises(Inv08Error) as cm:
            p.list()
        self.assertTrue(cm.exception.retryable)

    def test_normalization_and_error_translation(self):
        self.assertEqual(ad.normalize_state("cloud", "weird-new-state"), "UNKNOWN")
        self.assertEqual(ad.normalize_state("baremetal", "deployed"), "RUNNING")
        with self.assertRaises(Inv08Error):
            ad.normalize_capabilities({"create": True})
        with self.assertRaises(Inv08Error):
            ad.normalize_capabilities({k: True for k in ad.CAPABILITY_KEYS})  # max_nodes bool
        p = ad.make_provider("cloud")
        p.fail_next.append(ad.ProviderTransient("503"))
        p.fail_next.append(KeyError("secret=hunter2"))
        with self.assertRaises(Inv08Error) as cm:
            p.list()
        self.assertEqual(cm.exception.code, "INV08.PROVIDER.RETRYABLE")
        with self.assertRaises(Inv08Error) as cm:
            p.list()
        self.assertEqual(cm.exception.code, "INV08.PROVIDER.TERMINAL")
        self.assertNotIn("hunter2", json.dumps(cm.exception.to_dict()))
        with self.assertRaises(ValueError):
            ad.make_provider("mainframe")


# ======================================================================= 27 controller
class TestController(TmpCase):
    def test_scale_up_converges(self):
        e = Env(self.tmp)
        rep = e.ctl.reconcile(demand=10)
        self.assertEqual(rep["outcome"], "SUCCESS")
        self.assertTrue(rep["converged"])
        self.assertEqual(sorted(e.inner.list()), ["node-1", "node-2", "node-3"])

    def test_scale_down_drains_then_deletes(self):
        e = Env(self.tmp)
        e.ctl.reconcile(demand=10)
        e.clock.advance(1)
        rep = e.ctl.reconcile(demand=0)
        self.assertTrue(rep["converged"])
        self.assertEqual(len(e.inner.list()), 1)
        ops = [c for c in e.inner.calls if c[0] in ("drain", "delete")]
        self.assertEqual(ops[0][0], "drain")

    def test_idempotent_rounds_no_duplicate_ops(self):
        e = Env(self.tmp)
        e.ctl.reconcile(10)
        n = len(e.inner.calls)
        rep = e.ctl.reconcile(10)
        self.assertEqual(rep["ops"], [])
        self.assertEqual([c[0] for c in e.inner.calls[n:]], ["list", "list"])

    def test_drift_out_of_band_delete_recreated(self):
        e = Env(self.tmp)
        e.ctl.reconcile(4)
        e.inner.native["node-1"] = "terminated"          # out-of-band deletion
        rep = e.ctl.reconcile(4)
        self.assertTrue(rep["converged"])
        self.assertIn("create:node-1:2", rep["ops"])

    def test_foreign_node_reported_not_deleted(self):
        e = Env(self.tmp)
        e.inner.create("intruder", {}, idempotency_key="z", fence=1)
        rep = e.ctl.reconcile(4)
        self.assertEqual(rep["outcome"], "OPERATOR_REQUIRED")
        self.assertEqual(rep["drift"]["foreign"], ["intruder"])
        self.assertIn("intruder", e.inner.list())

    def test_terminal_create_failure_rolls_back_desired(self):
        e = Env(self.tmp)
        e.inner.max_nodes = 0                               # quota exhausted -> terminal
        rep = e.ctl.reconcile(4)
        self.assertEqual(rep["rolled_back"], ["node-1"])
        self.assertNotIn("node-1", e.ctl.pool.nodes)
        self.assertEqual(rep["outcome"], "PARTIAL")
        e.inner.max_nodes = 10
        e.clock.advance(1)
        self.assertTrue(e.ctl.reconcile(4)["converged"])

    def test_pending_create_times_out_and_rolls_back(self):
        e = Env(self.tmp, crash_hook=crash_at("create:after_pending"), op_timeout=5)
        with self.assertRaises(Crash):
            e.ctl.reconcile(4)
        e.clock.advance(10)
        ctl = e.restart(op_timeout=5)
        rep = ctl.reconcile(4)
        self.assertIn("create:node-1:1", rep["timed_out"])
        self.assertTrue(rep["converged"])

    def test_not_leader_takes_no_action(self):
        e = Env(self.tmp)
        other = LeaderElector(e.store, "ctl-b", clock=e.clock, ttl=30)
        self.assertIsNotNone(other.try_acquire())
        rep = e.ctl.reconcile(10)
        self.assertEqual(rep["outcome"], "RETRYABLE_FAILURE")
        self.assertEqual(e.inner.calls, [])

    def test_conflict_reported(self):
        e = Env(self.tmp)
        e.inner.fail_next.append(RuntimeError("x"))  # consumed by list -> terminal list failure
        rep = e.ctl.reconcile(4)
        self.assertEqual(rep["outcome"], "TERMINAL_FAILURE")


# ======================================================================= 29 lease store
class TestLeaseStore(TmpCase):
    def test_record_schema_validation(self):
        LeaseRecord("a/b", "h", 1, 1, 5.0, {})
        for bad in (dict(key=""), dict(key="x" * 129), dict(holder=""), dict(epoch=0), dict(version=True),
                    dict(expires=float("inf")), dict(data=[])):
            kw = dict(key="k", holder="h", epoch=1, version=1, expires=1.0, data={})
            kw.update(bad)
            with self.assertRaises(ValueError):
                LeaseRecord(**kw)

    def test_cas_semantics(self):
        s = LeaseStore(Path(self.tmp) / "s.json")
        e = s.issue_epoch()
        r = s.cas("k", 0, holder="a", epoch=e, expires=10)
        self.assertEqual(r.version, 1)
        with self.assertRaises(Inv08Error) as cm:
            s.cas("k", 0, holder="b", epoch=e, expires=10)
        self.assertEqual(cm.exception.code, "INV08.LEASE.CONFLICT")
        self.assertEqual(s.cas("k", 1, holder="a", epoch=e, expires=20).version, 2)
        with self.assertRaises(ValueError):
            s.cas("k", 2, holder="a", epoch=e + 5, expires=20)  # unissued epoch

    def test_durable_across_reopen_and_corruption_detected(self):
        p = Path(self.tmp) / "s.json"
        s = LeaseStore(p)
        s.acquire("k", "a", now=0, ttl=10)
        s2 = LeaseStore(p)
        self.assertEqual(s2.get("k").holder, "a")
        self.assertEqual(s2.fence_counter, 1)
        doc = json.loads(p.read_text())
        doc["body"]["records"]["k"]["holder"] = "evil"
        p.write_text(json.dumps(doc))
        with self.assertRaises(Inv08Error) as cm:
            LeaseStore(p)
        self.assertEqual(cm.exception.code, "INV08.STORE.CORRUPT")
        self.assertFalse((p.parent / "s.json.tmp").exists())

    def test_replication_model_declared_blocked(self):
        self.assertEqual(REPLICATION_MODEL["state"], "BLOCKED")

    def test_fencing_epochs_monotonic(self):
        s = LeaseStore(Path(self.tmp) / "s.json")
        a = s.acquire("k", "a", now=0, ttl=5)
        self.assertEqual(s.acquire("k", "a", now=1, ttl=5).epoch, a.epoch)   # renewal keeps
        self.assertIsNone(s.acquire("k", "b", now=2, ttl=5))                  # held
        b = s.acquire("k", "b", now=10, ttl=5)                                # after expiry
        self.assertGreater(b.epoch, a.epoch)
        with self.assertRaises(Inv08Error) as cm:
            s.check_fence("k", a.epoch)
        self.assertEqual(cm.exception.code, "INV08.FENCE.STALE")
        s.check_fence("k", b.epoch)

    def test_gc_and_orphans(self):
        s = LeaseStore(Path(self.tmp) / "s.json")
        s.acquire("old", "dead", now=0, ttl=1)
        s.acquire("live", "ghost", now=0, ttl=100)
        s.acquire("mine", "ctl", now=0, ttl=100)
        rep = s.gc(now=10, grace=5, live_holders={"ctl"})
        self.assertEqual(rep, {"removed": ["old"], "orphaned_unexpired": ["live"]})
        self.assertIsNone(LeaseStore(Path(self.tmp) / "s.json").get("old"))
        self.assertTrue(s.release("mine", "ctl", s.get("mine").epoch, now=11))
        self.assertFalse(s.release("live", "ctl", 1, now=11))

    def test_outage(self):
        s = LeaseStore(Path(self.tmp) / "s.json")
        s.available = False
        with self.assertRaises(Inv08Error) as cm:
            s.get("k")
        self.assertTrue(cm.exception.retryable)


# ======================================================================= 30 config schema
class TestConfigSchema(unittest.TestCase):
    def test_typed_schema_positive(self):
        c = validate(raw_cfg())
        self.assertEqual(c["pool"], SECURE_DEFAULTS["pool"])

    def test_unknown_and_type_errors(self):
        for bad in (raw_cfg(extra=1), raw_cfg(pool={"min_nodes": "1"}), raw_cfg(pool={"bogus": 1}),
                    raw_cfg(env="qa"), raw_cfg(site="Bad Site"), raw_cfg(providers=[]),
                    raw_cfg(providers=[{"name": "a", "kind": "cloud"}]),
                    raw_cfg(controller={"max_retries": 11})):
            with self.assertRaises(Inv08Error):
                validate(bad)
        with self.assertRaises(Inv08Error):
            validate([])

    def test_secure_defaults(self):
        c = validate(raw_cfg())
        self.assertFalse(c["security"]["allow_insecure_transport"])
        self.assertTrue(c["security"]["require_fencing"])
        self.assertTrue(c["security"]["audit_enabled"])

    def test_semantic_validation(self):
        for bad in (raw_cfg(pool={"min_nodes": 5, "max_nodes": 2}),
                    raw_cfg(controller={"op_timeout_s": 5, "reconcile_interval_s": 10}),
                    raw_cfg(controller={"leader_ttl_s": 5}),
                    raw_cfg(env="prod", security={"allow_insecure_transport": True}),
                    raw_cfg(providers=[{"name": "a", "kind": "cloud", "credentials": "hunter2"}]),
                    raw_cfg(providers=[{"name": "a", "kind": "cloud", "credentials": "secretref://x#1"}] * 2)):
            with self.assertRaises(Inv08Error) as cm:
                validate(bad)
            self.assertNotIn("hunter2", json.dumps(cm.exception.to_dict()))
        validate(raw_cfg(env="dev", security={"allow_insecure_transport": True}))  # dev may weaken

    def test_provenance(self):
        env = with_provenance(raw_cfg(), author="cfg-author-test", source="git:abc", created_ts=1)
        self.assertEqual(verify_envelope(env)["site"], "lab-1")
        with self.assertRaises(Inv08Error):
            with_provenance(raw_cfg(), author=" ", source="x", created_ts=1)
        env["config"]["site"] = "lab-2"
        with self.assertRaises(Inv08Error) as cm:
            verify_envelope(env)
        self.assertEqual(cm.exception.code, "INV08.CONFIG.TAMPERED")

    def test_scoped_activation(self):
        with tempfile.TemporaryDirectory() as t:
            dep = ConfigDeployer(t, env="staging", tenant="t1")
            with self.assertRaises(Inv08Error) as cm:
                dep.stage(with_provenance(raw_cfg(), author="a", source="s", created_ts=0))
            self.assertEqual(cm.exception.code, "INV08.CONFIG.SCOPE")
            ok = with_provenance(raw_cfg(env="staging", tenant="t1"), author="a", source="s", created_ts=0)
            sid = dep.stage(ok)
            self.assertEqual(dep.validate_staged(sid), [])
            dep.activate(sid)
            self.assertIsNone(ConfigDeployer(t, env="staging", tenant="t2").active())


# ======================================================================= 31 config deployment
class TestConfigDeploy(TmpCase):
    def _env(self, site):
        return with_provenance(raw_cfg(site=site), author="a", source="s", created_ts=0)

    def setUp(self):
        super().setUp()
        self.audit = AuditLog(Path(self.tmp) / "audit.jsonl")
        self.dep = ConfigDeployer(self.tmp, env="dev", audit=self.audit)

    def test_staging_is_not_active(self):
        sid = self.dep.stage(self._env("s1"))
        self.assertTrue((self.dep.dir / "staged" / f"{sid}.json").exists())
        self.assertIsNone(self.dep.active())

    def test_preactivation_validation_required(self):
        sid = self.dep.stage(self._env("s1"))
        with self.assertRaises(Inv08Error) as cm:
            self.dep.activate(sid)
        self.assertEqual(cm.exception.code, "INV08.CONFIG.NOT_VALIDATED")
        probs = self.dep.validate_staged(sid, [lambda c: "site not allowed" if c["site"] == "s1" else None])
        self.assertEqual(probs, ["site not allowed"])
        with self.assertRaises(Inv08Error):
            self.dep.activate(sid)

    def test_atomic_activation_and_lkg_rollback(self):
        a = self.dep.stage(self._env("s1"))
        self.dep.validate_staged(a)
        self.dep.activate(a)
        b = self.dep.stage(self._env("s2"))
        self.dep.validate_staged(b)
        self.dep.activate(b)
        self.assertEqual(self.dep.active()["config"]["site"], "s2")
        self.assertFalse(list(self.dep.dir.glob("*.tmp")))
        self.assertEqual(self.dep.rollback()["config"]["site"], "s1")
        self.assertEqual(self.dep.active()["config"]["site"], "s1")

    def test_failed_activation_quarantined_and_restored(self):
        a = self.dep.stage(self._env("s1"))
        self.dep.validate_staged(a)
        self.dep.activate(a)
        b = self.dep.stage(self._env("s2"))
        self.dep.validate_staged(b)
        with self.assertRaises(Inv08Error) as cm:
            self.dep.activate(b, verify=lambda c: 1 / 0)
        self.assertEqual(cm.exception.code, "INV08.CONFIG.ACTIVATION_FAILED")
        self.assertEqual(self.dep.active()["config"]["site"], "s1")
        self.assertTrue((self.dep.dir / "quarantine" / f"{b}.json").exists())
        self.assertTrue(verify_file(Path(self.tmp) / "audit.jsonl")[0])

    def test_rollback_without_lkg(self):
        with self.assertRaises(Inv08Error) as cm:
            self.dep.rollback()
        self.assertEqual(cm.exception.code, "INV08.CONFIG.NO_LKG")


# ======================================================================= 32 secrets
class TestSecrets(TmpCase):
    def test_reference_format(self):
        self.assertEqual(SecretRef.parse("secretref://db/pw#3"), SecretRef("db/pw", 3))
        self.assertIsNone(SecretRef.parse("secretref://db#latest").version)
        self.assertEqual(str(SecretRef("db", None)), "secretref://db#latest")
        for bad in ("hunter2", "secretref://db", "secretref://../x#1", "secretref://db#0", "secretref://Db#1",
                    "secretref://db/#1"):
            with self.assertRaises(ValueError) as cm:
                SecretRef.parse(bad)
            self.assertNotIn(bad, str(cm.exception))

    def test_env_and_file_provider_doubles(self):
        env = EnvSecretProvider({"INV08_SECRET_DB_PW__V1": "one", "INV08_SECRET_DB_PW__V2": "two"})
        self.assertEqual(env.get("db/pw", None), ("two", 2))
        self.assertEqual(env.get("db/pw", 1), ("one", 1))
        with self.assertRaises(Inv08Error):
            env.get("db/pw", 9)
        d = Path(self.tmp) / "db"
        d.mkdir()
        f = d / "1"
        f.write_text("filesecret\n")
        os.chmod(f, 0o600)
        fp = FileSecretProvider(self.tmp)
        self.assertEqual(fp.get("db", None), ("filesecret", 1))
        if os.name == "posix":
            os.chmod(f, 0o644)
            with self.assertRaises(Inv08Error) as cm:
                fp.get("db", 1)
            self.assertEqual(cm.exception.code, "INV08.SECRET.INSECURE_FILE")

    def test_cache_ttl_and_bounds(self):
        clock = FakeClock()
        r = SecretResolver(EnvSecretProvider({"INV08_SECRET_A__V1": "aaaa"}), clock=clock, ttl=10, max_entries=1)
        r.resolve("secretref://a#1")
        r.resolve("secretref://a#1")
        self.assertEqual(r.fetches, 1)
        clock.advance(11)
        r.resolve("secretref://a#1")
        self.assertEqual(r.fetches, 2)
        r.resolve("secretref://a#latest")
        self.assertEqual(len(r._cache), 1)

    def test_redaction(self):
        r = SecretResolver(EnvSecretProvider({"INV08_SECRET_A__V1": "s3cr3tvalue"}), clock=FakeClock())
        v = r.resolve("secretref://a#1")
        self.assertNotIn("s3cr3tvalue", repr(v) + str(v) + f"{v}")
        self.assertEqual(r.scrub("conn failed with s3cr3tvalue; token=abc"), "conn failed with [REDACTED]; [REDACTED]")
        self.assertEqual(redact({"password": "x"}), {"password": "[REDACTED]"})

    def test_rotation_and_revocation_without_redeploy(self):
        clock = FakeClock()
        env = {"INV08_SECRET_A__V1": "old-value"}
        r = SecretResolver(EnvSecretProvider(env), clock=clock, ttl=5)
        self.assertEqual(r.resolve("secretref://a#latest").reveal(), "old-value")
        env["INV08_SECRET_A__V2"] = "new-value"
        clock.advance(6)
        self.assertEqual(r.resolve("secretref://a#latest").reveal(), "new-value")
        r.revoke("a", 2)
        with self.assertRaises(Inv08Error) as cm:
            r.resolve("secretref://a#latest")
        self.assertEqual(cm.exception.code, "INV08.SECRET.REVOKED")
        self.assertEqual(r.resolve("secretref://a#1").reveal(), "old-value")


# ======================================================================= 33 bootstrap
class TestBootstrap(TmpCase):
    def test_single_command_and_deterministic_rerun(self):
        root = Path(self.tmp) / "cp"
        r1 = bootstrap(root, raw_cfg(), author="a", source="s")
        r2 = bootstrap(root, raw_cfg(), author="a", source="s")
        self.assertEqual(r1["manifest_digest"], r2["manifest_digest"])
        self.assertEqual(r2["steps"]["trust"], "existing")
        self.assertEqual(r2["steps"]["config"], "existing")

    def test_trust_seeding_nonproduction_and_protected(self):
        root = Path(self.tmp) / "cp"
        r = bootstrap(root, raw_cfg(), author="a", source="s", key_source=lambda n: b"k" * n)
        self.assertFalse(r["manifest"]["trust_production"])
        self.assertTrue(r["manifest"]["trust_kid"].startswith("nonprod-"))
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE((root / "trust" / "nonprod.key").stat().st_mode), 0o600)
        self.assertNotIn("kkkk", (root / "bootstrap.json").read_text())

    def test_schema_creation(self):
        root = Path(self.tmp) / "cp"
        bootstrap(root, raw_cfg(), author="a", source="s")
        self.assertEqual(LeaseStore(root / "store" / "leases.json", create=False).keys(), [])
        self.assertEqual(Journal(root / "journal").seq, 0)

    def test_registration_and_conflict(self):
        root = Path(self.tmp) / "cp"
        bootstrap(root, raw_cfg(), author="a", source="s")
        reg = json.loads((root / "registry" / "registry.json").read_text())
        self.assertEqual(reg["registry"]["providers"], [{"kind": "cloud", "name": "cloud-a"}])
        with self.assertRaises(Inv08Error) as cm:
            bootstrap(root, raw_cfg(site="lab-2"), author="a", source="s")
        self.assertEqual(cm.exception.code, "INV08.BOOTSTRAP.CONFLICT")
        with self.assertRaises(Inv08Error):
            bootstrap(Path(self.tmp) / "x", raw_cfg(env="nope"), author="a", source="s")

    def test_disaster_path_and_cli(self):
        root = Path(self.tmp) / "cp"
        cfgp = Path(self.tmp) / "cfg.json"
        cfgp.write_text(json.dumps(raw_cfg()))
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(bootstrap_main([str(root), str(cfgp), "--author", "a", "--source", "s"]), 0)
        (root / "store" / "leases.json").write_text("{garbage")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(bootstrap_main([str(root), str(cfgp), "--author", "a", "--source", "s"]), 2)
        r = bootstrap(root, raw_cfg(), author="a", source="s", disaster=True)
        self.assertEqual(r["steps"]["store_recovered"], "INV08.STORE.CORRUPT")
        self.assertEqual(len(r["quarantined"]), 1)
        LeaseStore(root / "store" / "leases.json")


# ======================================================================= 41 health
class TestHealth(TmpCase):
    def test_heartbeat_liveness(self):
        c = FakeClock()
        hb = Heartbeats(c, interval=10, miss_threshold=3)
        self.assertEqual(hb.check("ctl").status, UNHEALTHY)
        hb.beat("ctl")
        self.assertEqual(hb.check("ctl").status, HEALTHY)
        c.advance(10)
        self.assertEqual(hb.check("ctl").status, HEALTHY)          # boundary
        c.advance(1)
        self.assertEqual(hb.check("ctl").status, DEGRADED)
        c.advance(20)
        self.assertEqual(hb.check("ctl").status, UNHEALTHY)
        with self.assertRaises(ValueError):
            Heartbeats(c, interval=0)

    def test_stuck_operation_detector(self):
        e = Env(self.tmp, crash_hook=crash_at("create:after_pending"))
        with self.assertRaises(Crash):
            e.ctl.reconcile(4)
        self.assertEqual(stuck_ops(e.journal, e.clock(), 60).status, HEALTHY)
        chk = stuck_ops(e.journal, e.clock() + 61, 60)
        self.assertEqual(chk.status, UNHEALTHY)
        self.assertIn("create:node-1:1", chk.detail)

    def test_dependency_health(self):
        c = FakeClock()
        dh = DependencyHealth(window=10)
        for _ in range(10):
            dh.record("prov", True)
        self.assertEqual(dh.check("prov").status, HEALTHY)
        for _ in range(3):
            dh.record("prov", False)
        self.assertEqual(dh.check("prov").status, DEGRADED)
        for _ in range(3):
            dh.record("prov", False)
        self.assertEqual(dh.check("prov").status, UNHEALTHY)
        br = CircuitBreaker("x", clock=c, failure_threshold=1)
        with self.assertRaises(Inv08Error):
            br.call(lambda: (_ for _ in ()).throw(Inv08Error("INV08.PROVIDER.RETRYABLE", "x",
                                                              outcome=__import__("inv08_dynamic_infrastructure_model.production.core", fromlist=["Outcome"]).Outcome.RETRYABLE_FAILURE)))
        self.assertEqual(DependencyHealth().check("new", br).status, UNHEALTHY)

    def test_lease_store_health_and_lag(self):
        s = LeaseStore(Path(self.tmp) / "s.json")
        self.assertEqual(lease_store_health(s, 0, 5).status, DEGRADED)
        s.acquire("k", "a", now=100, ttl=10)
        self.assertEqual(lease_store_health(s, 104, 5).status, HEALTHY)
        self.assertEqual(lease_store_health(s, 106, 5).status, DEGRADED)
        s.available = False
        self.assertEqual(lease_store_health(s, 106, 5).status, UNHEALTHY)

    def test_aggregation_with_remediation(self):
        agg = aggregate([Check("a", HEALTHY, ""), Check("b", DEGRADED, "", "do x")])
        self.assertEqual(agg["status"], DEGRADED)
        self.assertEqual(agg["remediation"], ["b: do x"])
        self.assertEqual(aggregate([])["status"], UNHEALTHY)


# ======================================================================= 42 resilience
def _retryable():
    from ..core import Outcome
    return Inv08Error("INV08.PROVIDER.RETRYABLE", "x", outcome=Outcome.RETRYABLE_FAILURE)


class TestResilience(unittest.TestCase):
    def test_bounded_retry(self):
        c = FakeClock()
        calls = []

        def fn():
            calls.append(1)
            raise _retryable()
        with self.assertRaises(Inv08Error) as cm:
            call_with_retry(fn, policy=RetryPolicy(max_attempts=3), rng=random.Random(0), clock=c, sleep=c.sleep)
        self.assertEqual(len(calls), 3)
        self.assertEqual(cm.exception.code, "INV08.RETRY.EXHAUSTED")
        self.assertEqual(cm.exception.cause.code, "INV08.PROVIDER.RETRYABLE")
        calls.clear()

        def term():
            calls.append(1)
            raise ValueError("boom")
        with self.assertRaises(Inv08Error) as cm:
            call_with_retry(term, policy=RetryPolicy(), rng=random.Random(0), clock=c, sleep=c.sleep)
        self.assertEqual((len(calls), cm.exception.code), (1, "INV08.PROVIDER.TERMINAL"))
        with self.assertRaises(ValueError):
            RetryPolicy(max_attempts=0)
        seq = iter([_retryable(), None])

        def flaky():
            e = next(seq)
            if e:
                raise e
            return "ok"
        self.assertEqual(call_with_retry(flaky, policy=RetryPolicy(), rng=random.Random(0), clock=c,
                                         sleep=c.sleep), "ok")

    def test_backoff_full_jitter_deterministic(self):
        p = RetryPolicy(base_delay=1, max_delay=8)
        a = [p.backoff(i, random.Random(7)) for i in range(1, 8)]
        b = [p.backoff(i, random.Random(7)) for i in range(1, 8)]
        self.assertEqual(a, b)
        rng = random.Random(3)
        for i in range(1, 12):
            self.assertLessEqual(p.backoff(i, rng), min(8, 2 ** (i - 1)))
        with self.assertRaises(ValueError):
            p.backoff(0, rng)
        c = FakeClock(0)
        with self.assertRaises(Inv08Error):
            call_with_retry(lambda: (_ for _ in ()).throw(_retryable()),
                            policy=RetryPolicy(max_attempts=20, base_delay=1, max_delay=10, max_elapsed=15),
                            rng=random.Random(0), clock=c, sleep=c.sleep)
        self.assertLessEqual(c(), 15)

    def test_circuit_breaker_state_machine(self):
        c = FakeClock(0)
        br = CircuitBreaker("p", clock=c, failure_threshold=2, reset_timeout=10, half_open_successes=1)

        def fail():
            raise _retryable()
        for _ in range(2):
            with self.assertRaises(Inv08Error):
                br.call(fail)
        self.assertEqual(br.state, "OPEN")
        with self.assertRaises(Inv08Error) as cm:
            br.call(lambda: 1)
        self.assertEqual(cm.exception.code, "INV08.CIRCUIT.OPEN")
        c.advance(10)
        self.assertEqual(br.current_state(), "HALF_OPEN")
        with self.assertRaises(Inv08Error):
            br.call(fail)
        self.assertEqual(br.state, "OPEN")
        c.advance(10)
        self.assertEqual(br.call(lambda: 5), 5)
        self.assertEqual(br.state, "CLOSED")
        self.assertEqual(br.transitions, [("CLOSED", "OPEN"), ("OPEN", "HALF_OPEN"), ("HALF_OPEN", "OPEN"),
                                          ("OPEN", "HALF_OPEN"), ("HALF_OPEN", "CLOSED")])

    def test_load_shedding(self):
        c = FakeClock(0)
        adm = AdmissionController(clock=c, rate=1, burst=4, max_in_flight=10, reserve=2)
        adm.admit(1)
        adm.admit(1)
        with self.assertRaises(Inv08Error) as cm:
            adm.admit(1)
        self.assertEqual(cm.exception.code, "INV08.ADMISSION.SHED")
        adm.admit(0)                          # critical uses the reserve
        c.advance(2)
        adm.admit(1)
        self.assertEqual(adm.shed, 1)
        for _ in range(4):
            adm.release()
        with self.assertRaises(RuntimeError):
            adm.release()

    def test_retry_storm_and_recovery(self):
        c = FakeClock(0)
        budget = RetryBudget(ratio=0.1, min_retries=2)
        br = CircuitBreaker("p", clock=c, failure_threshold=50, reset_timeout=5)
        attempts = [0]
        up = [False]

        def dep():
            attempts[0] += 1
            if not up[0]:
                raise _retryable()
            return "ok"
        for _ in range(50):
            try:
                call_with_retry(dep, policy=RetryPolicy(max_attempts=5), rng=random.Random(0), clock=c,
                                sleep=c.sleep, budget=budget, breaker=br)
            except Inv08Error:
                pass
        # 50 callers x 5 attempts would be 250 calls without the budget/breaker.
        self.assertLess(attempts[0], 70)
        up[0] = True
        c.advance(10)
        self.assertEqual(call_with_retry(dep, policy=RetryPolicy(), rng=random.Random(0), clock=c,
                                         sleep=c.sleep, breaker=br), "ok")


# ======================================================================= 43 leader / fencing
class TestLeader(TmpCase):
    def setUp(self):
        super().setUp()
        self.c = FakeClock(0)
        self.store = LeaseStore(Path(self.tmp) / "s.json")

    def test_election_and_failover(self):
        a = LeaderElector(self.store, "a", clock=self.c, ttl=10, safety=1)
        b = LeaderElector(self.store, "b", clock=self.c, ttl=10, safety=1)
        la = a.try_acquire()
        self.assertTrue(a.is_leader())
        self.assertIsNone(b.try_acquire())
        self.c.advance(9.5)
        self.assertFalse(a.is_leader())       # safety margin: stop acting before expiry
        self.c.advance(1)
        lb = b.try_acquire()
        self.assertGreater(lb.epoch, la.epoch)
        with self.assertRaises(Inv08Error):
            a.require()
        b.step_down()
        self.assertIsNotNone(a.try_acquire())
        with self.assertRaises(ValueError):
            LeaderElector(self.store, "", clock=self.c)

    def test_monotonic_fencing_tokens(self):
        tokens = []
        for i in range(5):
            e = LeaderElector(self.store, f"n{i}", clock=self.c, ttl=1, safety=0)
            tokens.append(e.try_acquire().epoch)
            self.c.advance(2)
        self.assertEqual(tokens, sorted(set(tokens)))
        g = FenceGate("t")
        g.admit(3)
        with self.assertRaises(Inv08Error):
            g.admit(2)
        for bad in (0, True, "3"):
            with self.assertRaises(Inv08Error):
                g.admit(bad)

    def test_duplicate_controller_prevented(self):
        e = Env(self.tmp)
        e.ctl.reconcile(8)
        dup = Controller(Pool(**POOL), e.inner, Journal(Path(self.tmp) / "j2"),
                         LeaderElector(e.store, "ctl-b", clock=e.clock, ttl=30), clock=e.clock)
        self.assertEqual(dup.reconcile(100)["reason"], "not leader")

    def test_split_brain_detection(self):
        a = LeaderElector(self.store, "a", clock=self.c, ttl=5, safety=0)
        la = a.try_acquire()
        self.c.advance(6)                      # a paused (GC/partition) past its lease
        b = LeaderElector(self.store, "b", clock=self.c, ttl=5, safety=0)
        lb = b.try_acquire()
        rep = detect_split_brain(self.store, [la, lb])
        self.assertEqual((rep["winner"], rep["must_step_down"]), ("b", ["a"]))
        self.assertFalse(detect_split_brain(self.store, [lb])["split_brain"])

    def test_stale_writer_rejected_at_store_and_provider(self):
        a = LeaderElector(self.store, "a", clock=self.c, ttl=5, safety=0)
        la = a.try_acquire()
        self.c.advance(6)
        lb = LeaderElector(self.store, "b", clock=self.c, ttl=5, safety=0).try_acquire()
        with self.assertRaises(Inv08Error) as cm:
            self.store.check_fence(LEADER_KEY, la.epoch)
        self.assertEqual(cm.exception.code, "INV08.FENCE.STALE")
        p = ad.make_provider("cloud")
        p.create("n1", {}, idempotency_key="b1", fence=lb.epoch)
        with self.assertRaises(Inv08Error) as cm:
            p.delete("n1", idempotency_key="a1", fence=la.epoch)
        self.assertEqual(cm.exception.code, "INV08.FENCE.STALE")
        self.assertIn("n1", p.list())


# ======================================================================= 44 journal / recovery
class TestJournal(TmpCase):
    def _fill(self, j, n):
        for i in range(n):
            j.append(f"create:n{i}:1", "PENDING", kind="create", node_id=f"n{i}", ts=i)
            j.append(f"create:n{i}:1", "DONE", kind="create", node_id=f"n{i}", ts=i)

    def test_durable_journal_replay(self):
        j = Journal(self.tmp)
        self._fill(j, 3)
        j2 = Journal(self.tmp)
        self.assertEqual(j2.state, j.state)
        self.assertEqual(j2.seq, 6)
        with self.assertRaises(ValueError):
            j2.append("x", "WEIRD", kind="create", node_id="n", ts=0)

    def test_snapshots_and_compaction(self):
        j = Journal(self.tmp, keep=2)
        self._fill(j, 2)
        j.snapshot()
        self._fill(j, 1)
        j.snapshot()
        self._fill(j, 1)
        j.snapshot()
        self.assertEqual(len(list(Path(self.tmp).glob("snap-*.json"))), 2)
        j2 = Journal(self.tmp)
        self.assertEqual(j2.state, j.state)
        self.assertEqual(j2.recovery_report["snapshot"], "snap-000000000008.json")

    def test_replay_cursor(self):
        j = Journal(self.tmp)
        self._fill(j, 2)
        j.snapshot()
        self._fill(j, 1)
        j2 = Journal(self.tmp)
        self.assertEqual((j2.recovery_report["cursor"], j2.recovery_report["replayed"]), (4, 2))

    def test_restart_reconciliation_against_provider(self):
        e = Env(self.tmp, crash_hook=crash_at("create:after_call"))
        with self.assertRaises(Crash):
            e.ctl.reconcile(8)
        self.assertIn("node-1", e.inner.list())            # side effect happened, DONE not written
        before = dict(e.journal.state)
        ctl = e.restart()
        rep = ctl.reconcile(8)
        self.assertIn("create:node-1:1", rep["recovered"])
        self.assertTrue(rep["converged"])
        self.assertEqual(sorted(e.inner.list()), ["node-1", "node-2"])
        self.assertEqual(rpo_lost_ops(before, ctl.journal.state), [])

    def test_torn_tail_truncated_and_mid_corruption_refused(self):
        j = Journal(self.tmp)
        self._fill(j, 2)
        wal = Path(self.tmp) / "wal.jsonl"
        with open(wal, "ab") as fh:
            fh.write(b'{"seq":5,"op_i')
        j2 = Journal(self.tmp)
        self.assertEqual(j2.seq, 4)
        self.assertGreater(j2.recovery_report["truncated_tail_bytes"], 0)
        j2.append("x:1", "PENDING", kind="create", node_id="x", ts=9)
        lines = wal.read_bytes().splitlines()
        lines[1] = lines[1].replace(b"DONE", b"FAIL")
        wal.write_bytes(b"\n".join(lines) + b"\n")
        with self.assertRaises(Inv08Error) as cm:
            Journal(self.tmp)
        self.assertEqual(cm.exception.code, "INV08.JOURNAL.CORRUPT")

    def test_corrupt_snapshot_falls_back(self):
        j = Journal(self.tmp, keep=2)
        self._fill(j, 1)
        j.snapshot()
        self._fill(j, 1)
        latest = j.snapshot()
        latest.write_text("{}")
        j2 = Journal(self.tmp)
        self.assertEqual(j2.recovery_report["snapshots_rejected"], [latest.name])
        self.assertEqual(j2.state, j.state)


# ======================================================================= 45 controls
class TestControls(TmpCase):
    def setUp(self):
        super().setUp()
        self.clock = FakeClock()
        self.audit_path = Path(self.tmp) / "audit.jsonl"
        self.audit = AuditLog(self.audit_path)
        self.ctrl = Controls(self.audit, {"op-1": "operator", "lead-1": "sre_lead", "lead-2": "sre_lead"},
                             clock=self.clock)
        self.env = Env(Path(self.tmp), controls=self.ctrl, clock=self.clock)

    def test_quarantine_api(self):
        self.env.ctl.reconcile(8)
        self.ctrl.quarantine("op-1", "node-1", "suspected compromise")
        rep = self.env.ctl.reconcile(8)
        self.assertIn("drain:node-1:1", rep["ops"])
        self.assertEqual(self.env.inner.list()["node-1"]["state"], "DRAINING")
        self.clock.advance(1)
        rep = self.env.ctl.reconcile(0)
        self.assertIn("node-1", self.env.inner.list())      # never deleted while quarantined
        self.assertNotIn("node-1", rep["desired"])

    def test_freeze(self):
        self.env.ctl.reconcile(4)
        self.ctrl.freeze("op-1", "site:test-site", "change window")
        rep = self.env.ctl.reconcile(24)
        self.assertTrue(rep["frozen"])
        self.assertEqual(len(self.env.inner.list()), 1)
        with self.assertRaises(ValueError):
            self.ctrl.freeze("op-1", "bogus", "x")

    def test_kill_switch(self):
        self.ctrl.kill("lead-1", "runaway scaling")
        rep = self.env.ctl.reconcile(24)
        self.assertEqual(rep["outcome"], "BLOCKED")
        self.assertEqual(self.env.inner.calls, [])

    def test_authz_and_break_glass(self):
        with self.assertRaises(Inv08Error) as cm:
            self.ctrl.kill("op-1", "x")
        self.assertEqual(cm.exception.code, "INV08.AUTHZ.DENIED")
        with self.assertRaises(ValueError):
            self.ctrl.break_glass("op-1", "  ", 60)
        with self.assertRaises(ValueError):
            self.ctrl.break_glass("op-1", "incident", 99999)
        self.ctrl.break_glass("op-1", "incident 42", 60)
        self.ctrl.kill("op-1", "incident 42")
        self.clock.advance(61)
        with self.assertRaises(Inv08Error):
            self.ctrl.unkill("op-1", "lead-1")
        with self.assertRaises(ValueError):
            Controls(self.audit, {"x": "god"}, clock=self.clock)

    def test_safe_thaw_and_audit_trail(self):
        self.ctrl.quarantine("op-1", "node-9", "bad disk")
        with self.assertRaises(Inv08Error):
            self.ctrl.unquarantine("lead-1", "node-9", lambda n: False)
        self.ctrl.unquarantine("lead-1", "node-9", lambda n: True)
        self.ctrl.freeze("op-1", "global", "x")
        with self.assertRaises(Inv08Error):
            self.ctrl.thaw("lead-1", "global", lambda: False)
        self.ctrl.thaw("lead-1", "global", lambda: True)
        self.ctrl.kill("lead-1", "x")
        with self.assertRaises(Inv08Error):
            self.ctrl.unkill("lead-1", "lead-1")
        self.ctrl.unkill("lead-1", "lead-2")
        self.assertFalse(self.ctrl.is_killed())
        ok, problems, entries = verify_file(self.audit_path)
        self.assertTrue(ok, problems)
        self.assertEqual([e["outcome"] for e in entries].count("REFUSED"), 2)


# ======================================================================= 46 faults
class TestFaults(TmpCase):
    def test_provider_fault_injection(self):
        clock = FakeClock()
        inner = ad.make_provider("cloud")
        plan = FaultPlan([Fault("create", "transient", count=2), Fault("list", "latency", count=1, latency=3)])
        e = Env(self.tmp, provider=FaultyProvider(inner, plan, clock), clock=clock)
        e.inner = inner
        rep = e.ctl.reconcile(4)
        self.assertTrue(rep["converged"])
        self.assertEqual(plan.fired, [("list", "latency"), ("create", "transient"), ("create", "transient")])
        with self.assertRaises(ValueError):
            Fault("create", "meteor")

    def test_lost_response_no_duplicate(self):
        clock = FakeClock()
        inner = ad.make_provider("cloud")
        plan = FaultPlan([Fault("create", "lost_response", count=1)])
        e = Env(self.tmp, provider=FaultyProvider(inner, plan, clock), clock=clock)
        e.inner = inner
        self.assertTrue(e.ctl.reconcile(8)["converged"])
        self.assertEqual(sorted(inner.list()), ["node-1", "node-2"])
        self.assertEqual([c for c in inner.calls if c == ("create", "node-1")], [("create", "node-1")] * 2)

    def test_process_crash_restart_injection(self):
        for point in ("create:after_pending", "create:after_call", "delete:after_drain"):
            with tempfile.TemporaryDirectory() as t:
                e = Env(t)
                e.ctl.reconcile(8)
                e.ctl.crash_hook = crash_at(point)
                e.clock.advance(1)
                try:
                    e.ctl.reconcile(0 if point.startswith("delete") else 16)
                except Crash:
                    pass
                ctl = e.restart()
                n, _, rep = rounds_to_converge(ctl, 0 if point.startswith("delete") else 16, e.clock, interval=5)
                self.assertGreater(n, 0, (point, rep))

    def test_partition_latency_loss(self):
        clock = FakeClock()
        store = LeaseStore(Path(self.tmp) / "s.json")
        link = Partition(store, clock, seed=4)
        e = Env(self.tmp, store=link, clock=clock)
        self.assertTrue(e.ctl.reconcile(4)["converged"])
        link.partitioned = True
        rep = e.ctl.reconcile(40)
        self.assertEqual(rep["outcome"], "RETRYABLE_FAILURE")     # cannot confirm leadership -> no action
        self.assertEqual(len(e.inner.list()), 1)
        link.partitioned = False
        link.latency = 0.5
        link.loss = 0.3
        n, _, _ = rounds_to_converge(e.ctl, 40, clock, interval=1)
        self.assertGreater(n, 0)
        self.assertGreater(link.dropped, 0)

    def test_store_outage_injection(self):
        e = Env(self.tmp)
        e.ctl.reconcile(4)
        e.store.available = False
        rep = e.ctl.reconcile(8)
        self.assertEqual((rep["outcome"], rep["reason"]), ("RETRYABLE_FAILURE", "INV08.STORE.UNAVAILABLE"))
        self.assertFalse(e.elector.is_leader())
        e.store.available = True
        self.assertTrue(e.ctl.reconcile(8)["converged"])

    def test_rto_rpo_convergence_objectives(self):
        RTO_ROUNDS, RTO_SECONDS = 3, 60
        e = Env(self.tmp)
        e.ctl.reconcile(8)
        e.ctl.crash_hook = crash_at("create:after_call")
        e.clock.advance(1)
        with self.assertRaises(Crash):
            e.ctl.reconcile(20)
        before = json.loads(json.dumps(e.journal.state))
        e.clock.advance(31)                     # old leader lease (ttl 30) expires
        ctl = e.restart()
        n, secs, rep = rounds_to_converge(ctl, 20, e.clock, interval=10)
        self.assertTrue(0 < n <= RTO_ROUNDS, rep)
        self.assertLessEqual(secs, RTO_SECONDS)
        self.assertEqual(rpo_lost_ops(before, ctl.journal.state), [])
        self.assertEqual(len(e.inner.list()), 5)


if __name__ == "__main__":
    unittest.main()
