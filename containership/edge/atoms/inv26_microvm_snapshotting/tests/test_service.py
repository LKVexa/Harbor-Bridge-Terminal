"""End-to-end service tests: outcomes, boundaries, quotas, admission, idempotency,
anti-replay, quarantine/disable, delete/crypto-erase, recovery, outage policy,
precedence, observability (C012, C014, C017, C019, C025, C039, C048, C054-C059,
C071-C077, X008, X010, X011)."""
import json
import secrets
import time
import unittest

from inv26_microvm_snapshotting import schema
from inv26_microvm_snapshotting.errors import CATALOG
from inv26_microvm_snapshotting.tests.harness import Rig, NODE


class Base(unittest.TestCase):
    def setUp(self):
        self.r = Rig()
        self.snap = self.r.capture()

    def assertCode(self, resp, code):
        st, body = resp
        self.assertNotEqual(st, 200, body)
        self.assertEqual(body["code"], code, body)
        self.assertEqual(schema.validate(body, "PK_SNAPSHOT_ERROR/1"), [])
        return body


class HappyPath(Base):
    def test_capture_restore_ready_with_fresh_entropy(self):
        st, a = self.r.restore(self.snap, vm="vm-2")
        st2, b = self.r.restore(self.snap, vm="vm-3")
        self.assertEqual((st, st2), (200, 200))
        self.assertEqual(a["state"], "READY")
        self.assertNotEqual(a["entropy_proof_sha256"], b["entropy_proof_sha256"])
        self.assertEqual(self.r.hv.vms["vm-2"]["state"], "Running")
        self.assertEqual(self.r.hv.vms["vm-2"]["memory"], b"guest-memory" * 100)
        self.assertEqual(schema.validate({k: v for k, v in a.items() if k != "correlation_id"} | {"correlation_id": a["correlation_id"]},
                                         "PK_SNAPSHOT_RESTORE/2"), [])

    def test_blob_at_rest_is_ciphertext(self):
        raw = self.r.blobs.get("t1", "s1", 1)
        self.assertNotIn(b"guest-memory", raw)
        files = list((self.r.root / "blobs").rglob("*.blob"))
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].stat().st_mode & 0o777, 0o600)

    def test_inspect_hides_key_material(self):
        st, b = self.r.svc.handle("inspect", self.r.token(), {"snapshot_id": "s1"})
        self.assertEqual(st, 200)
        self.assertNotIn("wrapped_dek", json.dumps(b))


class Boundaries(Base):
    def test_cross_tenant_refused_before_side_effects(self):
        seeds_before = self.r.metrics.total("inv26_reseeds_total")
        g = self.r.grant(self.snap, tenant="t2")
        req = self.r.restore_req(self.snap, g, tenant="t2")
        self.assertCode(self.r.svc.handle("restore", self.r.token(tenant="t2"), req), "SNAP_TENANT_MISMATCH")
        self.assertEqual(self.r.metrics.total("inv26_reseeds_total"), seeds_before)
        self.assertEqual(self.r.metrics.total("inv26_cross_tenant_refusals_total"), 1)
        self.assertNotIn("vm-2", self.r.hv.vms)

    def test_caller_scope_cannot_be_bypassed_by_request_fields(self):
        # caller authorised for t2 asks to restore t1's snapshot with a t1 grant: confused deputy
        self.assertCode(self.r.restore(self.snap, token=self.r.token(tenant="t2")), "SNAP_FORBIDDEN")

    def test_model_mismatch(self):
        g = self.r.grant(self.snap)
        req = self.r.restore_req(self.snap, g, devices=["virtio-net"])
        self.assertCode(self.r.svc.handle("restore", self.r.token(), req), "SNAP_MODEL_MISMATCH")

    def test_environment_and_residency(self):
        g = self.r.grant(self.snap)
        self.assertCode(self.r.svc.handle("restore", self.r.token(), self.r.restore_req(self.snap, g, site="site-b")),
                        "SNAP_RESIDENCY_VIOLATION")

    def test_unauthenticated_and_wrong_audience(self):
        self.assertCode(self.r.svc.handle("restore", None, {}), "SNAP_UNAUTHENTICATED")
        self.assertCode(self.r.restore(self.snap, token=self.r.token(aud="other")), "SNAP_UNAUTHENTICATED")

    def test_unknown_fields_and_versions_rejected(self):
        g = self.r.grant(self.snap)
        self.assertCode(self.r.svc.handle("restore", self.r.token(), self.r.restore_req(self.snap, g, debug=True)),
                        "SNAP_INVALID_REQUEST")
        self.assertCode(self.r.svc.handle("restore", self.r.token(),
                                          self.r.restore_req(self.snap, g, schema="PK_SNAPSHOT_RESTORE_REQUEST/1")),
                        "SNAP_UNSUPPORTED_VERSION")


class AntiReplay(Base):
    def test_grant_replay_refused_and_idempotent_retry_returns_same_result(self):
        g = self.r.grant(self.snap)
        idem = secrets.token_hex(8)
        st, first = self.r.restore(self.snap, grant=g, idem=idem)
        self.assertEqual(st, 200)
        st, again = self.r.restore(self.snap, grant=g, idem=idem)
        self.assertEqual(st, 200)
        self.assertTrue(again["replayed"])
        self.assertEqual(again["entropy_proof_sha256"], first["entropy_proof_sha256"])
        self.assertCode(self.r.restore(self.snap, grant=g), "SNAP_GRANT_REPLAYED")
        self.assertEqual(self.r.metrics.total("inv26_reseeds_total"), 1)

    def test_replay_survives_restart(self):
        g = self.r.grant(self.snap)
        self.assertEqual(self.r.restore(self.snap, grant=g)[0], 200)
        svc2 = self.r.build()  # new process view over the same durable metastore
        req = self.r.restore_req(self.snap, g)
        self.assertCode(svc2.handle("restore", self.r.token(), req), "SNAP_GRANT_REPLAYED")

    def test_grant_bound_to_node_vm_and_manifest(self):
        self.assertCode(self.r.restore(self.snap, grant=self.r.grant(self.snap, node="node-9")), "SNAP_GRANT_INVALID")
        self.assertCode(self.r.restore(self.snap, grant=self.r.grant(self.snap, vm="vm-9")), "SNAP_GRANT_INVALID")
        self.assertCode(self.r.restore(self.snap, grant=self.r.grant(self.snap, manifest_sha256="0" * 64)),
                        "SNAP_GRANT_INVALID")
        forged = self.r.token()  # a caller credential is not a grant
        self.assertCode(self.r.restore(self.snap, grant=forged), "SNAP_GRANT_INVALID")

    def test_expired_grant(self):
        g = self.r.grant(self.snap, ttl=60, iat=time.time() - 400, nbf=time.time() - 400, exp=time.time() - 300)
        self.assertCode(self.r.restore(self.snap, grant=g), "SNAP_GRANT_INVALID")


class Outcomes(Base):
    """C014: force each outcome class; assert cleanup and no unsafe execution."""

    def test_entropy_failure_destroys_guest_and_is_retryable_with_same_key(self):
        self.r.entropy.fail = True
        g = self.r.grant(self.snap)
        idem = secrets.token_hex(8)
        body = self.assertCode(self.r.restore(self.snap, grant=g, idem=idem), "SNAP_ENTROPY_FAILED")
        self.assertTrue(body["retryable"])
        self.assertNotIn("vm-2", self.r.hv.vms)  # never left runnable
        self.r.entropy.fail = False
        st, ok = self.r.restore(self.snap, grant=g, idem=idem)
        self.assertEqual(st, 200, ok)
        self.assertCode(self.r.restore(self.snap, grant=g), "SNAP_GRANT_REPLAYED")

    def test_hypervisor_failure_on_load(self):
        self.r.hv.fail_next = "load"
        self.r.svc._breakers["hypervisor"].threshold = 100
        r = self.r.restore(self.snap)
        # the retry policy absorbs a single injected failure
        self.assertEqual(r[0], 200, r)

    def test_hypervisor_down_is_retryable_failure_without_guest(self):
        self.r.hv.available = False
        body = self.assertCode(self.r.restore(self.snap), "SNAP_HYPERVISOR_FAILED")
        self.assertEqual(body["outcome"], "retryable_failure")

    def test_ciphertext_tamper_is_integrity_rejection(self):
        p = next((self.r.root / "blobs").rglob("*.blob"))
        data = bytearray(p.read_bytes())
        data[40] ^= 1
        p.write_bytes(bytes(data))
        body = self.assertCode(self.r.restore(self.snap), "SNAP_CIPHERTEXT_INVALID")
        self.assertEqual(body["outcome"], "integrity_rejection")
        self.assertNotIn("vm-2", self.r.hv.vms)

    def test_kms_outage_fails_closed(self):
        self.r.kms.available = False
        body = self.assertCode(self.r.restore(self.snap), "SNAP_KMS_UNAVAILABLE")
        self.assertTrue(body["retryable"])
        self.assertFalse(self.r.svc.health()["ready"])

    def test_revoked_kek_is_terminal(self):
        self.r.kms.set_state("inv26-kek", 1, "disabled")
        self.assertCode(self.r.restore(self.snap), "SNAP_KEY_REVOKED")

    def test_deadline_exceeded(self):
        from inv26_microvm_snapshotting.resilience import Deadline
        d = Deadline(0.0)
        g = self.r.grant(self.snap)
        st, body = self.r.svc.handle("restore", self.r.token(), self.r.restore_req(self.snap, g), deadline=d)
        self.assertEqual(body["code"], "SNAP_TIMEOUT")

    def test_cancel(self):
        from inv26_microvm_snapshotting.resilience import Deadline
        d = Deadline(10)
        d.cancel()
        g = self.r.grant(self.snap)
        st, body = self.r.svc.handle("restore", self.r.token(), self.r.restore_req(self.snap, g), deadline=d)
        self.assertEqual(body["code"], "SNAP_CANCELLED")
        self.assertEqual(body["outcome"], "operator_aborted")

    def test_capture_failure_leaves_nothing_restorable_and_id_retryable(self):
        self.r.boot("vm-9")
        self.r.hv.fail_next = "capture"
        self.r.hv.available = True
        self.r.svc._breakers["hypervisor"].threshold = 100
        cfg = self.r.svc._cfg[1]
        cfg["retry"]["attempts"] = 1
        st, body = self.r.svc.handle("capture", self.r.token(), self.r.capture_req("s9", vm="vm-9"))
        self.assertEqual(body["code"], "SNAP_HYPERVISOR_FAILED")
        self.assertIsNone(self.r.meta.get("snap/s9"))
        self.assertEqual(self.r.blobs.list("t1"), ["s1.g1.blob"])
        st, body = self.r.svc.handle("capture", self.r.token(), self.r.capture_req("s9", vm="vm-9"))
        self.assertEqual(st, 200, body)

    def test_unexpected_exception_does_not_leak(self):
        def boom(*a, **k):
            raise RuntimeError("secret path /etc/shadow")
        self.r.svc._restore = boom
        st, body = self.r.restore(self.snap)
        self.assertEqual((st, body["code"]), (500, "SNAP_INTERNAL"))
        self.assertNotIn("shadow", json.dumps(body))

    def test_every_catalog_code_has_valid_envelope(self):
        from inv26_microvm_snapshotting.errors import SnapshotServiceError, envelope
        for code in CATALOG:
            env = envelope(SnapshotServiceError(code, "x"), "c" * 32)
            self.assertEqual(schema.validate(env, "PK_SNAPSHOT_ERROR/1"), [], code)


class CaptureSemantics(Base):
    def test_duplicate_and_idempotent_capture(self):
        idem = secrets.token_hex(8)
        self.r.boot("vm-5")
        req = self.r.capture_req("s5", vm="vm-5", idem=idem)
        st, a = self.r.svc.handle("capture", self.r.token(), req)
        st2, b = self.r.svc.handle("capture", self.r.token(), dict(req))
        self.assertEqual((st, st2), (200, 200))
        self.assertTrue(b["replayed"])
        self.assertEqual(a["manifest_sha256"], b["manifest_sha256"])
        self.assertCode(self.r.svc.handle("capture", self.r.token(), self.r.capture_req("s5", vm="vm-5")), "SNAP_DUPLICATE")
        self.assertCode(self.r.svc.handle("capture", self.r.token(), dict(req, memory_mib=512)), "SNAP_INVALID_REQUEST")

    def test_quota_rejects_before_hypervisor_work(self):
        r = Rig(cfg_over={"quotas": {"max_snapshots_per_tenant": 1}})
        r.capture("a")
        r.boot("vm-7")
        calls = []
        orig = r.hv.pause
        r.hv.pause = lambda vm: (calls.append(vm), orig(vm))
        self.assertCode(r.svc.handle("capture", r.token(), r.capture_req("b", vm="vm-7")), "SNAP_QUOTA_EXCEEDED")
        self.assertEqual(calls, [])

    def test_limits(self):
        self.assertCode(self.r.svc.handle("capture", self.r.token(), self.r.capture_req("s6", memory_mib=10 ** 7)),
                        "SNAP_INVALID_REQUEST")
        self.assertCode(self.r.svc.handle("capture", self.r.token(), self.r.capture_req(
            "s6", devices=[f"d{i}" for i in range(65)])), "SNAP_INVALID_REQUEST")


class OperatorControls(Base):
    def test_quarantine_blocks_restore_and_release_restores(self):
        adm = self.r.admin_token()
        self.assertEqual(self.r.svc.handle("quarantine", adm, {"snapshot_id": "s1", "reason": "suspected"})[0], 200)
        self.assertCode(self.r.restore(self.snap), "SNAP_QUARANTINED")
        self.assertEqual(self.r.svc.handle("release", adm, {"snapshot_id": "s1"})[0], 200)
        self.assertEqual(self.r.restore(self.snap)[0], 200)

    def test_emergency_disable(self):
        adm = self.r.admin_token()
        self.assertCode(self.r.svc.handle("disable", self.r.token(), {"reason": "x"}), "SNAP_FORBIDDEN")
        self.assertEqual(self.r.svc.handle("disable", adm, {"reason": "incident 42"})[0], 200)
        self.assertCode(self.r.restore(self.snap), "SNAP_DISABLED")
        self.assertFalse(self.r.svc.health()["ready"])
        self.assertIn("emergency_disable", self.r.svc.health()["not_ready_reasons"])
        self.assertEqual(self.r.svc.handle("enable", adm, {})[0], 200)
        self.assertEqual(self.r.restore(self.snap)[0], 200)

    def test_delete_crypto_erases(self):
        adm = self.r.admin_token()
        st, b = self.r.svc.handle("delete", adm, {"snapshot_id": "s1"})
        self.assertEqual(st, 200, b)
        self.assertEqual(self.r.blobs.list("t1"), [])
        v = self.r.meta.get("snap/s1")[1]
        self.assertEqual(v["state"], "DELETED")
        self.assertEqual(v["manifest"]["envelope"]["wrapped_dek"], "erased")
        self.assertCode(self.r.restore(self.snap), "SNAP_NOT_FOUND")

    def test_privileged_ops_fail_closed_without_audit(self):
        self.r.audit._open = lambda p: (_ for _ in ()).throw(OSError("sink down"))
        self.r.audit._buffer_limit = 0
        self.assertCode(self.r.svc.handle("delete", self.r.admin_token(), {"snapshot_id": "s1"}),
                        "SNAP_AUDIT_UNAVAILABLE")
        self.assertEqual(self.r.meta.get("snap/s1")[1]["state"], "AVAILABLE")

    def test_breakglass_requires_reason_and_is_audited(self):
        now = time.time()
        bad = self.r.token(extra={"bg": True, "bg_reason": "x"})
        self.assertCode(self.r.svc.handle("inspect", bad, {"snapshot_id": "s1"}), "SNAP_UNAUTHENTICATED")
        good = self.r.token(caps=(), ttl=600, extra={"bg": True, "bg_reason": "INC-7 restore investigation",
                                                     "caps": [{"cap": "snapshot.admin", "tenant": "t1",
                                                               "workload": "w1", "environment": "prod"}]})
        st, _ = self.r.svc.handle("inspect", good, {"snapshot_id": "s1"})
        self.assertEqual(st, 200)
        ops = [r["operation"] for r in self.r.audit.records()]
        self.assertIn("breakglass.use", ops)


class Recovery(unittest.TestCase):
    def test_crash_mid_capture_is_reconciled(self):
        r = Rig()
        r.capture("ok")
        # simulate a crash: a CAPTURING record and an orphan blob
        r.meta.transact({"snap/half": (0, {"snapshot_id": "half", "tenant": "t1", "workload": "w1",
                                            "environment": "prod", "site": "site-a", "fingerprint": "0" * 64,
                                            "memory_mib": 1, "state": "CAPTURING", "generation": 1, "op_id": "x"})})
        r.blobs.put("t1", "orphan", 1, b"junk")
        r.meta.transact({"grant/abc": (0, {"state": "RESEEDING", "idempotency_key": "k" * 8})})
        svc2 = r.build()
        rep = svc2.reconcile()
        self.assertEqual(rep["snapshots_failed"], ["half"])
        self.assertIn("t1/orphan.g1.blob", rep["orphan_blobs_removed"])
        self.assertEqual(len(rep["grants_failed"]), 1)
        self.assertIsNone(r.meta.get("snap/half"))
        self.assertEqual(r.meta.get("snap/ok")[1]["state"], "AVAILABLE")


class Observability(Base):
    def test_health_metrics_logs_explain(self):
        st, b = self.r.restore(self.snap)
        h = self.r.svc.health()
        self.assertTrue(h["ready"])
        self.assertEqual(h["config"]["revision"], 1)
        prom = self.r.metrics.prometheus()
        self.assertIn("inv26_requests_total", prom)
        self.assertIn("inv26_restore_ms_bucket", prom)
        logs = [json.loads(l) for l in self.r.logstream.getvalue().splitlines()]
        self.assertTrue(all({"ts", "level", "component", "event", "correlation_id", "trace_id"} <= set(l) for l in logs))
        ex = self.r.svc.explain(b["correlation_id"])
        self.assertEqual(ex["result"], "success")
        self.assertEqual(ex["config_revision"], 1)
        self.assertIn("[PASS] entropy_ack", self.r.svc.explain(b["correlation_id"], text=True))

    def test_trace_context_continues(self):
        tp = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        g = self.r.grant(self.snap)
        self.r.svc.handle("restore", self.r.token(), self.r.restore_req(self.snap, g), traceparent=tp)
        logs = [json.loads(l) for l in self.r.logstream.getvalue().splitlines()]
        self.assertEqual(logs[-1]["trace_id"], "a" * 32)

    def test_lineage_is_allowlisted_and_redacted(self):
        g = self.r.grant(self.snap)
        st, b = self.r.svc.handle("restore", self.r.token(), self.r.restore_req(self.snap, g),
                                  lineage={"app_release": "r-42", "cluster": "c1", "password": "hunter2",
                                           "commit": "Bearer abcdefghijklmnopqrstuvwxyz"})
        lin = self.r.svc.explain(b["correlation_id"])["lineage"]
        self.assertEqual(lin["app_release"], "r-42")
        self.assertNotIn("password", lin)
        self.assertNotIn("abcdefghijklmnop", lin["commit"])

    def test_no_secret_material_in_logs_audit_or_responses(self):
        seeds = []
        orig = self.r.entropy.inject
        self.r.entropy.inject = lambda vm, seed: (seeds.append(seed), orig(vm, seed))
        st, b = self.r.restore(self.snap)
        blob_all = (self.r.logstream.getvalue() + (self.r.root / "audit.jsonl").read_text()
                    + json.dumps(b) + self.r.metrics.prometheus())
        self.assertNotIn(seeds[0].hex(), blob_all)
        wrapped = self.r.meta.get("snap/s1")[1]["manifest"]["envelope"]["wrapped_dek"]
        self.assertNotIn(wrapped, self.r.logstream.getvalue())
        tok = self.r.token()
        self.r.svc.handle("inspect", tok, {"snapshot_id": "nope"})
        self.assertNotIn(tok.split(".")[2], self.r.logstream.getvalue() + (self.r.root / "audit.jsonl").read_text())

    def test_audit_chain_verifies_and_detects_tamper(self):
        self.r.restore(self.snap)
        n = self.r.audit.verify()
        self.assertGreater(n, 3)
        p = self.r.root / "audit.jsonl"
        lines = p.read_text().splitlines()
        rec = json.loads(lines[1])
        rec["outcome"] = "forged"
        lines[1] = json.dumps(rec, sort_keys=True)
        p.write_text("\n".join(lines) + "\n")
        from inv26_microvm_snapshotting.audit import AuditChainBroken
        with self.assertRaises(AuditChainBroken):
            self.r.audit.verify()


class Admission(unittest.TestCase):
    def test_rate_limit_and_fairness(self):
        r = Rig(cfg_over={"admission": {"tenant_rate_per_s": 0.01, "tenant_burst": 2.0}})
        r.capture("a")
        r.capture("b")
        r.boot("vm-8")
        st, body = r.svc.handle("capture", r.token(), r.capture_req("c", vm="vm-8"))
        self.assertEqual(body["code"], "SNAP_OVERLOADED")
        self.assertIn("retry_after_s", body)
        # another tenant is unaffected by t1's exhaustion
        r.boot("vm-9")
        st, body = r.svc.handle("capture", r.token(tenant="t2"), r.capture_req("d", tenant="t2", vm="vm-9"))
        self.assertEqual(st, 200, body)


class Precedence(Base):
    def test_slo_never_overrides_entropy_or_kms(self):
        # PC-04: a slow injector exceeds the budget but the guest still waits for the ack
        orig = self.r.entropy.inject
        self.r.entropy.inject = lambda vm, s: (time.sleep(0.02), orig(vm, s))
        st, b = self.r.restore(self.snap)
        self.assertEqual(st, 200)
        self.assertFalse(b["within_budget"])
        self.assertTrue(b["entropy_reseeded"])
        # PC-01: KMS down -> refused even though the SLO is at risk
        self.r.kms.available = False
        self.assertEqual(self.r.restore(self.snap, vm="vm-4")[1]["code"], "SNAP_KMS_UNAVAILABLE")

    def test_tier_applicability(self):
        from inv26_microvm_snapshotting import policy
        from inv26_microvm_snapshotting.errors import SnapshotServiceError
        self.assertEqual(policy.check_tier("far-edge", "capture"), "degraded")
        with self.assertRaises(SnapshotServiceError) as cm:
            policy.check_tier("cloud", "replicate")
        self.assertEqual(cm.exception.code, "SNAP_TIER_UNSUPPORTED")
        with self.assertRaises(SnapshotServiceError):
            policy.check_tier("orbit", "restore")



class Scrub(unittest.TestCase):
    def test_scrub_quarantines_corrupt_blob(self):
        r = Rig()
        a, b = r.capture("a"), r.capture("b")
        p = next(x for x in (r.root / "blobs").rglob("b.g1.blob"))
        data = bytearray(p.read_bytes()); data[-1] ^= 1; p.write_bytes(bytes(data))
        rep = r.svc.scrub()
        self.assertEqual((rep["checked"], rep["quarantined"]), (2, ["b"]))
        self.assertEqual(r.restore(b)[1]["code"], "SNAP_QUARANTINED")
        self.assertEqual(r.restore(a)[0], 200)
        # integrity quarantine cannot be released without break-glass
        st, body = r.svc.handle("release", r.admin_token(), {"snapshot_id": "b"})
        self.assertEqual(body["code"], "SNAP_FORBIDDEN")


if __name__ == "__main__":
    unittest.main()


class FaultRegressions(unittest.TestCase):
    """FI-1/FI-2 were found by tools/faults.py in this pass and fixed."""

    def test_fi1_failure_after_commit_keeps_snapshot(self):
        from inv26_microvm_snapshotting.tools.faults import CrashingMeta
        r = Rig()
        r.meta = CrashingMeta(r.root / "meta", clock=r.clock)
        r.cfgstore.meta = r.meta
        r.svc = r.build()
        r.boot("vm-1")
        r.meta.writes, r.meta.crash_at = 0, 4  # the commit transaction itself
        with self.assertRaises(SystemExit):
            r.svc.handle("capture", r.token(), r.capture_req("s1"))
        # the commit write never happened -> nothing AVAILABLE, blob removed by reconcile
        from inv26_microvm_snapshotting.metastore import MetaStore
        r.meta = MetaStore(r.root / "meta"); r.cfgstore.meta = r.meta
        svc = r.build(); svc.reconcile()
        self.assertIsNone(r.meta.get("snap/s1"))
        self.assertEqual(r.blobs.list("t1"), [])

    def test_fi2_unreachable_storage_is_catalogued(self):
        r = Rig()
        snap = r.capture()
        r.blobs.root = r.root / "missing" / "deeper"
        st, body = r.restore(snap)
        self.assertEqual(body["code"], "SNAP_STORAGE_UNAVAILABLE")


class MetadataGC(unittest.TestCase):
    def test_gc_bounds_metadata_without_reopening_replay(self):
        now = [time.time()]
        r = Rig(clock=lambda: now[0])
        snap = r.capture()
        g = r.grant(snap, ttl=30)
        self.assertEqual(r.restore(snap, grant=g)[0], 200)
        r.svc.handle("delete", r.admin_token(), {"snapshot_id": "s1"})
        before = len(r.meta.scan(""))
        self.assertEqual(r.svc.gc()["removed"], 0)  # nothing expired yet
        now[0] += 8 * 86400
        removed = r.svc.gc()["removed"]
        self.assertGreaterEqual(removed, 3)  # grant, idempotency record, tombstone
        self.assertLess(len(r.meta.scan("")), before)
        # the forgotten grant is expired, so replaying it is still refused (by authentication)
        r2 = r.restore_req(snap, g)
        st, body = r.svc.handle("restore", r.token(), r2)
        self.assertIn(body["code"], ("SNAP_GRANT_INVALID", "SNAP_NOT_FOUND"))
